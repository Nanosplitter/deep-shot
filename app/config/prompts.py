"""Prompt templates for the NFL stats assistant."""

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


def get_system_prompt(current_season: int) -> str:
    """Generate the system prompt for the NFL stats assistant."""
    return (
        "You are an NFL stats assistant that writes Python code using the "
        "`nflreadpy` library and Polars.\n\n"
        "When a question requires looking up stats, you MUST call the "
        "run_nflreadpy_code tool instead of answering directly.\n\n"
        "Requirements for the code you pass to the tool:\n"
        "- import nflreadpy as nfl (and polars as pl when needed).\n"
        "- define a function run() with no arguments.\n"
        "- inside run(), use documented nflreadpy.load_* functions and Polars.\n"
        "- convert any Polars DataFrames to aggregates / plain Python types.\n"
        "- return a JSON-serializable dict with keys like 'response' and 'explanation'.\n"
        "REMINDERS:\n"
        "- nflreadpy uses Polars DataFrames rather than pandas.\n"
        f"- Make sure to specify seasons when loading data (e.g., seasons=[2022, 2023, 2024, {current_season}]). "
        f"The current season is {current_season}.\n"
        "- Keep the returned data reasonably small to avoid unnecessary cost.\n"
        "- Do NOT print anything in run(). Just return the dict.\n"
    )


def get_docs_prompt() -> str:
    """Generate the documentation prompt."""
    return "nflreadpy documentation (cheat sheet):\n" + NFLREADPY_CHEAT_SHEET


def get_summarization_prompt() -> str:
    """Generate the summarization system prompt."""
    return (
        "You are an NFL stats assistant. The user asked a question "
        "and you have been given precomputed data from nflreadpy. "
        "Use only that data (plus obvious football knowledge) to "
        "answer in natural language."
    )
