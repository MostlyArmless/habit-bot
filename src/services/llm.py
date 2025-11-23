"""LLM service for Ollama integration."""

import json
import logging
from typing import Any

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Ollama LLM."""

    def __init__(self, use_fast_model: bool = False) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.llm_model_fast if use_fast_model else self.settings.llm_model
        self.timeout = 120.0  # 2 minutes for LLM responses

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a response from the LLM."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def extract_structured_data(
        self,
        response_text: str,
        question_text: str,
        category: str,
    ) -> dict[str, Any]:
        """Extract structured data from a free-text response."""
        system_prompt = """You are a health data extraction assistant. Your job is to extract structured information from user responses to health-related questions.

Always respond with valid JSON only. No explanation, no markdown, just the JSON object.

Extract the following types of information based on the category:
- For nutrition: food items, quantities, meal type, time eaten
- For sleep: duration, quality (1-10), wake time, bed time, interruptions
- For substances: substance type, amount, time consumed
- For physical_activity: activity type, duration, intensity (low/medium/high)
- For mental_state: mood (1-10), emotions, notable thoughts
- For stress_anxiety: level (1-10), triggers, physical symptoms
- For social_interaction: type, duration, people involved, quality (1-10)
- For work_productivity: focus level (1-10), tasks completed, interruptions
- For environment: location, noise level, temperature comfort
- For physical_symptoms: symptom type, severity (1-10), duration"""

        prompt = f"""Category: {category}
Question: {question_text}
User Response: {response_text}

Extract the structured data as JSON. Include a "summary" field with a brief summary and a "data" field with the extracted values."""

        try:
            result = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Low temperature for structured extraction
            )
            # Clean up response - remove markdown code blocks if present
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return {
                "summary": response_text[:200],
                "data": {},
                "parse_error": str(e),
                "raw_response": result if "result" in locals() else None,
            }
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Ollama: {e}")
            raise

    async def generate_questions(
        self,
        category: str,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Generate contextual questions for a category."""
        system_prompt = """You are a health tracking assistant. Generate concise, friendly questions to ask the user about their health behaviors.

Rules:
- Questions should be specific and easy to answer
- Avoid yes/no questions - ask for details
- Be conversational but not overly casual
- Focus on actionable information

Respond with a JSON array of 1-3 questions."""

        context_str = ""
        if context:
            context_str = f"\n\nContext from previous responses:\n{json.dumps(context, indent=2)}"

        prompt = f"""Generate questions for the category: {category}{context_str}

Return a JSON array of questions."""

        try:
            result = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,  # Higher temperature for variety
            )
            # Clean up response
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            questions = json.loads(result)
            if isinstance(questions, list):
                # Handle both plain strings and objects with 'question' key
                return [
                    q if isinstance(q, str) else q.get("question", str(q))
                    for q in questions
                ]
            return [questions] if isinstance(questions, str) else []
        except (json.JSONDecodeError, httpx.HTTPError) as e:
            logger.warning(f"Failed to generate questions: {e}")
            # Fallback to default questions
            return self._get_default_questions(category)

    def _get_default_questions(self, category: str) -> list[str]:
        """Get default questions for a category."""
        defaults = {
            "sleep": ["How did you sleep last night? Rate quality 1-10 and describe any issues."],
            "nutrition": ["What have you eaten recently? Include approximate times and portions."],
            "substances": ["Have you consumed any caffeine, alcohol, or other substances today?"],
            "physical_activity": ["What physical activity have you done today?"],
            "mental_state": ["How are you feeling right now? Rate your mood 1-10."],
            "stress_anxiety": ["What's your current stress level (1-10)? Any specific triggers?"],
            "social_interaction": ["Who have you interacted with today and how did it go?"],
            "work_productivity": ["How focused have you been today (1-10)? What did you accomplish?"],
            "environment": ["Describe your current environment - location, noise, comfort level."],
            "physical_symptoms": ["Any physical symptoms to note? Headaches, fatigue, pain?"],
        }
        return defaults.get(category, ["How are you doing right now?"])

    async def health_check(self) -> bool:
        """Check if Ollama is available and the model is loaded."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return self.model in models or any(self.model in m for m in models)
        except httpx.HTTPError:
            return False


def get_llm_service(use_fast_model: bool = False) -> LLMService:
    """Get an LLM service instance."""
    return LLMService(use_fast_model=use_fast_model)
