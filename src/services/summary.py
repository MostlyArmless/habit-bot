"""Summary generation service.

Generates LLM-powered summaries of user activity for different time periods.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.models.response import Response as ResponseModel
from src.models.user import User as UserModel
from src.services.llm import LLMService

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating activity summaries."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def _get_responses_for_period(
        self, user_id: int, db: Session, start_time: datetime, end_time: datetime
    ) -> list[ResponseModel]:
        """Get all responses for a specific time period."""
        return (
            db.query(ResponseModel)
            .filter(
                ResponseModel.user_id == user_id,
                ResponseModel.timestamp >= start_time,
                ResponseModel.timestamp < end_time,
            )
            .order_by(ResponseModel.timestamp.asc())
            .all()
        )

    def _format_responses_for_llm(self, responses: list[ResponseModel]) -> str:
        """Format responses into a readable text for LLM."""
        if not responses:
            return "No entries recorded during this period."

        lines = []
        for response in responses:
            timestamp = response.timestamp.strftime("%I:%M %p")
            category = response.category or "general"
            text = response.response_text or "N/A"
            lines.append(f"- [{timestamp}] {category}: {text}")

        return "\n".join(lines)

    async def generate_summary(
        self, user_id: int, db: Session, period: str = "today"
    ) -> dict[str, Any]:
        """Generate a summary for a specific time period.

        Args:
            user_id: User to generate summary for
            db: Database session
            period: One of "today", "yesterday", "week"

        Returns:
            Dictionary with:
            - period: The time period
            - summary: LLM-generated summary text
            - entry_count: Number of entries in this period
            - categories: List of categories covered
        """
        # Calculate time range based on period
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "today":
            start_time = today_start
            end_time = now
            period_label = "Today"
        elif period == "yesterday":
            start_time = today_start - timedelta(days=1)
            end_time = today_start
            period_label = "Yesterday"
        elif period == "week":
            start_time = today_start - timedelta(days=7)
            end_time = now
            period_label = "Past 7 Days"
        else:
            raise ValueError(f"Invalid period: {period}")

        # Get responses
        responses = self._get_responses_for_period(user_id, db, start_time, end_time)

        # Extract metadata
        entry_count = len(responses)
        categories = list(set(r.category for r in responses if r.category))

        # If no entries, return early
        if entry_count == 0:
            return {
                "period": period,
                "period_label": period_label,
                "summary": f"No activity recorded {period_label.lower()}.",
                "entry_count": 0,
                "categories": [],
            }

        # Format responses for LLM
        formatted_entries = self._format_responses_for_llm(responses)

        # Generate summary using LLM
        prompt = f"""You are analyzing a user's health and habit tracking data for {period_label.lower()}.

Here are all the entries:

{formatted_entries}

Generate a concise, insightful summary (2-4 sentences) that:
1. Highlights the main themes or patterns
2. Notes anything significant (good habits, potential concerns, interesting correlations)
3. Uses a supportive, non-judgmental tone

Focus on actionable insights rather than just listing what happened.

IMPORTANT: Output ONLY the summary text. Do NOT use markdown, code fences, or JSON formatting. Just plain text."""

        try:
            summary_text = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7,
            )

            # Clean up the response (remove any markdown artifacts)
            summary_text = summary_text.strip()
            if summary_text.startswith("```"):
                lines = summary_text.split("\n")
                summary_text = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                ).strip()

            logger.info(
                f"Generated {period} summary for user {user_id}: {entry_count} entries"
            )

            return {
                "period": period,
                "period_label": period_label,
                "summary": summary_text,
                "entry_count": entry_count,
                "categories": categories,
            }

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {
                "period": period,
                "period_label": period_label,
                "summary": f"Logged {entry_count} entries across {len(categories)} categories.",
                "entry_count": entry_count,
                "categories": categories,
            }

    async def generate_all_summaries(
        self, user_id: int, db: Session
    ) -> dict[str, dict[str, Any]]:
        """Generate summaries for all time periods.

        Returns:
            Dictionary with keys "today", "yesterday", "week"
        """
        summaries = {}

        for period in ["today", "yesterday", "week"]:
            summaries[period] = await self.generate_summary(user_id, db, period)

        return summaries
