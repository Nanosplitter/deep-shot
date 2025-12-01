"""NFL stats service using OpenAI for code generation."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.config.prompts import (
    get_system_prompt,
    get_retry_prompt,
    get_summarization_prompt,
)
from app.config.settings import Settings
from app.config.tools import TOOLS
from app.models.schemas import (
    ChatMessage,
    NFLResponse,
    StreamEvent,
    SummarizationResult,
)
from app.services.code_executor import CodeExecutor
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


@dataclass
class CodeGenResult:
    """Result from a code generation attempt."""

    success: bool
    code: str | None = None
    data: dict | None = None
    error: str | None = None
    attempts: int = 0


class NFLService:
    """Service for processing NFL stats queries using LLM-generated code."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.code_executor = CodeExecutor(timeout_seconds=settings.code_timeout_seconds)

    def _build_base_messages(self, user_input: str) -> list[dict[str, str]]:
        """Build the base message list for the LLM."""
        return [
            {
                "role": "system",
                "content": get_system_prompt(self.settings.current_season),
            },
            {"role": "user", "content": user_input},
        ]

    def _build_chat_messages(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Build message list for multi-turn conversation."""
        base = [
            {
                "role": "system",
                "content": get_system_prompt(self.settings.current_season),
            },
        ]
        conversation = [{"role": msg.role, "content": msg.content} for msg in messages]
        return base + conversation

    def _build_retry_messages(
        self,
        base_messages: list[dict[str, str]],
        code: str,
        error_traceback: str,
    ) -> list[dict[str, str]]:
        """Build messages for retry attempt after code failure."""
        return base_messages + [
            {
                "role": "assistant",
                "content": f"```python\n{code}\n```",
            },
            {
                "role": "user",
                "content": get_retry_prompt(error_traceback),
            },
        ]

    def _extract_function_call(self, response: Any) -> tuple[str, str] | None:
        """Extract function call from OpenAI response."""
        for item in response.output:
            if item.type == "function_call" and item.name == "run_nflreadpy_code":
                args = json.loads(item.arguments or "{}")
                code = args.get("code", "")
                return item.call_id, code
        return None

    def _extract_text_response(self, response: Any) -> str:
        """Extract text content from OpenAI response."""
        try:
            return response.output_text
        except AttributeError:
            parts = []
            for item in response.output:
                if hasattr(item, "content"):
                    for part in item.content:
                        if getattr(part, "type", None) == "output_text":
                            parts.append(part.text)
            return "".join(parts)

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        force_tool: bool = False,
        model: str | None = None,
        reasoning: bool = True,
    ) -> Any:
        """Make an async call to the OpenAI API."""
        kwargs = {
            "model": model or self.settings.model,
            "input": messages,
        }
        if not reasoning:
            kwargs["reasoning"] = {"effort": "low"}
        if tools:
            kwargs["tools"] = tools
            if force_tool:
                # Force the model to use the tool instead of responding with text
                kwargs["tool_choice"] = {
                    "type": "function",
                    "name": "run_nflreadpy_code",
                }

        return await self.client.responses.create(**kwargs)

    async def _summarize_result(
        self, user_input: str, result_data: dict
    ) -> tuple[bool, str]:
        """Ask LLM to summarize and validate the code execution result.

        Returns:
            Tuple of (is_valid, summary_or_reason)
        """
        response = await self.client.responses.parse(
            model=self.settings.summarization_model,
            input=[
                {"role": "system", "content": get_summarization_prompt()},
                {
                    "role": "user",
                    "content": (
                        f"Original question:\n{user_input}\n\n"
                        "Here is the JSON data returned by the code:\n"
                        f"```json\n{json.dumps(result_data, indent=2)}\n```"
                    ),
                },
            ],
            text_format=SummarizationResult,
            reasoning={"effort": "low"},
        )

        result = response.output_parsed
        return result.is_valid, result.summary

    async def _generate_and_execute(
        self,
        base_messages: list[dict[str, str]],
        model: str | None = None,
    ) -> CodeGenResult:
        """Generate code and execute it, with retries.

        Returns a CodeGenResult with success status and data or error.
        """
        messages = list(base_messages)
        attempt = 0
        last_code = None

        while attempt <= self.settings.max_retries:
            response = await self._call_llm(
                messages, tools=TOOLS, force_tool=True, model=model
            )
            function_call_result = self._extract_function_call(response)

            if function_call_result is None:
                text_response = self._extract_text_response(response)
                return CodeGenResult(
                    success=False,
                    error=f"Model responded with text instead of code: {text_response}",
                    attempts=attempt + 1,
                )

            _, code = function_call_result
            last_code = code
            logger.info(
                f"Generated code (attempt {attempt + 1}, model={model or self.settings.model}):\n{code}"
            )

            execution_result = self.code_executor.execute(code)

            if execution_result.success:
                logger.info(f"Code executed successfully: {execution_result.data}")
                return CodeGenResult(
                    success=True,
                    code=code,
                    data=execution_result.data,
                    attempts=attempt + 1,
                )

            attempt += 1
            error_info = execution_result.error or "Unknown error"
            if execution_result.traceback:
                error_info = f"{error_info}\n{execution_result.traceback}"

            logger.warning(f"Code execution failed (attempt {attempt}): {error_info}")

            if attempt > self.settings.max_retries:
                return CodeGenResult(
                    success=False,
                    code=code,
                    error=error_info,
                    attempts=attempt,
                )

            messages = self._build_retry_messages(base_messages, code, error_info)

        return CodeGenResult(
            success=False,
            code=last_code,
            error="Unexpected error in processing loop",
            attempts=attempt,
        )

    async def process_chat(self, chat_messages: list[ChatMessage]) -> NFLResponse:
        """Process a multi-turn NFL stats conversation and return a response."""
        if not chat_messages:
            return NFLResponse(
                response="No messages provided",
                attempts=0,
            )

        base_messages = self._build_chat_messages(chat_messages)
        latest_user_input = chat_messages[-1].content

        # Try with the default (mini) model first
        result = await self._generate_and_execute(base_messages)

        if result.success:
            is_valid, summary = await self._summarize_result(
                latest_user_input, result.data
            )

            if is_valid:
                return NFLResponse(
                    response=summary,
                    code_generated=result.code,
                    raw_data=result.data,
                    attempts=result.attempts,
                )

            # Data didn't pass sniff test - try with the bigger model
            logger.warning(
                f"Data validation failed: {summary}. Retrying with fallback model."
            )
            result = await self._generate_and_execute(
                base_messages, model=self.settings.fallback_model
            )

            if result.success:
                _, summary = await self._summarize_result(
                    latest_user_input, result.data
                )
                return NFLResponse(
                    response=summary,
                    code_generated=result.code,
                    raw_data=result.data,
                    attempts=result.attempts,
                    used_fallback=True,
                )

        # Code generation failed
        return NFLResponse(
            response=f"Failed to generate working code: {result.error}",
            code_generated=result.code,
            attempts=result.attempts,
        )

    async def process_chat_streaming(
        self, chat_messages: list[ChatMessage]
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a chat with streaming progress updates."""
        if not chat_messages:
            yield StreamEvent(
                event="error",
                step="analyzing",
                message="No messages provided",
            )
            return

        base_messages = self._build_chat_messages(chat_messages)
        latest_user_input = chat_messages[-1].content

        # Step 1: Analyzing
        yield StreamEvent(
            event="status",
            step="analyzing",
            message="🔍 Analyzing your question...",
        )

        # Try with the default (mini) model first
        messages = list(base_messages)
        attempt = 0
        last_code = None
        result = None

        while attempt <= self.settings.max_retries:
            # Step 2: Generating code
            yield StreamEvent(
                event="status",
                step="generating",
                message="⚙️ Generating code..."
                if attempt == 0
                else f"✨ Refining approach (attempt {attempt + 1})...",
                attempt=attempt + 1,
            )

            response = await self._call_llm(messages, tools=TOOLS, force_tool=True)
            function_call_result = self._extract_function_call(response)

            if function_call_result is None:
                text_response = self._extract_text_response(response)
                yield StreamEvent(
                    event="error",
                    step="generating",
                    message=f"Model responded with text instead of code",
                )
                return

            _, code = function_call_result
            last_code = code

            # Step 3: Executing
            yield StreamEvent(
                event="status",
                step="executing",
                message="⚡ Running the analysis...",
                attempt=attempt + 1,
            )

            execution_result = self.code_executor.execute(code)

            if execution_result.success:
                result = CodeGenResult(
                    success=True,
                    code=code,
                    data=execution_result.data,
                    attempts=attempt + 1,
                )
                break

            attempt += 1
            error_info = execution_result.error or "Unknown error"
            if execution_result.traceback:
                error_info = f"{error_info}\n{execution_result.traceback}"

            logger.warning(f"Code execution failed (attempt {attempt}): {error_info}")

            if attempt > self.settings.max_retries:
                result = CodeGenResult(
                    success=False,
                    code=code,
                    error=error_info,
                    attempts=attempt,
                )
                break

            # Step 4: Retrying
            yield StreamEvent(
                event="status",
                step="retrying",
                message="✨ Trying another approach...",
                attempt=attempt + 1,
            )
            messages = self._build_retry_messages(base_messages, code, error_info)

        if result is None:
            result = CodeGenResult(
                success=False,
                code=last_code,
                error="Unexpected error in processing loop",
                attempts=attempt,
            )

        if result.success:
            # Step 5: Validating
            yield StreamEvent(
                event="status",
                step="validating",
                message="✅ Checking the results...",
            )

            is_valid, summary = await self._summarize_result(
                latest_user_input, result.data
            )

            if is_valid:
                # Step 6: Complete
                yield StreamEvent(
                    event="complete",
                    step="summarizing",
                    message="📝 Preparing your answer...",
                    data=NFLResponse(
                        response=summary,
                        code_generated=result.code,
                        raw_data=result.data,
                        attempts=result.attempts,
                    ),
                )
                return

            # Data didn't pass sniff test - try with the bigger model
            logger.warning(
                f"Data validation failed: {summary}. Retrying with fallback model."
            )

            yield StreamEvent(
                event="status",
                step="fallback",
                message="🔄 Using advanced analysis...",
            )

            # Retry with fallback model
            fallback_messages = list(base_messages)
            fallback_attempt = 0

            while fallback_attempt <= self.settings.max_retries:
                yield StreamEvent(
                    event="status",
                    step="generating",
                    message=f"⚙️ Generating improved code...",
                    attempt=fallback_attempt + 1,
                )

                response = await self._call_llm(
                    fallback_messages,
                    tools=TOOLS,
                    force_tool=True,
                    model=self.settings.fallback_model,
                )
                function_call_result = self._extract_function_call(response)

                if function_call_result is None:
                    break

                _, code = function_call_result

                yield StreamEvent(
                    event="status",
                    step="executing",
                    message="⚡ Running the analysis...",
                    attempt=fallback_attempt + 1,
                )

                execution_result = self.code_executor.execute(code)

                if execution_result.success:
                    yield StreamEvent(
                        event="status",
                        step="validating",
                        message="✅ Checking the results...",
                    )

                    _, summary = await self._summarize_result(
                        latest_user_input, execution_result.data
                    )

                    yield StreamEvent(
                        event="complete",
                        step="summarizing",
                        message="📝 Preparing your answer...",
                        data=NFLResponse(
                            response=summary,
                            code_generated=code,
                            raw_data=execution_result.data,
                            attempts=result.attempts + fallback_attempt + 1,
                            used_fallback=True,
                        ),
                    )
                    return

                fallback_attempt += 1
                error_info = execution_result.error or "Unknown error"
                if execution_result.traceback:
                    error_info = f"{error_info}\n{execution_result.traceback}"

                if fallback_attempt > self.settings.max_retries:
                    break

                yield StreamEvent(
                    event="status",
                    step="retrying",
                    message="✨ Trying another approach...",
                    attempt=fallback_attempt + 1,
                )
                fallback_messages = self._build_retry_messages(
                    base_messages, code, error_info
                )

        # Code generation failed
        yield StreamEvent(
            event="error",
            step="generating",
            message=f"Unable to find the data you requested. Please try rephrasing your question.",
            data=NFLResponse(
                response=f"Failed to generate working code: {result.error}",
                code_generated=result.code,
                attempts=result.attempts,
            ),
        )
