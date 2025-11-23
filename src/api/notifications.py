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


@router.post("/prompt/{prompt_id}")
async def send_prompt_notification(prompt_id: int) -> dict:
    """Manually trigger a notification for a specific prompt."""
    service = NotificationService()
    result = await service.send_prompt_notification(prompt_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send"))

    return {
        "status": "sent",
        "prompt_id": prompt_id,
        "prompt_url": result["prompt_url"],
    }
