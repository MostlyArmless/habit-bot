"""Integration tests for notification API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestNotificationEndpoints:
    """Tests for notification API endpoints."""

    def test_send_test_notification_success(self, client: TestClient):
        """Test sending a test notification."""
        with patch(
            "src.services.notifications.NotificationService.send_test_notification",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            response = client.post("/api/v1/notifications/test")

        assert response.status_code == 200
        assert response.json()["status"] == "sent"

    def test_send_test_notification_failure(self, client: TestClient):
        """Test handling test notification failure."""
        with patch(
            "src.services.notifications.NotificationService.send_test_notification",
            new_callable=AsyncMock,
            return_value={"success": False, "error": "Connection refused"},
        ):
            response = client.post("/api/v1/notifications/test")

        assert response.status_code == 500

    def test_send_reminder_notification(self, client: TestClient):
        """Test sending a reminder notification."""
        with patch(
            "src.services.notifications.NotificationService.send_reminder_notification",
            new_callable=AsyncMock,
            return_value={
                "success": True,
                "reminder_id": 123,
                "reminder_url": "http://localhost:3000/reminder/123",
            },
        ):
            response = client.post("/api/v1/notifications/reminder/123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["reminder_id"] == 123
        assert "/reminder/123" in data["reminder_url"]


class TestNotificationFlow:
    """Integration tests for the full notification flow."""

    def test_create_reminder_and_notify(self, client: TestClient):
        """Test creating a reminder and triggering notification."""
        # Create a user
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "Notification Test User"},
        )
        user_id = user_response.json()["id"]

        # Create a reminder
        reminder_response = client.post(
            "/api/v1/reminders/",
            json={
                "user_id": user_id,
                "scheduled_time": datetime.now(timezone.utc).isoformat(),
                "questions": {"q1": "How are you feeling?"},
                "categories": ["mental_state"],
            },
        )
        assert reminder_response.status_code == 201
        reminder_id = reminder_response.json()["id"]

        # Trigger notification (mocked)
        with patch(
            "src.services.notifications.NotificationService.send_reminder_notification",
            new_callable=AsyncMock,
            return_value={
                "success": True,
                "reminder_id": reminder_id,
                "reminder_url": f"http://localhost:3000/reminder/{reminder_id}",
            },
        ):
            notify_response = client.post(f"/api/v1/notifications/reminder/{reminder_id}")

        assert notify_response.status_code == 200
        assert notify_response.json()["reminder_id"] == reminder_id

    def test_reminder_url_format(self, client: TestClient):
        """Test that notification URL format is correct."""
        with patch(
            "src.services.notifications.NotificationService.send_reminder_notification",
            new_callable=AsyncMock,
        ) as mock_notify:
            mock_notify.return_value = {
                "success": True,
                "reminder_id": 42,
                "reminder_url": "http://localhost:3000/reminder/42",
            }

            response = client.post("/api/v1/notifications/reminder/42")

            assert response.status_code == 200
            # Verify URL follows expected PWA route structure
            assert "/reminder/42" in response.json()["reminder_url"]
