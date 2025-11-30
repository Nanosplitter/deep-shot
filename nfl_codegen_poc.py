import os
import json
import traceback

from openai import OpenAI
import nflreadpy  # library under test
import polars as pl  # for you; model will also import this itself

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-5.1"

# ---------------------------------------------------------------------
# nflreadpy cheat sheet for the model (from official docs)
# ---------------------------------------------------------------------

NFLREADPY_CHEAT_SHEET = """
nflreadpy quick reference (Python)
Source: https://nflreadpy.nflverse.com/api/load_functions/

Basic usage:

    import nflreadpy as nfl
    import polars as pl

    # Play-by-play:
    pbp = nfl.load_pbp(seasons=[2025])  # returns a Polars DataFrame

    # Player stats:
    players = nfl.load_player_stats(seasons=[2025], summary_level="week")

    # Team stats:
    teams = nfl.load_team_stats(seasons=[2025], summary_level="week")

    # Schedules, rosters, etc.:
    sched = nfl.load_schedules(seasons=[2025])
    rosters = nfl.load_rosters(seasons=[2025])

Key function signatures (simplified):

    nfl.load_pbp(
        seasons: int | list[int] | bool | None = None
    ) -> pl.DataFrame

    nfl.load_player_stats(
        seasons: int | list[int] | bool | None = None,
        summary_level: Literal["week", "reg", "post", "reg+post"] = "week",
    ) -> pl.DataFrame

    nfl.load_team_stats(
        seasons: int | list[int] | bool | None = None,
        summary_level: Literal["week", "reg", "post", "reg+post"] = "week",
    ) -> pl.DataFrame

The play-by-play (pbp) DataFrame is a Polars DataFrame. Use Polars idioms:

    import polars as pl

    pbp = nfl.load_pbp(seasons=[2025])

    td_plays = pbp.filter(
        (pl.col("receiver_player_name") == "Sam LaPorta")
        & (pl.col("touchdown") == 1)
    )

    count = td_plays.height

Useful pbp columns for situational stats (from the pbp data dictionary):
- game_id
- season
- week
- posteam (offense team abbreviation, e.g., "DET")
- defteam (defense team abbreviation)
- passer_player_name
- rusher_player_name
- receiver_player_name
- touchdown (1 if play results in a TD, else 0)
- score_differential (offense score minus defense score BEFORE the play)
- quarter_seconds_remaining (seconds remaining in the current quarter)
- game_seconds_remaining
- down, ydstogo, yardline_100

IMPORTANT FOR THIS APP:
- Use Polars expressions with pl.col().
- Do NOT return Polars DataFrames directly from run().
- Always convert final results to plain Python types (ints, floats, strings, lists, dicts).
- Player names will be abbreviated in pbp, e.g., "J.Bates" for Jake Bates.
"""


# ---------------------------------------------------------------------
# Tool definition: model writes Python and we execute it (Responses API)
# ---------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "name": "run_nflreadpy_code",
        "description": (
            "Execute Python code that uses nflreadpy and Polars to answer NFL "
            "stats questions. The code MUST define a function run() that "
            "returns a JSON-serializable dict with the answer."
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
                        "     'answer': <number or string>,\n"
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
]


# ---------------------------------------------------------------------
# Local executor for model-generated code
# ---------------------------------------------------------------------


def run_nflreadpy_code_locally(code: str):
    """Execute model-generated Python code that uses `nflreadpy`.

    SECURITY WARNING:
    This uses exec() and is NOT sandboxed. Only do this in a trusted environment
    that you control, or add your own sandboxing.
    """

    # Environment we expose to the code.
    # Provide both `nfl` and `nflreadpy` aliases, and `pl` for Polars.
    env = {
        "__builtins__": __builtins__,  # tighten this if you want
        "nflreadpy": nflreadpy,
        "nfl": nflreadpy,
        "pl": pl,
    }

    # Execute the code; it must define run().
    exec(code, env)

    if "run" not in env or not callable(env["run"]):
        raise ValueError(
            "Model code must define a callable run() function with no args."
        )

    result = env["run"]()

    # Make sure the result can be JSON-serializable (no DataFrames leaking out).
    try:
        json.dumps(result)
    except TypeError as e:
        raise TypeError(
            "run() must return JSON-serializable data (dict of plain Python types). "
            f"Got error: {e}"
        )

    return result


# ---------------------------------------------------------------------
# Main orchestration with error-repair loop using Responses API
# ---------------------------------------------------------------------


def ask_nfl_bot(question: str, max_retries: int = 2):
    """Full flow with the Responses API:

    1. Ask the model your question + cheat sheet + tool definition.
    2. Model calls run_nflreadpy_code with a code string (via function_call).
    3. We exec that code locally using nflreadpy.
       - If it errors, we send code + traceback back in a new Responses call
         and ask it to fix itself (up to max_retries).
    4. Once code succeeds, we make a second Responses call that gives the
       JSON result to the model and asks for a natural-language answer.
    """

    base_system_message = {
        "role": "system",
        "content": (
            "You are an NFL stats assistant that writes Python code using the "
            "`nflreadpy` library and Polars.\n\n"
            "When a question requires looking up stats, you MUST call the "
            "run_nflreadpy_code tool instead of answering directly.\n\n"
            "Requirements for the code you pass to the tool:\n"
            "- import nflreadpy as nfl (and polars as pl when needed).\n"
            "- define a function run() with no arguments.\n"
            "- inside run(), use documented nflreadpy.load_* functions and Polars.\n"
            "- convert any Polars DataFrames to aggregates / plain Python types.\n"
            "- return a JSON-serializable dict with keys like 'answer' and 'explanation'.\n"
            "REMINDERS:\n"
            "- nflreadpy uses Polars DataFrames rather than pandas.\n"
            "- Make sure to specify seasons when loading data (e.g., seasons=[2022, 2023, 2024, 2025]). The current season is 2025.\n"
            "- Keep the returned data reasonably small to avoid unnecessary cost.\n"
            "- Do NOT print anything in run(). Just return the dict.\n"
        ),
    }

    docs_message = {
        "role": "system",
        "content": "nflreadpy documentation (cheat sheet):\n" + NFLREADPY_CHEAT_SHEET,
    }

    # We'll rebuild `messages` on each retry so we can add error context.
    base_messages = [
        base_system_message,
        docs_message,
        {"role": "user", "content": question},
    ]

    attempt = 0
    messages = list(base_messages)

    while True:
        # First Responses call: ask model to write and call the tool with code.
        resp = client.responses.create(
            model=MODEL,
            input=messages,
            tools=TOOLS,
        )

        # Look for a function_call for our tool.
        function_call = None
        for item in resp.output:
            if item.type == "function_call" and item.name == "run_nflreadpy_code":
                function_call = item
                break

        # If the model doesn't call the tool, just print its answer and stop.
        if function_call is None:
            print("\n--- Model answer (no tool used) ---\n")
            # Aggregate text output from the response.
            try:
                print(resp.output_text)
            except AttributeError:
                # Fallback: print whatever text blocks exist.
                for item in resp.output:
                    if hasattr(item, "content"):
                        for part in item.content:
                            if getattr(part, "type", None) == "output_text":
                                print(part.text, end="")
                print()
            return

        # Parse tool arguments (code string).
        args = json.loads(function_call.arguments or "{}")
        code = args.get("code", "")

        print(f"\n--- Generated code (attempt {attempt + 1}) ---\n")
        print(code)

        # Try executing the generated code locally.
        try:
            result = run_nflreadpy_code_locally(code)
        except Exception as e:
            attempt += 1
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))

            print(f"\n--- Code raised an error on attempt {attempt} ---\n")
            print(tb)

            if attempt > max_retries:
                print("\nGiving up after maximum retries. Last error above.")
                return

            # Ask the model to fix its own code by appending the error context
            # and then re-running the loop.
            messages = base_messages + [
                {
                    "role": "assistant",
                    "content": (
                        "I attempted to call run_nflreadpy_code with the following "
                        "code, but it caused a Python error when executed."
                    ),
                },
                {
                    "role": "assistant",
                    "content": f"```python\n{code}\n```",
                },
                {
                    "role": "user",
                    "content": (
                        "When I ran that code, I got this error:\n"
                        f"```text\n{tb}\n```\n"
                        "Please fix the code and try again. Only use documented "
                        "nflreadpy.load_* functions and Polars idioms from the "
                        "cheat sheet and docs."
                    ),
                },
            ]

            continue  # retry with new messages

        # If we get here, code executed successfully.
        print("\n--- Tool result (JSON from run()) ---\n")
        print(json.dumps(result, indent=2))

        # Second Responses call: let the model explain the JSON result
        final = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an NFL stats assistant. The user asked a question "
                        "and you have been given precomputed data from nflreadpy. "
                        "Use only that data (plus obvious football knowledge) to "
                        "answer in natural language."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Original question:\n{question}\n\n"
                        "Here is the JSON data returned by the code:\n"
                        f"```json\n{json.dumps(result, indent=2)}\n```"
                    ),
                },
            ],
        )

        print("\n--- Final answer ---\n")
        try:
            print(final.output_text)
        except AttributeError:
            for item in final.output:
                if hasattr(item, "content"):
                    for part in item.content:
                        if getattr(part, "type", None) == "output_text":
                            print(part.text, end="")
            print()

        return


if __name__ == "__main__":
    # Your previous example question:
    default_question = "How many interceptions did Jared Goff throw in his most recent game where he threw at least 3 interceptions?"

    # If you want interactive usage instead, comment the line above and uncomment:
    # default_question = input("Ask an NFL stats question: ")

    ask_nfl_bot(default_question)
