from app.models.candidate import Candidate
from app.schemas.candidate import (
    CandidateDetail,
    CandidateListItem,
    CertificationOut,
    CVOut,
    EducationOut,
    ExperienceOut,
    LabelBadge,
    LanguageOut,
    ProjectOut,
)


def _label_badges(candidate: Candidate) -> list[LabelBadge]:
    return [LabelBadge(id=cl.label.id, name=cl.label.name, color=cl.label.color) for cl in candidate.labels]


def to_list_item(candidate: Candidate) -> CandidateListItem:
    return CandidateListItem(
        id=candidate.id,
        full_name=candidate.full_name,
        current_title=candidate.current_title,
        years_of_experience=candidate.years_of_experience,
        location=candidate.location,
        email=candidate.email,
        ai_score=candidate.ai_score,
        status=candidate.status,
        skills=[cs.skill.name for cs in candidate.skills],
        labels=_label_badges(candidate),
        updated_at=candidate.updated_at,
        created_at=candidate.created_at,
    )


def to_detail(candidate: Candidate) -> CandidateDetail:
    base = to_list_item(candidate)
    return CandidateDetail(
        **base.model_dump(),
        phone=candidate.phone,
        summary=candidate.summary,
        source=candidate.source,
        experiences=[ExperienceOut.model_validate(e) for e in candidate.experiences],
        educations=[EducationOut.model_validate(e) for e in candidate.educations],
        certifications=[CertificationOut.model_validate(c) for c in candidate.certifications],
        languages=[LanguageOut.model_validate(l) for l in candidate.languages],
        projects=[ProjectOut.model_validate(p) for p in candidate.projects],
        cvs=[CVOut.model_validate(c) for c in candidate.cvs],
    )
