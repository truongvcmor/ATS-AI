from pydantic import BaseModel


class KPIs(BaseModel):
    total_candidates: int
    new_candidates_last_30_days: int
    open_jobs: int
    candidates_in_pipeline: int
    ai_shortlisted: int
    hired: int


class TimeSeriesPoint(BaseModel):
    label: str
    value: int


class SkillCount(BaseModel):
    skill: str
    count: int


class LocationCount(BaseModel):
    location: str
    count: int


class StageCount(BaseModel):
    stage: str
    count: int


class ScoreBucket(BaseModel):
    bucket: str
    count: int


class DashboardResponse(BaseModel):
    kpis: KPIs
    candidates_over_time: list[TimeSeriesPoint]
    candidates_by_source: list[TimeSeriesPoint]
    top_skills: list[SkillCount]
    top_locations: list[LocationCount]
    pipeline_by_stage: list[StageCount]
    ai_score_distribution: list[ScoreBucket]
