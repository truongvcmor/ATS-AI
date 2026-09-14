def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@ats.com", "password": "secret123", "full_name": "Alice", "role": "RECRUITER"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "alice@ats.com"

    resp = client.post("/api/auth/login", data={"username": "alice@ats.com", "password": "secret123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@ats.com"


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "bob@ats.com", "password": "correct-pw", "full_name": "Bob", "role": "RECRUITER"},
    )
    resp = client.post("/api/auth/login", data={"username": "bob@ats.com", "password": "wrong-pw"})
    assert resp.status_code == 401


def test_duplicate_registration_rejected(client):
    payload = {"email": "dup@ats.com", "password": "secret123", "full_name": "Dup", "role": "RECRUITER"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 400


def test_endpoints_require_auth(client):
    resp = client.get("/api/candidates")
    assert resp.status_code == 401
