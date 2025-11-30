"""Prompt templates for the NFL stats assistant.

All prompts are loaded from markdown files in the backend/prompts/ directory
for easy editing.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "nflreadpy_schema_columns_only.md"


def _load_file(path: Path) -> str:
    """Load a file's contents, returning empty string if not found."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def get_system_prompt(current_season: int) -> str:
    """Generate the system prompt for the NFL stats assistant."""
    template = _load_file(PROMPTS_DIR / "system_prompt.md")
    prompt = template.replace("{{current_season}}", str(current_season))

    # Append column schema if available
    schema = _load_file(SCHEMA_PATH)
    if schema:
        prompt += "\n\n## Column Reference\n\n" + schema

    return prompt


def get_retry_prompt(error: str) -> str:
    """Generate the retry prompt after a code execution failure."""
    template = _load_file(PROMPTS_DIR / "retry_prompt.md")
    return template.replace("{{error}}", error)


def get_summarization_prompt() -> str:
    """Generate the summarization system prompt."""
    return _load_file(PROMPTS_DIR / "summarization_prompt.md")
