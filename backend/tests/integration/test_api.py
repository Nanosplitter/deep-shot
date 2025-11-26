"""Integration tests for the NFL API."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import NFLResponse
from app.config.settings import Settings
from app.api.routes.nfl import get_nfl_service, get_settings


@pytest.fixture
def test_settings():
    return Settings(
        openai_api_key="test-api-key",
        model="gpt-5.1",
        max_retries=2,
        current_season=2025,
        code_timeout_seconds=5,
    )


@pytest.fixture
def mock_nfl_service():
    service = MagicMock()
    service.process = AsyncMock()
    service.process_chat = AsyncMock()
    return service


@pytest.fixture
def client(test_settings, mock_nfl_service):
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_nfl_service] = lambda: mock_nfl_service

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_health_returns_healthy_status(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestProcessEndpoint:
    def test_process_valid_input_returns_response(self, client, mock_nfl_service):
        mock_nfl_service.process.return_value = NFLResponse(
            response="The answer is 42",
            code_generated=None,
            raw_data=None,
            attempts=1,
        )

        response = client.post("/nfl/process", json={"input": "How many touchdowns?"})

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "The answer is 42"

    def test_process_with_code_generation_returns_code_and_data(
        self, client, mock_nfl_service
    ):
        mock_nfl_service.process.return_value = NFLResponse(
            response="There were 42 touchdowns",
            code_generated='def run(): return {"response": 42}',
            raw_data={"response": 42},
            attempts=1,
        )

        response = client.post("/nfl/process", json={"input": "How many touchdowns?"})

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "There were 42 touchdowns"
        assert data["raw_data"] == {"response": 42}
        assert data["code_generated"] is not None

    def test_process_missing_input_returns_422(self, client):
        response = client.post("/nfl/process", json={})

        assert response.status_code == 422

    def test_process_llm_error_returns_500(self, client, mock_nfl_service):
        mock_nfl_service.process.side_effect = Exception("API Error")

        response = client.post("/nfl/process", json={"input": "Test question"})

        assert response.status_code == 500


class TestResponseSchema:
    def test_response_matches_nfl_response_schema(self, client, mock_nfl_service):
        mock_nfl_service.process.return_value = NFLResponse(
            response="Test response",
            code_generated=None,
            raw_data=None,
            attempts=1,
        )

        response = client.post("/nfl/process", json={"input": "Test"})

        data = response.json()
        nfl_response = NFLResponse(**data)
        assert nfl_response.response == "Test response"
        assert nfl_response.attempts >= 1


class TestChatEndpoint:
    def test_chat_valid_messages_returns_response(self, client, mock_nfl_service):
        mock_nfl_service.process_chat.return_value = NFLResponse(
            response="Follow up answer",
            code_generated=None,
            raw_data=None,
            attempts=1,
        )

        response = client.post(
            "/nfl/chat",
            json={
                "messages": [
                    {"role": "user", "content": "How many touchdowns?"},
                    {"role": "assistant", "content": "There were 42"},
                    {"role": "user", "content": "What about last season?"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Follow up answer"

    def test_chat_with_code_generation_returns_code_and_data(
        self, client, mock_nfl_service
    ):
        mock_nfl_service.process_chat.return_value = NFLResponse(
            response="Last season had 38 touchdowns",
            code_generated='def run(): return {"response": 38}',
            raw_data={"response": 38},
            attempts=1,
        )

        response = client.post(
            "/nfl/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Compare touchdowns by season"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["raw_data"] == {"response": 38}
        assert data["code_generated"] is not None

    def test_chat_empty_messages_returns_400(self, client):
        response = client.post("/nfl/chat", json={"messages": []})

        assert response.status_code == 400

    def test_chat_missing_messages_returns_422(self, client):
        response = client.post("/nfl/chat", json={})

        assert response.status_code == 422

    def test_chat_llm_error_returns_500(self, client, mock_nfl_service):
        mock_nfl_service.process_chat.side_effect = Exception("API Error")

        response = client.post(
            "/nfl/chat",
            json={"messages": [{"role": "user", "content": "Test"}]},
        )

        assert response.status_code == 500
