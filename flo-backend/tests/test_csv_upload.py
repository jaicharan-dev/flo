import io
import pytest

@pytest.fixture
def auth_headers(client):
    import uuid
    unique_email = f"csvuser_{uuid.uuid4().hex[:8]}@example.com"
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


def test_upload_valid_csv(client, auth_headers):
    # Pre-create category for auto-categorization test
    client.post(
        "/transactions/categories",
        json={"name": "Food & Dining", "keywords": "restaurant, pizza, coffee"},
        headers=auth_headers
    )

    csv_content = (
        "Date,Amount,Description,Type\n"
        "2026-08-01,250.0,Starbucks coffee,Expense\n"
        "2026-08-02,1200.0,Dominos pizza,Expense\n"
        "2026-08-03,50000.0,Monthly Salary,Income\n"
    )

    file_tuple = ("statement.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    response = client.post(
        "/transactions/upload-csv",
        files={"file": file_tuple},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 3
    assert data["skipped_count"] == 0
    assert len(data["errors"]) == 0

    # Verify transactions exist in DB feed
    txs = client.get("/transactions/?limit=10", headers=auth_headers).json()
    assert len(txs) == 3


def test_upload_invalid_file_extension(client, auth_headers):
    file_tuple = ("file.pdf", io.BytesIO(b"dummy pdf content"), "application/pdf")
    response = client.post(
        "/transactions/upload-csv",
        files={"file": file_tuple},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "Only .csv files are supported" in response.json()["detail"]


def test_upload_missing_required_headers(client, auth_headers):
    csv_content = "UnknownHeader1,UnknownHeader2\n1,2\n"
    file_tuple = ("bad_headers.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    response = client.post(
        "/transactions/upload-csv",
        files={"file": file_tuple},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "CSV must contain at least 'amount' and 'description' columns" in response.json()["detail"]
