from tests.test_candidates import _upload_and_wait
from tests.factories import make_cv_docx

JOB_PAYLOAD = {"title": "Backend Engineer", "requirements": "Python, FastAPI", "status": "OPEN"}


def _create_job_and_candidate(client, auth_headers):
    job = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD).json()
    upload = _upload_and_wait(
        client, auth_headers, make_cv_docx("Pipeline Candidate", "pipeline@example.com", "0966666666")
    )
    return job, upload["candidate_id"]


def test_application_lifecycle_and_stage_transitions(client, auth_headers):
    job, candidate_id = _create_job_and_candidate(client, auth_headers)

    resp = client.post("/api/applications", headers=auth_headers, json={"candidate_id": candidate_id, "job_id": job["id"]})
    assert resp.status_code == 201
    application = resp.json()

    stages = {s["name"]: s["id"] for s in client.get(f"/api/jobs/{job['id']}/stages", headers=auth_headers).json()}
    initial_stage = next(s for s in client.get(f"/api/jobs/{job['id']}/stages", headers=auth_headers).json() if s["order"] == 0)
    assert application["current_stage_id"] == initial_stage["id"]

    # duplicate application rejected
    dup = client.post("/api/applications", headers=auth_headers, json={"candidate_id": candidate_id, "job_id": job["id"]})
    assert dup.status_code == 400

    for stage_name in ["Screening", "Technical Interview", "Offer", "Hired"]:
        resp = client.patch(
            f"/api/applications/{application['id']}/stage", headers=auth_headers, json={"stage_id": stages[stage_name]}
        )
        assert resp.status_code == 200
        assert resp.json()["current_stage_id"] == stages[stage_name]

    history = client.get(f"/api/candidates/{candidate_id}/history", headers=auth_headers).json()
    stage_change_events = [h for h in history if h["type"] == "STAGE_CHANGED"]
    assert len(stage_change_events) == 4

    dashboard = client.get("/api/dashboard", headers=auth_headers).json()
    assert dashboard["kpis"]["hired"] >= 1


def test_job_candidates_endpoint_lists_applications(client, auth_headers):
    job, candidate_id = _create_job_and_candidate(client, auth_headers)
    client.post("/api/applications", headers=auth_headers, json={"candidate_id": candidate_id, "job_id": job["id"]})

    resp = client.get(f"/api/jobs/{job['id']}/candidates", headers=auth_headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["candidate"]["full_name"] == "Pipeline Candidate"


def test_assessment_create_and_list(client, auth_headers):
    job, candidate_id = _create_job_and_candidate(client, auth_headers)

    payload = {
        "job_id": job["id"],
        "interview_type": "Phone Interview",
        "interviewer": "Alice Recruiter",
        "score": 7.5,
        "strengths": "Good communication",
        "weaknesses": "Needs more system design depth",
        "comments": "Proceed to technical round",
        "recommendation": "HIRE",
    }
    resp = client.post(f"/api/candidates/{candidate_id}/assessments", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    assert resp.json()["recommendation"] == "HIRE"

    resp = client.get(f"/api/candidates/{candidate_id}/assessments", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    history = client.get(f"/api/candidates/{candidate_id}/history", headers=auth_headers).json()
    assert any(h["type"] == "ASSESSMENT_ADDED" for h in history)
