"""Populates the database with realistic demo data: ~30 candidates (uploaded and
parsed through the real CV pipeline), 5 jobs, 10 labels, applications, AI
screenings, pipeline movement, and assessments.

Run inside the backend container / venv with:
    python -m app.seed
Safe to re-run: it skips creating users/labels/jobs that already exist, but
will add a fresh batch of candidates each time it runs (duplicate detection
still applies per-candidate via email/phone).
"""

import io
import logging
import random
import uuid

import docx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.application import PipelineStage
from app.models.enums import AssessmentRecommendation, UserRole
from app.models.job import Job
from app.models.label import Label
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.models.assessment import Assessment
from app.services.candidate.candidate_service import add_label_to_candidate, log_activity
from app.services.recruitment.pipeline_service import create_application, ensure_default_stages, move_stage
from app.services.screening.screening_service import ScreeningService
from app.services.llm.factory import get_llm_service
from app.seed_data import CATEGORY_COUNTS, JOB_TEMPLATES, LABELS, LOCATIONS, PERSONA_CATEGORIES, ENGLISH_NAMES, VIETNAMESE_NAMES
from app.utils.file_storage import save_upload
from app.workers.cv_processing import process_cv_upload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

random.seed(42)


def _slugify(name: str) -> str:
    return name.lower().replace(" ", ".")


def build_cv_docx(name: str, email: str, phone: str, location: str, title: str, skills: str, company: str, category: str, summary: str) -> bytes:
    doc = docx.Document()
    doc.add_paragraph(name)
    doc.add_paragraph(email)
    doc.add_paragraph(phone)
    doc.add_paragraph(location)
    doc.add_paragraph("")
    doc.add_paragraph("SUMMARY")
    years = random.randint(2, 10)
    doc.add_paragraph(f"{title} with {years} years of experience. {summary}")
    doc.add_paragraph("")
    doc.add_paragraph("SKILLS")
    doc.add_paragraph(skills)
    doc.add_paragraph("")
    doc.add_paragraph("WORK EXPERIENCE")
    doc.add_paragraph(f"{title} at {company} (Jan 2021 - Present)")
    doc.add_paragraph(f"Delivered impactful work applying {skills} in a fast-paced team.")
    doc.add_paragraph("")
    prev_company = company + " Prior"
    doc.add_paragraph(f"{title} at {prev_company} (Jun 2016 - Dec 2020)")
    doc.add_paragraph("Contributed to core team initiatives and cross-functional projects.")
    doc.add_paragraph("")
    doc.add_paragraph("EDUCATION")
    doc.add_paragraph("Bachelor of Science, National University (2012 - 2016)")
    doc.add_paragraph("")
    doc.add_paragraph("LANGUAGES")
    doc.add_paragraph("English (Fluent), Vietnamese (Native)")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def ensure_users(db) -> None:
    users = [
        ("admin@ats.com", "admin123", "Admin User", UserRole.ADMIN),
        ("recruiter@ats.com", "recruiter123", "Recruiter One", UserRole.RECRUITER),
        ("manager@ats.com", "manager123", "Hiring Manager", UserRole.HIRING_MANAGER),
    ]
    for email, password, full_name, role in users:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            continue
        db.add(User(email=email, hashed_password=hash_password(password), full_name=full_name, role=role))
    db.commit()
    logger.info("Users ready: admin@ats.com / recruiter@ats.com / manager@ats.com (see passwords above)")


def ensure_labels(db) -> dict[str, Label]:
    result = {}
    for name, color in LABELS:
        label = db.execute(select(Label).where(Label.name == name)).scalar_one_or_none()
        if not label:
            label = Label(name=name, color=color)
            db.add(label)
            db.flush()
        result[name] = label
    db.commit()
    return result


def ensure_jobs(db) -> list[Job]:
    jobs = []
    for template in JOB_TEMPLATES:
        fields = {k: v for k, v in template.items() if k != "category"}
        job = db.execute(select(Job).where(Job.title == template["title"])).scalar_one_or_none()
        if not job:
            job = Job(**fields)
            db.add(job)
            db.flush()
            ensure_default_stages(db, job)
        job.category = template["category"]  # in-memory only, not persisted
        jobs.append(job)
    db.commit()
    return jobs


def seed_candidates(db) -> list[tuple[uuid.UUID, str]]:
    candidate_ids: list[tuple[uuid.UUID, str]] = []
    name_pool = list(zip(VIETNAMESE_NAMES, ["vn"] * len(VIETNAMESE_NAMES))) + list(
        zip(ENGLISH_NAMES, ["en"] * len(ENGLISH_NAMES))
    )
    random.shuffle(name_pool)
    name_idx = 0
    phone_counter = 900000000

    for category, count in zip(PERSONA_CATEGORIES, CATEGORY_COUNTS):
        for _ in range(count):
            name, _origin = name_pool[name_idx % len(name_pool)]
            name_idx += 1
            title = random.choice(category["titles"])
            skills = random.choice(category["skill_pools"])
            company = random.choice(category["companies"])
            location = random.choice(LOCATIONS)
            phone_counter += 1
            phone = f"0{phone_counter}"
            email = f"{_slugify(name)}{phone_counter % 1000}@example.com"

            file_bytes = build_cv_docx(
                name, email, phone, location, title, skills, company, category["category"], category["summary"]
            )
            ext = ".docx"
            file_path = save_upload(file_bytes, f"{_slugify(name)}.docx", ext)
            job = ProcessingJob(
                file_name=f"{_slugify(name)}.docx",
                file_path=file_path,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            process_cv_upload(job.id)

            db.refresh(job)
            if job.status.value == "COMPLETED" and job.candidate_id:
                candidate_ids.append((job.candidate_id, category["category"]))
            else:
                logger.warning("Seed candidate failed to process: %s (%s)", name, job.error_message)

    logger.info("Seeded %s candidates", len(candidate_ids))
    return candidate_ids


def attach_labels_and_history(db, candidate_ids: list[tuple[uuid.UUID, str]], labels: dict[str, Label], jobs: list[Job]) -> None:
    llm_service = get_llm_service()
    screening_service = ScreeningService(llm_service)
    label_names = list(labels.keys())

    for candidate_id, category in candidate_ids:
        # every candidate gets 1-2 labels
        for label_name in random.sample(label_names, k=random.choice([1, 2])):
            add_label_to_candidate(db, candidate_id, labels[label_name].id)

        # ~70% of candidates apply to a job and get screened; prefer a job matching
        # their own background most of the time so scores/recommendations look realistic
        if random.random() < 0.7:
            matching_jobs = [j for j in jobs if getattr(j, "category", None) == category]
            if matching_jobs and random.random() < 0.8:
                job = random.choice(matching_jobs)
            else:
                job = random.choice(jobs)
            from app.models.candidate import Candidate

            candidate = db.get(Candidate, candidate_id)
            try:
                application = create_application(db, candidate_id, job.id)
            except Exception:
                continue

            try:
                screening_service.screen(db, job, candidate)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Screening failed for %s: %s", candidate_id, exc)

            # move roughly half of applicants further down the pipeline
            if random.random() < 0.5:
                stages = db.execute(
                    select(PipelineStage).where(PipelineStage.job_id == job.id).order_by(PipelineStage.order)
                ).scalars().all()
                target_stage = random.choice(stages[1:5])
                move_stage(db, application, target_stage.id)

            # ~40% of applicants get an assessment
            if random.random() < 0.4:
                db.add(
                    Assessment(
                        candidate_id=candidate_id,
                        job_id=job.id,
                        interview_type=random.choice(["Phone Interview", "Technical Interview", "Final Interview"]),
                        interviewer=random.choice(["Alice Recruiter", "Bao HR", "Chris Hiring Manager"]),
                        score=round(random.uniform(5.5, 9.5), 1),
                        strengths="Strong communication and relevant experience.",
                        weaknesses="Could improve on some job-specific depth.",
                        comments="Solid candidate overall.",
                        recommendation=random.choice(list(AssessmentRecommendation)),
                    )
                )
                log_activity(db, candidate_id, "ASSESSMENT_ADDED", "Assessment recorded during seeding")
                db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        ensure_users(db)
        labels = ensure_labels(db)
        jobs = ensure_jobs(db)
        candidate_ids = seed_candidates(db)
        attach_labels_and_history(db, candidate_ids, labels, jobs)
        logger.info("Seeding complete: %s candidates, %s jobs, %s labels", len(candidate_ids), len(jobs), len(labels))
    finally:
        db.close()


if __name__ == "__main__":
    main()
