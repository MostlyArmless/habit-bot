"""Summary API endpoints for activity summaries."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User as UserModel
from src.services.summary import SummaryService

router = APIRouter(prefix="/api/v1/summaries", tags=["summaries"])


def _summary_to_dict(summary):
    """Convert a summary model to a dictionary, or return None placeholder."""
    if summary is None:
        return None
    return {
        "period": summary.period,
        "period_label": summary.period_label,
        "summary": summary.summary_text,
        "entry_count": summary.entry_count,
        "categories": summary.categories,
        "generated_at": summary.generated_at.isoformat() if summary.generated_at else None,
    }


@router.get("/")
async def get_summaries(
    user_id: int = Query(..., description="User ID to fetch summaries for"),
    db: Session = Depends(get_db),
) -> dict:
    """Get cached activity summaries for today, yesterday, and the past week.

    Summaries are generated periodically in the background. If no summaries
    exist yet, returns None for missing periods.

    Returns:
        Dictionary with keys "today", "yesterday", "week", each containing:
        - period: Period identifier
        - period_label: Human-readable period name
        - summary: LLM-generated summary text
        - entry_count: Number of entries in this period
        - categories: List of categories covered
        - generated_at: When the summary was generated (ISO format)
        or None if the summary doesn't exist yet
    """
    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch latest summaries from database
    summary_service = SummaryService()
    summaries = summary_service.get_all_latest_summaries(user_id, db)

    return {
        "today": _summary_to_dict(summaries["today"]),
        "yesterday": _summary_to_dict(summaries["yesterday"]),
        "week": _summary_to_dict(summaries["week"]),
    }


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
