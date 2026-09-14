from abc import ABC, abstractmethod
from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

# A parsed CV's field lengths are inherently unbounded — a real-world CV can
# put an entire paragraph where we expect a short "certification name" or
# "school" (this has actually happened: a résumé section got misclassified
# and produced a 400+ char "certification"), and the DB columns storing
# these are bounded VARCHARs. Truncating here — once, at the canonical
# parsed-CV shape used by *both* RuleBasedCVParser and LLMCVParser — means
# neither parser implementation, nor any future one, can ever crash the
# whole upload pipeline with a StringDataRightTruncation error. Matches the
# column widths in app/models/candidate.py and app/models/user's siblings.


def _truncate(max_len: int):
    def validator(v: object) -> object:
        if isinstance(v, str) and len(v) > max_len:
            return v[: max_len - 1].rstrip() + "…"
        return v

    return validator


def _truncate_list(max_len: int):
    def validator(v: object) -> object:
        if isinstance(v, list):
            return [_truncate(max_len)(item) for item in v]
        return v

    return validator


Text255 = Annotated[str, BeforeValidator(_truncate(255))]
Text100 = Annotated[str, BeforeValidator(_truncate(100))]
OptionalText255 = Annotated[str | None, BeforeValidator(_truncate(255))]
OptionalText100 = Annotated[str | None, BeforeValidator(_truncate(100))]
OptionalText50 = Annotated[str | None, BeforeValidator(_truncate(50))]
OptionalText500 = Annotated[str | None, BeforeValidator(_truncate(500))]
SkillList = Annotated[list[str], BeforeValidator(_truncate_list(150))]  # Skill.name column width


class ParsedExperience(BaseModel):
    company: Text255
    position: Text255
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None


class ParsedEducation(BaseModel):
    school: Text255
    degree: OptionalText255 = None
    major: OptionalText255 = None
    start_date: date | None = None
    end_date: date | None = None


class ParsedCertification(BaseModel):
    name: Text255
    issuer: OptionalText255 = None
    issue_date: date | None = None


class ParsedLanguage(BaseModel):
    name: Text100
    proficiency: OptionalText100 = None


class ParsedProject(BaseModel):
    name: Text255
    description: str | None = None
    technologies: OptionalText500 = None


class ParsedCV(BaseModel):
    full_name: Text255 = "Unknown Candidate"
    email: OptionalText255 = None
    phone: OptionalText50 = None
    location: OptionalText255 = None
    current_title: OptionalText255 = None
    years_of_experience: float | None = None
    summary: str | None = None
    skills: SkillList = Field(default_factory=list)
    work_experience: list[ParsedExperience] = Field(default_factory=list)
    education: list[ParsedEducation] = Field(default_factory=list)
    certifications: list[ParsedCertification] = Field(default_factory=list)
    languages: list[ParsedLanguage] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)


class CVParser(ABC):
    """Abstraction so the parsing backend (rule-based today, LLM-backed later) is swappable."""

    @abstractmethod
    def parse(self, raw_text: str) -> ParsedCV:
        raise NotImplementedError
