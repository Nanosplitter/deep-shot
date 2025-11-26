"""Tool definitions for OpenAI function calling."""

NFLREADPY_TOOL = {
    "type": "function",
    "name": "run_nflreadpy_code",
    "description": (
        "Execute Python code that uses nflreadpy and Polars to answer NFL "
        "stats questions. The code MUST define a function run() that "
        "returns a JSON-serializable dict with the response."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Python code that:\n"
                    "1) imports nflreadpy as nfl (and polars as pl if needed),\n"
                    "2) defines run() with no arguments,\n"
                    "3) uses nfl.load_pbp / load_player_stats / load_team_stats "
                    "   or other documented functions,\n"
                    "4) returns a JSON-serializable dict like:\n"
                    "   {\n"
                    "     'response': <number or string>,\n"
                    "     'explanation': <string>,\n"
                    "     'details': {... optional ...}\n"
                    "   }\n"
                    "DO NOT print; just return the dict from run()."
                ),
            }
        },
        "required": ["code"],
        "additionalProperties": False,
    },
}

TOOLS = [NFLREADPY_TOOL]
