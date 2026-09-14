import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CandidateStatus


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company: str
    position: str
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    school: str
    degree: str | None = None
    major: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    issuer: str | None = None
    issue_date: date | None = None


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    proficiency: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    technologies: str | None = None


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    file_name: str
    content_type: str
    extraction_method: str
    is_primary: bool
    uploaded_at: datetime


class LabelBadge(BaseModel):
    id: uuid.UUID
    name: str
    color: str


class CandidateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    current_title: str | None = None
    years_of_experience: float | None = None
    location: str | None = None
    email: str | None = None
    ai_score: float | None = None
    status: CandidateStatus
    skills: list[str] = []
    labels: list[LabelBadge] = []
    updated_at: datetime
    created_at: datetime


class CandidateDetail(CandidateListItem):
    phone: str | None = None
    summary: str | None = None
    source: str
    experiences: list[ExperienceOut] = []
    educations: list[EducationOut] = []
    certifications: list[CertificationOut] = []
    languages: list[LanguageOut] = []
    projects: list[ProjectOut] = []
    cvs: list[CVOut] = []


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    current_title: str | None = None
    years_of_experience: float | None = None
    summary: str | None = None
    status: CandidateStatus | None = None


class DuplicateCandidateInfo(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    cv_count: int


class MergeRequest(BaseModel):
    source_candidate_id: uuid.UUID
    target_candidate_id: uuid.UUID


class PaginatedCandidates(BaseModel):
    items: list[CandidateListItem]
    total: int
    page: int
    page_size: int
