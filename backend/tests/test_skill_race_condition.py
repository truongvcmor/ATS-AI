"""Regression test for a real production bug: two background CV-processing
tasks (e.g. from a bulk upload of several CVs at once) both introducing the
same brand-new skill name raced on INSERT and crashed one of the two
pipelines with `psycopg2.errors.UniqueViolation` on `skills.name`.
get_or_create_skill now uses an atomic upsert (INSERT ... ON CONFLICT DO
NOTHING) instead of check-then-insert, so the loser of the race just reads
back what the winner wrote instead of raising.
"""

import threading

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.candidate.candidate_service import get_or_create_skill


def test_concurrent_get_or_create_skill_does_not_raise():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    skill_name = "RaceConditionSkill"

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM candidate_skills"))
        conn.execute(text("DELETE FROM skills WHERE name = :name"), {"name": skill_name})
        conn.commit()

    errors: list[Exception] = []
    skill_ids: list[str] = []
    barrier = threading.Barrier(2)

    def worker():
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)  # maximize the chance both sessions race the insert
            skill = get_or_create_skill(session, skill_name)
            session.commit()
            skill_ids.append(str(skill.id))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == [], f"get_or_create_skill raised under concurrency: {errors}"
    assert len(skill_ids) == 2
    assert skill_ids[0] == skill_ids[1]  # both threads must resolve to the same row

    engine.dispose()
