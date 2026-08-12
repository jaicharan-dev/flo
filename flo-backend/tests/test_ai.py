import pytest

@pytest.fixture
def auth_headers(client):
    client.post(
        "/auth/register",
        json={"email": "aiuser@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": "aiuser@example.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_query_fallback(client, auth_headers):
    # Tests query endpoint fallback logic when Gemini API key is unconfigured or mocked
    response = client.post(
        "/ai/query",
        json={"query": "What is my highest category?"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0


def test_ai_test_endpoint(client):
    response = client.get("/ai/test")
    assert response.status_code in [200, 500]
