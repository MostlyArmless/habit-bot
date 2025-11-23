"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.api import (
    categories_router,
    health_router,
    prompts_router,
    responses_router,
    users_router,
)
from src.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Habit Bot API",
    description="Personal Health Tracking System using Ecological Momentary Assessment (EMA)",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(prompts_router)
app.include_router(responses_router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "Habit Bot API",
        "version": "0.1.0",
        "docs": "/docs",
    }
