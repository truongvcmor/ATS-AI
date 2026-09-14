import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, RecruiterOrAdmin
from app.models.label import CandidateLabel, Label
from app.schemas.label import LabelCreate, LabelOut, LabelUpdate

router = APIRouter(prefix="/labels", tags=["labels"])


def _label_out(db: DbSession, label: Label) -> LabelOut:
    count = db.execute(
        select(func.count()).select_from(CandidateLabel).where(CandidateLabel.label_id == label.id)
    ).scalar_one()
    out = LabelOut.model_validate(label)
    out.candidate_count = count
    return out


@router.post("", response_model=LabelOut, status_code=status.HTTP_201_CREATED)
def create_label(payload: LabelCreate, db: DbSession, current_user: RecruiterOrAdmin) -> LabelOut:
    existing = db.execute(select(Label).where(Label.name.ilike(payload.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Label already exists")
    label = Label(name=payload.name, color=payload.color)
    db.add(label)
    db.commit()
    db.refresh(label)
    return _label_out(db, label)


@router.get("", response_model=list[LabelOut])
def list_labels(db: DbSession, current_user: CurrentUser) -> list[LabelOut]:
    labels = list(db.execute(select(Label).order_by(Label.name)).scalars().all())
    return [_label_out(db, l) for l in labels]


@router.patch("/{label_id}", response_model=LabelOut)
def update_label(label_id: uuid.UUID, payload: LabelUpdate, db: DbSession, current_user: RecruiterOrAdmin) -> LabelOut:
    label = db.get(Label, label_id)
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(label, field, value)
    db.commit()
    db.refresh(label)
    return _label_out(db, label)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_label(label_id: uuid.UUID, db: DbSession, current_user: RecruiterOrAdmin) -> None:
    label = db.get(Label, label_id)
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    db.execute(CandidateLabel.__table__.delete().where(CandidateLabel.label_id == label_id))
    db.delete(label)
    db.commit()
