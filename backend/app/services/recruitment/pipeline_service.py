import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import DEFAULT_STAGES, Application, PipelineStage
from app.models.job import Job
from app.services.candidate.candidate_service import log_activity


def ensure_default_stages(db: Session, job: Job) -> list[PipelineStage]:
    existing = db.execute(select(PipelineStage).where(PipelineStage.job_id == job.id)).scalars().all()
    if existing:
        return list(existing)
    stages = [PipelineStage(job_id=job.id, name=name, order=order, is_terminal=terminal) for name, order, terminal in DEFAULT_STAGES]
    db.add_all(stages)
    db.flush()
    return stages


def get_stages_for_job(db: Session, job_id: uuid.UUID) -> list[PipelineStage]:
    return list(
        db.execute(select(PipelineStage).where(PipelineStage.job_id == job_id).order_by(PipelineStage.order)).scalars()
    )


def create_application(db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID) -> Application:
    existing = db.execute(
        select(Application).where(Application.candidate_id == candidate_id, Application.job_id == job_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate already applied to this job")

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    stages = get_stages_for_job(db, job_id) or ensure_default_stages(db, job)
    first_stage = min(stages, key=lambda s: s.order)

    application = Application(candidate_id=candidate_id, job_id=job_id, current_stage_id=first_stage.id)
    db.add(application)
    log_activity(db, candidate_id, "APPLIED", f"Applied to '{job.title}'", metadata={"job_id": str(job_id)})
    db.commit()
    db.refresh(application)
    return application


def move_stage(db: Session, application: Application, new_stage_id: uuid.UUID) -> Application:
    new_stage = db.get(PipelineStage, new_stage_id)
    if new_stage is None or new_stage.job_id != application.job_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stage for this job")

    old_stage = db.get(PipelineStage, application.current_stage_id)
    application.current_stage_id = new_stage.id
    job = db.get(Job, application.job_id)
    log_activity(
        db,
        application.candidate_id,
        "STAGE_CHANGED",
        f"Moved from '{old_stage.name if old_stage else '?'}' to '{new_stage.name}' for '{job.title if job else '?'}'",
        metadata={"job_id": str(application.job_id), "from_stage": old_stage.name if old_stage else None, "to_stage": new_stage.name},
    )
    db.commit()
    db.refresh(application)
    return application
