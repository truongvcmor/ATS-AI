from tests.test_candidates import _upload_and_wait
from tests.factories import make_cv_docx


def _seed_candidates(client, auth_headers):
    _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx("Python Dev", "pythondev@example.com", "0900000011", skills="Python, FastAPI, Docker", location="Hanoi"),
        filename="python.docx",
    )
    _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx("Java Dev", "javadev@example.com", "0900000012", skills="Java, Spring Boot", title="Backend Engineer", location="Da Nang"),
        filename="java.docx",
    )
    _upload_and_wait(
        client,
        auth_headers,
        make_cv_docx(
            "Fullstack Dev", "fullstackdev@example.com", "0900000013", skills="Python, React, TypeScript", location="Ho Chi Minh City"
        ),
        filename="fullstack.docx",
    )


def test_keyword_search_and(client, auth_headers):
    _seed_candidates(client, auth_headers)
    resp = client.get("/api/search/candidates", headers=auth_headers, params={"q": "Python AND FastAPI"})
    assert resp.status_code == 200
    names = [i["full_name"] for i in resp.json()["items"]]
    assert names == ["Python Dev"]


def test_keyword_search_or(client, auth_headers):
    _seed_candidates(client, auth_headers)
    resp = client.get("/api/search/candidates", headers=auth_headers, params={"q": "Java OR TypeScript"})
    names = {i["full_name"] for i in resp.json()["items"]}
    assert names == {"Java Dev", "Fullstack Dev"}


def test_keyword_search_exclusion(client, auth_headers):
    _seed_candidates(client, auth_headers)
    resp = client.get("/api/search/candidates", headers=auth_headers, params={"q": "Python -React"})
    names = {i["full_name"] for i in resp.json()["items"]}
    assert names == {"Python Dev"}


def test_filter_by_location_and_skill(client, auth_headers):
    _seed_candidates(client, auth_headers)
    resp = client.get("/api/candidates", headers=auth_headers, params={"locations": ["Hanoi"]})
    names = {i["full_name"] for i in resp.json()["items"]}
    assert names == {"Python Dev"}

    resp = client.get("/api/candidates", headers=auth_headers, params={"skills": ["Java"]})
    names = {i["full_name"] for i in resp.json()["items"]}
    assert names == {"Java Dev"}


def test_semantic_search_returns_relevance_scores(client, auth_headers):
    _seed_candidates(client, auth_headers)
    resp = client.get(
        "/api/search/candidates",
        headers=auth_headers,
        params={"q": "Backend engineer experienced in building RAG systems", "semantic": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert all(item["relevance_score"] is not None for item in body["items"])
