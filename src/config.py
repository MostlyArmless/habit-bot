"""Configuration management for the application."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(
        default="postgresql://habit_user:habit_password@localhost:5432/habit_bot"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # API
    api_key: str = Field(default="dev-api-key")
    environment: str = Field(default="development")

    # LLM
    ollama_base_url: str = Field(default="http://localhost:11434")
    llm_model: str = Field(default="gemma2:32b")

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.environment == "test"


class AppConfig:
    """Application configuration loaded from config.yaml."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = Path("config.yaml")

        self._config: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}

    @property
    def user(self) -> dict[str, Any]:
        """User configuration."""
        return self._config.get("user", {"name": "User", "timezone": "UTC"})

    @property
    def schedule(self) -> dict[str, Any]:
        """Schedule configuration."""
        return self._config.get(
            "schedule",
            {
                "wake_time": "06:30",
                "sleep_time": "22:30",
                "screens_off": "21:00",
                "bed_time": "22:00",
            },
        )

    @property
    def prompts(self) -> dict[str, Any]:
        """Prompts configuration."""
        return self._config.get(
            "prompts",
            {
                "default_frequency": 4,
                "min_interval_minutes": 120,
                "max_interval_minutes": 300,
                "reminder_intervals": [5, 10, 20],
                "max_reminders": 3,
            },
        )

    @property
    def categories(self) -> list[dict[str, Any]]:
        """Categories configuration."""
        return self._config.get("categories", [])

    @property
    def llm(self) -> dict[str, Any]:
        """LLM configuration."""
        return self._config.get(
            "llm",
            {
                "model": "gemma2:32b",
                "max_retries": 5,
                "temperature": 0.3,
            },
        )

    @property
    def server(self) -> dict[str, Any]:
        """Server configuration."""
        return self._config.get(
            "server",
            {
                "host": "0.0.0.0",
                "port": 8000,
                "lan_only": True,
            },
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


@lru_cache
def get_app_config() -> AppConfig:
    """Get cached app config instance."""
    return AppConfig()
