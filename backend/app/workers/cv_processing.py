import logging
import uuid

from app.core.database import SessionLocal
from app.models.candidate import CandidateCV
from app.models.embedding import CandidateEmbedding
from app.models.enums import ProcessingStatus
from app.models.processing_job import ProcessingJob
from app.services.candidate.candidate_service import (
    apply_parsed_details,
    create_candidate_from_parsed,
    log_activity,
)
from app.services.candidate.duplicate_detection import find_duplicate
from app.services.cv_parser.base import ParsedCV
from app.services.cv_parser.extractors import extract_text
from app.services.cv_parser.factory import get_cv_parser
from app.services.embedding.factory import get_embedding_service

logger = logging.getLogger(__name__)


def _build_embedding_text(parsed: ParsedCV) -> str:
    parts = [
        parsed.full_name,
        parsed.current_title or "",
        parsed.summary or "",
        "Skills: " + ", ".join(parsed.skills),
    ]
    for exp in parsed.work_experience:
        parts.append(f"{exp.position} at {exp.company}. {exp.description or ''}")
    for proj in parsed.projects:
        parts.append(f"Project {proj.name}: {proj.description or ''} {proj.technologies or ''}")
    return "\n".join(p for p in parts if p)


def _set_status(db, job: ProcessingJob, status: ProcessingStatus, error: str | None = None) -> None:
    job.status = status
    if error is not None:
        job.error_message = error
    db.commit()


def process_cv_upload(processing_job_id: uuid.UUID) -> None:
    """Runs the full extract -> parse -> normalize -> dup-detect -> upsert -> embed -> index
    pipeline for one uploaded file. Executed via FastAPI BackgroundTasks so the upload
    request returns immediately with a processing_job id the frontend can poll."""
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, processing_job_id)
        if job is None:
            logger.error("ProcessingJob %s not found", processing_job_id)
            return

        try:
            _set_status(db, job, ProcessingStatus.PARSING)
            with open(job.file_path, "rb") as f:
                file_bytes = f.read()
            ext = "." + job.file_name.rsplit(".", 1)[-1].lower()
            raw_text, extraction_method = extract_text(file_bytes, ext)
            if not raw_text.strip():
                raise ValueError("No extractable text found in file (including OCR, for scanned/image CVs)")

            parser = get_cv_parser()
            parsed = parser.parse(raw_text)

            _set_status(db, job, ProcessingStatus.PROCESSING)
            duplicate = find_duplicate(db, parsed)
            if duplicate is not None:
                candidate = duplicate
                apply_parsed_details(db, candidate, parsed)
                job.duplicate_of_candidate_id = candidate.id
                is_primary_cv = False
                activity_desc = f"Duplicate CV detected and attached to existing profile '{candidate.full_name}'"
            else:
                candidate = create_candidate_from_parsed(db, parsed)
                is_primary_cv = True
                activity_desc = "CV uploaded and candidate profile created"

            if extraction_method == "ocr":
                activity_desc += " (scanned — extracted via OCR)"

            db.add(
                CandidateCV(
                    candidate_id=candidate.id,
                    file_name=job.file_name,
                    file_path=job.file_path,
                    content_type=job.content_type,
                    raw_text=raw_text,
                    extraction_method=extraction_method,
                    is_primary=is_primary_cv,
                )
            )
            log_activity(
                db,
                candidate.id,
                "CV_UPLOADED",
                activity_desc,
                metadata={"file_name": job.file_name, "extraction_method": extraction_method},
            )
            db.flush()

            _set_status(db, job, ProcessingStatus.INDEXING)
            embedding_service = get_embedding_service()
            vector = embedding_service.embed(_build_embedding_text(parsed))
            existing_embedding = (
                db.query(CandidateEmbedding).filter(CandidateEmbedding.candidate_id == candidate.id).one_or_none()
            )
            if existing_embedding:
                existing_embedding.vector = vector
                existing_embedding.model_name = embedding_service.model_name
            else:
                db.add(
                    CandidateEmbedding(
                        candidate_id=candidate.id, vector=vector, model_name=embedding_service.model_name
                    )
                )

            job.candidate_id = candidate.id
            _set_status(db, job, ProcessingStatus.COMPLETED)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            job = db.get(ProcessingJob, processing_job_id)
            logger.error("CV processing failed for job %s", processing_job_id, exc_info=True)
            _set_status(db, job, ProcessingStatus.FAILED, error=str(exc)[:2000])
    finally:
        db.close()
