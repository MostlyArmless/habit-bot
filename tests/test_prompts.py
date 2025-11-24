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


def test_get_upcoming_prompts(client: TestClient):
    """Test getting upcoming scheduled prompts."""
    # Create a user
    user_response = client.post("/api/v1/users/", json={"name": "Upcoming Prompt User"})
    user_id = user_response.json()["id"]

    # Create a future prompt (1 hour from now)
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time,
            "questions": {"q1": "How is your energy level?"},
            "categories": ["mental_state"],
        },
    )

    # Create another future prompt (2 hours from now)
    future_time_2 = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time_2,
            "questions": {"q1": "How was your lunch?"},
            "categories": ["nutrition"],
        },
    )

    # Get upcoming prompts
    response = client.get(f"/api/v1/prompts/upcoming?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify prompts are sorted by scheduled_time ascending
    if len(data) >= 2:
        first_time = data[0]["scheduled_time"]
        second_time = data[1]["scheduled_time"]
        assert first_time <= second_time


def test_get_upcoming_prompts_empty(client: TestClient):
    """Test getting upcoming prompts when none exist."""
    user_response = client.post("/api/v1/users/", json={"name": "No Upcoming User"})
    user_id = user_response.json()["id"]

    response = client.get(f"/api/v1/prompts/upcoming?user_id={user_id}")
    assert response.status_code == 200
    assert response.json() == []


def test_get_upcoming_prompts_excludes_past(client: TestClient):
    """Test that past prompts are not included in upcoming."""
    user_response = client.post("/api/v1/users/", json={"name": "Past Prompt User"})
    user_id = user_response.json()["id"]

    # Create a past prompt
    past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": past_time,
            "questions": {"q1": "Past question"},
        },
    )

    # Create a future prompt
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/prompts/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time,
            "questions": {"q1": "Future question"},
        },
    )

    # Get upcoming - should only include future
    response = client.get(f"/api/v1/prompts/upcoming?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()

    # All returned prompts should be in the future
    now = datetime.utcnow()
    for prompt in data:
        scheduled = datetime.fromisoformat(prompt["scheduled_time"].replace("Z", ""))
        assert scheduled > now


def test_generate_prompts_for_user(client: TestClient):
    """Test generating prompts automatically for a user."""
    # Create a user with wake/sleep times
    user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Generate Prompt User",
            "wake_time": "08:00:00",
            "sleep_time": "22:00:00",
        },
    )
    user_id = user_response.json()["id"]

    # Generate prompts
    response = client.post(f"/api/v1/prompts/generate?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "scheduled" in data


def test_generate_prompts_user_not_found(client: TestClient):
    """Test generating prompts for non-existent user."""
    response = client.post("/api/v1/prompts/generate?user_id=99999")
    assert response.status_code == 404
