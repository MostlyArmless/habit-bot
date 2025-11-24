"""Tests for Celery tasks."""

from datetime import datetime, time, timezone

import pytest

from src.tasks.reminder_tasks import _calculate_reminder_times


class TestReminderScheduling:
    """Tests for reminder scheduling logic."""

    def test_calculate_reminder_times_basic(self):
        """Test basic reminder time calculation."""
        wake = time(8, 0)
        sleep = time(22, 0)

        times = _calculate_reminder_times(wake, sleep, num_reminders=4)

        assert len(times) == 4
        # Reminders should be between wake and sleep times
        for t in times:
            assert t >= wake
            assert t <= sleep

    def test_calculate_reminder_times_evenly_spaced(self):
        """Test that reminders are evenly spaced."""
        wake = time(8, 0)  # 8:00 AM
        sleep = time(20, 0)  # 8:00 PM (12 hours)

        times = _calculate_reminder_times(wake, sleep, num_reminders=3)

        # With 12 hours and 3 reminders, interval should be 3 hours
        # Reminders at 11:00, 14:00, 17:00
        assert len(times) == 3
        assert times[0].hour == 11
        assert times[1].hour == 14
        assert times[2].hour == 17

    def test_calculate_reminder_times_single_reminder(self):
        """Test with single reminder."""
        wake = time(8, 0)
        sleep = time(20, 0)

        times = _calculate_reminder_times(wake, sleep, num_reminders=1)

        assert len(times) == 1
        # Single reminder should be at midpoint
        assert times[0].hour == 14

    def test_calculate_reminder_times_handles_late_sleeper(self):
        """Test with someone who sleeps late."""
        wake = time(10, 0)
        sleep = time(2, 0)  # 2 AM next day

        times = _calculate_reminder_times(wake, sleep, num_reminders=4)

        assert len(times) == 4
        # All times should be valid
        for t in times:
            assert 0 <= t.hour < 24


class TestCeleryTaskImports:
    """Test that Celery tasks can be imported."""

    def test_import_llm_tasks(self):
        """Test LLM task imports."""
        from src.tasks.llm_tasks import process_pending_responses, process_response

        assert process_response is not None
        assert process_pending_responses is not None

    def test_import_reminder_tasks(self):
        """Test reminder task imports."""
        from src.tasks.reminder_tasks import (
            create_scheduled_reminders_for_user,
            schedule_pending_reminders,
            send_reminder_notification,
        )

        assert schedule_pending_reminders is not None
        assert send_reminder_notification is not None
        assert create_scheduled_reminders_for_user is not None

    def test_celery_app_configuration(self):
        """Test Celery app is configured correctly."""
        from src.celery_app import app

        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert "schedule-reminders-every-minute" in app.conf.beat_schedule
        assert "process-pending-responses-every-30s" in app.conf.beat_schedule
