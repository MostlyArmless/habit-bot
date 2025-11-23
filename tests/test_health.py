"""Tests for health endpoints."""

from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Habit Bot API"
    assert data["version"] == "0.1.0"


def test_health_check(client: TestClient):
    """Test basic health check."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_db_health_check(client: TestClient):
    """Test database health check."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
