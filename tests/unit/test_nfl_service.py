"""Unit tests for NFLService."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.models.schemas import CodeExecutionResult


class TestNFLServiceBuildMessages:
    def test_build_base_messages_contains_system_prompts(self, nfl_service):
        messages = nfl_service._build_base_messages("test question")

        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "system"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "test question"

    def test_build_base_messages_includes_current_season(self, nfl_service):
        messages = nfl_service._build_base_messages("test question")

        assert "2025" in messages[0]["content"]

    def test_build_retry_messages_appends_error_context(self, nfl_service):
        base_messages = [{"role": "user", "content": "test"}]
        code = "def run(): pass"
        error = "NameError: name 'x' is not defined"

        messages = nfl_service._build_retry_messages(base_messages, code, error)

        assert len(messages) == 4
        assert "error" in messages[-1]["content"].lower()
        assert code in messages[-2]["content"]


class TestNFLServiceExtractors:
    def test_extract_function_call_returns_call_id_and_code(
        self, nfl_service, mock_function_call_response
    ):
        response = mock_function_call_response("def run(): return {}")

        result = nfl_service._extract_function_call(response)

        assert result is not None
        assert result[0] == "call_123"
        assert "def run()" in result[1]

    def test_extract_function_call_returns_none_for_text_response(
        self, nfl_service, mock_text_response
    ):
        response = mock_text_response("Just a text answer")

        result = nfl_service._extract_function_call(response)

        assert result is None

    def test_extract_text_response_gets_output_text(
        self, nfl_service, mock_text_response
    ):
        response = mock_text_response("The answer is 42")

        result = nfl_service._extract_text_response(response)

        assert result == "The answer is 42"

    def test_extract_text_response_falls_back_to_content(self, nfl_service):
        mock_response = MagicMock()
        del mock_response.output_text
        mock_part = MagicMock()
        mock_part.type = "output_text"
        mock_part.text = "fallback text"
        mock_item = MagicMock()
        mock_item.content = [mock_part]
        mock_response.output = [mock_item]

        result = nfl_service._extract_text_response(mock_response)

        assert result == "fallback text"


class TestNFLServiceProcess:
    @pytest.mark.asyncio
    async def test_process_successful_code_execution_returns_response(
        self, nfl_service, mock_function_call_response, mock_text_response
    ):
        nfl_service._call_llm = AsyncMock(
            side_effect=[
                mock_function_call_response('def run():\n    return {"response": 42}'),
                mock_text_response("The answer is 42"),
            ]
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"response": 42})
        )

        result = await nfl_service.process("What is the answer?")

        assert result.response == "The answer is 42"
        assert result.raw_data == {"response": 42}
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_process_no_tool_call_returns_text_response(
        self, nfl_service, mock_text_response
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_text_response("Direct answer without code")
        )

        result = await nfl_service.process("Simple question")

        assert result.response == "Direct answer without code"
        assert result.code_generated is None
        assert result.raw_data is None

    @pytest.mark.asyncio
    async def test_process_retry_on_code_failure_succeeds_second_attempt(
        self, nfl_service, mock_function_call_response, mock_text_response
    ):
        nfl_service._call_llm = AsyncMock(
            side_effect=[
                mock_function_call_response("def run():\n    return bad_var"),
                mock_function_call_response(
                    'def run():\n    return {"response": "fixed"}'
                ),
                mock_text_response("Fixed answer"),
            ]
        )
        execution_results = [
            CodeExecutionResult(success=False, error="NameError", traceback="..."),
            CodeExecutionResult(success=True, data={"response": "fixed"}),
        ]
        nfl_service.code_executor.execute = MagicMock(side_effect=execution_results)

        result = await nfl_service.process("Question needing retry")

        assert result.response == "Fixed answer"
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_process_max_retries_exceeded_returns_error(
        self, nfl_service, mock_function_call_response
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response("def run():\n    return bad_var")
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(
                success=False, error="NameError", traceback="..."
            )
        )

        result = await nfl_service.process("Failing question")

        assert "Failed to generate working code" in result.response
        assert result.attempts == 3


class TestNFLServiceLLMCalls:
    @pytest.mark.asyncio
    async def test_call_llm_passes_tools_when_provided(
        self, nfl_service, mock_openai_client
    ):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())
        tools = [{"type": "function", "name": "test_tool"}]

        await nfl_service._call_llm([{"role": "user", "content": "test"}], tools=tools)

        mock_openai_client.responses.create.assert_called_once()
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_call_llm_omits_tools_when_none(
        self, nfl_service, mock_openai_client
    ):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())

        await nfl_service._call_llm([{"role": "user", "content": "test"}])

        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert "tools" not in call_kwargs

    @pytest.mark.asyncio
    async def test_summarize_result_calls_llm_with_data(
        self, nfl_service, mock_openai_client
    ):
        mock_response = MagicMock()
        mock_response.output_text = "Summary text"
        mock_openai_client.responses.create = AsyncMock(return_value=mock_response)
        result_data = {"response": 42}

        summary = await nfl_service._summarize_result("Original question", result_data)

        assert summary == "Summary text"
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert "42" in call_kwargs["input"][1]["content"]
