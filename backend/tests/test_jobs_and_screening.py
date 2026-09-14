from tests.test_candidates import _upload_and_wait
from tests.factories import make_cv_docx


JOB_PAYLOAD = {
    "title": "Senior Python AI Engineer",
    "department": "Engineering",
    "location": "Ho Chi Minh City",
    "requirements": "5+ years experience\nStrong Python\nExperience with FastAPI\nExperience with RAG\nExperience with LLM\nExperience with vector databases",
    "preferred_requirements": "Experience with LangChain\nExperience with Qdrant",
    "status": "OPEN",
}


def test_job_crud(client, auth_headers):
    resp = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD)
    assert resp.status_code == 201
    job = resp.json()
    assert job["status"] == "OPEN"

    resp = client.patch(f"/api/jobs/{job['id']}", headers=auth_headers, json={"status": "PAUSED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"

    resp = client.get("/api/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert any(j["id"] == job["id"] for j in resp.json())

    resp = client.delete(f"/api/jobs/{job['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/jobs/{job['id']}", headers=auth_headers).status_code == 404


def test_job_gets_default_pipeline_stages(client, auth_headers):
    job = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD).json()
    stages = client.get(f"/api/jobs/{job['id']}/stages", headers=auth_headers).json()
    names = [s["name"] for s in stages]
    assert names == ["New", "Screening", "Phone Interview", "Technical Interview", "Final Interview", "Offer", "Hired", "Rejected"]


def test_screening_scores_strong_match_candidate_highly(client, auth_headers):
    job = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD).json()
    cv = make_cv_docx(
        "Strong Match Candidate",
        "strongmatch@example.com",
        "0922222222",
        skills="Python, FastAPI, LangChain, RAG, LLM, Qdrant",
    )
    upload = _upload_and_wait(client, auth_headers, cv)
    candidate_id = upload["candidate_id"]

    resp = client.post(
        f"/api/jobs/{job['id']}/screen", headers=auth_headers, json={"job_id": job["id"], "candidate_ids": [candidate_id]}
    )
    assert resp.status_code == 200
    result = resp.json()[0]
    assert result["overall_score"] >= 70
    assert result["recommendation"] in ("STRONG_MATCH", "MATCH")
    assert "Python" in result["matched_requirements"] or any("Python" in m for m in result["matched_requirements"])

    # candidate.ai_score should be updated
    detail = client.get(f"/api/candidates/{candidate_id}", headers=auth_headers).json()
    assert detail["ai_score"] == result["overall_score"]


def test_screening_scores_weak_match_candidate_lower(client, auth_headers):
    job = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD).json()
    cv = make_cv_docx(
        "Weak Match Candidate",
        "weakmatch@example.com",
        "0933333333",
        skills="Marketing, SEO, Content Marketing",
        title="Marketing Specialist",
    )
    upload = _upload_and_wait(client, auth_headers, cv)
    candidate_id = upload["candidate_id"]

    resp = client.post(
        f"/api/jobs/{job['id']}/screen", headers=auth_headers, json={"job_id": job["id"], "candidate_ids": [candidate_id]}
    )
    result = resp.json()[0]
    assert result["overall_score"] < 70
    assert result["recommendation"] in ("WEAK_MATCH", "POSSIBLE_MATCH")


def test_recommendations_ranks_matching_candidate_first(client, auth_headers):
    job = client.post("/api/jobs", headers=auth_headers, json=JOB_PAYLOAD).json()
    strong = _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx("Strong Fit", "strongfit@example.com", "0944444444", skills="Python, FastAPI, LangChain, RAG, LLM, Qdrant"),
        filename="strong.docx",
    )
    weak = _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx("Weak Fit", "weakfit@example.com", "0955555555", skills="Sales, CRM, Negotiation", title="Sales Executive"),
        filename="weak.docx",
    )

    resp = client.post(f"/api/jobs/{job['id']}/recommendations", headers=auth_headers)
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    ids_in_order = [r["candidate"]["id"] for r in recs]
    assert ids_in_order.index(strong["candidate_id"]) < ids_in_order.index(weak["candidate_id"])
