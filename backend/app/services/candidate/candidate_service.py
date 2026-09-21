import os
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application
from app.models.assessment import Assessment
from app.models.processing_job import ProcessingJob
from app.models.candidate import (
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateProject,
    CandidateSkill,
    Skill,
)
from app.models.activity import CandidateActivity
from app.models.embedding import CandidateEmbedding
from app.models.label import CandidateLabel, Label  # noqa: F401 (CandidateLabel referenced by string in Candidate model)
from app.models.screening import ScreeningResult
from app.schemas.candidate import CandidateUpdate
from app.services.cv_parser.base import ParsedCV
from app.utils.text_normalize import normalize_email, normalize_name, normalize_phone


def log_activity(
    db: Session,
    candidate_id: uuid.UUID,
    type_: str,
    description: str,
    metadata: dict | None = None,
    created_by: str | None = None,
) -> CandidateActivity:
    activity = CandidateActivity(
        candidate_id=candidate_id,
        type=type_,
        description=description,
        activity_metadata=metadata,
        created_by=created_by,
    )
    db.add(activity)
    return activity


def candidate_load_options():
    return (
        selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
        selectinload(Candidate.experiences),
        selectinload(Candidate.educations),
        selectinload(Candidate.certifications),
        selectinload(Candidate.languages),
        selectinload(Candidate.projects),
        selectinload(Candidate.cvs),
        selectinload(Candidate.labels).selectinload(CandidateLabel.label),
    )


def get_candidate_or_404(db: Session, candidate_id: uuid.UUID) -> Candidate:
    stmt = select(Candidate).where(Candidate.id == candidate_id).options(*candidate_load_options())
    candidate = db.execute(stmt).unique().scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


def get_or_create_skill(db: Session, name: str) -> Skill:
    """Concurrent uploads that both introduce the same brand-new skill (e.g.
    two CVs mentioning "C++" processed by two background tasks at once) can
    race here: both see "not found" and both try to insert. Use an atomic
    upsert instead of check-then-insert so the second writer never raises a
    UniqueViolation on `skills.name` and crashes that candidate's pipeline."""
    name = name.strip()
    skill = db.execute(select(Skill).where(Skill.name.ilike(name))).scalar_one_or_none()
    if skill is not None:
        return skill

    stmt = (
        pg_insert(Skill)
        .values(id=uuid.uuid4(), name=name)
        .on_conflict_do_nothing(index_elements=[Skill.name])
        .returning(Skill)
    )
    inserted = db.execute(stmt).scalar_one_or_none()
    if inserted is not None:
        return inserted

    # Lost the race — another session inserted it first; fetch what they wrote.
    return db.execute(select(Skill).where(Skill.name.ilike(name))).scalar_one()


def create_candidate_from_parsed(db: Session, parsed: ParsedCV, source: str = "upload") -> Candidate:
    candidate = Candidate(
        full_name=parsed.full_name,
        normalized_name=normalize_name(parsed.full_name),
        email=normalize_email(parsed.email) if parsed.email else None,
        phone=normalize_phone(parsed.phone) if parsed.phone else None,
        location=parsed.location,
        current_title=parsed.current_title,
        years_of_experience=parsed.years_of_experience,
        summary=parsed.summary,
        portfolio_url=parsed.portfolio_url,
        current_level=parsed.current_level,
        primary_specialty=parsed.primary_specialty,
        source=source,
    )
    db.add(candidate)
    db.flush()
    apply_parsed_details(db, candidate, parsed)
    return candidate


def apply_parsed_details(db: Session, candidate: Candidate, parsed: ParsedCV) -> None:
    for skill_name in parsed.skills:
        skill = get_or_create_skill(db, skill_name)
        exists = db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_id == candidate.id, CandidateSkill.skill_id == skill.id
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(CandidateSkill(candidate_id=candidate.id, skill_id=skill.id))

    # Re-uploading a CV for an existing candidate (duplicate detection) must not
    # duplicate their experience/education/etc entries, so dedupe by identity key.
    existing_experience_keys = {
        (e.company.lower(), e.position.lower(), e.start_date)
        for e in db.execute(select(CandidateExperience).where(CandidateExperience.candidate_id == candidate.id)).scalars()
    }
    for exp in parsed.work_experience:
        if (exp.company.lower(), exp.position.lower(), exp.start_date) in existing_experience_keys:
            continue
        db.add(
            CandidateExperience(
                candidate_id=candidate.id,
                company=exp.company,
                position=exp.position,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                description=exp.description,
            )
        )

    existing_education_keys = {
        (e.school.lower(), (e.degree or "").lower(), e.start_date)
        for e in db.execute(select(CandidateEducation).where(CandidateEducation.candidate_id == candidate.id)).scalars()
    }
    for edu in parsed.education:
        if (edu.school.lower(), (edu.degree or "").lower(), edu.start_date) in existing_education_keys:
            continue
        db.add(
            CandidateEducation(
                candidate_id=candidate.id,
                school=edu.school,
                degree=edu.degree,
                major=edu.major,
                start_date=edu.start_date,
                end_date=edu.end_date,
            )
        )

    existing_cert_names = {
        c.name.lower()
        for c in db.execute(
            select(CandidateCertification).where(CandidateCertification.candidate_id == candidate.id)
        ).scalars()
    }
    for cert in parsed.certifications:
        if cert.name.lower() in existing_cert_names:
            continue
        db.add(
            CandidateCertification(
                candidate_id=candidate.id, name=cert.name, issuer=cert.issuer, issue_date=cert.issue_date
            )
        )

    existing_language_names = {
        l.name.lower()
        for l in db.execute(select(CandidateLanguage).where(CandidateLanguage.candidate_id == candidate.id)).scalars()
    }
    for lang in parsed.languages:
        if lang.name.lower() in existing_language_names:
            continue
        db.add(CandidateLanguage(candidate_id=candidate.id, name=lang.name, proficiency=lang.proficiency))

    existing_project_names = {
        p.name.lower()
        for p in db.execute(select(CandidateProject).where(CandidateProject.candidate_id == candidate.id)).scalars()
    }
    for proj in parsed.projects:
        if proj.name.lower() in existing_project_names:
            continue
        db.add(
            CandidateProject(
                candidate_id=candidate.id, name=proj.name, description=proj.description, technologies=proj.technologies
            )
        )


def update_candidate(db: Session, candidate: Candidate, update: CandidateUpdate) -> Candidate:
    data = update.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = normalize_email(data["email"])
    if "phone" in data and data["phone"]:
        data["phone"] = normalize_phone(data["phone"])
    if "full_name" in data and data["full_name"]:
        candidate.normalized_name = normalize_name(data["full_name"])
    for field, value in data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def delete_candidate(db: Session, candidate: Candidate) -> None:
    """Hard delete, per the privacy/right-to-erasure requirement (section 21).
    Unlike merge, this permanently removes the candidate and all related records."""
    candidate_id = candidate.id
    db.execute(
        ProcessingJob.__table__.update()
        .where(ProcessingJob.candidate_id == candidate_id)
        .values(candidate_id=None)
    )
    db.execute(
        ProcessingJob.__table__.update()
        .where(ProcessingJob.duplicate_of_candidate_id == candidate_id)
        .values(duplicate_of_candidate_id=None)
    )
    db.execute(Application.__table__.delete().where(Application.candidate_id == candidate_id))
    db.execute(Assessment.__table__.delete().where(Assessment.candidate_id == candidate_id))
    db.execute(ScreeningResult.__table__.delete().where(ScreeningResult.candidate_id == candidate_id))
    db.execute(CandidateActivity.__table__.delete().where(CandidateActivity.candidate_id == candidate_id))
    db.execute(CandidateEmbedding.__table__.delete().where(CandidateEmbedding.candidate_id == candidate_id))

    for cv in candidate.cvs:
        try:
            if os.path.exists(cv.file_path):
                os.remove(cv.file_path)
        except OSError:
            pass

    db.delete(candidate)
    db.commit()


def add_label_to_candidate(db: Session, candidate_id: uuid.UUID, label_id: uuid.UUID) -> None:
    exists = db.execute(
        select(CandidateLabel).where(CandidateLabel.candidate_id == candidate_id, CandidateLabel.label_id == label_id)
    ).scalar_one_or_none()
    if exists:
        return
    label = db.get(Label, label_id)
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    db.add(CandidateLabel(candidate_id=candidate_id, label_id=label_id))
    log_activity(db, candidate_id, "LABEL_ADDED", f"Label '{label.name}' added")
    db.commit()


def remove_label_from_candidate(db: Session, candidate_id: uuid.UUID, label_id: uuid.UUID) -> None:
    link = db.execute(
        select(CandidateLabel).where(CandidateLabel.candidate_id == candidate_id, CandidateLabel.label_id == label_id)
    ).scalar_one_or_none()
    if link is None:
        return
    label = db.get(Label, label_id)
    db.delete(link)
    if label:
        log_activity(db, candidate_id, "LABEL_REMOVED", f"Label '{label.name}' removed")
    db.commit()
