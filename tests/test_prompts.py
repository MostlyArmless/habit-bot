"""Tests for prompt endpoints."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_create_prompt(client: TestClient):
    """Test creating a prompt."""
    # Create a user first
    user_response = client.post("/api/v1/users/", json={"name": "Prompt Test User"})
    user_id = user_response.json()["id"]

    scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": scheduled_time,
            "questions": {"q1": "How are you feeling?"},
            "categories": ["mental_state"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["status"] == "scheduled"
    assert "mental_state" in data["categories"]


def test_create_prompt_user_not_found(client: TestClient):
    """Test creating a prompt for non-existent user."""
    response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": 99999,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test question"},
        },
    )
    assert response.status_code == 404


def test_list_prompts(client: TestClient):
    """Test listing prompts."""
    # Create a user and prompt
    user_response = client.post("/api/v1/users/", json={"name": "List Prompts User"})
    user_id = user_response.json()["id"]

    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )

    response = client.get("/api/v1/prompts/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_prompts_filter_by_user(client: TestClient):
    """Test listing prompts filtered by user."""
    # Create a user and prompt
    user_response = client.post("/api/v1/users/", json={"name": "Filter User"})
    user_id = user_response.json()["id"]

    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )

    response = client.get(f"/api/v1/prompts/?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert all(p["user_id"] == user_id for p in data)


def test_get_prompt(client: TestClient):
    """Test getting a prompt by ID."""
    # Create a user and prompt
    user_response = client.post("/api/v1/users/", json={"name": "Get Prompt User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test question"},
        },
    )
    prompt_id = create_response.json()["id"]

    response = client.get(f"/api/v1/prompts/{prompt_id}")
    assert response.status_code == 200
    assert response.json()["id"] == prompt_id


def test_acknowledge_prompt(client: TestClient):
    """Test acknowledging a prompt."""
    # Create a user and prompt
    user_response = client.post("/api/v1/users/", json={"name": "Ack Prompt User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    prompt_id = create_response.json()["id"]

    response = client.post(f"/api/v1/prompts/{prompt_id}/acknowledge")
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


def test_update_prompt_status(client: TestClient):
    """Test updating a prompt's status."""
    # Create a user and prompt
    user_response = client.post("/api/v1/users/", json={"name": "Update Prompt User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    prompt_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/prompts/{prompt_id}", json={"status": "sent"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
