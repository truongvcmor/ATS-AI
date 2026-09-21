import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EmploymentType, GenderRequirement, JobStatus, SalaryCurrency, SeniorityLevel


class JobCreate(BaseModel):
    title: str
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    level: SeniorityLevel | None = None

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: SalaryCurrency = SalaryCurrency.VND
    salary_negotiable: bool = False

    working_hours: str | None = None
    benefits: str | None = None
    hiring_reason: str | None = None

    # Informational only — see Job.gender_requirement / Job.age_min/age_max
    # in app/models/job.py. Never used by screening/recommendations.
    age_min: int | None = None
    age_max: int | None = None
    gender_requirement: GenderRequirement = GenderRequirement.ANY

    description: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None  # mandatory requirements
    preferred_requirements: str | None = None  # nice-to-have
    technical_skills: str | None = None
    soft_skills: str | None = None

    status: JobStatus = JobStatus.DRAFT


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType | None = None
    level: SeniorityLevel | None = None

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: SalaryCurrency | None = None
    salary_negotiable: bool | None = None

    working_hours: str | None = None
    benefits: str | None = None
    hiring_reason: str | None = None

    age_min: int | None = None
    age_max: int | None = None
    gender_requirement: GenderRequirement | None = None

    description: str | None = None
    responsibilities: str | None = None
    preferred_requirements: str | None = None
    requirements: str | None = None
    technical_skills: str | None = None
    soft_skills: str | None = None

    status: JobStatus | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType
    level: SeniorityLevel | None = None

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: SalaryCurrency
    salary_negotiable: bool

    working_hours: str | None = None
    benefits: str | None = None
    hiring_reason: str | None = None

    age_min: int | None = None
    age_max: int | None = None
    gender_requirement: GenderRequirement

    description: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    preferred_requirements: str | None = None
    technical_skills: str | None = None
    soft_skills: str | None = None

    status: JobStatus
    created_at: datetime
    updated_at: datetime
    application_count: int = 0
