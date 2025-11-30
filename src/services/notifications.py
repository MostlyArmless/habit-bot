"""Notification service for sending push notifications via ntfy."""

import logging
from typing import Any

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications via ntfy.sh."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.server = self.settings.ntfy_server
        self.topic = self.settings.ntfy_topic
        self.pwa_base_url = self.settings.pwa_base_url
        self.timeout = 10.0

    def _get_notification_url(self) -> str:
        """Get the full ntfy URL for publishing."""
        return f"{self.server}/{self.topic}"

    def _get_reminder_url(self, reminder_id: int) -> str:
        """Get the PWA URL for a specific reminder."""
        return f"{self.pwa_base_url}/reminder/{reminder_id}"

    def _get_story_url(self) -> str:
        """Get the PWA URL for the story submission page."""
        return f"{self.pwa_base_url}/story"

    async def send_reminder_notification(self, reminder_id: int) -> dict[str, Any]:
        """Send a notification for a reminder check-in.

        Args:
            reminder_id: ID of the reminder to notify about

        Returns:
            dict with success status and any error info
        """
        reminder_url = self._get_reminder_url(reminder_id)

        # Generic message with no PII
        headers = {
            "Title": "Time to check in",
            "Priority": "high",
            "Tags": "clipboard",
            "Click": reminder_url,
            "Actions": f"view, Open, {reminder_url}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._get_notification_url(),
                    content="Tap to answer a few quick questions",
                    headers=headers,
                )
                response.raise_for_status()

                logger.info(f"Sent notification for reminder {reminder_id}")
                return {
                    "success": True,
                    "reminder_id": reminder_id,
                    "reminder_url": reminder_url,
                }

        except httpx.HTTPError as e:
            logger.error(f"Failed to send notification for reminder {reminder_id}: {e}")
            return {
                "success": False,
                "reminder_id": reminder_id,
                "error": str(e),
            }

    async def send_story_reminder(self, user_id: int) -> dict[str, Any]:
        """Send a notification to remind the user to tell a story.

        Args:
            user_id: ID of the user to notify

        Returns:
            dict with success status and any error info
        """
        story_url = self._get_story_url()

        headers = {
            "Title": "Story Time",
            "Priority": "default",
            "Tags": "book",
            "Click": story_url,
            "Actions": f"view, Tell Story, {story_url}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._get_notification_url(),
                    content="Time to practice storytelling! Tell me about something interesting that happened.",
                    headers=headers,
                )
                response.raise_for_status()

                logger.info(f"Sent story reminder notification to user {user_id}")
                return {
                    "success": True,
                    "user_id": user_id,
                    "story_url": story_url,
                }

        except httpx.HTTPError as e:
            logger.error(f"Failed to send story reminder for user {user_id}: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e),
            }

    async def send_test_notification(self) -> dict[str, Any]:
        """Send a test notification to verify ntfy is working.

        Returns:
            dict with success status
        """
        headers = {
            "Title": "Habit Bot Test",
            "Priority": "low",
            "Tags": "white_check_mark",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._get_notification_url(),
                    content="Test notification - ntfy is working!",
                    headers=headers,
                )
                response.raise_for_status()

                logger.info("Sent test notification")
                return {"success": True}

        except httpx.HTTPError as e:
            logger.error(f"Failed to send test notification: {e}")
            return {"success": False, "error": str(e)}


def get_notification_service() -> NotificationService:
    """Get a notification service instance."""
    return NotificationService()
