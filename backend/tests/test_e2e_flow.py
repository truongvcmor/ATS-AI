from tests.test_candidates import _upload_and_wait
from tests.factories import make_cv_docx


def test_full_recruitment_flow(client, auth_headers):
    # 1. Upload CV -> candidate created
    upload = _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx("E2E Candidate", "e2e@example.com", "0977777777", skills="Python, FastAPI, RAG, LLM, Qdrant"),
    )
    assert upload["status"] == "COMPLETED"
    candidate_id = upload["candidate_id"]

    # 2. Search candidate
    search = client.get("/api/search/candidates", headers=auth_headers, params={"q": "Python"}).json()
    assert any(i["id"] == candidate_id for i in search["items"])

    # 3. Create job and apply
    job = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "title": "AI Engineer",
            "requirements": "3+ years experience\nPython\nLLM\nRAG\nFastAPI\nVector Database",
            "status": "OPEN",
        },
    ).json()
    application = client.post(
        "/api/applications", headers=auth_headers, json={"candidate_id": candidate_id, "job_id": job["id"]}
    ).json()
    assert application["candidate_id"] == candidate_id

    # 4. AI screening
    screen_resp = client.post(
        f"/api/jobs/{job['id']}/screen", headers=auth_headers, json={"job_id": job["id"], "candidate_ids": [candidate_id]}
    )
    assert screen_resp.status_code == 200
    screening = screen_resp.json()[0]
    assert screening["overall_score"] >= 0

    # 5. Move pipeline stage
    stages = {s["name"]: s["id"] for s in client.get(f"/api/jobs/{job['id']}/stages", headers=auth_headers).json()}
    move_resp = client.patch(
        f"/api/applications/{application['id']}/stage", headers=auth_headers, json={"stage_id": stages["Technical Interview"]}
    )
    assert move_resp.status_code == 200

    # 6. History recorded for every step
    history = client.get(f"/api/candidates/{candidate_id}/history", headers=auth_headers).json()
    event_types = {h["type"] for h in history}
    assert {"CV_UPLOADED", "APPLIED", "AI_SCREENING", "STAGE_CHANGED"}.issubset(event_types)

    # 7. Candidate is reusable: recommend them for a second, unrelated job
    second_job = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={"title": "Senior Backend Engineer", "requirements": "Python, FastAPI, PostgreSQL", "status": "OPEN"},
    ).json()
    recs = client.post(f"/api/jobs/{second_job['id']}/recommendations", headers=auth_headers).json()
    assert any(r["candidate"]["id"] == candidate_id for r in recs["recommendations"])
