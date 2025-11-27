"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from src.config import get_settings

settings = get_settings()

app = Celery(
    "habit_bot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks.llm_tasks", "src.tasks.reminder_tasks", "src.tasks.summary_tasks", "src.tasks.garmin_tasks"],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Los_Angeles",  # Use Pacific timezone for cron schedules
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Rate limiting for LLM calls
    task_default_rate_limit="10/m",
    # Result expiration
    result_expires=3600,  # 1 hour
    # Beat schedule for periodic tasks
    beat_schedule={
        "schedule-reminders-every-minute": {
            "task": "src.tasks.reminder_tasks.schedule_pending_reminders",
            "schedule": 60.0,  # Every minute
        },
        "process-pending-responses-every-30s": {
            "task": "src.tasks.llm_tasks.process_pending_responses",
            "schedule": 30.0,  # Every 30 seconds
        },
        "create-daily-reminders": {
            "task": "src.tasks.reminder_tasks.create_daily_reminders_for_all_users",
            "schedule": 3600.0,  # Every hour (will skip if reminders already exist)
        },
        "generate-summaries-every-hour": {
            "task": "summary_tasks.generate_summaries_for_all_users",
            "schedule": 3600.0,  # Every hour
        },
        "sync-garmin-daily-at-8:30am": {
            "task": "garmin_tasks.sync_garmin_for_all_users",
            "schedule": crontab(hour=8, minute=30),  # 8:30am Pacific (respects DST)
        },
    },
)
