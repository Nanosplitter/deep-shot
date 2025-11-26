"""Secure code executor with AST validation and timeout."""

import ast
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

import nflreadpy
import polars as pl

from app.models.schemas import (
    CodeExecutionResult,
    CodeExecutionError,
    CodeValidationError,
)


ALLOWED_IMPORTS = frozenset(
    {
        "nflreadpy",
        "nfl",
        "polars",
        "pl",
        "datetime",
        "math",
        "statistics",
        "json",
        "re",
    }
)

FORBIDDEN_CALLS = frozenset(
    {
        "eval",
        "exec",
        "open",
        "__import__",
        "compile",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "input",
        "breakpoint",
    }
)

FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "__builtins__",
        "__code__",
        "__globals__",
        "__subclasses__",
        "__bases__",
        "__mro__",
        "__class__",
    }
)

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Safe import that only allows whitelisted modules."""
    base_module = name.split(".")[0]
    if base_module not in ALLOWED_IMPORTS:
        raise ImportError(f"Import of '{name}' is not allowed")
    return __builtins__["__import__"](name, globals, locals, fromlist, level)


class ASTValidator(ast.NodeVisitor):
    """AST visitor that validates code for security."""

    def __init__(self):
        self.errors: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            if module_name not in ALLOWED_IMPORTS:
                self.errors.append(f"Import of '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            module_name = node.module.split(".")[0]
            if module_name not in ALLOWED_IMPORTS:
                self.errors.append(f"Import from '{node.module}' is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Call to '{node.func.id}' is not allowed")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                self.errors.append(f"Call to '{node.func.attr}' is not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.errors.append(f"Access to '{node.attr}' is not allowed")
        self.generic_visit(node)


class CodeExecutor:
    """Executes model-generated Python code with security constraints."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def validate_code(self, code: str) -> None:
        """Validate code using AST analysis."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise CodeValidationError(f"Syntax error in code: {e}")

        validator = ASTValidator()
        validator.visit(tree)

        if validator.errors:
            raise CodeValidationError(
                "Code validation failed:\n"
                + "\n".join(f"  - {e}" for e in validator.errors)
            )

    def _create_execution_environment(self) -> dict[str, Any]:
        """Create a restricted execution environment."""
        import datetime
        import math
        import statistics
        import re

        safe_builtins_with_import = {**SAFE_BUILTINS, "__import__": _safe_import}

        return {
            "__builtins__": safe_builtins_with_import,
            "nflreadpy": nflreadpy,
            "nfl": nflreadpy,
            "polars": pl,
            "pl": pl,
            "datetime": datetime,
            "math": math,
            "statistics": statistics,
            "json": json,
            "re": re,
        }

    def _execute_code(self, code: str) -> dict:
        """Execute code and return result. Called within thread pool."""
        env = self._create_execution_environment()
        exec(code, env)

        if "run" not in env or not callable(env["run"]):
            raise CodeExecutionError(
                "Code must define a callable run() function with no arguments"
            )

        result = env["run"]()

        try:
            json.dumps(result)
        except TypeError as e:
            raise CodeExecutionError(
                f"run() must return JSON-serializable data. Got error: {e}"
            )

        return result

    def execute(self, code: str) -> CodeExecutionResult:
        """Execute code with validation and timeout."""
        try:
            self.validate_code(code)
        except CodeValidationError as e:
            return CodeExecutionResult(
                success=False,
                error=e.message,
            )

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_code, code)
                try:
                    result = future.result(timeout=self.timeout_seconds)
                    return CodeExecutionResult(success=True, data=result)
                except FuturesTimeoutError:
                    return CodeExecutionResult(
                        success=False,
                        error=f"Code execution timed out after {self.timeout_seconds} seconds",
                    )
        except CodeExecutionError as e:
            return CodeExecutionResult(
                success=False,
                error=e.message,
                traceback=e.traceback_str,
            )
        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            return CodeExecutionResult(
                success=False,
                error=str(e),
                traceback=tb,
            )
