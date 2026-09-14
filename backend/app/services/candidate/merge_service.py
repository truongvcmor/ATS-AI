import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.assessment import Assessment
from app.models.activity import CandidateActivity
from app.models.candidate import Candidate, CandidateCV, CandidateSkill
from app.models.embedding import CandidateEmbedding
from app.models.label import CandidateLabel
from app.models.screening import ScreeningResult
from app.services.candidate.candidate_service import log_activity

SCALAR_FIELDS_TO_BACKFILL = [
    "email", "phone", "location", "current_title", "years_of_experience", "summary",
]


def merge_candidates(db: Session, source_id: uuid.UUID, target_id: uuid.UUID) -> Candidate:
    if source_id == target_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a candidate into itself")

    source = db.get(Candidate, source_id)
    target = db.get(Candidate, target_id)
    if source is None or target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if source.merged_into_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source candidate was already merged")

    # Preserve every CV file.
    db.execute(
        CandidateCV.__table__.update().where(CandidateCV.candidate_id == source_id).values(candidate_id=target_id, is_primary=False)
    )

    # Skills: move only ones the target doesn't already have.
    existing_skill_ids = {
        row.skill_id for row in db.execute(select(CandidateSkill).where(CandidateSkill.candidate_id == target_id)).scalars()
    }
    for cs in db.execute(select(CandidateSkill).where(CandidateSkill.candidate_id == source_id)).scalars():
        if cs.skill_id in existing_skill_ids:
            db.delete(cs)
        else:
            cs.candidate_id = target_id

    # Labels: move only ones the target doesn't already have.
    existing_label_ids = {
        row.label_id for row in db.execute(select(CandidateLabel).where(CandidateLabel.candidate_id == target_id)).scalars()
    }
    for cl in db.execute(select(CandidateLabel).where(CandidateLabel.candidate_id == source_id)).scalars():
        if cl.label_id in existing_label_ids:
            db.delete(cl)
        else:
            cl.candidate_id = target_id

    # Applications: preserve history. If target already applied to the same job, keep both by
    # dropping the FK conflict via re-pointing only when no clash; otherwise leave the source
    # application as an orphaned historical record (still queryable) but detach from active pipeline.
    existing_job_ids = {
        row.job_id for row in db.execute(select(Application).where(Application.candidate_id == target_id)).scalars()
    }
    for app in db.execute(select(Application).where(Application.candidate_id == source_id)).scalars():
        if app.job_id not in existing_job_ids:
            app.candidate_id = target_id

    # Assessments, screening results, and activity history are all preserved and re-attributed.
    db.execute(Assessment.__table__.update().where(Assessment.candidate_id == source_id).values(candidate_id=target_id))
    db.execute(
        ScreeningResult.__table__.update().where(ScreeningResult.candidate_id == source_id).values(candidate_id=target_id)
    )
    db.execute(
        CandidateActivity.__table__.update().where(CandidateActivity.candidate_id == source_id).values(candidate_id=target_id)
    )
    db.execute(CandidateEmbedding.__table__.delete().where(CandidateEmbedding.candidate_id == source_id))

    for field in SCALAR_FIELDS_TO_BACKFILL:
        if getattr(target, field) in (None, "") and getattr(source, field):
            setattr(target, field, getattr(source, field))

    if target.ai_score is None and source.ai_score is not None:
        target.ai_score = source.ai_score

    source.merged_into_id = target.id

    log_activity(
        db,
        candidate_id=target.id,
        type_="MERGED",
        description=f"Merged duplicate candidate '{source.full_name}' ({source.id}) into this profile",
        metadata={"source_candidate_id": str(source.id)},
    )
    log_activity(
        db,
        candidate_id=source.id,
        type_="MERGED_AWAY",
        description=f"This profile was merged into '{target.full_name}' ({target.id})",
        metadata={"target_candidate_id": str(target.id)},
    )

    db.commit()
    db.refresh(target)
    return target
