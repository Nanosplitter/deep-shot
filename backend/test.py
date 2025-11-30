import nflreadpy as nfl
import polars as pl


def run():
    stats = nfl.load_player_stats(seasons=[2025], summary_level="reg")
    passing = (
        stats.filter(pl.col("attempts") > 0)
        .with_columns(
            [
                (((pl.col("completions") / pl.col("attempts")) - 0.3) * 5)
                .clip(0, 2.375)
                .alias("a"),
                (((pl.col("passing_yards") / pl.col("attempts")) - 3) * 0.25)
                .clip(0, 2.375)
                .alias("b"),
                ((pl.col("passing_tds") / pl.col("attempts")) * 20)
                .clip(0, 2.375)
                .alias("c"),
                (2.375 - ((pl.col("passing_interceptions") / pl.col("attempts")) * 25))
                .clip(0, 2.375)
                .alias("d"),
            ]
        )
        .with_columns(
            (((pl.col("a") + pl.col("b") + pl.col("c") + pl.col("d")) / 6) * 100).alias(
                "passer_rating"
            )
        )
        .filter(pl.col("attempts") >= 50)
        .select(
            [
                "player_display_name",
                "team",
                "attempts",
                "completions",
                "passing_yards",
                "passing_tds",
                "passing_interceptions",
                "passer_rating",
            ]
        )
        .sort("passer_rating", descending=True)
    )

    top = passing.head(1).to_dicts()

    return {
        "response": top,
        "explanation": "Highest passer rating so far in the 2025 regular season (min 50 attempts).",
    }


run()
