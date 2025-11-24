"""Prompt scheduling and notification tasks."""

import logging
from datetime import datetime, timedelta, timezone

from src.celery_app import app
from src.database import SessionLocal
from src.models.prompt import Prompt, PromptStatus
from src.models.user import User

logger = logging.getLogger(__name__)


@app.task
def schedule_pending_prompts() -> dict:
    """Find prompts that are ready to be sent and mark them.

    This periodic task checks for prompts where:
    - scheduled_time has passed
    - status is still 'scheduled'

    It marks them as 'sent' and queues notifications.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find prompts ready to send
        ready_prompts = (
            db.query(Prompt)
            .filter(Prompt.status == PromptStatus.SCHEDULED.value)
            .filter(Prompt.scheduled_time <= now)
            .limit(50)
            .all()
        )

        sent = 0
        for prompt in ready_prompts:
            prompt.status = PromptStatus.SENT.value
            prompt.sent_at = now
            db.commit()

            # Queue notification task
            send_prompt_notification.delay(prompt.id)
            sent += 1

        logger.info(f"Sent {sent} prompts")
        return {"sent": sent}

    finally:
        db.close()


def run_async(coro):
    """Run an async coroutine in a sync context."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_prompt_notification(self, prompt_id: int) -> dict:
    """Send a push notification for a prompt via ntfy.

    Args:
        prompt_id: ID of the prompt to notify about
    """
    from src.services.notifications import NotificationService

    db = SessionLocal()
    try:
        prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            return {"success": False, "error": "Prompt not found"}

        # Send ntfy notification
        notification_service = NotificationService()
        result = run_async(notification_service.send_prompt_notification(prompt_id))

        if result["success"]:
            logger.info(
                f"Sent ntfy notification for prompt {prompt.id}: "
                f"{len(prompt.questions)} questions in categories {prompt.categories}"
            )
        else:
            logger.warning(f"Failed to send ntfy notification: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Error sending notification for prompt {prompt_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@app.task
def create_daily_prompts_for_all_users() -> dict:
    """Create scheduled prompts for all users.

    This periodic task runs daily to generate prompts for all active users.
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total_scheduled = 0

        for user in users:
            result = create_scheduled_prompts_for_user(user.id)
            if result.get("success"):
                total_scheduled += result.get("scheduled", 0)

        logger.info(f"Daily prompt generation: scheduled {total_scheduled} prompts for {len(users)} users")
        return {"success": True, "total_scheduled": total_scheduled, "users": len(users)}

    finally:
        db.close()


@app.task
def create_scheduled_prompts_for_user(user_id: int) -> dict:
    """Create scheduled prompts for a user based on their preferences.

    This task generates prompts for the upcoming period based on:
    - User's wake/sleep times
    - Category preferences
    - Response history (to avoid over-asking)

    Args:
        user_id: ID of the user to schedule prompts for
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Get user's schedule preferences
        # Prompts only allowed between wake_time and screens_off_time
        wake_time = user.wake_time or datetime.strptime("08:00:00", "%H:%M:%S").time()
        # Use screens_off_time as the cutoff (fall back to sleep_time, then default)
        end_time = user.screens_off_time or user.sleep_time or datetime.strptime("21:00:00", "%H:%M:%S").time()

        # Calculate prompts for today
        now = datetime.now(timezone.utc)
        today = now.date()

        # Default categories to check
        categories = [
            "mental_state",
            "sleep",
            "nutrition",
            "physical_activity",
            "stress_anxiety",
        ]

        # Schedule prompts between wake and screens-off times
        scheduled = 0
        prompt_times = _calculate_prompt_times(wake_time, end_time, num_prompts=4)

        for i, prompt_time in enumerate(prompt_times):
            scheduled_dt = datetime.combine(today, prompt_time, tzinfo=timezone.utc)

            # Skip if time has already passed
            if scheduled_dt <= now:
                continue

            # Check if prompt already exists for this time
            existing = (
                db.query(Prompt)
                .filter(Prompt.user_id == user_id)
                .filter(Prompt.scheduled_time == scheduled_dt)
                .first()
            )
            if existing:
                continue

            # Select categories for this prompt (rotate through them)
            prompt_categories = [categories[i % len(categories)]]

            prompt = Prompt(
                user_id=user_id,
                scheduled_time=scheduled_dt,
                questions={f"q1": f"How are you doing with your {prompt_categories[0]}?"},
                categories=prompt_categories,
                status=PromptStatus.SCHEDULED.value,
            )
            db.add(prompt)
            db.commit()
            scheduled += 1

        logger.info(f"Scheduled {scheduled} prompts for user {user_id}")
        return {"success": True, "scheduled": scheduled}

    finally:
        db.close()


def _calculate_prompt_times(wake_time, end_time, num_prompts: int = 4) -> list:
    """Calculate evenly spaced prompt times between wake and screens-off.

    Args:
        wake_time: User's wake time
        end_time: User's screens-off time (or sleep time as fallback)
        num_prompts: Number of prompts to schedule

    Returns:
        List of time objects for prompt scheduling
    """
    from datetime import time as dt_time

    # Convert to minutes since midnight for easier calculation
    wake_minutes = wake_time.hour * 60 + wake_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    # Handle case where end time is after midnight
    if end_minutes < wake_minutes:
        end_minutes += 24 * 60

    # Calculate interval
    total_minutes = end_minutes - wake_minutes
    interval = total_minutes // (num_prompts + 1)

    times = []
    for i in range(1, num_prompts + 1):
        minutes = (wake_minutes + interval * i) % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        times.append(dt_time(hour=hours, minute=mins))

    return times
