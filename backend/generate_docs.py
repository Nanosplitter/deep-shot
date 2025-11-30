"""Generate nflreadpy column documentation by calling the actual functions."""

import pathlib

import nflreadpy as nfl

# Map function names to their callable and required arguments
LOADERS = {
    "load_pbp": lambda: nfl.load_pbp(seasons=[2025]),
    "load_player_stats": lambda: nfl.load_player_stats(
        seasons=[2025], summary_level="reg"
    ),
    "load_schedules": lambda: nfl.load_schedules(seasons=[2025]),
    "load_rosters": lambda: nfl.load_rosters(seasons=[2025]),
    "load_snap_counts": lambda: nfl.load_snap_counts(seasons=[2025]),
    "load_injuries": lambda: nfl.load_injuries(seasons=[2025]),
    "load_nextgen_stats": lambda: nfl.load_nextgen_stats(seasons=[2025]),
    "load_depth_charts": lambda: nfl.load_depth_charts(seasons=[2025]),
    "load_trades": lambda: nfl.load_trades(),
    "load_contracts": lambda: nfl.load_contracts(),
    "load_combine": lambda: nfl.load_combine(seasons=[2025]),
}


def get_columns_markdown(func_name: str, loader_fn) -> str:
    """Call a loader function and return markdown with its column names."""
    try:
        df = loader_fn()
        columns = df.columns
        column_list = ", ".join(columns)
        return f"## {func_name} columns\n\n{column_list}\n\n"
    except Exception as e:
        return f"## {func_name} columns\n\nFailed to load: {e}\n\n"


def main():
    parts = [
        "# nflreadpy Column Reference (compressed)\n\n",
        "For each loader below, this lists **only** the column names returned in the DataFrame.\n",
        "Use this as a contract to avoid hallucinating non-existent columns.\n\n",
    ]

    for func_name, loader_fn in LOADERS.items():
        print(f"Loading {func_name}...")
        parts.append(get_columns_markdown(func_name, loader_fn))

    out_path = pathlib.Path("nflreadpy_schema_columns_only.md")
    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
