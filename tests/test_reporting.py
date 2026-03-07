from __future__ import annotations

from pathlib import Path

import pandas as pd

from chess_variant_research.reporting import _md_table, generate_markdown_report


def test_md_table_empty() -> None:
    assert _md_table(pd.DataFrame()) == "_No data available._"


def test_generate_markdown_report(tmp_path: Path) -> None:
    out = tmp_path / "r.md"
    summary = pd.DataFrame([{"variant": "swapped_white", "games": 10, "score_pct": 51.0}])
    openings = pd.DataFrame([{"variant": "swapped_white", "opening_family": "e4", "games": 5}])
    ratings = pd.DataFrame([{"variant": "swapped_white", "elo_diff": 10.0}])
    generate_markdown_report(
        out,
        metadata={
            "generated_at": "now",
            "engine_name": "e",
            "time_control": "1+0",
            "variants": "x",
        },
        summary_df=summary,
        opening_df=openings,
        ratings_df=ratings,
        findings="done",
    )
    text = out.read_text(encoding="utf-8")
    assert "Chess Variant Research Report" in text
    assert "done" in text


def test_generate_markdown_report_without_sample_columns(tmp_path: Path) -> None:
    out = tmp_path / "r2.md"
    summary = pd.DataFrame([{"x": 1}])
    generate_markdown_report(
        out,
        metadata={},
        summary_df=summary,
        opening_df=pd.DataFrame(),
        ratings_df=pd.DataFrame(),
        findings="x",
    )
    assert out.exists()
