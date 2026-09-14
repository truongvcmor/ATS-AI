from fastapi import APIRouter

from app.api.v1 import applications, auth, candidates, dashboard, jobs, labels, search, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(labels.router)
api_router.include_router(search.router)
api_router.include_router(dashboard.router)
api_router.include_router(settings.router)
