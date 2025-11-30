"""Story reminder and processing tasks."""

import logging
from datetime import datetime, time as dt_time, timezone

import pytz

from src.celery_app import app
from src.database import SessionLocal
from src.models.story import Story, StoryProcessingStatus
from src.models.user import User

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine in a sync context."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task
def send_story_reminders() -> dict:
    """Send 8pm story reminders to all users.

    This task runs daily at 8pm and sends a reminder to each user
    to tell a story.
    """
    from src.services.notifications import NotificationService

    db = SessionLocal()
    try:
        users = db.query(User).all()
        sent = 0

        notification_service = NotificationService()

        for user in users:
            # Get user's timezone
            user_tz = pytz.timezone(user.timezone) if user.timezone else pytz.UTC
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(user_tz)

            # Check if it's 8pm in the user's timezone (within a 1-hour window)
            current_hour = now_local.hour
            if current_hour != 20:  # 8pm
                logger.debug(f"Skipping user {user.id} - not 8pm in their timezone (currently {current_hour}:00)")
                continue

            # Send the story reminder
            try:
                result = run_async(
                    notification_service.send_story_reminder(user.id)
                )
                if result["success"]:
                    sent += 1
                    logger.info(f"Sent story reminder to user {user.id}")
                else:
                    logger.warning(f"Failed to send story reminder to user {user.id}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error sending story reminder to user {user.id}: {e}")

        logger.info(f"Sent {sent} story reminders")
        return {"success": True, "sent": sent}

    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_story(self, story_id: int) -> dict:
    """Process a story with the LLM to provide Toastmaster-style feedback.

    Args:
        story_id: ID of the story to process

    Returns:
        dict with processing result
    """
    from src.services.llm import LLMService

    db = SessionLocal()
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return {"success": False, "error": "Story not found"}

        # Update status to processing
        story.processing_status = StoryProcessingStatus.PROCESSING.value
        story.processing_attempts += 1
        db.commit()

        llm = LLMService()

        try:
            # System prompt for Toastmaster-style feedback
            system_prompt = """You are an experienced Toastmasters International instructor, dedicated to helping people become more compelling storytellers. Your role is to provide constructive, actionable feedback that helps the storyteller improve their craft.

When analyzing a story, evaluate it across these key dimensions:

**Structure & Clarity**
- Does the story have a clear beginning, middle, and end?
- Is there a compelling hook that draws the listener in?
- Does it build toward a satisfying resolution or insight?

**Emotional Impact**
- Does the story connect emotionally with the audience?
- Are there specific sensory details that make the experience vivid?
- Does it evoke feelings or create a memorable impression?

**Pacing & Flow**
- Is the story concise or does it meander?
- Are there unnecessary tangents or details that could be cut?
- Does the narrative flow naturally from one point to the next?

**Character & Voice**
- Is the storyteller's unique voice present?
- If there are other people in the story, can we "see" them?
- Does dialogue (if any) sound natural and serve the story?

**Purpose & Takeaway**
- What's the point of this story? Is it clear?
- Will the audience remember this story tomorrow? Why or why not?
- Is there a lesson, insight, or "aha moment"?

Provide your feedback in a warm, encouraging tone. Start with what works well in the story - be specific about strengths. Then offer 2-3 concrete suggestions for improvement, explaining WHY each suggestion would make the story more compelling. Keep your total feedback to about 200-300 words.

Format your response as JSON with these fields:
{
    "overall_impression": "Brief 1-2 sentence summary of the story's impact",
    "strengths": ["Specific strength 1", "Specific strength 2", "Specific strength 3"],
    "suggestions": [
        {
            "area": "Structure/Emotion/Pacing/Voice/Purpose",
            "suggestion": "What to improve",
            "why": "Why this will make the story better"
        }
    ],
    "memorable_moment": "The single most memorable part of this story",
    "encouragement": "A final encouraging message"
}"""

            feedback_json = run_async(
                llm.generate(
                    prompt=f"Here's the story to analyze:\n\n{story.story_text}",
                    system_prompt=system_prompt,
                    temperature=0.7,  # More creative for feedback
                    max_tokens=1000,
                )
            )

            # Parse JSON response
            import json

            # Clean up response - remove markdown code blocks if present
            feedback_json = feedback_json.strip()
            if feedback_json.startswith("```json"):
                feedback_json = feedback_json[7:]
            if feedback_json.startswith("```"):
                feedback_json = feedback_json[3:]
            if feedback_json.endswith("```"):
                feedback_json = feedback_json[:-3]
            feedback_json = feedback_json.strip()

            feedback = json.loads(feedback_json)

            story.feedback = feedback
            story.processing_status = StoryProcessingStatus.COMPLETED.value
            db.commit()

            logger.info(f"Successfully processed story {story_id}")
            return {"success": True, "story_id": story_id}

        except Exception as e:
            logger.error(f"Error processing story {story_id}: {e}")
            story.processing_status = StoryProcessingStatus.FAILED.value
            db.commit()

            # Retry if we haven't exceeded max retries
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)

            return {"success": False, "error": str(e)}

    finally:
        db.close()


@app.task
def process_pending_stories() -> dict:
    """Find and queue pending stories for processing.

    This is a periodic task that finds stories with pending status
    and queues them for LLM processing.
    """
    db = SessionLocal()
    try:
        pending = (
            db.query(Story)
            .filter(Story.processing_status == StoryProcessingStatus.PENDING.value)
            .filter(Story.processing_attempts < 3)
            .limit(10)
            .all()
        )

        queued = 0
        for story in pending:
            process_story.delay(story.id)
            queued += 1

        logger.info(f"Queued {queued} stories for processing")
        return {"queued": queued}

    finally:
        db.close()
