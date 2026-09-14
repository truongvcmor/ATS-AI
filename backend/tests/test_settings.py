import pytest

from app.services.llm.factory import get_llm_service
from app.services.llm.mock import MockLLMService
from app.services.llm.rotating_service import RotatingLLMService


@pytest.fixture(autouse=True)
def _reset_llm_cache():
    yield
    get_llm_service.cache_clear()


def _admin_headers(client):
    email = "settings-admin@ats.com"
    client.post("/api/auth/register", json={"email": email, "password": "password123", "full_name": "Admin", "role": "ADMIN"})
    token = client.post("/api/auth/login", data={"username": email, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_non_admin_cannot_view_or_edit_ai_settings(client, auth_headers):
    # auth_headers fixture is a RECRUITER (see conftest.py)
    assert client.get("/api/settings/ai", headers=auth_headers).status_code == 403
    assert client.put("/api/settings/ai", headers=auth_headers, json={"llm_provider": "mock"}).status_code == 403


def test_admin_gets_default_mock_settings(client):
    headers = _admin_headers(client)
    resp = client.get("/api/settings/ai", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "mock"
    assert body["openai_configured"] is False
    assert body["openai_keys_masked"] == []


def test_admin_can_set_and_mask_openai_key(client):
    headers = _admin_headers(client)
    resp = client.put(
        "/api/settings/ai", headers=headers, json={"llm_provider": "openai", "openai_api_keys": "sk-abcd1234efgh"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "openai"
    assert body["openai_source"] == "database"
    assert body["openai_keys_masked"] == ["****efgh"]
    assert "sk-abcd1234efgh" not in resp.text  # the raw key must never be echoed back

    # and it actually took effect live, no restart needed
    service = get_llm_service()
    assert isinstance(service, RotatingLLMService)


def test_clearing_key_reverts_to_mock(client):
    headers = _admin_headers(client)
    client.put("/api/settings/ai", headers=headers, json={"llm_provider": "openai", "openai_api_keys": "sk-temp-key"})
    resp = client.put("/api/settings/ai", headers=headers, json={"llm_provider": "mock", "openai_api_keys": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "mock"
    assert body["openai_configured"] is False
    assert isinstance(get_llm_service(), MockLLMService)


def test_partial_update_leaves_other_fields_untouched(client):
    headers = _admin_headers(client)
    client.put("/api/settings/ai", headers=headers, json={"openai_model": "gpt-4-custom"})
    resp = client.put("/api/settings/ai", headers=headers, json={"gemini_model": "gemini-custom"})
    body = resp.json()
    assert body["openai_model"] == "gpt-4-custom"  # untouched by the second PUT
    assert body["gemini_model"] == "gemini-custom"


def test_test_connection_endpoint_reports_failure_for_bad_key(client):
    headers = _admin_headers(client)
    resp = client.post("/api/settings/ai/test", headers=headers, json={"provider": "openai", "api_key": "sk-definitely-invalid"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["message"]


def test_test_connection_without_any_key_configured_fails_cleanly(client):
    headers = _admin_headers(client)
    client.put("/api/settings/ai", headers=headers, json={"gemini_api_keys": ""})
    resp = client.post("/api/settings/ai/test", headers=headers, json={"provider": "gemini"})
    body = resp.json()
    assert body["ok"] is False
    assert "No gemini API key" in body["message"]
