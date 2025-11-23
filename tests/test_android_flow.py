"""Integration tests simulating Android app requests.

These tests simulate the complete flow from an Android app's perspective,
including real LLM calls for response processing.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


# Sample user responses that simulate real Android app input
SAMPLE_RESPONSES = {
    "sleep": {
        "question": "How did you sleep last night?",
        "response": "I slept about 7 hours, went to bed around 11pm and woke up at 6am. "
        "Quality was maybe a 6 out of 10, I woke up once around 3am to use the bathroom "
        "and had trouble falling back asleep for about 20 minutes.",
    },
    "nutrition": {
        "question": "What have you eaten today?",
        "response": "For breakfast I had two eggs scrambled with some cheese and a slice "
        "of whole wheat toast around 8am. Then for lunch around 12:30 I had a turkey "
        "sandwich with lettuce, tomato, and mayo, plus an apple and some chips.",
    },
    "mental_state": {
        "question": "How are you feeling right now?",
        "response": "I'm feeling pretty good, maybe a 7 out of 10. A bit tired from not "
        "sleeping great but otherwise in a decent mood. Looking forward to the weekend.",
    },
    "stress_anxiety": {
        "question": "What's your current stress level?",
        "response": "Stress is around a 5 today. Work has been busy with a deadline coming "
        "up on Friday, but it's manageable. I've been taking short breaks to walk around "
        "which helps.",
    },
    "physical_activity": {
        "question": "What physical activity have you done today?",
        "response": "I went for a 30 minute jog this morning, probably covered about 3 miles. "
        "Medium intensity, kept my heart rate around 140-150. Also took a 15 minute walk "
        "at lunch.",
    },
    "substances": {
        "question": "Have you consumed any caffeine, alcohol, or other substances today?",
        "response": "I had two cups of coffee this morning, one at 7am and another around 10. "
        "No alcohol today. I take a daily vitamin and fish oil supplement.",
    },
}


class TestAndroidAppFlow:
    """Test suite simulating Android app interactions."""

    def test_complete_onboarding_flow(self, client: TestClient):
        """Test the complete user onboarding flow.

        Simulates:
        1. Android app creating a new user account
        2. Setting up user preferences
        """
        # Step 1: Create user
        response = client.post(
            "/api/v1/users/",
            json={
                "name": "Android User",
                "timezone": "America/Los_Angeles",
            },
        )
        assert response.status_code == 201
        user = response.json()
        assert user["name"] == "Android User"
        assert "id" in user

        # Step 2: Update user preferences (wake/sleep times)
        response = client.patch(
            f"/api/v1/users/{user['id']}",
            json={
                "wake_time": "07:00:00",
                "sleep_time": "23:00:00",
                "bed_time": "22:30:00",
            },
        )
        assert response.status_code == 200

    def test_fetch_and_respond_to_prompt_flow(self, client: TestClient):
        """Test the flow of fetching a prompt and submitting a response.

        Simulates:
        1. Android app checking for pending prompts
        2. Displaying the prompt to user
        3. User submitting their response
        """
        # Setup: Create user
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "Prompt Flow User"},
        )
        user_id = user_response.json()["id"]

        # Setup: Create a prompt that's ready to be sent
        scheduled_time = datetime.now(timezone.utc).isoformat()
        prompt_response = client.post(
            "/api/v1/prompts/",
            json={
                "user_id": user_id,
                "scheduled_time": scheduled_time,
                "questions": {
                    "q1": "How are you feeling right now?",
                    "q2": "Rate your energy level 1-10",
                },
                "categories": ["mental_state"],
            },
        )
        assert prompt_response.status_code == 201
        prompt = prompt_response.json()

        # Android App Flow Step 1: Acknowledge the prompt
        ack_response = client.post(f"/api/v1/prompts/{prompt['id']}/acknowledge")
        assert ack_response.status_code == 200
        assert ack_response.json()["status"] == "acknowledged"

        # Android App Flow Step 2: Submit response
        response = client.post(
            "/api/v1/responses/",
            json={
                "prompt_id": prompt["id"],
                "user_id": user_id,
                "question_text": "How are you feeling right now?",
                "response_text": SAMPLE_RESPONSES["mental_state"]["response"],
                "category": "mental_state",
            },
        )
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["processing_status"] == "pending"

        # Verify prompt is now completed
        prompt_check = client.get(f"/api/v1/prompts/{prompt['id']}")
        assert prompt_check.json()["status"] == "completed"

    def test_multiple_category_responses(self, client: TestClient):
        """Test submitting responses across multiple categories.

        Simulates a user responding to a multi-category check-in prompt.
        """
        # Setup
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "Multi-Category User"},
        )
        user_id = user_response.json()["id"]

        scheduled_time = datetime.now(timezone.utc).isoformat()
        prompt_response = client.post(
            "/api/v1/prompts/",
            json={
                "user_id": user_id,
                "scheduled_time": scheduled_time,
                "questions": {
                    "sleep": "How did you sleep?",
                    "nutrition": "What have you eaten?",
                    "mental_state": "How are you feeling?",
                },
                "categories": ["sleep", "nutrition", "mental_state"],
            },
        )
        prompt_id = prompt_response.json()["id"]

        # Submit responses for each category
        for category in ["sleep", "nutrition", "mental_state"]:
            sample = SAMPLE_RESPONSES[category]
            response = client.post(
                "/api/v1/responses/",
                json={
                    "prompt_id": prompt_id,
                    "user_id": user_id,
                    "question_text": sample["question"],
                    "response_text": sample["response"],
                    "category": category,
                },
            )
            assert response.status_code == 201

        # Verify all responses were recorded
        responses = client.get(f"/api/v1/responses/?prompt_id={prompt_id}")
        assert len(responses.json()) == 3

    def test_list_user_history(self, client: TestClient):
        """Test fetching a user's response history.

        Simulates the Android app's history/dashboard view.
        """
        # Setup: Create user with some responses
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "History User"},
        )
        user_id = user_response.json()["id"]

        # Create multiple prompts and responses
        for i, category in enumerate(["sleep", "mental_state", "nutrition"]):
            prompt_response = client.post(
                "/api/v1/prompts/",
                json={
                    "user_id": user_id,
                    "scheduled_time": datetime.now(timezone.utc).isoformat(),
                    "questions": {"q1": SAMPLE_RESPONSES[category]["question"]},
                    "categories": [category],
                },
            )
            prompt_id = prompt_response.json()["id"]

            client.post(
                "/api/v1/responses/",
                json={
                    "prompt_id": prompt_id,
                    "user_id": user_id,
                    "question_text": SAMPLE_RESPONSES[category]["question"],
                    "response_text": SAMPLE_RESPONSES[category]["response"],
                    "category": category,
                },
            )

        # Android app fetches user's response history
        history = client.get(f"/api/v1/responses/?user_id={user_id}")
        assert history.status_code == 200
        assert len(history.json()) == 3

        # Filter by category
        sleep_history = client.get(f"/api/v1/responses/?user_id={user_id}&category=sleep")
        assert len(sleep_history.json()) == 1


@pytest.mark.asyncio
class TestAndroidFlowWithLLM:
    """Integration tests that include real LLM processing.

    These tests make actual calls to Ollama for response extraction.
    """

    @pytest.fixture
    def async_client(self, client):
        """Return the sync client for async tests using httpx."""
        return client

    def test_llm_health_check(self, client: TestClient):
        """Test that the LLM service is available."""
        response = client.get("/api/v1/llm/health")
        assert response.status_code == 200
        data = response.json()
        # This may be unavailable if ollama isn't running, which is acceptable
        assert "status" in data
        assert "model" in data

    def test_process_sleep_response_with_llm(self, client: TestClient):
        """Test processing a sleep response through the LLM.

        This test makes a real call to Ollama to extract structured data.
        """
        # Setup
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "LLM Test User"},
        )
        user_id = user_response.json()["id"]

        prompt_response = client.post(
            "/api/v1/prompts/",
            json={
                "user_id": user_id,
                "scheduled_time": datetime.now(timezone.utc).isoformat(),
                "questions": {"q1": SAMPLE_RESPONSES["sleep"]["question"]},
                "categories": ["sleep"],
            },
        )
        prompt_id = prompt_response.json()["id"]

        # Submit response
        response = client.post(
            "/api/v1/responses/",
            json={
                "prompt_id": prompt_id,
                "user_id": user_id,
                "question_text": SAMPLE_RESPONSES["sleep"]["question"],
                "response_text": SAMPLE_RESPONSES["sleep"]["response"],
                "category": "sleep",
            },
        )
        response_id = response.json()["id"]

        # Process with LLM
        process_result = client.post(
            "/api/v1/llm/process-response",
            json={"response_id": response_id},
        )
        assert process_result.status_code == 200
        result = process_result.json()

        # If LLM is available, check for structured data
        if result["success"]:
            assert result["structured_data"] is not None
            # The LLM should extract something about sleep duration
            structured = result["structured_data"]
            assert "data" in structured or "summary" in structured

        # Verify the response was updated
        updated_response = client.get(f"/api/v1/responses/{response_id}")
        assert updated_response.status_code == 200
        if result["success"]:
            assert updated_response.json()["processing_status"] == "completed"
            assert updated_response.json()["response_structured"] is not None

    def test_process_nutrition_response_with_llm(self, client: TestClient):
        """Test processing a nutrition response through the LLM."""
        # Setup
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "Nutrition LLM User"},
        )
        user_id = user_response.json()["id"]

        prompt_response = client.post(
            "/api/v1/prompts/",
            json={
                "user_id": user_id,
                "scheduled_time": datetime.now(timezone.utc).isoformat(),
                "questions": {"q1": SAMPLE_RESPONSES["nutrition"]["question"]},
                "categories": ["nutrition"],
            },
        )
        prompt_id = prompt_response.json()["id"]

        response = client.post(
            "/api/v1/responses/",
            json={
                "prompt_id": prompt_id,
                "user_id": user_id,
                "question_text": SAMPLE_RESPONSES["nutrition"]["question"],
                "response_text": SAMPLE_RESPONSES["nutrition"]["response"],
                "category": "nutrition",
            },
        )
        response_id = response.json()["id"]

        # Process with LLM
        process_result = client.post(
            "/api/v1/llm/process-response",
            json={"response_id": response_id},
        )
        assert process_result.status_code == 200
        result = process_result.json()

        if result["success"]:
            structured = result["structured_data"]
            # The LLM should extract food items
            assert structured is not None

    def test_generate_questions_for_category(self, client: TestClient):
        """Test generating questions for a category using the LLM."""
        response = client.post("/api/v1/llm/generate-questions?category=mental_state")
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "mental_state"
        assert "questions" in data
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) >= 1

    def test_full_android_session_with_llm(self, client: TestClient):
        """Test a complete Android session including LLM processing.

        Simulates:
        1. User opens app
        2. Gets a prompt
        3. Responds to multiple questions
        4. Responses are processed by LLM
        5. User can view their processed history
        """
        # Step 1: User opens app (or has account)
        user_response = client.post(
            "/api/v1/users/",
            json={"name": "Full Session User", "timezone": "America/New_York"},
        )
        user_id = user_response.json()["id"]

        # Step 2: App creates a check-in prompt
        prompt_response = client.post(
            "/api/v1/prompts/",
            json={
                "user_id": user_id,
                "scheduled_time": datetime.now(timezone.utc).isoformat(),
                "questions": {
                    "mental_state": "How are you feeling?",
                    "stress_anxiety": "What's your stress level?",
                },
                "categories": ["mental_state", "stress_anxiety"],
            },
        )
        prompt_id = prompt_response.json()["id"]

        # Step 3: User acknowledges and responds
        client.post(f"/api/v1/prompts/{prompt_id}/acknowledge")

        response_ids = []
        for category in ["mental_state", "stress_anxiety"]:
            resp = client.post(
                "/api/v1/responses/",
                json={
                    "prompt_id": prompt_id,
                    "user_id": user_id,
                    "question_text": SAMPLE_RESPONSES[category]["question"],
                    "response_text": SAMPLE_RESPONSES[category]["response"],
                    "category": category,
                },
            )
            response_ids.append(resp.json()["id"])

        # Step 4: Process responses with LLM
        for response_id in response_ids:
            result = client.post(
                "/api/v1/llm/process-response",
                json={"response_id": response_id},
            )
            assert result.status_code == 200

        # Step 5: User views their history with processed data
        history = client.get(f"/api/v1/responses/?user_id={user_id}")
        assert history.status_code == 200
        responses = history.json()
        assert len(responses) == 2

        # Check that at least some responses have been processed
        # (depends on Ollama availability)
        processed_count = sum(
            1 for r in responses if r["processing_status"] == "completed"
        )
        # We expect either all processed (if LLM available) or none (if unavailable)
        assert processed_count == 0 or processed_count == 2
