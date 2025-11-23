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

    def _get_prompt_url(self, prompt_id: int) -> str:
        """Get the PWA URL for a specific prompt."""
        return f"{self.pwa_base_url}/prompt/{prompt_id}"

    async def send_prompt_notification(self, prompt_id: int) -> dict[str, Any]:
        """Send a notification for a prompt check-in.

        Args:
            prompt_id: ID of the prompt to notify about

        Returns:
            dict with success status and any error info
        """
        prompt_url = self._get_prompt_url(prompt_id)

        # Generic message with no PII
        headers = {
            "Title": "Time to check in",
            "Priority": "high",
            "Tags": "clipboard",
            "Click": prompt_url,
            "Actions": f"view, Open, {prompt_url}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._get_notification_url(),
                    content="Tap to answer a few quick questions",
                    headers=headers,
                )
                response.raise_for_status()

                logger.info(f"Sent notification for prompt {prompt_id}")
                return {
                    "success": True,
                    "prompt_id": prompt_id,
                    "prompt_url": prompt_url,
                }

        except httpx.HTTPError as e:
            logger.error(f"Failed to send notification for prompt {prompt_id}: {e}")
            return {
                "success": False,
                "prompt_id": prompt_id,
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
