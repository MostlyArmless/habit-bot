"""Notification API endpoints."""

from fastapi import APIRouter, HTTPException

from src.services.notifications import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.post("/test")
async def send_test_notification() -> dict:
    """Send a test notification to verify ntfy is working."""
    service = NotificationService()
    result = await service.send_test_notification()

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send"))

    return {"status": "sent", "message": "Test notification sent successfully"}


@router.post("/reminder/{reminder_id}")
async def send_reminder_notification(reminder_id: int) -> dict:
    """Manually trigger a notification for a specific reminder."""
    service = NotificationService()
    result = await service.send_reminder_notification(reminder_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send"))

    return {
        "status": "sent",
        "reminder_id": reminder_id,
        "reminder_url": result["reminder_url"],
    }
