from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.services.cv_parser.base import ParsedCV
from app.utils.text_normalize import normalize_email, normalize_name, normalize_phone


def find_duplicate(db: Session, parsed: ParsedCV) -> Candidate | None:
    """Primary match: email or phone. Secondary: normalized full name.
    Already-merged candidates are excluded so we always point at a canonical profile."""
    base_stmt = select(Candidate).where(Candidate.merged_into_id.is_(None))

    if parsed.email:
        email = normalize_email(parsed.email)
        match = db.execute(base_stmt.where(Candidate.email == email)).scalar_one_or_none()
        if match:
            return match

    if parsed.phone:
        phone = normalize_phone(parsed.phone)
        match = db.execute(base_stmt.where(Candidate.phone == phone)).scalar_one_or_none()
        if match:
            return match

    normalized = normalize_name(parsed.full_name)
    if normalized and normalized != "unknown candidate":
        match = db.execute(base_stmt.where(Candidate.normalized_name == normalized)).scalar_one_or_none()
        if match:
            return match

    return None
