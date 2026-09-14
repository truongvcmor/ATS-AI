from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.settings import AISettingsOut, AISettingsTestRequest, AISettingsTestResult, AISettingsUpdate
from app.services.settings.settings_service import build_settings_out, get_or_create_row, test_provider, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.ADMIN))]


@router.get("/ai", response_model=AISettingsOut)
def get_ai_settings(db: DbSession, current_user: AdminOnly) -> AISettingsOut:
    row = get_or_create_row(db)
    return build_settings_out(row)


@router.put("/ai", response_model=AISettingsOut)
def put_ai_settings(payload: AISettingsUpdate, db: DbSession, current_user: AdminOnly) -> AISettingsOut:
    row = update_settings(db, payload, updated_by=current_user.email)
    return build_settings_out(row)


@router.post("/ai/test", response_model=AISettingsTestResult)
def post_test_ai_provider(payload: AISettingsTestRequest, current_user: AdminOnly) -> AISettingsTestResult:
    return test_provider(payload.provider, payload.api_key, payload.model)
