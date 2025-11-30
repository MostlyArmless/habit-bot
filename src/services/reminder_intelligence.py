"""Intelligent reminder generation service.

Analyzes response history to identify gaps and generate targeted questions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.models.response import Response as ResponseModel
from src.models.user import User as UserModel
from src.services.llm import LLMService

logger = logging.getLogger(__name__)


class ReminderIntelligenceService:
    """Service for intelligent reminder generation."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

        # All trackable categories
        self.all_categories = [
            "sleep",
            "nutrition",
            "physical_activity",
            "substances",
            "mental_state",
            "stress_anxiety",
            "physical_symptoms",
            "social_interaction",
            "work_productivity",
            "environment",
        ]

        # Category-specific frequency limits (in hours)
        # These define the MINIMUM time between asking about each category
        self.category_frequency_limits = {
            "sleep": 24,  # Only ask about sleep once per day max
            "mental_state": 4,  # Can check in on mental state more frequently
            "stress_anxiety": 6,
            "nutrition": 8,
            "physical_activity": 8,
            "substances": 12,
            "physical_symptoms": 12,
            "social_interaction": 12,
            "work_productivity": 12,
            "environment": 24,
        }

    def analyze_category_coverage(
        self, user_id: int, db: Session, lookback_hours: int = 24
    ) -> dict[str, Any]:
        """Analyze which categories have been covered recently.

        Args:
            user_id: User to analyze
            db: Database session
            lookback_hours: How far back to look

        Returns:
            Dictionary with:
            - covered_categories: List of categories with recent responses
            - gap_categories: List of categories without recent coverage
            - category_counts: Dict of category -> count
            - last_response_by_category: Dict of category -> timestamp
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        # Get recent responses
        recent_responses = (
            db.query(ResponseModel)
            .filter(ResponseModel.user_id == user_id)
            .filter(ResponseModel.timestamp >= cutoff)
            .filter(ResponseModel.deleted_at.is_(None))
            .all()
        )

        # Count responses by category
        category_counts: dict[str, int] = {}
        last_response_by_category: dict[str, datetime] = {}

        for response in recent_responses:
            if response.category:
                category_counts[response.category] = category_counts.get(response.category, 0) + 1

                # Track most recent response for each category
                if (
                    response.category not in last_response_by_category
                    or response.timestamp > last_response_by_category[response.category]
                ):
                    last_response_by_category[response.category] = response.timestamp

        covered_categories = list(category_counts.keys())
        gap_categories = [cat for cat in self.all_categories if cat not in covered_categories]

        return {
            "covered_categories": covered_categories,
            "gap_categories": gap_categories,
            "category_counts": category_counts,
            "last_response_by_category": last_response_by_category,
            "total_responses": len(recent_responses),
        }

    def get_last_asked_times(self, user_id: int, db: Session) -> dict[str, datetime]:
        """Get the last time each category was asked in a reminder.

        This checks reminders (not responses) to see when we last asked about each category,
        which is important for enforcing frequency limits.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dict mapping category -> last asked timestamp
        """
        from src.models.reminder import Reminder as ReminderModel

        # Get all recent reminders for this user
        recent_reminders = (
            db.query(ReminderModel)
            .filter(ReminderModel.user_id == user_id)
            .order_by(ReminderModel.scheduled_time.desc())
            .limit(100)  # Look at last 100 reminders
            .all()
        )

        last_asked: dict[str, datetime] = {}

        for reminder in recent_reminders:
            if not reminder.categories:
                continue

            # reminder.categories is a list of category names
            for category in reminder.categories:
                # Only record if we haven't seen this category yet (we want the most recent)
                if category not in last_asked:
                    last_asked[category] = reminder.scheduled_time

        return last_asked

    def get_recent_context(
        self, user_id: int, db: Session, category: str, limit: int = 3
    ) -> list[dict[str, Any]]:
        """Get recent responses for a category to provide context.

        Args:
            user_id: User ID
            db: Database session
            category: Category to get context for
            limit: Max number of recent responses

        Returns:
            List of response summaries
        """
        responses = (
            db.query(ResponseModel)
            .filter(ResponseModel.user_id == user_id)
            .filter(ResponseModel.category == category)
            .filter(ResponseModel.deleted_at.is_(None))
            .order_by(ResponseModel.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "timestamp": resp.timestamp.isoformat(),
                "question": resp.question_text,
                "response": resp.response_text,
            }
            for resp in responses
        ]

    async def generate_questions_for_categories(
        self, categories: list[str], user_id: int, db: Session
    ) -> dict[str, list[str]]:
        """Generate intelligent questions for given categories.

        Args:
            categories: List of categories to generate questions for
            user_id: User ID for context
            db: Database session

        Returns:
            Dict mapping category -> list of questions
        """
        questions_by_category: dict[str, list[str]] = {}

        for category in categories:
            # Get recent context for this category
            recent_responses = self.get_recent_context(user_id, db, category, limit=3)

            # Build context dict for LLM
            context_dict = {"recent_responses": recent_responses} if recent_responses else None

            try:
                questions_list = await self.llm_service.generate_questions(category, context_dict)
                if questions_list and isinstance(questions_list, list):
                    questions_by_category[category] = questions_list[:4]  # Max 4 per category
                else:
                    # Fallback to generic question
                    questions_by_category[category] = [
                        f"How are you doing with your {category.replace('_', ' ')}?"
                    ]
            except Exception as e:
                logger.error(f"Failed to generate questions for {category}: {e}")
                # Fallback
                questions_by_category[category] = [
                    f"How are you doing with your {category.replace('_', ' ')}?"
                ]

        return questions_by_category

    async def generate_intelligent_reminder(
        self, user_id: int, db: Session
    ) -> dict[str, Any]:
        """Generate an intelligent reminder based on recent activity gaps.

        Args:
            user_id: User to generate reminder for
            db: Database session

        Returns:
            Dictionary with:
            - questions: Dict of question_key -> question_text
            - categories: List of categories covered
            - reasoning: Why these questions were chosen
        """
        now = datetime.now(timezone.utc)

        # Get when each category was last asked
        last_asked_times = self.get_last_asked_times(user_id, db)

        # Filter out categories that were asked too recently
        eligible_categories = []
        for category in self.all_categories:
            min_hours = self.category_frequency_limits.get(category, 12)  # Default 12 hours
            last_asked = last_asked_times.get(category)

            if last_asked is None:
                # Never asked before, eligible
                eligible_categories.append(category)
            else:
                # Make last_asked timezone aware if it isn't
                if last_asked.tzinfo is None:
                    last_asked = last_asked.replace(tzinfo=timezone.utc)

                hours_since_asked = (now - last_asked).total_seconds() / 3600
                if hours_since_asked >= min_hours:
                    eligible_categories.append(category)
                else:
                    logger.debug(
                        f"Skipping {category}: asked {hours_since_asked:.1f}h ago "
                        f"(min interval: {min_hours}h)"
                    )

        # If no categories are eligible, use mental_state as fallback (it has shortest interval)
        if not eligible_categories:
            logger.warning("No eligible categories! Using mental_state as fallback")
            eligible_categories = ["mental_state"]

        # Analyze what's been covered in last 24 hours (for responses, not reminders)
        analysis = self.analyze_category_coverage(user_id, db, lookback_hours=24)

        gap_categories = [c for c in analysis["gap_categories"] if c in eligible_categories]
        covered_categories = [c for c in analysis["covered_categories"] if c in eligible_categories]

        # Prioritize gaps, but also check in on covered categories if they're important
        target_categories = []

        # Always include gaps (up to 3)
        target_categories.extend(gap_categories[:3])

        # If we have fewer than 3 categories, add some covered ones
        if len(target_categories) < 3 and covered_categories:
            # Sort covered by how long ago they were updated
            covered_sorted = sorted(
                covered_categories,
                key=lambda c: analysis["last_response_by_category"].get(c, datetime.min),
            )
            target_categories.extend(covered_sorted[: 3 - len(target_categories)])

        # If still no categories, use eligible ones
        if not target_categories:
            target_categories = eligible_categories[:3]

        # Generate questions for these categories
        questions_by_category = await self.generate_questions_for_categories(
            target_categories, user_id, db
        )

        # Flatten into single question dict
        all_questions: dict[str, str] = {}
        all_categories: list[str] = []
        question_idx = 1

        for category, questions in questions_by_category.items():
            all_categories.append(category)
            for question in questions:
                all_questions[f"q{question_idx}"] = question
                question_idx += 1

        reasoning = (
            f"Covering {len(gap_categories)} gap categories and "
            f"{len([c for c in target_categories if c in covered_categories])} recent categories. "
            f"Total responses in last 24h: {analysis['total_responses']}. "
            f"Eligible categories (respecting frequency limits): {len(eligible_categories)}/{len(self.all_categories)}"
        )

        return {
            "questions": all_questions,
            "categories": all_categories,
            "reasoning": reasoning,
            "analysis": analysis,
        }
