from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard.dashboard_service import build_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: DbSession, current_user: CurrentUser) -> DashboardResponse:
    return build_dashboard(db)
