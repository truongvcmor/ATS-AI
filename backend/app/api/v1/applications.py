import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.deps import DbSession, RecruiterOrAdmin
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationStageUpdate
from app.services.recruitment.pipeline_service import create_application, move_stage

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create(payload: ApplicationCreate, db: DbSession, current_user: RecruiterOrAdmin) -> Application:
    return create_application(db, payload.candidate_id, payload.job_id)


@router.patch("/{application_id}/stage", response_model=ApplicationOut)
def update_stage(
    application_id: uuid.UUID, payload: ApplicationStageUpdate, db: DbSession, current_user: RecruiterOrAdmin
) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return move_stage(db, application, payload.stage_id)
