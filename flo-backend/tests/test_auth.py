import pytest

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"email": "testuser@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created successfully"
    assert "user_id" in data


def test_register_duplicate_email(client):
    client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password123"}
    )
    response = client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_user(client):
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "securepassword"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "securepassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client):
    client.post(
        "/auth/register",
        json={"email": "invalid@example.com", "password": "correctpassword"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "invalid@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_refresh_token(client):
    client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": "refresh@example.com", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
