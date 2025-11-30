"""Reminder scheduling and notification tasks."""

import logging
from datetime import datetime, timedelta, timezone

from src.celery_app import app
from src.database import SessionLocal
from src.models.reminder import Reminder, ReminderStatus
from src.models.user import User

logger = logging.getLogger(__name__)


@app.task
def schedule_pending_reminders() -> dict:
    """Find reminders that are ready to be sent and mark them.

    This periodic task checks for reminders where:
    - scheduled_time has passed
    - status is still 'scheduled'

    It marks them as 'sent' and queues notifications.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find reminders ready to send
        ready_reminders = (
            db.query(Reminder)
            .filter(Reminder.status == ReminderStatus.SCHEDULED.value)
            .filter(Reminder.scheduled_time <= now)
            .limit(50)
            .all()
        )

        sent = 0
        for reminder in ready_reminders:
            reminder.status = ReminderStatus.SENT.value
            reminder.sent_at = now
            db.commit()

            # Queue notification task
            send_reminder_notification.delay(reminder.id)
            sent += 1

        logger.info(f"Sent {sent} reminders")
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
def send_reminder_notification(self, reminder_id: int) -> dict:
    """Send a push notification for a reminder via ntfy.

    Args:
        reminder_id: ID of the reminder to notify about
    """
    from src.services.notifications import NotificationService

    db = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return {"success": False, "error": "Reminder not found"}

        # Send ntfy notification
        notification_service = NotificationService()
        result = run_async(notification_service.send_reminder_notification(reminder_id))

        if result["success"]:
            logger.info(
                f"Sent ntfy notification for reminder {reminder.id}: "
                f"{len(reminder.questions)} questions in categories {reminder.categories}"
            )
        else:
            logger.warning(f"Failed to send ntfy notification: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Error sending notification for reminder {reminder_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@app.task
def create_daily_reminders_for_all_users() -> dict:
    """Create scheduled reminders for all users.

    This periodic task runs daily to generate reminders for all active users.
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total_scheduled = 0

        for user in users:
            result = create_scheduled_reminders_for_user(user.id)
            if result.get("success"):
                total_scheduled += result.get("scheduled", 0)

        logger.info(f"Daily reminder generation: scheduled {total_scheduled} reminders for {len(users)} users")
        return {"success": True, "total_scheduled": total_scheduled, "users": len(users)}

    finally:
        db.close()


@app.task
def create_scheduled_reminders_for_user(user_id: int) -> dict:
    """Create scheduled reminders for a user based on their preferences.

    This task generates reminders for the upcoming period based on:
    - User's wake/sleep times (in user's local timezone)
    - Category preferences
    - Response history (to avoid over-asking)
    - Category frequency limits (e.g., sleep only once per day)

    Args:
        user_id: ID of the user to schedule reminders for
    """
    import pytz
    from src.services.reminder_intelligence import ReminderIntelligenceService

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Get user's timezone (default to UTC if not set)
        user_tz = pytz.timezone(user.timezone) if user.timezone else pytz.UTC

        # Get user's schedule preferences (in their local timezone)
        # Reminders only allowed between wake_time and screens_off_time
        wake_time = user.wake_time or datetime.strptime("08:00:00", "%H:%M:%S").time()
        # Use screens_off_time as the cutoff (fall back to sleep_time, then default)
        end_time = user.screens_off_time or user.sleep_time or datetime.strptime("21:00:00", "%H:%M:%S").time()

        # Get current time in user's timezone
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(user_tz)
        today_local = now_local.date()

        # Use intelligence service to generate smart reminders
        intelligence_service = ReminderIntelligenceService()
        reminder_data = run_async(intelligence_service.generate_intelligent_reminder(user_id, db))

        # Calculate time window
        wake_minutes = wake_time.hour * 60 + wake_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        if end_minutes <= wake_minutes:
            end_minutes += 24 * 60  # Handle overnight span

        total_minutes = end_minutes - wake_minutes

        # Generate 3-4 reminder times spread throughout the day
        num_reminders = min(4, max(2, len(reminder_data["questions"]) // 3))
        reminder_times = _calculate_reminder_times(wake_time, end_time, num_reminders=num_reminders)

        # Distribute questions across reminders
        scheduled = 0
        questions_per_reminder = max(1, len(reminder_data["questions"]) // num_reminders)
        question_keys = list(reminder_data["questions"].keys())

        for i, reminder_time in enumerate(reminder_times):
            # Create datetime in user's local timezone
            scheduled_local = user_tz.localize(datetime.combine(today_local, reminder_time))

            # Skip if time has already passed
            if scheduled_local <= now_local:
                continue

            # Convert to UTC for storage
            scheduled_utc = scheduled_local.astimezone(pytz.UTC).replace(tzinfo=None)

            # Check if reminder already exists for this time
            existing = (
                db.query(Reminder)
                .filter(Reminder.user_id == user_id)
                .filter(Reminder.scheduled_time == scheduled_utc)
                .first()
            )
            if existing:
                continue

            # Distribute questions across reminders
            start_idx = i * questions_per_reminder
            end_idx = start_idx + questions_per_reminder
            if i == num_reminders - 1:
                # Last reminder gets any remaining questions
                end_idx = len(question_keys)

            reminder_questions = {
                key: reminder_data["questions"][key]
                for key in question_keys[start_idx:end_idx]
                if start_idx < len(question_keys)
            }

            if not reminder_questions:
                continue

            reminder = Reminder(
                user_id=user_id,
                scheduled_time=scheduled_utc,
                questions=reminder_questions,
                categories=reminder_data["categories"],
                status=ReminderStatus.SCHEDULED.value,
            )
            db.add(reminder)
            db.commit()
            scheduled += 1

        logger.info(
            f"Scheduled {scheduled} intelligent reminders for user {user_id} in timezone {user.timezone}. "
            f"Reasoning: {reminder_data['reasoning']}"
        )
        return {"success": True, "scheduled": scheduled, "reasoning": reminder_data["reasoning"]}

    finally:
        db.close()


def _calculate_reminder_times(wake_time, end_time, num_reminders: int = 4) -> list:
    """Calculate evenly spaced reminder times between wake and screens-off.

    Args:
        wake_time: User's wake time
        end_time: User's screens-off time (or sleep time as fallback)
        num_reminders: Number of reminders to schedule

    Returns:
        List of time objects for reminder scheduling
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
    interval = total_minutes // (num_reminders + 1)

    times = []
    for i in range(1, num_reminders + 1):
        minutes = (wake_minutes + interval * i) % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        times.append(dt_time(hour=hours, minute=mins))

    return times
