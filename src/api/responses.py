"""Response API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.prompt import Prompt as PromptModel
from src.models.prompt import PromptStatus
from src.models.response import ProcessingStatus
from src.models.response import Response as ResponseModel
from src.schemas.response import Response, ResponseCreate

router = APIRouter(prefix="/api/v1/responses", tags=["responses"])


@router.post("/", response_model=Response, status_code=201)
def create_response(response: ResponseCreate, db: Session = Depends(get_db)) -> ResponseModel:
    """Submit a response to a prompt."""
    # Verify prompt exists
    prompt = db.query(PromptModel).filter(PromptModel.id == response.prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Create the response
    db_response = ResponseModel(**response.model_dump())
    db.add(db_response)

    # Update prompt status to completed if all questions answered
    # For now, mark as completed on first response
    prompt.status = PromptStatus.COMPLETED.value

    db.commit()
    db.refresh(db_response)
    return db_response


@router.get("/", response_model=list[Response])
def list_responses(
    user_id: int | None = None,
    prompt_id: int | None = None,
    category: str | None = None,
    processing_status: str | None = None,
    include_deleted: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ResponseModel]:
    """List responses with optional filtering."""
    query = db.query(ResponseModel)

    # Filter out soft-deleted records by default
    if not include_deleted:
        query = query.filter(ResponseModel.deleted_at.is_(None))

    if user_id:
        query = query.filter(ResponseModel.user_id == user_id)
    if prompt_id:
        query = query.filter(ResponseModel.prompt_id == prompt_id)
    if category:
        query = query.filter(ResponseModel.category == category)
    if processing_status:
        query = query.filter(ResponseModel.processing_status == processing_status)

    return query.order_by(ResponseModel.timestamp.desc()).offset(skip).limit(limit).all()


@router.get("/{response_id}", response_model=Response)
def get_response(response_id: int, db: Session = Depends(get_db)) -> ResponseModel:
    """Get a response by ID."""
    response = (
        db.query(ResponseModel)
        .filter(ResponseModel.id == response_id)
        .filter(ResponseModel.deleted_at.is_(None))
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    return response


@router.get("/pending", response_model=list[Response])
def get_pending_responses(
    limit: int = 10, db: Session = Depends(get_db)
) -> list[ResponseModel]:
    """Get responses pending LLM processing."""
    return (
        db.query(ResponseModel)
        .filter(ResponseModel.processing_status == ProcessingStatus.PENDING.value)
        .filter(ResponseModel.deleted_at.is_(None))
        .order_by(ResponseModel.timestamp.asc())
        .limit(limit)
        .all()
    )


@router.delete("/{response_id}", status_code=204)
def delete_response(response_id: int, db: Session = Depends(get_db)) -> None:
    """Soft delete a response by ID."""
    response = (
        db.query(ResponseModel)
        .filter(ResponseModel.id == response_id)
        .filter(ResponseModel.deleted_at.is_(None))
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    response.soft_delete()
    db.commit()
