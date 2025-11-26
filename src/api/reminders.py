"""Reminder API endpoints for scheduled check-in notifications."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.reminder import Reminder as ReminderModel
from src.models.reminder import ReminderStatus
from src.models.user import User as UserModel
from src.schemas.reminder import Reminder, ReminderCreate, ReminderUpdate, ReminderWithResponses
from src.services.reminder_intelligence import ReminderIntelligenceService

router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


@router.post("/", response_model=Reminder, status_code=201)
def create_reminder(reminder: ReminderCreate, db: Session = Depends(get_db)) -> ReminderModel:
    """Create a new reminder."""
    user = db.query(UserModel).filter(UserModel.id == reminder.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_reminder = ReminderModel(**reminder.model_dump())
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


@router.get("/", response_model=list[Reminder])
def list_reminders(
    user_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ReminderModel]:
    """List reminders with optional filtering."""
    query = db.query(ReminderModel)

    if user_id:
        query = query.filter(ReminderModel.user_id == user_id)
    if status:
        query = query.filter(ReminderModel.status == status)

    return query.order_by(ReminderModel.scheduled_time.desc()).offset(skip).limit(limit).all()


@router.get("/next", response_model=Reminder | None)
def get_next_reminder(
    user_id: int = Query(..., description="User ID to get next reminder for"),
    db: Session = Depends(get_db),
) -> ReminderModel | None:
    """Get the next scheduled reminder for a user."""
    reminder = (
        db.query(ReminderModel)
        .filter(
            ReminderModel.user_id == user_id,
            ReminderModel.status == ReminderStatus.SCHEDULED.value,
            ReminderModel.scheduled_time <= datetime.utcnow(),
        )
        .order_by(ReminderModel.scheduled_time.asc())
        .first()
    )
    return reminder


@router.get("/upcoming", response_model=list[Reminder])
def get_upcoming_reminders(
    user_id: int = Query(..., description="User ID to get upcoming reminders for"),
    limit: int = Query(10, description="Maximum number of reminders to return"),
    db: Session = Depends(get_db),
) -> list[ReminderModel]:
    """Get upcoming scheduled reminders for a user (future reminders not yet sent)."""
    reminders = (
        db.query(ReminderModel)
        .filter(
            ReminderModel.user_id == user_id,
            ReminderModel.status == ReminderStatus.SCHEDULED.value,
            ReminderModel.scheduled_time > datetime.utcnow(),
        )
        .order_by(ReminderModel.scheduled_time.asc())
        .limit(limit)
        .all()
    )
    return reminders


@router.get("/{reminder_id}", response_model=ReminderWithResponses)
def get_reminder(reminder_id: int, db: Session = Depends(get_db)) -> ReminderModel:
    """Get a reminder by ID with its responses."""
    reminder = db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.patch("/{reminder_id}", response_model=Reminder)
def update_reminder(
    reminder_id: int, reminder_update: ReminderUpdate, db: Session = Depends(get_db)
) -> ReminderModel:
    """Update a reminder's status or sent_time."""
    reminder = db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    update_data = reminder_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return reminder


@router.post("/generate", response_model=dict)
async def generate_reminders_for_user(
    user_id: int = Query(..., description="User ID to generate reminders for"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> dict:
    """Generate intelligent reminders based on response history gaps.

    Analyzes recent responses to identify which categories need coverage,
    then generates targeted questions using LLM.

    Reminders are only scheduled between wake_time and screens_off_time.
    """
    from datetime import time as dt_time, timezone

    import pytz

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's timezone (default to UTC if not set)
    user_tz = pytz.timezone(user.timezone) if user.timezone else pytz.UTC

    # Reminders only allowed between wake_time and screens_off_time (user's local time)
    wake_time = user.wake_time or dt_time(8, 0)
    end_time = user.screens_off_time or user.sleep_time or dt_time(21, 0)

    # Get current time in user's timezone
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(user_tz)
    today_local = now_local.date()

    # Calculate time window
    wake_minutes = wake_time.hour * 60 + wake_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if end_minutes <= wake_minutes:
        end_minutes += 24 * 60  # Handle overnight span

    total_minutes = end_minutes - wake_minutes

    # Use intelligence service to generate smart reminder
    intelligence_service = ReminderIntelligenceService()
    reminder_data = await intelligence_service.generate_intelligent_reminder(user_id, db)

    # Generate 3-4 reminder times spread throughout the day
    num_reminders = min(4, max(2, len(reminder_data["questions"]) // 3))
    interval = total_minutes // (num_reminders + 1)

    scheduled = 0
    questions_per_reminder = len(reminder_data["questions"]) // num_reminders
    question_keys = list(reminder_data["questions"].keys())

    for i in range(1, num_reminders + 1):
        minutes = wake_minutes + interval * i
        hours = (minutes // 60) % 24
        mins = minutes % 60
        reminder_time = dt_time(hour=hours, minute=mins)

        # Create datetime in user's local timezone
        scheduled_local = user_tz.localize(datetime.combine(today_local, reminder_time))

        # Skip if this time has already passed
        if scheduled_local <= now_local:
            continue

        # Convert to UTC for storage
        scheduled_utc = scheduled_local.astimezone(pytz.UTC).replace(tzinfo=None)

        # Check for existing reminder at this time
        existing = (
            db.query(ReminderModel)
            .filter(ReminderModel.user_id == user_id)
            .filter(ReminderModel.scheduled_time == scheduled_utc)
            .first()
        )
        if existing:
            continue

        # Distribute questions across reminders
        start_idx = (i - 1) * questions_per_reminder
        end_idx = start_idx + questions_per_reminder
        if i == num_reminders:
            # Last reminder gets any remaining questions
            end_idx = len(question_keys)

        reminder_questions = {
            key: reminder_data["questions"][key]
            for key in question_keys[start_idx:end_idx]
        }

        if not reminder_questions:
            continue

        reminder = ReminderModel(
            user_id=user_id,
            scheduled_time=scheduled_utc,
            questions=reminder_questions,
            categories=reminder_data["categories"],
            status=ReminderStatus.SCHEDULED.value,
        )
        db.add(reminder)
        scheduled += 1

    db.commit()

    return {
        "success": True,
        "scheduled": scheduled,
        "total_questions": len(reminder_data["questions"]),
        "categories_covered": reminder_data["categories"],
        "reasoning": reminder_data["reasoning"],
    }


@router.post("/{reminder_id}/acknowledge", response_model=Reminder)
def acknowledge_reminder(reminder_id: int, db: Session = Depends(get_db)) -> ReminderModel:
    """Acknowledge that a user has opened a reminder."""
    reminder = db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.status = ReminderStatus.ACKNOWLEDGED.value
    db.commit()
    db.refresh(reminder)
    return reminder
