"""Prompt API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.prompt import Prompt as PromptModel
from src.models.prompt import PromptStatus
from src.models.user import User as UserModel
from src.schemas.prompt import Prompt, PromptCreate, PromptUpdate, PromptWithResponses

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


@router.post("/", response_model=Prompt, status_code=201)
def create_prompt(prompt: PromptCreate, db: Session = Depends(get_db)) -> PromptModel:
    """Create a new prompt."""
    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == prompt.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_prompt = PromptModel(**prompt.model_dump())
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt


@router.get("/", response_model=list[Prompt])
def list_prompts(
    user_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[PromptModel]:
    """List prompts with optional filtering."""
    query = db.query(PromptModel)

    if user_id:
        query = query.filter(PromptModel.user_id == user_id)
    if status:
        query = query.filter(PromptModel.status == status)

    return query.order_by(PromptModel.scheduled_time.desc()).offset(skip).limit(limit).all()


@router.get("/next", response_model=Prompt | None)
def get_next_prompt(
    user_id: int = Query(..., description="User ID to get next prompt for"),
    db: Session = Depends(get_db),
) -> PromptModel | None:
    """Get the next scheduled prompt for a user."""
    prompt = (
        db.query(PromptModel)
        .filter(
            PromptModel.user_id == user_id,
            PromptModel.status == PromptStatus.SCHEDULED.value,
            PromptModel.scheduled_time <= datetime.utcnow(),
        )
        .order_by(PromptModel.scheduled_time.asc())
        .first()
    )
    return prompt


@router.get("/upcoming", response_model=list[Prompt])
def get_upcoming_prompts(
    user_id: int = Query(..., description="User ID to get upcoming prompts for"),
    limit: int = Query(10, description="Maximum number of prompts to return"),
    db: Session = Depends(get_db),
) -> list[PromptModel]:
    """Get upcoming scheduled prompts for a user (future prompts not yet sent)."""
    prompts = (
        db.query(PromptModel)
        .filter(
            PromptModel.user_id == user_id,
            PromptModel.status == PromptStatus.SCHEDULED.value,
            PromptModel.scheduled_time > datetime.utcnow(),
        )
        .order_by(PromptModel.scheduled_time.asc())
        .limit(limit)
        .all()
    )
    return prompts


@router.get("/{prompt_id}", response_model=PromptWithResponses)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)) -> PromptModel:
    """Get a prompt by ID with its responses."""
    prompt = db.query(PromptModel).filter(PromptModel.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.patch("/{prompt_id}", response_model=Prompt)
def update_prompt(
    prompt_id: int, prompt_update: PromptUpdate, db: Session = Depends(get_db)
) -> PromptModel:
    """Update a prompt's status or sent_time."""
    prompt = db.query(PromptModel).filter(PromptModel.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = prompt_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)
    return prompt


@router.post("/generate", response_model=dict)
def generate_prompts_for_user(
    user_id: int = Query(..., description="User ID to generate prompts for"),
    db: Session = Depends(get_db),
) -> dict:
    """Generate scheduled prompts for a user based on their wake/sleep times.

    This creates prompts for today that haven't already been scheduled.
    """
    from datetime import time as dt_time

    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's schedule preferences
    wake_time = user.wake_time or dt_time(8, 0)
    sleep_time = user.sleep_time or dt_time(22, 0)

    # Calculate prompts for today
    now = datetime.utcnow()
    today = now.date()

    # Default categories to check
    categories = [
        "mental_state",
        "sleep",
        "nutrition",
        "physical_activity",
        "stress_anxiety",
    ]

    # Calculate evenly spaced prompt times
    wake_minutes = wake_time.hour * 60 + wake_time.minute
    sleep_minutes = sleep_time.hour * 60 + sleep_time.minute
    if sleep_minutes < wake_minutes:
        sleep_minutes += 24 * 60

    num_prompts = 4
    total_minutes = sleep_minutes - wake_minutes
    interval = total_minutes // (num_prompts + 1)

    scheduled = 0
    for i in range(1, num_prompts + 1):
        minutes = (wake_minutes + interval * i) % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        prompt_time = dt_time(hour=hours, minute=mins)

        scheduled_dt = datetime.combine(today, prompt_time)

        # Skip if time has already passed
        if scheduled_dt <= now:
            continue

        # Check if prompt already exists for this time
        existing = (
            db.query(PromptModel)
            .filter(PromptModel.user_id == user_id)
            .filter(PromptModel.scheduled_time == scheduled_dt)
            .first()
        )
        if existing:
            continue

        # Select category for this prompt
        prompt_categories = [categories[i % len(categories)]]

        prompt = PromptModel(
            user_id=user_id,
            scheduled_time=scheduled_dt,
            questions={"q1": f"How are you doing with your {prompt_categories[0].replace('_', ' ')}?"},
            categories=prompt_categories,
            status=PromptStatus.SCHEDULED.value,
        )
        db.add(prompt)
        scheduled += 1

    db.commit()
    return {"success": True, "scheduled": scheduled}


@router.post("/{prompt_id}/acknowledge", response_model=Prompt)
def acknowledge_prompt(prompt_id: int, db: Session = Depends(get_db)) -> PromptModel:
    """Acknowledge that a user has opened a prompt."""
    prompt = db.query(PromptModel).filter(PromptModel.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.status = PromptStatus.ACKNOWLEDGED.value
    db.commit()
    db.refresh(prompt)
    return prompt
