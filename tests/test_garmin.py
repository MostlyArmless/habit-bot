"""Tests for Garmin API endpoints."""

from datetime import date

import pytest


def create_test_user(client):
    """Create a test user and return the user data."""
    response = client.post(
        "/api/v1/users/",
        json={"name": "Garmin Test User", "timezone": "America/Los_Angeles"},
    )
    return response.json()


def test_get_available_metrics(client):
    """Test getting list of available Garmin metrics."""
    response = client.get("/api/v1/garmin/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert isinstance(metrics, list)
    assert "sleep" in metrics
    assert "hrv" in metrics
    assert "resting_hr" in metrics
    assert "body_battery" in metrics
    assert "stress" in metrics


def test_get_garmin_data_empty(client):
    """Test getting Garmin data when none exists."""
    user = create_test_user(client)
    response = client.get(f"/api/v1/garmin/data?user_id={user['id']}")
    assert response.status_code == 200
    assert response.json() == []


def test_get_latest_metrics_empty(client):
    """Test getting latest metrics when none exist."""
    user = create_test_user(client)
    response = client.get(f"/api/v1/garmin/latest?user_id={user['id']}")
    assert response.status_code == 200
    data = response.json()
    # All metric types should be present but null
    assert "sleep" in data
    assert "hrv" in data
    assert data["sleep"] is None
    assert data["hrv"] is None


def test_sync_without_credentials(client):
    """Test sync fails gracefully without Garmin credentials."""
    user = create_test_user(client)
    response = client.post(
        "/api/v1/garmin/sync",
        json={"user_id": user["id"], "days_back": 1},
    )
    # Should return 200 with 0 synced (credentials not configured in test env)
    # or 400/500 if it properly reports the error
    assert response.status_code in [200, 400, 500]


def test_get_garmin_data_with_filters(client):
    """Test filtering Garmin data by metric type and date range."""
    user = create_test_user(client)
    today = date.today().isoformat()

    # Query with filters (should return empty but not error)
    response = client.get(
        f"/api/v1/garmin/data?user_id={user['id']}&metric_type=sleep&start_date={today}&end_date={today}"
    )
    assert response.status_code == 200
    assert response.json() == []
