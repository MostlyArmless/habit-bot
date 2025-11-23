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


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_prompt_notification(self, prompt_id: int) -> dict:
    """Send a push notification for a prompt.

    This is a placeholder - actual implementation will integrate
    with Firebase Cloud Messaging for Android notifications.

    Args:
        prompt_id: ID of the prompt to notify about
    """
    db = SessionLocal()
    try:
        prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            return {"success": False, "error": "Prompt not found"}

        user = db.query(User).filter(User.id == prompt.user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # TODO: Integrate with Firebase Cloud Messaging
        # For now, just log the notification
        logger.info(
            f"Would send notification to user {user.id} for prompt {prompt.id}: "
            f"{len(prompt.questions)} questions in categories {prompt.categories}"
        )

        return {
            "success": True,
            "prompt_id": prompt_id,
            "user_id": user.id,
        }

    except Exception as e:
        logger.error(f"Error sending notification for prompt {prompt_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}

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
        wake_time = user.wake_time or datetime.strptime("08:00:00", "%H:%M:%S").time()
        sleep_time = user.sleep_time or datetime.strptime("22:00:00", "%H:%M:%S").time()

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

        # Schedule 3-5 prompts throughout the day
        scheduled = 0
        prompt_times = _calculate_prompt_times(wake_time, sleep_time, num_prompts=4)

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


def _calculate_prompt_times(wake_time, sleep_time, num_prompts: int = 4) -> list:
    """Calculate evenly spaced prompt times between wake and sleep.

    Args:
        wake_time: User's wake time
        sleep_time: User's sleep time
        num_prompts: Number of prompts to schedule

    Returns:
        List of time objects for prompt scheduling
    """
    from datetime import time as dt_time

    # Convert to minutes since midnight for easier calculation
    wake_minutes = wake_time.hour * 60 + wake_time.minute
    sleep_minutes = sleep_time.hour * 60 + sleep_time.minute

    # Handle case where sleep time is after midnight
    if sleep_minutes < wake_minutes:
        sleep_minutes += 24 * 60

    # Calculate interval
    total_minutes = sleep_minutes - wake_minutes
    interval = total_minutes // (num_prompts + 1)

    times = []
    for i in range(1, num_prompts + 1):
        minutes = (wake_minutes + interval * i) % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        times.append(dt_time(hour=hours, minute=mins))

    return times
