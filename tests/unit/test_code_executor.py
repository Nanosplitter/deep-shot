"""Unit tests for CodeExecutor."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.code_executor import CodeExecutor, ASTValidator, CodeValidationError


class TestASTValidator:
    def test_visit_import_allowed_module_passes(self):
        import ast

        code = "import nflreadpy as nfl"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert validator.errors == []

    def test_visit_import_forbidden_module_fails(self):
        import ast

        code = "import os"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "os" in validator.errors[0]

    def test_visit_import_subprocess_fails(self):
        import ast

        code = "import subprocess"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "subprocess" in validator.errors[0]

    def test_visit_import_from_allowed_module_passes(self):
        import ast

        code = "from datetime import datetime"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert validator.errors == []

    def test_visit_import_from_forbidden_module_fails(self):
        import ast

        code = "from os import system"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "os" in validator.errors[0]

    def test_visit_call_eval_fails(self):
        import ast

        code = "eval('1+1')"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "eval" in validator.errors[0]

    def test_visit_call_exec_fails(self):
        import ast

        code = "exec('x = 1')"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "exec" in validator.errors[0]

    def test_visit_call_open_fails(self):
        import ast

        code = "open('file.txt')"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "open" in validator.errors[0]

    def test_visit_call_import_fails(self):
        import ast

        code = "__import__('os')"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "__import__" in validator.errors[0]

    def test_visit_attribute_builtins_fails(self):
        import ast

        code = "x.__builtins__"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "__builtins__" in validator.errors[0]

    def test_visit_attribute_globals_fails(self):
        import ast

        code = "x.__globals__"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 1
        assert "__globals__" in validator.errors[0]

    def test_visit_multiple_violations_collects_all(self):
        import ast

        code = "import os\neval('x')\nopen('file')"
        tree = ast.parse(code)
        validator = ASTValidator()

        validator.visit(tree)

        assert len(validator.errors) == 3


class TestCodeExecutorValidation:
    def test_validate_code_valid_nflreadpy_code_passes(self, code_executor):
        code = """
import nflreadpy as nfl
import polars as pl

def run():
    return {"response": "test"}
"""

        code_executor.validate_code(code)

    def test_validate_code_syntax_error_raises(self, code_executor):
        code = "def run(\n"

        with pytest.raises(CodeValidationError) as exc_info:
            code_executor.validate_code(code)

        assert "Syntax error" in exc_info.value.message

    def test_validate_code_forbidden_import_raises(self, code_executor):
        code = """
import os

def run():
    return os.getcwd()
"""

        with pytest.raises(CodeValidationError) as exc_info:
            code_executor.validate_code(code)

        assert "os" in exc_info.value.message

    def test_validate_code_eval_call_raises(self, code_executor):
        code = """
def run():
    return eval("1+1")
"""

        with pytest.raises(CodeValidationError) as exc_info:
            code_executor.validate_code(code)

        assert "eval" in exc_info.value.message


class TestCodeExecutorExecution:
    def test_execute_valid_code_returns_success(self, code_executor):
        code = """
def run():
    return {"response": 42, "explanation": "test"}
"""

        result = code_executor.execute(code)

        assert result.success is True
        assert result.data == {"response": 42, "explanation": "test"}

    def test_execute_missing_run_function_returns_failure(self, code_executor):
        code = """
def other_function():
    return 42
"""

        result = code_executor.execute(code)

        assert result.success is False
        assert "run()" in result.error

    def test_execute_non_callable_run_returns_failure(self, code_executor):
        code = """
run = 42
"""

        result = code_executor.execute(code)

        assert result.success is False
        assert "run()" in result.error

    def test_execute_non_json_serializable_returns_failure(self, code_executor):
        code = """
def run():
    return {"data": lambda x: x}
"""

        result = code_executor.execute(code)

        assert result.success is False
        assert "JSON-serializable" in result.error

    def test_execute_runtime_error_returns_failure(self, code_executor):
        code = """
def run():
    return 1 / 0
"""

        result = code_executor.execute(code)

        assert result.success is False
        assert (
            "division by zero" in result.error.lower() or result.traceback is not None
        )

    def test_execute_validation_failure_returns_failure(self, code_executor):
        code = """
import os

def run():
    return {"response": "test"}
"""

        result = code_executor.execute(code)

        assert result.success is False
        assert "os" in result.error

    @patch("app.services.code_executor.ThreadPoolExecutor")
    def test_execute_timeout_returns_failure(self, mock_executor_class):
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        mock_executor = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = FuturesTimeoutError()
        mock_executor.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.submit.return_value = mock_future
        mock_executor_class.return_value = mock_executor
        executor = CodeExecutor(timeout_seconds=1)
        code = """
def run():
    return {"response": "test"}
"""

        result = executor.execute(code)

        assert result.success is False
        assert "timed out" in result.error

    def test_execute_with_math_module_succeeds(self, code_executor):
        code = """
import math

def run():
    return {"response": math.sqrt(16)}
"""

        result = code_executor.execute(code)

        assert result.success is True
        assert result.data["response"] == 4.0

    def test_execute_with_datetime_module_succeeds(self, code_executor):
        code = """
import datetime

def run():
    return {"response": str(datetime.date(2025, 1, 1))}
"""

        result = code_executor.execute(code)

        assert result.success is True
        assert result.data["response"] == "2025-01-01"

    def test_execute_with_statistics_module_succeeds(self, code_executor):
        code = """
import statistics

def run():
    return {"response": statistics.mean([1, 2, 3, 4, 5])}
"""

        result = code_executor.execute(code)

        assert result.success is True
        assert result.data["response"] == 3.0
