"""LLM processing tasks."""

import asyncio
import logging

from src.celery_app import app
from src.database import SessionLocal
from src.models.response import ProcessingStatus
from src.models.response import Response as ResponseModel
from src.services.llm import LLMService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine in a sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_response(self, response_id: int) -> dict:
    """Process a single response with the LLM.

    Args:
        response_id: ID of the response to process

    Returns:
        dict with processing result
    """
    db = SessionLocal()
    try:
        response = db.query(ResponseModel).filter(ResponseModel.id == response_id).first()
        if not response:
            return {"success": False, "error": "Response not found"}

        # Update status to processing
        response.processing_status = ProcessingStatus.PROCESSING.value
        response.processing_attempts += 1
        db.commit()

        llm = LLMService()

        try:
            structured_data = run_async(
                llm.extract_structured_data(
                    response_text=response.response_text,
                    question_text=response.question_text,
                    category=response.category or "general",
                )
            )

            response.response_structured = structured_data
            response.processing_status = ProcessingStatus.COMPLETED.value
            db.commit()

            logger.info(f"Successfully processed response {response_id}")
            return {"success": True, "response_id": response_id}

        except Exception as e:
            logger.error(f"Error processing response {response_id}: {e}")
            response.processing_status = ProcessingStatus.FAILED.value
            db.commit()

            # Retry if we haven't exceeded max retries
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)

            return {"success": False, "error": str(e)}

    finally:
        db.close()


@app.task
def process_pending_responses() -> dict:
    """Find and queue pending responses for processing.

    This is a periodic task that finds responses with pending status
    and queues them for LLM processing.
    """
    db = SessionLocal()
    try:
        pending = (
            db.query(ResponseModel)
            .filter(ResponseModel.processing_status == ProcessingStatus.PENDING.value)
            .filter(ResponseModel.processing_attempts < 3)
            .limit(10)
            .all()
        )

        queued = 0
        for response in pending:
            process_response.delay(response.id)
            queued += 1

        logger.info(f"Queued {queued} responses for processing")
        return {"queued": queued}

    finally:
        db.close()
