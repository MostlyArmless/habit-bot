"""Garmin Connect integration service."""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from garminconnect import Garmin
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.garmin_data import GarminData, GarminMetricType

logger = logging.getLogger(__name__)

# Token storage path
TOKEN_STORE = Path("/tmp/garmin_tokens")


class GarminService:
    """Service for fetching data from Garmin Connect."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Garmin | None = None

    def _get_client(self) -> Garmin:
        """Get authenticated Garmin client, reusing tokens if available."""
        if self._client is not None:
            return self._client

        email = self.settings.garmin_email
        password = self.settings.garmin_password

        if not email or not password:
            raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD must be set")

        TOKEN_STORE.mkdir(parents=True, exist_ok=True)
        token_file = TOKEN_STORE / "garmin_session.json"

        client = Garmin(email, password)

        # Try to load existing session
        if token_file.exists():
            try:
                client.login(token_file)
                logger.info("Logged in using saved session")
                self._client = client
                return client
            except Exception as e:
                logger.warning(f"Failed to use saved session: {e}")

        # Fresh login
        client.login()
        client.garth.dump(str(token_file))
        logger.info("Fresh login successful, session saved")
        self._client = client
        return client

    def fetch_sleep(self, target_date: date) -> dict[str, Any]:
        """Fetch sleep data for a specific date."""
        client = self._get_client()
        date_str = target_date.isoformat()
        return client.get_sleep_data(date_str) or {}

    def fetch_hrv(self, target_date: date) -> dict[str, Any]:
        """Fetch HRV data for a specific date."""
        client = self._get_client()
        date_str = target_date.isoformat()
        return client.get_hrv_data(date_str) or {}

    def fetch_resting_hr(self, target_date: date) -> dict[str, Any]:
        """Fetch resting heart rate for a specific date."""
        client = self._get_client()
        date_str = target_date.isoformat()
        # Get heart rate data which includes resting HR
        return client.get_heart_rates(date_str) or {}

    def fetch_body_battery(self, target_date: date) -> dict[str, Any]:
        """Fetch body battery data for a specific date."""
        client = self._get_client()
        date_str = target_date.isoformat()
        return client.get_body_battery(date_str) or {}

    def fetch_stress(self, target_date: date) -> dict[str, Any]:
        """Fetch stress data for a specific date."""
        client = self._get_client()
        date_str = target_date.isoformat()
        return client.get_stress_data(date_str) or {}

    def fetch_all_metrics(self, target_date: date) -> dict[str, dict[str, Any]]:
        """Fetch all tracked metrics for a specific date."""
        metrics = {}

        try:
            metrics["sleep"] = self.fetch_sleep(target_date)
        except Exception as e:
            logger.error(f"Failed to fetch sleep: {e}")
            metrics["sleep"] = {"error": str(e)}

        try:
            metrics["hrv"] = self.fetch_hrv(target_date)
        except Exception as e:
            logger.error(f"Failed to fetch HRV: {e}")
            metrics["hrv"] = {"error": str(e)}

        try:
            metrics["resting_hr"] = self.fetch_resting_hr(target_date)
        except Exception as e:
            logger.error(f"Failed to fetch resting HR: {e}")
            metrics["resting_hr"] = {"error": str(e)}

        try:
            metrics["body_battery"] = self.fetch_body_battery(target_date)
        except Exception as e:
            logger.error(f"Failed to fetch body battery: {e}")
            metrics["body_battery"] = {"error": str(e)}

        try:
            metrics["stress"] = self.fetch_stress(target_date)
        except Exception as e:
            logger.error(f"Failed to fetch stress: {e}")
            metrics["stress"] = {"error": str(e)}

        return metrics

    def sync_metrics_to_db(
        self,
        db: Session,
        user_id: int,
        target_date: date,
        metrics: dict[str, dict[str, Any]] | None = None,
    ) -> list[GarminData]:
        """Sync Garmin metrics to database for a specific date.

        Args:
            db: Database session
            user_id: User ID to associate data with
            target_date: Date to sync metrics for
            metrics: Optional pre-fetched metrics (will fetch if not provided)

        Returns:
            List of created/updated GarminData records
        """
        if metrics is None:
            metrics = self.fetch_all_metrics(target_date)

        now = datetime.now(timezone.utc)
        results = []

        # Process each metric type
        metric_configs = [
            (GarminMetricType.SLEEP, "sleep", self._extract_sleep_value),
            (GarminMetricType.SLEEP_SCORE, "sleep", self._extract_sleep_score_value),
            (GarminMetricType.HRV, "hrv", self._extract_hrv_value),
            (GarminMetricType.RESTING_HR, "resting_hr", self._extract_resting_hr_value),
            (GarminMetricType.BODY_BATTERY, "body_battery", self._extract_body_battery_value),
            (GarminMetricType.STRESS, "stress", self._extract_stress_value),
        ]

        for metric_type, key, extractor in metric_configs:
            data = metrics.get(key, {})
            if "error" in data:
                continue

            # Extract primary value
            value = extractor(data)

            # Upsert: update if exists, create if not
            existing = (
                db.query(GarminData)
                .filter(
                    GarminData.user_id == user_id,
                    GarminData.metric_type == metric_type.value,
                    GarminData.metric_date == target_date,
                    GarminData.deleted_at.is_(None),
                )
                .first()
            )

            if existing:
                existing.value = value
                existing.details = data
                existing.fetched_at = now
                results.append(existing)
            else:
                record = GarminData(
                    user_id=user_id,
                    metric_type=metric_type.value,
                    metric_date=target_date,
                    fetched_at=now,
                    value=value,
                    details=data,
                )
                db.add(record)
                results.append(record)

        db.commit()
        for r in results:
            db.refresh(r)

        return results

    def sync_date_range(
        self,
        db: Session,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[GarminData]:
        """Sync metrics for a date range."""
        all_results = []
        current = start_date

        while current <= end_date:
            logger.info(f"Syncing Garmin data for {current}")
            try:
                results = self.sync_metrics_to_db(db, user_id, current)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to sync {current}: {e}")
            current += timedelta(days=1)

        return all_results

    # Value extractors for each metric type
    @staticmethod
    def _extract_sleep_value(data: dict) -> Decimal | None:
        """Extract total sleep duration in hours."""
        if duration := data.get("dailySleepDTO", {}).get("sleepTimeSeconds"):
            return Decimal(str(round(duration / 3600, 2)))
        return None

    @staticmethod
    def _extract_sleep_score_value(data: dict) -> Decimal | None:
        """Extract sleep score (0-100)."""
        if score := data.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value"):
            return Decimal(str(score))
        # Alternative location for sleep score
        if score := data.get("dailySleepDTO", {}).get("overallSleepScore"):
            return Decimal(str(score))
        return None

    @staticmethod
    def _extract_hrv_value(data: dict) -> Decimal | None:
        """Extract HRV baseline/average."""
        if hrv_summary := data.get("hrvSummary", {}):
            if baseline := hrv_summary.get("baselineLowUpper"):
                return Decimal(str(baseline))
            if weekly := hrv_summary.get("weeklyAvg"):
                return Decimal(str(weekly))
        return None

    @staticmethod
    def _extract_resting_hr_value(data: dict) -> Decimal | None:
        """Extract resting heart rate."""
        if resting := data.get("restingHeartRate"):
            return Decimal(str(resting))
        return None

    @staticmethod
    def _extract_body_battery_value(data: dict) -> Decimal | None:
        """Extract body battery (latest or charged value)."""
        if isinstance(data, list) and data:
            # Body battery returns a list of readings
            latest = data[-1] if data else None
            if latest and "charged" in latest:
                return Decimal(str(latest["charged"]))
        elif isinstance(data, dict):
            if charged := data.get("charged"):
                return Decimal(str(charged))
        return None

    @staticmethod
    def _extract_stress_value(data: dict) -> Decimal | None:
        """Extract average stress level."""
        if avg := data.get("avgStressLevel"):
            return Decimal(str(avg))
        if overall := data.get("overallStressLevel"):
            return Decimal(str(overall))
        return None


# Singleton instance
_garmin_service: GarminService | None = None


def get_garmin_service() -> GarminService:
    """Get or create GarminService singleton."""
    global _garmin_service
    if _garmin_service is None:
        _garmin_service = GarminService()
    return _garmin_service
