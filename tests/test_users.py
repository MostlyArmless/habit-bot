"""Tests for user endpoints."""

from fastapi.testclient import TestClient


def test_create_user(client: TestClient):
    """Test creating a user."""
    response = client.post(
        "/api/v1/users/",
        json={"name": "Test User", "timezone": "America/Los_Angeles"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["timezone"] == "America/Los_Angeles"
    assert "id" in data


def test_list_users(client: TestClient):
    """Test listing users."""
    # Create a user first
    client.post("/api/v1/users/", json={"name": "List Test User"})

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_user(client: TestClient):
    """Test getting a user by ID."""
    # Create a user first
    create_response = client.post("/api/v1/users/", json={"name": "Get Test User"})
    user_id = create_response.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test User"


def test_get_user_not_found(client: TestClient):
    """Test getting a non-existent user."""
    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404


def test_update_user(client: TestClient):
    """Test updating a user."""
    # Create a user first
    create_response = client.post("/api/v1/users/", json={"name": "Update Test User"})
    user_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"name": "Updated Name", "timezone": "Europe/London"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["timezone"] == "Europe/London"


def test_delete_user(client: TestClient):
    """Test deleting a user."""
    # Create a user first
    create_response = client.post("/api/v1/users/", json={"name": "Delete Test User"})
    user_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 404
