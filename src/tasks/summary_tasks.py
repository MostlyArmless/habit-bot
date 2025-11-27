"""Celery tasks for generating activity summaries."""

import asyncio
import logging

from src.celery_app import app as celery_app
from src.database import SessionLocal
from src.models.user import User as UserModel
from src.services.summary import SummaryService

logger = logging.getLogger(__name__)


@celery_app.task(name="summary_tasks.generate_summaries_for_all_users")
def generate_summaries_for_all_users():
    """Generate summaries for all active users.

    This task runs periodically (e.g., every hour) to keep summaries fresh.
    """
    logger.info("Starting summary generation for all users")
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(UserModel).all()
        logger.info(f"Found {len(users)} users")

        for user in users:
            try:
                # Generate summaries for this user
                summary_service = SummaryService()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    summaries = loop.run_until_complete(
                        summary_service.generate_all_summaries(user.id, db)
                    )
                    logger.info(
                        f"Generated {len(summaries)} summaries for user {user.id}"
                    )
                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Failed to generate summaries for user {user.id}: {e}")
                continue

        logger.info("Completed summary generation for all users")

    except Exception as e:
        logger.error(f"Failed to generate summaries: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="summary_tasks.generate_summaries_for_user")
def generate_summaries_for_user(user_id: int):
    """Generate summaries for a specific user.

    Args:
        user_id: User ID to generate summaries for
    """
    logger.info(f"Starting summary generation for user {user_id}")
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return

        # Generate summaries
        summary_service = SummaryService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            summaries = loop.run_until_complete(
                summary_service.generate_all_summaries(user_id, db)
            )
            logger.info(f"Generated {len(summaries)} summaries for user {user_id}")
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to generate summaries for user {user_id}: {e}")
        raise
    finally:
        db.close()
