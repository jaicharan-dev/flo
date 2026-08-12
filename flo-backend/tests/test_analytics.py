import pytest

@pytest.fixture
def auth_headers_with_data(client):
    import uuid
    unique_email = f"analytics_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": unique_email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    cat_res = client.post(
        "/transactions/categories",
        json={"name": "Shopping", "monthly_limit": 10000.0},
        headers=headers
    )
    cat_data = cat_res.json()
    cat_id = cat_data["category_id"]

    # Add income
    client.post(
        "/transactions/",
        json={"amount": 50000.0, "type": "Income", "description": "Salary", "transaction_date": "2026-08-01", "category_id": None},
        headers=headers
    )

    # Add normal expenses (5 * 300 = 1500 + 25000 = 26500)
    for amt in [200.0, 300.0, 250.0, 400.0, 350.0]:
        client.post(
            "/transactions/",
            json={"amount": amt, "type": "Expense", "description": "Regular buy", "transaction_date": "2026-08-05", "category_id": cat_id},
            headers=headers
        )

    # Add statistical outlier expense (IQR test)
    client.post(
        "/transactions/",
        json={"amount": 25000.0, "type": "Expense", "description": "New Laptop", "transaction_date": "2026-08-08", "category_id": cat_id},
        headers=headers
    )

    return headers


def test_get_kpis(client, auth_headers_with_data):
    response = client.get("/analytics/kpis", headers=auth_headers_with_data)
    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == 50000.0
    assert data["total_expense"] == 26500.0
    assert data["net_balance"] == 23500.0


def test_budget_vs_actual(client, auth_headers_with_data):
    response = client.get("/analytics/budget-vs-actual", headers=auth_headers_with_data)
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "totals" in data


def test_stats_and_outliers(client, auth_headers_with_data):
    response = client.get("/analytics/stats-and-outliers", headers=auth_headers_with_data)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 6
    assert data["max"] == 25000.0
    assert "iqr" in data
    assert len(data["outliers"]) > 0
    assert data["outliers"][0]["amount"] == 25000.0
