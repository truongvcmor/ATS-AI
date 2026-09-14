import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EmploymentType, JobStatus


class JobCreate(BaseModel):
    title: str
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    description: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    preferred_requirements: str | None = None
    status: JobStatus = JobStatus.DRAFT


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType | None = None
    description: str | None = None
    responsibilities: str | None = None
    preferred_requirements: str | None = None
    requirements: str | None = None
    status: JobStatus | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType
    description: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    preferred_requirements: str | None = None
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    application_count: int = 0
