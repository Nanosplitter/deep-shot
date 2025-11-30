"""NFL stats service using OpenAI for code generation."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config.prompts import (
    get_system_prompt,
    get_retry_prompt,
    get_summarization_prompt,
)
from app.config.settings import Settings
from app.config.tools import TOOLS
from app.models.schemas import ChatMessage, NFLResponse, CodeExecutionResult
from app.services.code_executor import CodeExecutor

logger = logging.getLogger(__name__)


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

    async def _summarize_result(self, user_input: str, result_data: dict) -> str:
        """Ask LLM to summarize the code execution result."""
        response = await self._call_llm(
            [
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
            model=self.settings.summarization_model,
            reasoning=False,
        )
        return self._extract_text_response(response)

    async def process(self, user_input: str) -> NFLResponse:
        """Process an NFL stats query and return a response."""
        base_messages = self._build_base_messages(user_input)
        messages = list(base_messages)
        attempt = 0
        last_code = None

        while attempt <= self.settings.max_retries:
            response = await self._call_llm(messages, tools=TOOLS, force_tool=True)
            function_call_result = self._extract_function_call(response)

            if function_call_result is None:
                # Model didn't use tool despite being forced - return text response
                text_response = self._extract_text_response(response)
                return NFLResponse(
                    response=text_response,
                    code_generated=last_code,
                    attempts=attempt + 1,
                )

            _, code = function_call_result
            last_code = code
            logger.info(f"Generated code (attempt {attempt + 1}):\n{code}")

            execution_result = self.code_executor.execute(code)

            if execution_result.success:
                logger.info(f"Code executed successfully: {execution_result.data}")
                summary = await self._summarize_result(
                    user_input, execution_result.data
                )
                return NFLResponse(
                    response=summary,
                    code_generated=code,
                    raw_data=execution_result.data,
                    attempts=attempt + 1,
                )

            attempt += 1
            error_info = execution_result.error or "Unknown error"
            if execution_result.traceback:
                error_info = f"{error_info}\n{execution_result.traceback}"

            logger.warning(f"Code execution failed (attempt {attempt}): {error_info}")

            if attempt > self.settings.max_retries:
                return NFLResponse(
                    response=f"Failed to generate working code after {attempt} attempts. Last error: {error_info}",
                    code_generated=code,
                    attempts=attempt,
                )

            messages = self._build_retry_messages(base_messages, code, error_info)

        return NFLResponse(
            response="Unexpected error in processing loop",
            code_generated=last_code,
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
        messages = list(base_messages)
        attempt = 0
        last_code = None
        latest_user_input = chat_messages[-1].content if chat_messages else ""

        while attempt <= self.settings.max_retries:
            response = await self._call_llm(messages, tools=TOOLS, force_tool=True)
            function_call_result = self._extract_function_call(response)

            if function_call_result is None:
                # Model didn't use tool despite being forced - return text response
                text_response = self._extract_text_response(response)
                return NFLResponse(
                    response=text_response,
                    code_generated=last_code,
                    attempts=attempt + 1,
                )

            _, code = function_call_result
            last_code = code
            logger.info(f"Generated code (attempt {attempt + 1}):\n{code}")

            execution_result: CodeExecutionResult = self.code_executor.execute(code)

            if execution_result.success:
                logger.info(f"Code executed successfully: {execution_result.data}")
                summary = await self._summarize_result(
                    latest_user_input, execution_result.data
                )
                return NFLResponse(
                    response=summary,
                    code_generated=code,
                    raw_data=execution_result.data,
                    attempts=attempt + 1,
                )

            attempt += 1
            error_info = execution_result.error or "Unknown error"
            if execution_result.traceback:
                error_info = f"{error_info}\n{execution_result.traceback}"

            logger.warning(f"Code execution failed (attempt {attempt}): {error_info}")

            if attempt > self.settings.max_retries:
                return NFLResponse(
                    response=f"Failed to generate working code after {attempt} attempts. Last error: {error_info}",
                    code_generated=code,
                    attempts=attempt,
                )

            messages = self._build_retry_messages(base_messages, code, error_info)

        return NFLResponse(
            response="Unexpected error in processing loop",
            code_generated=last_code,
            attempts=attempt,
        )
