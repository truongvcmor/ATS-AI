import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, RecruiterOrAdmin
from app.models.activity import CandidateActivity
from app.models.enums import ProcessingStatus
from app.models.processing_job import ProcessingJob
from app.models.assessment import Assessment
from app.models.screening import ScreeningResult
from app.schemas.activity import ActivityOut
from app.schemas.assessment import AssessmentCreate, AssessmentOut
from app.schemas.candidate import CandidateDetail, CandidateUpdate, MergeRequest, PaginatedCandidates
from app.schemas.processing import ProcessingJobOut, UploadResponse
from app.schemas.screening import ScreeningResultOut
from app.schemas.search import CandidateSearchParams, SortBy
from app.services.candidate.candidate_service import (
    add_label_to_candidate,
    delete_candidate,
    get_candidate_or_404,
    log_activity,
    remove_label_from_candidate,
    update_candidate,
)
from app.services.candidate.mappers import to_detail, to_list_item
from app.services.candidate.merge_service import merge_candidates
from app.services.search.service import SearchService
from app.utils.file_storage import save_upload, validate_cv_file
from app.workers.cv_processing import process_cv_upload

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_cvs(
    db: DbSession,
    background_tasks: BackgroundTasks,
    current_user: RecruiterOrAdmin,
    files: list[UploadFile],
) -> UploadResponse:
    jobs: list[ProcessingJob] = []
    for file in files:
        ext = validate_cv_file(file)
        file_bytes = file.file.read()
        file_path = save_upload(file_bytes, file.filename or "cv", ext)
        job = ProcessingJob(
            file_name=file.filename or "cv",
            file_path=file_path,
            content_type=file.content_type or "application/octet-stream",
            status=ProcessingStatus.UPLOADING,
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    for job in jobs:
        db.refresh(job)
        background_tasks.add_task(process_cv_upload, job.id)
    return UploadResponse(jobs=[ProcessingJobOut.model_validate(j) for j in jobs])


@router.get("/processing", response_model=list[ProcessingJobOut])
def list_processing_jobs(db: DbSession, current_user: CurrentUser, limit: int = 50) -> list[ProcessingJob]:
    stmt = select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/processing/{job_id}", response_model=ProcessingJobOut)
def get_processing_job(job_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    return job


@router.post("/processing/{job_id}/retry", response_model=ProcessingJobOut)
def retry_processing_job(
    job_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin, background_tasks: BackgroundTasks
) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    job.status = ProcessingStatus.UPLOADING
    job.error_message = None
    db.commit()
    background_tasks.add_task(process_cv_upload, job.id)
    db.refresh(job)
    return job


@router.get("", response_model=PaginatedCandidates)
def list_candidates(
    db: DbSession,
    current_user: CurrentUser,
    q: str | None = None,
    semantic: bool = False,
    skills: list[str] = Query(default=[]),
    min_experience: float | None = None,
    locations: list[str] = Query(default=[]),
    labels: list[str] = Query(default=[]),
    min_ai_score: float | None = None,
    sort_by: SortBy = SortBy.RECENTLY_UPDATED,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedCandidates:
    params = CandidateSearchParams(
        q=q,
        semantic=semantic,
        skills=skills,
        min_experience=min_experience,
        locations=locations,
        labels=labels,
        min_ai_score=min_ai_score,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    items, _relevance, total = SearchService().search(db, params)
    return PaginatedCandidates(
        items=[to_list_item(c) for c in items], total=total, page=page, page_size=page_size
    )


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> CandidateDetail:
    candidate = get_candidate_or_404(db, candidate_id)
    return to_detail(candidate)


@router.patch("/{candidate_id}", response_model=CandidateDetail)
def patch_candidate(
    candidate_id: uuid.UUID, payload: CandidateUpdate, db: DbSession, current_user: RecruiterOrAdmin
) -> CandidateDetail:
    candidate = get_candidate_or_404(db, candidate_id)
    candidate = update_candidate(db, candidate, payload)
    return to_detail(candidate)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_candidate(
    candidate_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin
) -> None:
    candidate = get_candidate_or_404(db, candidate_id)
    delete_candidate(db, candidate)


@router.post("/{candidate_id}/merge", response_model=CandidateDetail)
def merge_candidate(
    candidate_id: uuid.UUID, payload: MergeRequest, db: DbSession, current_user: RecruiterOrAdmin
) -> CandidateDetail:
    if payload.target_candidate_id != candidate_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_candidate_id must match the URL id")
    target = merge_candidates(db, source_id=payload.source_candidate_id, target_id=payload.target_candidate_id)
    return to_detail(get_candidate_or_404(db, target.id))


@router.get("/{candidate_id}/history", response_model=list[ActivityOut])
def get_candidate_history(candidate_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[CandidateActivity]:
    get_candidate_or_404(db, candidate_id)
    stmt = (
        select(CandidateActivity)
        .where(CandidateActivity.candidate_id == candidate_id)
        .order_by(CandidateActivity.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/{candidate_id}/assessments", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    candidate_id: uuid.UUID, payload: AssessmentCreate, db: DbSession, current_user: CurrentUser
) -> Assessment:
    get_candidate_or_404(db, candidate_id)
    assessment = Assessment(candidate_id=candidate_id, **payload.model_dump())
    db.add(assessment)
    log_activity(
        db,
        candidate_id,
        "ASSESSMENT_ADDED",
        f"{payload.interview_type} assessment by {payload.interviewer}: {payload.recommendation.value}",
        metadata={"recommendation": payload.recommendation.value, "score": payload.score},
    )
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/{candidate_id}/assessments", response_model=list[AssessmentOut])
def list_assessments(candidate_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[Assessment]:
    get_candidate_or_404(db, candidate_id)
    stmt = select(Assessment).where(Assessment.candidate_id == candidate_id).order_by(Assessment.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get("/{candidate_id}/cvs/{cv_id}/download")
def download_cv(candidate_id: uuid.UUID, cv_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> FileResponse:
    candidate = get_candidate_or_404(db, candidate_id)
    cv = next((c for c in candidate.cvs if c.id == cv_id), None)
    if cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return FileResponse(path=cv.file_path, filename=cv.file_name, media_type=cv.content_type)


@router.get("/{candidate_id}/screening", response_model=list[ScreeningResultOut])
def list_screening_results(candidate_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[ScreeningResult]:
    get_candidate_or_404(db, candidate_id)
    stmt = (
        select(ScreeningResult)
        .where(ScreeningResult.candidate_id == candidate_id)
        .order_by(ScreeningResult.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/{candidate_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_label(candidate_id: uuid.UUID, label_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin) -> None:
    get_candidate_or_404(db, candidate_id)
    add_label_to_candidate(db, candidate_id, label_id)


@router.delete("/{candidate_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_label(candidate_id: uuid.UUID, label_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin) -> None:
    get_candidate_or_404(db, candidate_id)
    remove_label_from_candidate(db, candidate_id, label_id)
