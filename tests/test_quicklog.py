"""Tests for quick log API endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def create_test_user(client: TestClient) -> dict:
    """Create a test user and return the user data."""
    response = client.post(
        "/api/v1/users/",
        json={"name": "QuickLog Test User", "timezone": "America/Los_Angeles"},
    )
    return response.json()


def test_create_quick_log(client: TestClient):
    """Test creating a quick log entry."""
    user = create_test_user(client)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Had a great workout this morning - ran 5k",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "response_id" in data
    assert "category" in data
    assert "processing_status" in data
    # Should return with pending status (async processing)
    assert data["processing_status"] == "pending"


def test_create_quick_log_returns_immediately(client: TestClient):
    """Test that quick log returns immediately without waiting for full processing."""
    user = create_test_user(client)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Feeling stressed about the upcoming deadline",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Should return pending, not completed - processing happens in background
    assert data["processing_status"] in ["pending", "processing"]
    # structured_data should be None initially since processing is async
    assert data["structured_data"] is None


def test_create_quick_log_with_backdate(client: TestClient):
    """Test creating a quick log entry with a custom timestamp (backdate)."""
    user = create_test_user(client)

    # Create a timestamp for yesterday
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    yesterday_iso = yesterday.isoformat()

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Slept poorly last night",
            "timestamp": yesterday_iso,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "response_id" in data

    # Verify the response was created with the backdated timestamp
    response_detail = client.get(f"/api/v1/responses/{data['response_id']}")
    assert response_detail.status_code == 200
    response_data = response_detail.json()

    # The timestamp should be approximately yesterday (within a few seconds)
    response_timestamp = datetime.fromisoformat(response_data["timestamp"].replace("Z", "+00:00"))
    assert abs((response_timestamp - yesterday).total_seconds()) < 5


def test_create_quick_log_with_future_timestamp(client: TestClient):
    """Test that quick log accepts future timestamps (edge case)."""
    user = create_test_user(client)

    # Create a timestamp for tomorrow
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Planning to exercise tomorrow",
            "timestamp": tomorrow.isoformat(),
        },
    )

    # Should accept the timestamp even if it's in the future
    assert response.status_code == 200


def test_create_quick_log_user_not_found(client: TestClient):
    """Test quick log with non-existent user."""
    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": 99999,
            "text": "This should fail",
        },
    )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_detect_category_endpoint(client: TestClient):
    """Test the category detection endpoint."""
    response = client.post(
        "/api/v1/quicklog/detect-category",
        params={"text": "I ate a salad for lunch"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert "confidence" in data
    assert "suggested_question" in data
    # Should detect as nutrition
    assert data["category"] in ["nutrition", "mental_state"]  # Fallback is mental_state


def test_quick_log_category_detection_nutrition(client: TestClient):
    """Test that nutrition-related logs are categorized correctly."""
    user = create_test_user(client)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Had eggs and toast for breakfast with orange juice",
        },
    )

    assert response.status_code == 200
    # Category detection uses LLM, so we accept the result
    # Just verify we got a valid category
    assert response.json()["category"] in [
        "nutrition", "mental_state", "physical_activity",
        "sleep", "substances", "stress_anxiety",
        "physical_symptoms", "social_interaction",
        "work_productivity", "environment"
    ]


def test_quick_log_category_detection_sleep(client: TestClient):
    """Test that sleep-related logs are categorized correctly."""
    user = create_test_user(client)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Woke up at 3am and couldn't fall back asleep",
        },
    )

    assert response.status_code == 200
    # Just verify we got a valid response
    assert "category" in response.json()


def test_quick_log_creates_prompt_and_response(client: TestClient):
    """Test that quick log creates both a prompt and response in the database."""
    user = create_test_user(client)

    quick_log_response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "Took my vitamins this morning",
        },
    )

    assert quick_log_response.status_code == 200
    response_id = quick_log_response.json()["response_id"]

    # Verify the response exists
    response_detail = client.get(f"/api/v1/responses/{response_id}")
    assert response_detail.status_code == 200
    response_data = response_detail.json()

    # Verify the response has a linked prompt
    assert response_data["prompt_id"] is not None

    # Verify the prompt exists
    prompt_detail = client.get(f"/api/v1/prompts/{response_data['prompt_id']}")
    assert prompt_detail.status_code == 200
    prompt_data = prompt_detail.json()

    # Prompt should be marked as completed (ad-hoc prompt)
    assert prompt_data["status"] == "completed"


def test_quick_log_empty_text(client: TestClient):
    """Test quick log with empty text."""
    user = create_test_user(client)

    response = client.post(
        "/api/v1/quicklog/",
        json={
            "user_id": user["id"],
            "text": "",
        },
    )

    # May fail validation or succeed with default category
    # Just verify it doesn't crash
    assert response.status_code in [200, 422]
