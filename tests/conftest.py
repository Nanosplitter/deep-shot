"""Pytest configuration and fixtures."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config.settings import Settings
from app.services.code_executor import CodeExecutor
from app.services.nfl_service import NFLService


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="test-api-key",
        model="gpt-5.1",
        max_retries=2,
        current_season=2025,
        code_timeout_seconds=5,
    )


@pytest.fixture
def code_executor(settings):
    return CodeExecutor(timeout_seconds=settings.code_timeout_seconds)


@pytest.fixture
def mock_openai_client():
    return AsyncMock()


@pytest.fixture
def nfl_service(settings, mock_openai_client):
    service = NFLService(settings)
    service.client = mock_openai_client
    return service


@pytest.fixture
def mock_function_call_response():
    def _create(code: str):
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.type = "function_call"
        mock_item.name = "run_nflreadpy_code"
        mock_item.call_id = "call_123"
        mock_item.arguments = json.dumps({"code": code})
        mock_response.output = [mock_item]
        return mock_response

    return _create


@pytest.fixture
def mock_text_response():
    def _create(text: str):
        mock_response = MagicMock()
        mock_response.output_text = text
        mock_response.output = []
        return mock_response

    return _create
