"""Unit tests for NFLService."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.models.schemas import ChatMessage, CodeExecutionResult, SummarizationResult


class TestNFLServiceBuildMessages:
    def test_build_base_messages_structure(self, nfl_service):
        messages = nfl_service._build_base_messages("test question")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "test question"

    def test_build_base_messages_includes_current_season(self, nfl_service):
        messages = nfl_service._build_base_messages("test question")

        assert "2025" in messages[0]["content"]

    def test_build_retry_messages_appends_error_context(self, nfl_service):
        base_messages = [{"role": "user", "content": "test"}]
        code = "def run(): pass"
        error = "NameError: name 'x' is not defined"

        messages = nfl_service._build_retry_messages(base_messages, code, error)

        assert len(messages) == 3
        assert "error" in messages[-1]["content"].lower()
        assert code in messages[-2]["content"]

    def test_build_chat_messages_includes_conversation(self, nfl_service):
        chat_messages = [
            ChatMessage(role="user", content="First question"),
            ChatMessage(role="assistant", content="First answer"),
            ChatMessage(role="user", content="Follow up"),
        ]

        messages = nfl_service._build_chat_messages(chat_messages)

        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "First question"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Follow up"


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


class TestSummarizeResult:
    @pytest.mark.asyncio
    async def test_summarize_returns_valid_with_summary(
        self, nfl_service, mock_openai_client, mock_summarization_response
    ):
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(True, "The Lions scored 42 points")
        )

        is_valid, summary = await nfl_service._summarize_result(
            "How many points?", {"points": 42}
        )

        assert is_valid is True
        assert summary == "The Lions scored 42 points"

    @pytest.mark.asyncio
    async def test_summarize_returns_invalid_with_reason(
        self, nfl_service, mock_openai_client, mock_summarization_response
    ):
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(
                False, "Data shows 0 touchdowns which seems wrong for this player"
            )
        )

        is_valid, reason = await nfl_service._summarize_result(
            "How many TDs?", {"touchdowns": 0}
        )

        assert is_valid is False
        assert "0 touchdowns" in reason

    @pytest.mark.asyncio
    async def test_summarize_uses_correct_model(
        self, nfl_service, mock_openai_client, mock_summarization_response
    ):
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(True, "Summary")
        )

        await nfl_service._summarize_result("Question", {"data": 1})

        call_kwargs = mock_openai_client.responses.parse.call_args[1]
        assert call_kwargs["model"] == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_summarize_uses_structured_output(
        self, nfl_service, mock_openai_client, mock_summarization_response
    ):
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(True, "Summary")
        )

        await nfl_service._summarize_result("Question", {"data": 1})

        call_kwargs = mock_openai_client.responses.parse.call_args[1]
        assert call_kwargs["text_format"] == SummarizationResult


class TestGenerateAndExecute:
    @pytest.mark.asyncio
    async def test_successful_execution_returns_success(
        self, nfl_service, mock_function_call_response
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response(
                'def run():\n    return {"value": 42}'
            )
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"value": 42})
        )

        result = await nfl_service._generate_and_execute(
            [{"role": "user", "content": "test"}]
        )

        assert result.success is True
        assert result.data == {"value": 42}
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure_succeeds(
        self, nfl_service, mock_function_call_response
    ):
        nfl_service._call_llm = AsyncMock(
            side_effect=[
                mock_function_call_response("def run(): return bad"),
                mock_function_call_response('def run(): return {"fixed": True}'),
            ]
        )
        nfl_service.code_executor.execute = MagicMock(
            side_effect=[
                CodeExecutionResult(success=False, error="NameError"),
                CodeExecutionResult(success=True, data={"fixed": True}),
            ]
        )

        result = await nfl_service._generate_and_execute(
            [{"role": "user", "content": "test"}]
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_returns_failure(
        self, nfl_service, mock_function_call_response
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response("def run(): return bad")
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=False, error="NameError")
        )

        result = await nfl_service._generate_and_execute(
            [{"role": "user", "content": "test"}]
        )

        assert result.success is False
        assert result.attempts == 3  # max_retries=2 means 3 total attempts
        assert "NameError" in result.error

    @pytest.mark.asyncio
    async def test_uses_specified_model(self, nfl_service, mock_function_call_response):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response("def run(): return {}")
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={})
        )

        await nfl_service._generate_and_execute(
            [{"role": "user", "content": "test"}], model="gpt-5.1-codex"
        )

        call_kwargs = nfl_service._call_llm.call_args[1]
        assert call_kwargs["model"] == "gpt-5.1-codex"


class TestProcessWithValidation:
    @pytest.mark.asyncio
    async def test_valid_data_returns_summary(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response('def run(): return {"points": 42}')
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"points": 42})
        )
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(True, "The team scored 42 points")
        )
        messages = [ChatMessage(role="user", content="How many points?")]

        result = await nfl_service.process_chat(messages)

        assert result.response == "The team scored 42 points"
        assert result.used_fallback is False
        assert result.raw_data == {"points": 42}

    @pytest.mark.asyncio
    async def test_invalid_data_triggers_fallback(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        # First attempt: mini model generates bad code/data
        # Second attempt: fallback model generates good code/data
        call_count = [0]

        def mock_call_llm(*args, **kwargs):
            call_count[0] += 1
            return mock_function_call_response('def run(): return {"tds": 0}')

        nfl_service._call_llm = AsyncMock(side_effect=mock_call_llm)
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"tds": 0})
        )

        # First summarization: invalid, second: valid
        mock_openai_client.responses.parse = AsyncMock(
            side_effect=[
                mock_summarization_response(False, "0 TDs seems wrong for Mahomes"),
                mock_summarization_response(True, "Patrick Mahomes has 25 TDs"),
            ]
        )
        messages = [ChatMessage(role="user", content="How many TDs does Mahomes have?")]

        result = await nfl_service.process_chat(messages)

        assert result.used_fallback is True
        assert "25 TDs" in result.response

    @pytest.mark.asyncio
    async def test_fallback_uses_correct_model(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response('def run(): return {"data": 0}')
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"data": 0})
        )
        mock_openai_client.responses.parse = AsyncMock(
            side_effect=[
                mock_summarization_response(False, "Data seems wrong"),
                mock_summarization_response(True, "Corrected answer"),
            ]
        )
        messages = [ChatMessage(role="user", content="Question")]

        await nfl_service.process_chat(messages)

        # Check that fallback model was used in second call
        call_args_list = nfl_service._call_llm.call_args_list
        assert len(call_args_list) >= 2
        # First call uses default model (no explicit model kwarg or default)
        # Second call should use fallback model
        second_call_kwargs = call_args_list[1][1]
        assert second_call_kwargs.get("model") == "gpt-5.1-codex"

    @pytest.mark.asyncio
    async def test_fallback_failure_returns_error(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response("def run(): return bad")
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=False, error="SyntaxError")
        )
        messages = [ChatMessage(role="user", content="Question")]

        result = await nfl_service.process_chat(messages)

        assert "Failed to generate working code" in result.response


class TestProcessChat:
    @pytest.mark.asyncio
    async def test_process_chat_empty_messages_returns_error(self, nfl_service):
        result = await nfl_service.process_chat([])

        assert result.response == "No messages provided"
        assert result.attempts == 0

    @pytest.mark.asyncio
    async def test_process_chat_valid_data_returns_summary(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response('def run(): return {"yards": 150}')
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"yards": 150})
        )
        mock_openai_client.responses.parse = AsyncMock(
            return_value=mock_summarization_response(True, "The player has 150 yards")
        )
        messages = [
            ChatMessage(role="user", content="How many yards did he have?"),
        ]

        result = await nfl_service.process_chat(messages)

        assert result.response == "The player has 150 yards"
        assert result.raw_data == {"yards": 150}

    @pytest.mark.asyncio
    async def test_process_chat_invalid_data_triggers_fallback(
        self,
        nfl_service,
        mock_function_call_response,
        mock_summarization_response,
        mock_openai_client,
    ):
        nfl_service._call_llm = AsyncMock(
            return_value=mock_function_call_response('def run(): return {"data": 0}')
        )
        nfl_service.code_executor.execute = MagicMock(
            return_value=CodeExecutionResult(success=True, data={"data": 0})
        )
        mock_openai_client.responses.parse = AsyncMock(
            side_effect=[
                mock_summarization_response(False, "Data seems implausible"),
                mock_summarization_response(True, "Corrected: 150 yards"),
            ]
        )
        messages = [
            ChatMessage(role="user", content="How many rushing yards?"),
        ]

        result = await nfl_service.process_chat(messages)

        assert result.used_fallback is True
        assert "150 yards" in result.response


class TestLLMCalls:
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
    async def test_call_llm_force_tool_sets_tool_choice(
        self, nfl_service, mock_openai_client
    ):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())
        tools = [{"type": "function", "name": "run_nflreadpy_code"}]

        await nfl_service._call_llm(
            [{"role": "user", "content": "test"}], tools=tools, force_tool=True
        )

        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["tool_choice"] == {
            "type": "function",
            "name": "run_nflreadpy_code",
        }

    @pytest.mark.asyncio
    async def test_call_llm_omits_tools_when_none(
        self, nfl_service, mock_openai_client
    ):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())

        await nfl_service._call_llm([{"role": "user", "content": "test"}])

        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert "tools" not in call_kwargs

    @pytest.mark.asyncio
    async def test_call_llm_with_custom_model(self, nfl_service, mock_openai_client):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())

        await nfl_service._call_llm(
            [{"role": "user", "content": "test"}], model="custom-model"
        )

        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_call_llm_reasoning_disabled(self, nfl_service, mock_openai_client):
        mock_openai_client.responses.create = AsyncMock(return_value=MagicMock())

        await nfl_service._call_llm(
            [{"role": "user", "content": "test"}], reasoning=False
        )

        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["reasoning"] == {"effort": "low"}
