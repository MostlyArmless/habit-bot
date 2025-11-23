"""Tests for response endpoints."""

from datetime import datetime

from fastapi.testclient import TestClient


def test_create_response(client: TestClient):
    """Test creating a response."""
    # Create user and prompt first
    user_response = client.post("/api/v1/users/", json={"name": "Response Test User"})
    user_id = user_response.json()["id"]

    prompt_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "How are you?"},
        },
    )
    prompt_id = prompt_response.json()["id"]

    response = client.post(
        "/api/v1/responses/",
        json={
            "prompt_id": prompt_id,
            "user_id": user_id,
            "question_text": "How are you?",
            "response_text": "I'm feeling great today!",
            "category": "mental_state",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["response_text"] == "I'm feeling great today!"
    assert data["processing_status"] == "pending"


def test_create_response_prompt_not_found(client: TestClient):
    """Test creating a response for non-existent prompt."""
    response = client.post(
        "/api/v1/responses/",
        json={
            "prompt_id": 99999,
            "user_id": 1,
            "question_text": "Test?",
            "response_text": "Test response",
        },
    )
    assert response.status_code == 404


def test_list_responses(client: TestClient):
    """Test listing responses."""
    # Create test data
    user_response = client.post("/api/v1/users/", json={"name": "List Response User"})
    user_id = user_response.json()["id"]

    prompt_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    prompt_id = prompt_response.json()["id"]

    client.post(
        "/api/v1/responses/",
        json={
            "prompt_id": prompt_id,
            "user_id": user_id,
            "question_text": "Test?",
            "response_text": "Response",
        },
    )

    response = client.get("/api/v1/responses/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_responses_filter_by_category(client: TestClient):
    """Test listing responses filtered by category."""
    # Create test data
    user_response = client.post("/api/v1/users/", json={"name": "Filter Response User"})
    user_id = user_response.json()["id"]

    prompt_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    prompt_id = prompt_response.json()["id"]

    client.post(
        "/api/v1/responses/",
        json={
            "prompt_id": prompt_id,
            "user_id": user_id,
            "question_text": "Test?",
            "response_text": "Response",
            "category": "nutrition",
        },
    )

    response = client.get("/api/v1/responses/?category=nutrition")
    assert response.status_code == 200
    data = response.json()
    assert all(r["category"] == "nutrition" for r in data if r["category"])


def test_get_response(client: TestClient):
    """Test getting a response by ID."""
    # Create test data
    user_response = client.post("/api/v1/users/", json={"name": "Get Response User"})
    user_id = user_response.json()["id"]

    prompt_response = client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    prompt_id = prompt_response.json()["id"]

    create_response = client.post(
        "/api/v1/responses/",
        json={
            "prompt_id": prompt_id,
            "user_id": user_id,
            "question_text": "Test?",
            "response_text": "Get test response",
        },
    )
    response_id = create_response.json()["id"]

    response = client.get(f"/api/v1/responses/{response_id}")
    assert response.status_code == 200
    assert response.json()["response_text"] == "Get test response"


def test_get_response_not_found(client: TestClient):
    """Test getting a non-existent response."""
    response = client.get("/api/v1/responses/99999")
    assert response.status_code == 404
