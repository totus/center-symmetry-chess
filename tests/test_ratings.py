from __future__ import annotations

import pandas as pd

from chess_variant_research.ratings import elo_ci_from_scores, estimate_elo_by_variant, score_to_elo


def test_score_to_elo_monotonic() -> None:
    assert score_to_elo(0.6) > score_to_elo(0.5)


def test_elo_ci_handles_empty() -> None:
    lo, hi = elo_ci_from_scores(pd.Series([], dtype=float))
    assert str(lo) == "nan"
    assert str(hi) == "nan"


def test_estimate_elo_by_variant_handles_scored_and_unscored() -> None:
    df = pd.DataFrame(
        [
            {"variant": "swapped_white", "result": "1-0"},
            {"variant": "swapped_white", "result": "1/2-1/2"},
            {"variant": "swapped_black", "result": "*"},
        ]
    )
    out = estimate_elo_by_variant(df)
    assert set(out["variant"]) == {"swapped_white", "swapped_black"}
