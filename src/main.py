"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import (
    categories_router,
    garmin_router,
    health_router,
    llm_router,
    notifications_router,
    quicklog_router,
    reminders_router,
    responses_router,
    summaries_router,
    users_router,
)
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def run_migrations() -> None:
    """Run alembic migrations on startup."""
    import os

    # Skip migrations during testing
    if os.environ.get("TESTING") == "1":
        logger.info("Skipping migrations in test mode")
        return

    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup - run migrations
    run_migrations()
    yield
    # Shutdown


app = FastAPI(
    title="Habit Bot API",
    description="Personal Health Tracking System using Ecological Momentary Assessment (EMA)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for PWA access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(reminders_router)
app.include_router(responses_router)
app.include_router(llm_router)
app.include_router(notifications_router)
app.include_router(quicklog_router)
app.include_router(garmin_router)
app.include_router(summaries_router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "Habit Bot API",
        "version": "0.1.0",
        "docs": "/docs",
    }
