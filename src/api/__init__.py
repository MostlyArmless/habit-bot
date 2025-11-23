"""API routers."""

from src.api.categories import router as categories_router
from src.api.health import router as health_router
from src.api.llm import router as llm_router
from src.api.notifications import router as notifications_router
from src.api.prompts import router as prompts_router
from src.api.responses import router as responses_router
from src.api.users import router as users_router

__all__ = [
    "categories_router",
    "health_router",
    "llm_router",
    "notifications_router",
    "prompts_router",
    "responses_router",
    "users_router",
]
