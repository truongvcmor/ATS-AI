import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EmploymentType, GenderRequirement, JobStatus, SalaryCurrency, SeniorityLevel


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type"), default=EmploymentType.FULL_TIME
    )
    level: Mapped[SeniorityLevel | None] = mapped_column(Enum(SeniorityLevel, name="seniority_level"), nullable=True)

    # Salary range — both ends optional (e.g. only a floor, or fully negotiable).
    salary_min: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    salary_currency: Mapped[SalaryCurrency] = mapped_column(
        Enum(SalaryCurrency, name="salary_currency"), default=SalaryCurrency.VND
    )
    salary_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)

    working_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    hiring_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Informational only — displayed on the job posting for compliance/context
    # (e.g. physical-requirement or legally-exempt roles). Never read by the
    # screening/recommendation services: candidates are ranked strictly on
    # job-related qualifications, per app/prompts/screening.py.
    age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender_requirement: Mapped[GenderRequirement] = mapped_column(
        Enum(GenderRequirement, name="gender_requirement"), default=GenderRequirement.ANY
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)  # mandatory requirements
    preferred_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)  # nice-to-have
    technical_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    soft_skills: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
