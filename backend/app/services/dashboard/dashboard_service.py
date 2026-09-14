from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, PipelineStage
from app.models.candidate import Candidate, CandidateSkill, Skill
from app.models.enums import JobStatus
from app.models.job import Job
from app.schemas.dashboard import (
    DashboardResponse,
    KPIs,
    LocationCount,
    ScoreBucket,
    SkillCount,
    StageCount,
    TimeSeriesPoint,
)

SCORE_BUCKETS = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
AI_SHORTLIST_THRESHOLD = 80


def build_dashboard(db: Session) -> DashboardResponse:
    active_candidates = select(Candidate).where(Candidate.merged_into_id.is_(None))
    candidates = list(db.execute(active_candidates).scalars().all())

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    total_candidates = len(candidates)
    new_candidates = sum(1 for c in candidates if c.created_at >= thirty_days_ago)
    open_jobs = db.execute(select(func.count()).select_from(Job).where(Job.status == JobStatus.OPEN)).scalar_one()

    stage_rows = db.execute(
        select(PipelineStage.name, PipelineStage.is_terminal, func.count(Application.id))
        .join(Application, Application.current_stage_id == PipelineStage.id)
        .group_by(PipelineStage.name, PipelineStage.is_terminal)
    ).all()
    candidates_in_pipeline = db.execute(
        select(func.count(func.distinct(Application.candidate_id)))
        .join(PipelineStage, Application.current_stage_id == PipelineStage.id)
        .where(PipelineStage.is_terminal.is_(False))
    ).scalar_one()
    hired = db.execute(
        select(func.count(func.distinct(Application.candidate_id)))
        .join(PipelineStage, Application.current_stage_id == PipelineStage.id)
        .where(PipelineStage.name == "Hired")
    ).scalar_one()
    ai_shortlisted = sum(1 for c in candidates if (c.ai_score or 0) >= AI_SHORTLIST_THRESHOLD)

    kpis = KPIs(
        total_candidates=total_candidates,
        new_candidates_last_30_days=new_candidates,
        open_jobs=open_jobs,
        candidates_in_pipeline=candidates_in_pipeline,
        ai_shortlisted=ai_shortlisted,
        hired=hired,
    )

    by_day: Counter[str] = Counter()
    for c in candidates:
        if c.created_at >= now - timedelta(days=14):
            by_day[c.created_at.date().isoformat()] += 1
    days = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    candidates_over_time = [TimeSeriesPoint(label=d, value=by_day.get(d, 0)) for d in days]

    source_counter = Counter(c.source for c in candidates)
    candidates_by_source = [TimeSeriesPoint(label=k, value=v) for k, v in source_counter.most_common()]

    skill_rows = db.execute(
        select(Skill.name, func.count(CandidateSkill.id))
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .group_by(Skill.name)
        .order_by(func.count(CandidateSkill.id).desc())
        .limit(10)
    ).all()
    top_skills = [SkillCount(skill=name, count=count) for name, count in skill_rows]

    location_counter = Counter(c.location for c in candidates if c.location)
    top_locations = [LocationCount(location=loc, count=count) for loc, count in location_counter.most_common(10)]

    pipeline_by_stage = [StageCount(stage=name, count=count) for name, is_terminal, count in stage_rows]

    score_buckets = []
    for low, high in SCORE_BUCKETS:
        count = sum(1 for c in candidates if c.ai_score is not None and low <= c.ai_score <= high)
        score_buckets.append(ScoreBucket(bucket=f"{low}-{high}", count=count))

    return DashboardResponse(
        kpis=kpis,
        candidates_over_time=candidates_over_time,
        candidates_by_source=candidates_by_source,
        top_skills=top_skills,
        top_locations=top_locations,
        pipeline_by_stage=pipeline_by_stage,
        ai_score_distribution=score_buckets,
    )
