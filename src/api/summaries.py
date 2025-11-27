"""Summary API endpoints for activity summaries."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User as UserModel
from src.services.summary import SummaryService

router = APIRouter(prefix="/api/v1/summaries", tags=["summaries"])


@router.get("/")
async def get_summaries(
    user_id: int = Query(..., description="User ID to generate summaries for"),
    db: Session = Depends(get_db),
) -> dict:
    """Get activity summaries for today, yesterday, and the past week.

    Returns:
        Dictionary with keys "today", "yesterday", "week", each containing:
        - period: Period identifier
        - period_label: Human-readable period name
        - summary: LLM-generated summary text
        - entry_count: Number of entries in this period
        - categories: List of categories covered
    """
    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate summaries
    summary_service = SummaryService()
    summaries = await summary_service.generate_all_summaries(user_id, db)

    return summaries


@router.get("/{period}")
async def get_summary_for_period(
    period: str,
    user_id: int = Query(..., description="User ID to generate summary for"),
    db: Session = Depends(get_db),
) -> dict:
    """Get activity summary for a specific time period.

    Args:
        period: One of "today", "yesterday", "week"
        user_id: User ID

    Returns:
        Dictionary with:
        - period: Period identifier
        - period_label: Human-readable period name
        - summary: LLM-generated summary text
        - entry_count: Number of entries in this period
        - categories: List of categories covered
    """
    if period not in ["today", "yesterday", "week"]:
        raise HTTPException(
            status_code=400, detail="Period must be one of: today, yesterday, week"
        )

    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate summary
    summary_service = SummaryService()
    summary = await summary_service.generate_summary(user_id, db, period)

    return summary
