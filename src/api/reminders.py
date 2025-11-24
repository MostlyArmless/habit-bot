"""Reminder API endpoints for scheduled check-in notifications."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.reminder import Reminder as ReminderModel
from src.models.reminder import ReminderStatus
from src.models.user import User as UserModel
from src.schemas.reminder import Reminder, ReminderCreate, ReminderUpdate, ReminderWithResponses

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
def generate_reminders_for_user(
    user_id: int = Query(..., description="User ID to generate reminders for"),
    db: Session = Depends(get_db),
) -> dict:
    """Generate scheduled reminders for a user based on their wake/screens-off times.

    This creates reminders for today that haven't already been scheduled.
    Reminders are only scheduled between wake_time and screens_off_time.
    """
    from datetime import time as dt_time

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Reminders only allowed between wake_time and screens_off_time
    wake_time = user.wake_time or dt_time(8, 0)
    end_time = user.screens_off_time or user.sleep_time or dt_time(21, 0)

    now = datetime.utcnow()
    today = now.date()

    categories = [
        "mental_state",
        "sleep",
        "nutrition",
        "physical_activity",
        "stress_anxiety",
    ]

    # Calculate evenly spaced reminder times between wake and screens-off
    wake_minutes = wake_time.hour * 60 + wake_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if end_minutes < wake_minutes:
        end_minutes += 24 * 60

    num_reminders = 4
    total_minutes = end_minutes - wake_minutes
    interval = total_minutes // (num_reminders + 1)

    scheduled = 0
    for i in range(1, num_reminders + 1):
        minutes = (wake_minutes + interval * i) % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        reminder_time = dt_time(hour=hours, minute=mins)

        scheduled_dt = datetime.combine(today, reminder_time)

        if scheduled_dt <= now:
            continue

        existing = (
            db.query(ReminderModel)
            .filter(ReminderModel.user_id == user_id)
            .filter(ReminderModel.scheduled_time == scheduled_dt)
            .first()
        )
        if existing:
            continue

        reminder_categories = [categories[i % len(categories)]]

        reminder = ReminderModel(
            user_id=user_id,
            scheduled_time=scheduled_dt,
            questions={"q1": f"How are you doing with your {reminder_categories[0].replace('_', ' ')}?"},
            categories=reminder_categories,
            status=ReminderStatus.SCHEDULED.value,
        )
        db.add(reminder)
        scheduled += 1

    db.commit()
    return {"success": True, "scheduled": scheduled}


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
