#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chess_variant_research.metrics import summarize_games, summarize_openings
from chess_variant_research.utils import write_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--openings-output", type=Path, default=Path("data/processed/openings.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.games)
    summary = summarize_games(df, by="variant")
    openings = summarize_openings(df)
    write_table(summary, args.output)
    write_table(openings, args.openings_output)
    print(f"Wrote aggregate rows={len(summary)} -> {args.output}")
    print(f"Wrote opening rows={len(openings)} -> {args.openings_output}")


if __name__ == "__main__":
    main()
