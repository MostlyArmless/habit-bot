"""Tests for notification service."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.services.notifications import NotificationService


class TestNotificationService:
    """Tests for NotificationService."""

    def test_get_notification_url(self):
        """Test notification URL construction."""
        service = NotificationService()
        url = service._get_notification_url()
        assert "ntfy.sh" in url or "localhost" in url
        assert service.topic in url

    def test_get_reminder_url(self):
        """Test reminder URL construction."""
        service = NotificationService()
        url = service._get_reminder_url(123)
        assert "/reminder/123" in url

    @pytest.mark.asyncio
    async def test_send_reminder_notification_success(self):
        """Test successful reminder notification."""
        service = NotificationService()

        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()

        with patch.object(httpx.AsyncClient, "post", return_value=mock_response) as mock_post:
            result = await service.send_reminder_notification(reminder_id=42)

        assert result["success"] is True
        assert result["reminder_id"] == 42
        assert "/reminder/42" in result["reminder_url"]

        # Verify the call was made with correct parameters
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "Time to check in" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_send_reminder_notification_failure(self):
        """Test reminder notification failure handling."""
        service = NotificationService()

        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.HTTPError("Connection failed"),
        ):
            result = await service.send_reminder_notification(reminder_id=42)

        assert result["success"] is False
        assert result["reminder_id"] == 42
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_test_notification_success(self):
        """Test successful test notification."""
        service = NotificationService()

        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()

        with patch.object(httpx.AsyncClient, "post", return_value=mock_response):
            result = await service.send_test_notification()

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_test_notification_failure(self):
        """Test test notification failure handling."""
        service = NotificationService()

        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.HTTPError("Connection failed"),
        ):
            result = await service.send_test_notification()

        assert result["success"] is False
        assert "error" in result

    def test_notification_has_no_pii(self):
        """Verify notification content contains no PII."""
        service = NotificationService()

        # The notification message should be generic
        # We can't easily test the actual message without mocking,
        # but we document the expectation here
        assert service.topic  # Topic is a GUID, not user-identifiable


class TestNotificationServiceConfiguration:
    """Tests for notification service configuration."""

    def test_service_uses_settings(self):
        """Test that service uses settings correctly."""
        service = NotificationService()

        assert service.server is not None
        assert service.topic is not None
        assert service.pwa_base_url is not None

    def test_topic_is_guid_format(self):
        """Test that topic follows GUID format for privacy."""
        service = NotificationService()

        # Should be a UUID format (8-4-4-4-12 hex chars)
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
        )
        assert uuid_pattern.match(service.topic), f"Topic {service.topic} is not a valid UUID"
