"""LLM API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.response import ProcessingStatus
from src.models.response import Response as ResponseModel
from src.services.llm import LLMService, get_llm_service

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


class ProcessResponseRequest(BaseModel):
    """Request to process a response with LLM."""

    response_id: int


class ProcessResponseResult(BaseModel):
    """Result of processing a response."""

    response_id: int
    success: bool
    structured_data: dict | None = None
    error: str | None = None


class GenerateQuestionsResult(BaseModel):
    """Result of generating questions for a category."""

    category: str
    questions: list[str]


@router.get("/health")
async def llm_health_check(
    llm: LLMService = Depends(get_llm_service),
) -> dict[str, str | bool]:
    """Check if the LLM service is available."""
    is_available = await llm.health_check()
    return {
        "status": "healthy" if is_available else "unavailable",
        "model": llm.model,
        "available": is_available,
    }


@router.post("/process-response", response_model=ProcessResponseResult)
async def process_response(
    request: ProcessResponseRequest,
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm_service),
) -> ProcessResponseResult:
    """Process a response with the LLM to extract structured data."""
    response = db.query(ResponseModel).filter(ResponseModel.id == request.response_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    # Update status to processing
    response.processing_status = ProcessingStatus.PROCESSING.value
    response.processing_attempts += 1
    db.commit()

    try:
        structured_data = await llm.extract_structured_data(
            response_text=response.response_text,
            question_text=response.question_text,
            category=response.category or "general",
        )

        # Update response with structured data
        response.response_structured = structured_data
        response.processing_status = ProcessingStatus.COMPLETED.value
        db.commit()

        return ProcessResponseResult(
            response_id=response.id,
            success=True,
            structured_data=structured_data,
        )
    except Exception as e:
        response.processing_status = ProcessingStatus.FAILED.value
        db.commit()

        return ProcessResponseResult(
            response_id=response.id,
            success=False,
            error=str(e),
        )


@router.post("/generate-questions", response_model=GenerateQuestionsResult)
async def generate_questions(
    category: str,
    llm: LLMService = Depends(get_llm_service),
) -> GenerateQuestionsResult:
    """Generate questions for a category."""
    questions = await llm.generate_questions(category=category)
    return GenerateQuestionsResult(category=category, questions=questions)
