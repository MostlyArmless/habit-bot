"""Quick log API for ad-hoc entries."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.prompt import Prompt, PromptStatus
from src.models.response import ProcessingStatus
from src.models.response import Response as ResponseModel
from src.models.user import User
from src.services.llm import LLMService, get_llm_service
from src.tasks.llm_tasks import process_response

router = APIRouter(prefix="/api/v1/quicklog", tags=["quicklog"])


class QuickLogRequest(BaseModel):
    """Request for quick logging."""

    user_id: int
    text: str
    timestamp: datetime | None = None  # Optional: backdate entries to a specific time


class QuickLogResponse(BaseModel):
    """Response from quick logging."""

    response_id: int
    category: str
    summary: str
    structured_data: dict | None
    processing_status: str


class CategoryDetectionResult(BaseModel):
    """Result of category detection."""

    category: str
    confidence: str
    suggested_question: str


@router.post("/", response_model=QuickLogResponse)
async def create_quick_log(
    request: QuickLogRequest,
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm_service),
) -> QuickLogResponse:
    """Create a quick log entry with auto-categorization.

    This endpoint:
    1. Uses LLM to detect the category of the log (fast, synchronous)
    2. Creates a prompt and response automatically
    3. Queues background task for structured data extraction
    4. Returns immediately so user can submit more entries
    """
    # Verify user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Use LLM to detect category (fast operation with small model)
    category_result = await _detect_category(llm, request.text)

    # Use provided timestamp or default to now
    entry_time = request.timestamp if request.timestamp else datetime.now(timezone.utc)
    # Ensure timezone-aware
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)

    # Create an ad-hoc prompt
    prompt = Prompt(
        user_id=request.user_id,
        scheduled_time=entry_time,
        sent_time=entry_time,
        questions={"q1": category_result.suggested_question},
        categories=[category_result.category],
        status=PromptStatus.COMPLETED.value,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    # Create the response with PENDING status
    response = ResponseModel(
        prompt_id=prompt.id,
        user_id=request.user_id,
        question_text=category_result.suggested_question,
        response_text=request.text,
        category=category_result.category,
        timestamp=entry_time,
        processing_status=ProcessingStatus.PENDING.value,
    )
    db.add(response)
    db.commit()
    db.refresh(response)

    # Queue background task for structured data extraction
    process_response.delay(response.id)

    # Return immediately - processing happens in background
    return QuickLogResponse(
        response_id=response.id,
        category=category_result.category,
        summary=f"Processing: {request.text[:80]}..." if len(request.text) > 80 else f"Processing: {request.text}",
        structured_data=None,
        processing_status=ProcessingStatus.PENDING.value,
    )


async def _detect_category(llm: LLMService, text: str) -> CategoryDetectionResult:
    """Use LLM to detect the category of a log entry."""
    system_prompt = """You are a health tracking assistant. Categorize the user's log entry into one of these categories:
- nutrition: food, drinks, meals, eating
- sleep: sleep quality, naps, tiredness, rest
- substances: medications, pills, caffeine, alcohol, supplements
- physical_activity: exercise, walking, sports, movement
- mental_state: mood, emotions, feelings, mental health
- stress_anxiety: stress, worry, anxiety, overwhelm
- physical_symptoms: pain, headaches, illness, physical discomfort
- social_interaction: conversations, meetings, social events
- work_productivity: work tasks, focus, productivity
- environment: location, weather, surroundings

Respond with JSON only:
{
  "category": "the_category",
  "confidence": "high/medium/low",
  "suggested_question": "A question that would have prompted this response"
}"""

    prompt = f"Log entry: {text}"

    try:
        import json

        result = await llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.1)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        data = json.loads(result)
        return CategoryDetectionResult(
            category=data.get("category", "mental_state"),
            confidence=data.get("confidence", "medium"),
            suggested_question=data.get("suggested_question", "What would you like to log?"),
        )
    except Exception:
        # Default to mental_state if detection fails
        return CategoryDetectionResult(
            category="mental_state",
            confidence="low",
            suggested_question="What would you like to log?",
        )


@router.post("/detect-category", response_model=CategoryDetectionResult)
async def detect_category(
    text: str,
    llm: LLMService = Depends(get_llm_service),
) -> CategoryDetectionResult:
    """Detect the category of a text without creating a log entry."""
    return await _detect_category(llm, text)
