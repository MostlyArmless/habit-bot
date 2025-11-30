"""Story API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.story import Story as StoryModel
from src.models.story import StoryProcessingStatus
from src.models.user import User as UserModel
from src.schemas.story import Story, StoryCreate
from src.tasks.story_tasks import process_story

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])


@router.post("/", response_model=Story, status_code=201)
def create_story(story: StoryCreate, db: Session = Depends(get_db)) -> StoryModel:
    """Submit a story for storytelling practice.

    The story will be queued for LLM analysis to receive Toastmaster-style feedback.
    """
    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == story.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create the story
    db_story = StoryModel(**story.model_dump())
    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    # Queue the story for LLM processing
    process_story.delay(db_story.id)

    return db_story


@router.get("/", response_model=list[Story])
def list_stories(
    user_id: int | None = None,
    processing_status: str | None = None,
    include_deleted: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[StoryModel]:
    """List stories with optional filtering."""
    query = db.query(StoryModel)

    # Filter out soft-deleted records by default
    if not include_deleted:
        query = query.filter(StoryModel.deleted_at.is_(None))

    if user_id:
        query = query.filter(StoryModel.user_id == user_id)
    if processing_status:
        query = query.filter(StoryModel.processing_status == processing_status)

    return query.order_by(StoryModel.timestamp.desc()).offset(skip).limit(limit).all()


@router.get("/{story_id}", response_model=Story)
def get_story(story_id: int, db: Session = Depends(get_db)) -> StoryModel:
    """Get a story by ID with its feedback."""
    story = (
        db.query(StoryModel)
        .filter(StoryModel.id == story_id)
        .filter(StoryModel.deleted_at.is_(None))
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.get("/pending", response_model=list[Story])
def get_pending_stories(
    limit: int = 10, db: Session = Depends(get_db)
) -> list[StoryModel]:
    """Get stories pending LLM processing."""
    return (
        db.query(StoryModel)
        .filter(StoryModel.processing_status == StoryProcessingStatus.PENDING.value)
        .filter(StoryModel.deleted_at.is_(None))
        .order_by(StoryModel.timestamp.asc())
        .limit(limit)
        .all()
    )


@router.delete("/{story_id}", status_code=204)
def delete_story(story_id: int, db: Session = Depends(get_db)) -> None:
    """Soft delete a story by ID."""
    story = (
        db.query(StoryModel)
        .filter(StoryModel.id == story_id)
        .filter(StoryModel.deleted_at.is_(None))
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.soft_delete()
    db.commit()
