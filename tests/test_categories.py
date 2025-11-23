"""Tests for category endpoints."""

from fastapi.testclient import TestClient


def test_create_category(client: TestClient):
    """Test creating a category."""
    response = client.post(
        "/api/v1/categories/",
        json={
            "name": "test_sleep",
            "description": "Sleep tracking category",
            "frequency_per_day": 1,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_sleep"
    assert data["description"] == "Sleep tracking category"
    assert data["frequency_per_day"] == 1


def test_create_duplicate_category(client: TestClient):
    """Test creating a category with duplicate name."""
    # Create first category
    client.post("/api/v1/categories/", json={"name": "duplicate_test"})

    # Try to create duplicate
    response = client.post("/api/v1/categories/", json={"name": "duplicate_test"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_categories(client: TestClient):
    """Test listing categories."""
    # Create a category first
    client.post("/api/v1/categories/", json={"name": "list_test_category"})

    response = client.get("/api/v1/categories/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_category(client: TestClient):
    """Test getting a category by ID."""
    # Create a category first
    create_response = client.post(
        "/api/v1/categories/", json={"name": "get_test_category"}
    )
    category_id = create_response.json()["id"]

    response = client.get(f"/api/v1/categories/{category_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "get_test_category"


def test_get_category_not_found(client: TestClient):
    """Test getting a non-existent category."""
    response = client.get("/api/v1/categories/99999")
    assert response.status_code == 404


def test_delete_category(client: TestClient):
    """Test deleting a category."""
    # Create a category first
    create_response = client.post(
        "/api/v1/categories/", json={"name": "delete_test_category"}
    )
    category_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/categories/{category_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/api/v1/categories/{category_id}")
    assert get_response.status_code == 404
