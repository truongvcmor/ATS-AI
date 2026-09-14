import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, RecruiterOrAdmin
from app.models.application import Application, PipelineStage
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.screening import ScreeningResult
from app.schemas.application import ApplicationOut, PipelineStageOut
from app.schemas.job import JobCreate, JobOut, JobUpdate
from app.schemas.recommendation import RecommendationResponse
from app.schemas.screening import BulkScreeningRequest, ScreeningResultOut
from app.services.llm.factory import get_llm_service
from app.services.recruitment.pipeline_service import ensure_default_stages, get_stages_for_job
from app.services.recruitment.recommendation_service import RecommendationService
from app.services.screening.screening_service import ScreeningService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_out(db: DbSession, job: Job) -> JobOut:
    count = db.execute(select(func.count()).select_from(Application).where(Application.job_id == job.id)).scalar_one()
    out = JobOut.model_validate(job)
    out.application_count = count
    return out


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: DbSession, current_user: RecruiterOrAdmin) -> JobOut:
    job = Job(**payload.model_dump())
    db.add(job)
    db.flush()
    ensure_default_stages(db, job)
    db.commit()
    db.refresh(job)
    return _job_out(db, job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: DbSession, current_user: CurrentUser, status_filter: str | None = None) -> list[JobOut]:
    stmt = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    jobs = list(db.execute(stmt).scalars().all())
    return [_job_out(db, j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_out(db, job)


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: uuid.UUID, payload: JobUpdate, db: DbSession, current_user: RecruiterOrAdmin) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return _job_out(db, job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin) -> None:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    db.execute(Application.__table__.delete().where(Application.job_id == job_id))
    db.execute(ScreeningResult.__table__.delete().where(ScreeningResult.job_id == job_id))
    db.execute(PipelineStage.__table__.delete().where(PipelineStage.job_id == job_id))
    db.delete(job)
    db.commit()


@router.get("/{job_id}/stages", response_model=list[PipelineStageOut])
def list_stages(job_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[PipelineStageOut]:
    return get_stages_for_job(db, job_id)


@router.get("/{job_id}/candidates", response_model=list[ApplicationOut])
def list_job_candidates(job_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[ApplicationOut]:
    stmt = select(Application).where(Application.job_id == job_id)
    applications = list(db.execute(stmt).scalars().all())
    return [ApplicationOut.model_validate(app) for app in applications]


@router.post("/{job_id}/screen", response_model=list[ScreeningResultOut])
def screen_job_candidates(
    job_id: uuid.UUID, payload: BulkScreeningRequest, db: DbSession, current_user: RecruiterOrAdmin
) -> list[ScreeningResultOut]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if payload.candidate_ids:
        candidate_ids = payload.candidate_ids
    else:
        stmt = select(Application.candidate_id).where(Application.job_id == job_id)
        candidate_ids = list(db.execute(stmt).scalars().all())
    if not candidate_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No candidates to screen")

    service = ScreeningService(get_llm_service())
    results = []
    for candidate_id in candidate_ids:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            continue
        results.append(service.screen(db, job, candidate))
    return results


@router.post("/{job_id}/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    job_id: uuid.UUID, db: DbSession, current_user: CurrentUser, limit: int = 20
) -> RecommendationResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    service = RecommendationService(get_llm_service())
    recs = service.find_candidates_for_job(db, job, limit=limit)
    return RecommendationResponse(job_id=job_id, recommendations=recs)
