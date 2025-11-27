"""Celery tasks for Garmin data synchronization."""

import logging
from datetime import date, timedelta

from src.celery_app import app
from src.database import SessionLocal
from src.models.user import User as UserModel
from src.services.garmin import get_garmin_service

logger = logging.getLogger(__name__)


@app.task(name="garmin_tasks.sync_garmin_for_all_users")
def sync_garmin_for_all_users() -> dict:
    """Sync Garmin data for all users who have Garmin credentials configured.

    This task runs daily to fetch the latest health metrics from Garmin Connect.
    """
    logger.info("Starting Garmin sync for all users")
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(UserModel).all()
        total_synced = 0
        successful_users = 0

        for user in users:
            try:
                # For now, sync all users (later we could check for garmin_connected flag)
                garmin_service = get_garmin_service()

                # Sync last 2 days (yesterday and today)
                end_date = date.today()
                start_date = end_date - timedelta(days=1)

                results = garmin_service.sync_date_range(db, user.id, start_date, end_date)
                total_synced += len(results)
                successful_users += 1

                logger.info(f"Synced {len(results)} metrics for user {user.id}")

            except Exception as e:
                logger.error(f"Failed to sync Garmin for user {user.id}: {e}")
                continue

        logger.info(f"Completed Garmin sync: {total_synced} metrics for {successful_users}/{len(users)} users")
        return {
            "success": True,
            "total_synced": total_synced,
            "successful_users": successful_users,
            "total_users": len(users),
        }

    except Exception as e:
        logger.error(f"Garmin sync failed: {e}")
        raise
    finally:
        db.close()


@app.task(name="garmin_tasks.sync_garmin_for_user")
def sync_garmin_for_user(user_id: int, days_back: int = 7) -> dict:
    """Sync Garmin data for a specific user.

    Args:
        user_id: User ID to sync data for
        days_back: Number of days to sync (default: 7)
    """
    logger.info(f"Starting Garmin sync for user {user_id} ({days_back} days)")
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": "User not found"}

        # Sync date range
        garmin_service = get_garmin_service()
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back - 1)

        results = garmin_service.sync_date_range(db, user_id, start_date, end_date)

        logger.info(f"Synced {len(results)} metrics for user {user_id}")
        return {
            "success": True,
            "synced_count": len(results),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to sync Garmin for user {user_id}: {e}")
        raise
    finally:
        db.close()
