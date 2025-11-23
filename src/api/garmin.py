"""Garmin Connect API endpoints."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.garmin_data import GarminData, GarminMetricType
from src.services.garmin import get_garmin_service

router = APIRouter(prefix="/api/v1/garmin", tags=["garmin"])


class GarminSyncRequest(BaseModel):
    """Request to sync Garmin data."""

    user_id: int
    start_date: date | None = None
    end_date: date | None = None
    days_back: int = 7  # Default to last 7 days if no dates specified


class GarminSyncResponse(BaseModel):
    """Response from Garmin sync."""

    synced_count: int
    start_date: date
    end_date: date
    metrics: list[str]


class GarminDataResponse(BaseModel):
    """Response schema for Garmin data."""

    id: int
    user_id: int
    metric_type: str
    metric_date: date
    value: float | None
    details: dict | list | None
    fetched_at: datetime

    class Config:
        from_attributes = True


@router.post("/sync", response_model=GarminSyncResponse)
def sync_garmin_data(
    request: GarminSyncRequest,
    db: Session = Depends(get_db),
) -> GarminSyncResponse:
    """Sync Garmin data for a user.

    If start_date and end_date are not provided, syncs the last `days_back` days.
    """
    garmin = get_garmin_service()

    # Determine date range
    if request.start_date and request.end_date:
        start = request.start_date
        end = request.end_date
    else:
        end = date.today()
        start = end - timedelta(days=request.days_back - 1)

    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    try:
        results = garmin.sync_date_range(db, request.user_id, start, end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Garmin sync failed: {e}")

    # Get unique metric types that were synced
    metrics = list(set(r.metric_type for r in results))

    return GarminSyncResponse(
        synced_count=len(results),
        start_date=start,
        end_date=end,
        metrics=metrics,
    )


@router.get("/data", response_model=list[GarminDataResponse])
def get_garmin_data(
    user_id: int,
    metric_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[GarminData]:
    """Get Garmin data for a user with optional filtering."""
    query = db.query(GarminData).filter(
        GarminData.user_id == user_id,
        GarminData.deleted_at.is_(None),
    )

    if metric_type:
        query = query.filter(GarminData.metric_type == metric_type)
    if start_date:
        query = query.filter(GarminData.metric_date >= start_date)
    if end_date:
        query = query.filter(GarminData.metric_date <= end_date)

    return query.order_by(GarminData.metric_date.desc()).limit(limit).all()


@router.get("/metrics", response_model=list[str])
def get_available_metrics() -> list[str]:
    """Get list of available Garmin metric types."""
    return [m.value for m in GarminMetricType]


@router.get("/latest", response_model=dict[str, GarminDataResponse | None])
def get_latest_metrics(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict[str, GarminData | None]:
    """Get the latest value for each metric type for a user."""
    result = {}

    for metric_type in GarminMetricType:
        latest = (
            db.query(GarminData)
            .filter(
                GarminData.user_id == user_id,
                GarminData.metric_type == metric_type.value,
                GarminData.deleted_at.is_(None),
            )
            .order_by(GarminData.metric_date.desc())
            .first()
        )
        result[metric_type.value] = latest

    return result
