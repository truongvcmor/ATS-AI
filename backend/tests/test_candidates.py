import time

from tests.factories import make_cv_docx, make_cv_with_oversized_certification_line

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_MIME_BY_EXT = {
    ".docx": DOCX_MIME,
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _upload_and_wait(client, headers, file_bytes, filename="cv.docx", timeout=10):
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    mime_type = _MIME_BY_EXT.get(ext, DOCX_MIME)
    resp = client.post(
        "/api/candidates/upload",
        headers=headers,
        files=[("files", (filename, file_bytes, mime_type))],
    )
    assert resp.status_code == 202, resp.text
    job = resp.json()["jobs"][0]

    deadline = time.time() + timeout
    while time.time() < deadline:
        status_resp = client.get(f"/api/candidates/processing/{job['id']}", headers=headers)
        job = status_resp.json()
        if job["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.2)
    return job


def test_upload_cv_creates_candidate(client, auth_headers):
    file_bytes = make_cv_docx("Nguyen Van A", "nguyenvana@example.com", "0901234567")
    job = _upload_and_wait(client, auth_headers, file_bytes)
    assert job["status"] == "COMPLETED"
    assert job["candidate_id"]

    detail = client.get(f"/api/candidates/{job['candidate_id']}", headers=auth_headers).json()
    assert detail["full_name"] == "Nguyen Van A"
    assert detail["email"] == "nguyenvana@example.com"
    assert "Python" in detail["skills"]
    assert detail["years_of_experience"] and detail["years_of_experience"] > 0
    assert len(detail["experiences"]) == 1
    assert len(detail["cvs"]) == 1


def test_candidate_crud_update_and_delete(client, auth_headers):
    file_bytes = make_cv_docx("Tran Thi B", "tranthib@example.com", "0912345678")
    job = _upload_and_wait(client, auth_headers, file_bytes)
    candidate_id = job["candidate_id"]

    resp = client.patch(
        f"/api/candidates/{candidate_id}", headers=auth_headers, json={"location": "Da Nang", "current_title": "Staff Engineer"}
    )
    assert resp.status_code == 200
    assert resp.json()["location"] == "Da Nang"
    assert resp.json()["current_title"] == "Staff Engineer"

    resp = client.delete(f"/api/candidates/{candidate_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/candidates/{candidate_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_duplicate_detection_attaches_second_cv_to_same_candidate(client, auth_headers):
    file_bytes = make_cv_docx("Le Van C", "levanc@example.com", "0987654321")
    job1 = _upload_and_wait(client, auth_headers, file_bytes, filename="cv1.docx")
    job2 = _upload_and_wait(client, auth_headers, file_bytes, filename="cv2.docx")

    assert job1["candidate_id"] == job2["candidate_id"]
    assert job2["duplicate_of_candidate_id"] == job1["candidate_id"]

    detail = client.get(f"/api/candidates/{job1['candidate_id']}", headers=auth_headers).json()
    assert len(detail["cvs"]) == 2
    # re-uploading the identical CV must not duplicate experience/education entries
    assert len(detail["experiences"]) == 1

    resp = client.get(f"/api/candidates?page_size=50", headers=auth_headers)
    assert resp.json()["total"] == 1


def test_merge_two_distinct_candidates_preserves_history(client, auth_headers):
    a = make_cv_docx("Pham Van D", "phamvand@example.com", "0900000001")
    b = make_cv_docx("Pham Van D Duplicate", "phamvand2@example.com", "0900000002")
    job_a = _upload_and_wait(client, auth_headers, a, filename="a.docx")
    job_b = _upload_and_wait(client, auth_headers, b, filename="b.docx")
    assert job_a["candidate_id"] != job_b["candidate_id"]

    resp = client.post(
        f"/api/candidates/{job_a['candidate_id']}/merge",
        headers=auth_headers,
        json={"source_candidate_id": job_b["candidate_id"], "target_candidate_id": job_a["candidate_id"]},
    )
    assert resp.status_code == 200
    merged = resp.json()
    assert len(merged["cvs"]) == 2

    history = client.get(f"/api/candidates/{job_a['candidate_id']}/history", headers=auth_headers).json()
    assert any(h["type"] == "MERGED" for h in history)

    source_history = client.get(f"/api/candidates/{job_b['candidate_id']}/history", headers=auth_headers).json()
    assert any(h["type"] == "MERGED_AWAY" for h in source_history)


def test_labels_crud_and_attach(client, auth_headers):
    resp = client.post("/api/labels", headers=auth_headers, json={"name": "Potential Hire", "color": "#f59e0b"})
    assert resp.status_code == 201
    label = resp.json()

    job = _upload_and_wait(client, auth_headers, make_cv_docx("Vo Thi E", "vothie@example.com", "0911111111"))
    resp = client.post(f"/api/candidates/{job['candidate_id']}/labels/{label['id']}", headers=auth_headers)
    assert resp.status_code == 204

    detail = client.get(f"/api/candidates/{job['candidate_id']}", headers=auth_headers).json()
    assert any(l["name"] == "Potential Hire" for l in detail["labels"])

    resp = client.delete(f"/api/candidates/{job['candidate_id']}/labels/{label['id']}", headers=auth_headers)
    assert resp.status_code == 204
    detail = client.get(f"/api/candidates/{job['candidate_id']}", headers=auth_headers).json()
    assert detail["labels"] == []


def test_upload_survives_an_oversized_parsed_field(client, auth_headers):
    file_bytes = make_cv_with_oversized_certification_line(
        "Oversized Field Candidate", "oversized@example.com", "0999999999"
    )
    job = _upload_and_wait(client, auth_headers, file_bytes)
    assert job["status"] == "COMPLETED", job.get("error_message")

    detail = client.get(f"/api/candidates/{job['candidate_id']}", headers=auth_headers).json()
    assert len(detail["certifications"]) == 1
    assert len(detail["certifications"][0]["name"]) <= 255
