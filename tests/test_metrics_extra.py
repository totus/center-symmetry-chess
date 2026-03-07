from __future__ import annotations

import pandas as pd

from chess_variant_research.metrics import compare_swaps, summarize_openings


def test_summarize_openings_and_compare_swaps() -> None:
    df = pd.DataFrame(
        [
            {"game_id": "1", "variant": "swapped_white", "opening_family": "e4", "result": "1-0"},
            {"game_id": "2", "variant": "swapped_black", "opening_family": "e4", "result": "0-1"},
        ]
    )
    opening = summarize_openings(df)
    assert len(opening) == 2
    comp = compare_swaps(df)
    assert comp["delta_score_pct"] is not None


def test_compare_swaps_missing_side() -> None:
    df = pd.DataFrame(
        [{"game_id": "1", "variant": "swapped_white", "opening_family": "e4", "result": "1-0"}]
    )
    assert compare_swaps(df)["delta_score_pct"] is None
