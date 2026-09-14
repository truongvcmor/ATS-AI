def test_upload_rejects_unsupported_extension(client, auth_headers):
    resp = client.post(
        "/api/candidates/upload",
        headers=auth_headers,
        files=[("files", ("resume.txt", b"just plain text", "text/plain"))],
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_upload_requires_recruiter_or_admin_role(client):
    email = "viewer@ats.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Viewer", "role": "HIRING_MANAGER"},
    )
    token = client.post("/api/auth/login", data={"username": email, "password": "password123"}).json()["access_token"]

    resp = client.post(
        "/api/candidates/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=[("files", ("resume.docx", b"fake bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert resp.status_code == 403
