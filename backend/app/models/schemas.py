"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: str = Field(..., description="The message content")


class NFLInput(BaseModel):
    """Request model for NFL stats queries."""

    input: str = Field(..., description="The NFL stats question to process")


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


class CodeExecutionResult(BaseModel):
    """Result of executing generated code."""

    success: bool
    data: dict | None = None
    error: str | None = None
    traceback: str | None = None


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
