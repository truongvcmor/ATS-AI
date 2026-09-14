def _hiring_manager_headers(client):
    email = "manager-rbac@ats.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "HM", "role": "HIRING_MANAGER"},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_hiring_manager_cannot_create_job(client):
    headers = _hiring_manager_headers(client)
    resp = client.post("/api/jobs", headers=headers, json={"title": "Should Not Be Created", "status": "OPEN"})
    assert resp.status_code == 403


def test_hiring_manager_can_view_jobs_and_candidates(client, auth_headers):
    # recruiter creates a job first
    job = client.post("/api/jobs", headers=auth_headers, json={"title": "Viewable Job", "status": "OPEN"}).json()

    headers = _hiring_manager_headers(client)
    resp = client.get("/api/jobs", headers=headers)
    assert resp.status_code == 200
    assert any(j["id"] == job["id"] for j in resp.json())

    resp = client.get("/api/candidates", headers=headers)
    assert resp.status_code == 200


def test_hiring_manager_can_add_assessment(client, auth_headers):
    from tests.test_candidates import _upload_and_wait
    from tests.factories import make_cv_docx

    upload = _upload_and_wait(client, auth_headers, make_cv_docx("RBAC Candidate", "rbaccandidate@example.com", "0988888888"))
    headers = _hiring_manager_headers(client)
    resp = client.post(
        f"/api/candidates/{upload['candidate_id']}/assessments",
        headers=headers,
        json={
            "interview_type": "Final Interview",
            "interviewer": "Hiring Manager",
            "recommendation": "HIRE",
        },
    )
    assert resp.status_code == 201


def test_recruiter_cannot_upload_as_hiring_manager_only_action_is_still_allowed(client, auth_headers):
    # sanity check that the RECRUITER role (the default test user) keeps working end to end
    resp = client.post("/api/labels", headers=auth_headers, json={"name": "RBAC Label", "color": "#000000"})
    assert resp.status_code == 201
