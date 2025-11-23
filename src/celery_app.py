"""Celery application configuration."""

from celery import Celery

from src.config import get_settings

settings = get_settings()

app = Celery(
    "habit_bot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks.llm_tasks", "src.tasks.prompt_tasks"],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
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
        "schedule-prompts-every-minute": {
            "task": "src.tasks.prompt_tasks.schedule_pending_prompts",
            "schedule": 60.0,  # Every minute
        },
        "process-pending-responses-every-30s": {
            "task": "src.tasks.llm_tasks.process_pending_responses",
            "schedule": 30.0,  # Every 30 seconds
        },
    },
)
