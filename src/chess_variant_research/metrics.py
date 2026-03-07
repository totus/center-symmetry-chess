from __future__ import annotations

from typing import Any

import pandas as pd

RESULT_POINTS = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}


def add_score_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["white_score"] = out["result"].map(RESULT_POINTS)
    out["black_score"] = 1.0 - out["white_score"]
    return out


def summarize_games(df: pd.DataFrame, by: str = "variant") -> pd.DataFrame:
    data = add_score_columns(df)

    def _agg(g: pd.DataFrame) -> pd.Series:
        white_wins = int((g["result"] == "1-0").sum())
        black_wins = int((g["result"] == "0-1").sum())
        draws = int((g["result"] == "1/2-1/2").sum())
        total = len(g)
        return pd.Series(
            {
                "games": total,
                "white_win_rate": white_wins / total if total else 0.0,
                "black_win_rate": black_wins / total if total else 0.0,
                "draw_rate": draws / total if total else 0.0,
                "score_pct": float(g["white_score"].mean() * 100),
                "kingside_castle_white": float((g["white_castling_side"] == "kingside").mean()),
                "queenside_castle_white": float((g["white_castling_side"] == "queenside").mean()),
                "kingside_castle_black": float((g["black_castling_side"] == "kingside").mean()),
                "queenside_castle_black": float((g["black_castling_side"] == "queenside").mean()),
                "no_castle_white": float((g["white_castling_side"] == "none").mean()),
                "no_castle_black": float((g["black_castling_side"] == "none").mean()),
                "avg_white_castle_move": (
                    float(g["white_castling_move"].dropna().mean())
                    if g["white_castling_move"].notna().any()
                    else float("nan")
                ),
                "avg_black_castle_move": (
                    float(g["black_castling_move"].dropna().mean())
                    if g["black_castling_move"].notna().any()
                    else float("nan")
                ),
                "avg_game_length": float(g["move_count"].mean()),
            }
        )

    return data.groupby(by, dropna=False).apply(_agg).reset_index()


def summarize_openings(df: pd.DataFrame) -> pd.DataFrame:
    data = add_score_columns(df)
    return (
        data.groupby(["variant", "opening_family"], dropna=False)
        .agg(games=("game_id", "count"), score_pct=("white_score", lambda s: float(s.mean() * 100)))
        .reset_index()
    )


def compare_swaps(df: pd.DataFrame) -> dict[str, Any]:
    data = add_score_columns(df)
    sw = data[data["variant"] == "swapped_white"]["white_score"].dropna()
    sb = data[data["variant"] == "swapped_black"]["white_score"].dropna()
    if len(sw) == 0 or len(sb) == 0:
        return {"delta_score_pct": None}
    return {"delta_score_pct": float((sw.mean() - sb.mean()) * 100)}
