import pytest

@pytest.fixture
def auth_headers(client):
    import uuid
    unique_email = f"txuser_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": unique_email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_category(client, auth_headers):
    response = client.post(
        "/transactions/categories",
        json={"name": "Food & Dining", "keywords": "food, pizza, burger", "monthly_limit": 5000.0},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Category created!"
    assert "category_id" in data


def test_add_transaction_with_category(client, auth_headers):
    cat_res = client.post(
        "/transactions/categories",
        json={"name": "Groceries", "keywords": "milk, bread, vegetables"},
        headers=auth_headers
    )
    cat_id = cat_res.json()["category_id"]

    response = client.post(
        "/transactions/",
        json={
            "amount": 450.0,
            "type": "Expense",
            "description": "Weekly vegetables",
            "transaction_date": "2026-08-10",
            "category_id": cat_id
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Transaction saved successfully!"


def test_add_transaction_auto_categorization(client, auth_headers):
    client.post(
        "/transactions/categories",
        json={"name": "Vehicles", "keywords": "cycle, tire, bike, petrol"},
        headers=auth_headers
    )

    response = client.post(
        "/transactions/",
        json={
            "amount": 350.0,
            "type": "Expense",
            "description": "cycle tire puncher",
            "transaction_date": "2026-08-11"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Transaction saved successfully!"

    tx_list = client.get("/transactions/", headers=auth_headers).json()
    assert len(tx_list) > 0
    assert tx_list[0]["category_id"] is not None


def test_get_transactions(client, auth_headers):
    response = client.get("/transactions/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
