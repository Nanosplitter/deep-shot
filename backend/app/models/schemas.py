"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: str = Field(..., description="The message content")


class NFLChatInput(BaseModel):
    """Request model for multi-turn NFL stats conversations."""

    messages: list[ChatMessage] = Field(
        ..., description="The conversation history including the current message"
    )


class NFLResponse(BaseModel):
    """Response model for NFL stats queries."""

    response: str = Field(..., description="Natural language response to the input")
    code_generated: str | None = Field(
        default=None, description="The Python code generated to answer the query"
    )
    raw_data: dict | None = Field(
        default=None, description="Raw data returned by the executed code"
    )
    attempts: int = Field(
        default=1, description="Number of code generation attempts made"
    )
    used_fallback: bool = Field(
        default=False, description="Whether the fallback model was used"
    )


class CodeExecutionResult(BaseModel):
    """Result of executing generated code."""

    success: bool
    data: dict | None = None
    error: str | None = None
    traceback: str | None = None


class SummarizationResult(BaseModel):
    """Structured output from the summarization model."""

    is_valid: bool = Field(
        ...,
        description="Whether the data appears to correctly answer the user's question",
    )
    summary: str = Field(
        ...,
        description="If valid: the natural language summary. If invalid: explanation of why the data seems wrong.",
    )


class CodeExecutionError(Exception):
    """Exception raised when code execution fails."""

    def __init__(self, message: str, traceback_str: str | None = None):
        super().__init__(message)
        self.message = message
        self.traceback_str = traceback_str


class CodeValidationError(Exception):
    """Exception raised when code fails AST validation."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class StreamEvent(BaseModel):
    """Event model for streaming progress updates."""

    event: str = Field(..., description="Event type: 'status', 'complete', or 'error'")
    step: str = Field(
        ...,
        description="Current step: 'analyzing', 'generating', 'executing', 'retrying', 'validating', 'summarizing', 'fallback'",
    )
    message: str = Field(..., description="User-friendly status message")
    attempt: int | None = Field(default=None, description="Current attempt number")
    data: NFLResponse | None = Field(
        default=None, description="Final response data when complete"
    )
