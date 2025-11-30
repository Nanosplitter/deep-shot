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
    CodeExecutionResult,
    SummarizationResult,
)
from app.services.code_executor import CodeExecutor

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
            kwargs["reasoning"] = {"effort": "minimal"}
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
            reasoning={"effort": "minimal"},
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

    async def process(self, user_input: str) -> NFLResponse:
        """Process an NFL stats query and return a response."""
        base_messages = self._build_base_messages(user_input)

        # Try with the default (mini) model first
        result = await self._generate_and_execute(base_messages)

        if result.success:
            is_valid, summary = await self._summarize_result(user_input, result.data)

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
                # Don't re-validate, just summarize (to avoid infinite loop)
                _, summary = await self._summarize_result(user_input, result.data)
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
