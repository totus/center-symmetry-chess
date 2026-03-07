from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Template

REPORT_TEMPLATE = Template(
    """# Chess Variant Research Report

## Experiment Metadata

- Generated: {{ generated_at }}
- Engine: {{ engine_name }}
- Time control: {{ time_control }}
- Variants: {{ variants }}

## Variant Definitions

- `orthodox`: standard start
- `swapped_white`: White king/queen swapped
- `swapped_black`: Black king/queen swapped
- `swapped_both`: both sides swapped

Castling uses Chess960 legality with orthodox destination squares (`c/g` for kings).

## Sample Sizes

{{ sample_table }}

## Match Results Summary

{{ summary_table }}

## Opening Behavior Summary

{{ opening_table }}

## Rating Estimates

{{ rating_table }}

## Key Findings

{{ findings }}

## Known Limitations

- Results depend on selected engine build/options/time control.
- If no external rating tool (Ordo/BayesElo) is used, Elo confidence is approximate.
- Opening suite coverage may bias results if too narrow.
"""
)


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data available._"
    return str(df.to_markdown(index=False))


def generate_markdown_report(
    output: Path,
    metadata: dict[str, str],
    summary_df: pd.DataFrame,
    opening_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    findings: str,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if {"variant", "games"}.issubset(summary_df.columns):
        sample = summary_df[["variant", "games"]]
    else:
        sample = pd.DataFrame()
    text = REPORT_TEMPLATE.render(
        generated_at=metadata.get("generated_at", "unknown"),
        engine_name=metadata.get("engine_name", "unknown"),
        time_control=metadata.get("time_control", "unknown"),
        variants=metadata.get("variants", "unknown"),
        sample_table=_md_table(sample),
        summary_table=_md_table(summary_df),
        opening_table=_md_table(opening_df),
        rating_table=_md_table(ratings_df),
        findings=findings,
    )
    output.write_text(text, encoding="utf-8")
    return output
