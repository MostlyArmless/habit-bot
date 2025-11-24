"""Tests for reminder endpoints."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_create_reminder(client: TestClient):
    """Test creating a reminder."""
    # Create a user first
    user_response = client.post("/api/v1/users/", json={"name": "Reminder Test User"})
    user_id = user_response.json()["id"]

    scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/reminders/",
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


def test_create_reminder_user_not_found(client: TestClient):
    """Test creating a reminder for non-existent user."""
    response = client.post(
        "/api/v1/reminders/",
        json={
            "user_id": 99999,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test question"},
        },
    )
    assert response.status_code == 404


def test_list_reminders(client: TestClient):
    """Test listing reminders."""
    # Create a user and reminder
    user_response = client.post("/api/v1/users/", json={"name": "List Reminders User"})
    user_id = user_response.json()["id"]

    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )

    response = client.get("/api/v1/reminders/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_reminders_filter_by_user(client: TestClient):
    """Test listing reminders filtered by user."""
    # Create a user and reminder
    user_response = client.post("/api/v1/users/", json={"name": "Filter User"})
    user_id = user_response.json()["id"]

    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )

    response = client.get(f"/api/v1/reminders/?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert all(r["user_id"] == user_id for r in data)


def test_get_reminder(client: TestClient):
    """Test getting a reminder by ID."""
    # Create a user and reminder
    user_response = client.post("/api/v1/users/", json={"name": "Get Reminder User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test question"},
        },
    )
    reminder_id = create_response.json()["id"]

    response = client.get(f"/api/v1/reminders/{reminder_id}")
    assert response.status_code == 200
    assert response.json()["id"] == reminder_id


def test_acknowledge_reminder(client: TestClient):
    """Test acknowledging a reminder."""
    # Create a user and reminder
    user_response = client.post("/api/v1/users/", json={"name": "Ack Reminder User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    reminder_id = create_response.json()["id"]

    response = client.post(f"/api/v1/reminders/{reminder_id}/acknowledge")
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


def test_update_reminder_status(client: TestClient):
    """Test updating a reminder's status."""
    # Create a user and reminder
    user_response = client.post("/api/v1/users/", json={"name": "Update Reminder User"})
    user_id = user_response.json()["id"]

    create_response = client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": datetime.utcnow().isoformat(),
            "questions": {"q1": "Test"},
        },
    )
    reminder_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/reminders/{reminder_id}", json={"status": "sent"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"


def test_get_upcoming_reminders(client: TestClient):
    """Test getting upcoming scheduled reminders."""
    # Create a user
    user_response = client.post("/api/v1/users/", json={"name": "Upcoming Reminder User"})
    user_id = user_response.json()["id"]

    # Create a future reminder (1 hour from now)
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time,
            "questions": {"q1": "How is your energy level?"},
            "categories": ["mental_state"],
        },
    )

    # Create another future reminder (2 hours from now)
    future_time_2 = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time_2,
            "questions": {"q1": "How was your lunch?"},
            "categories": ["nutrition"],
        },
    )

    # Get upcoming reminders
    response = client.get(f"/api/v1/reminders/upcoming?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify reminders are sorted by scheduled_time ascending
    if len(data) >= 2:
        first_time = data[0]["scheduled_time"]
        second_time = data[1]["scheduled_time"]
        assert first_time <= second_time


def test_get_upcoming_reminders_empty(client: TestClient):
    """Test getting upcoming reminders when none exist."""
    user_response = client.post("/api/v1/users/", json={"name": "No Upcoming User"})
    user_id = user_response.json()["id"]

    response = client.get(f"/api/v1/reminders/upcoming?user_id={user_id}")
    assert response.status_code == 200
    assert response.json() == []


def test_get_upcoming_reminders_excludes_past(client: TestClient):
    """Test that past reminders are not included in upcoming."""
    user_response = client.post("/api/v1/users/", json={"name": "Past Reminder User"})
    user_id = user_response.json()["id"]

    # Create a past reminder
    past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": past_time,
            "questions": {"q1": "Past question"},
        },
    )

    # Create a future reminder
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    client.post(
        "/api/v1/reminders/",
        json={
            "user_id": user_id,
            "scheduled_time": future_time,
            "questions": {"q1": "Future question"},
        },
    )

    # Get upcoming - should only include future
    response = client.get(f"/api/v1/reminders/upcoming?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()

    # All returned reminders should be in the future
    now = datetime.utcnow()
    for reminder in data:
        scheduled = datetime.fromisoformat(reminder["scheduled_time"].replace("Z", ""))
        assert scheduled > now


def test_generate_reminders_for_user(client: TestClient):
    """Test generating reminders automatically for a user."""
    # Create a user with wake/sleep times
    user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Generate Reminder User",
            "wake_time": "08:00:00",
            "sleep_time": "22:00:00",
        },
    )
    user_id = user_response.json()["id"]

    # Generate reminders
    response = client.post(f"/api/v1/reminders/generate?user_id={user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "scheduled" in data


def test_generate_reminders_user_not_found(client: TestClient):
    """Test generating reminders for non-existent user."""
    response = client.post("/api/v1/reminders/generate?user_id=99999")
    assert response.status_code == 404
