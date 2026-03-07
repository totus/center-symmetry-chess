#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chess_variant_research.ratings import estimate_elo_by_variant
from chess_variant_research.utils import write_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.games)
    ratings = estimate_elo_by_variant(df)
    write_table(ratings, args.output)
    print(f"Wrote rating rows={len(ratings)} -> {args.output}")


if __name__ == "__main__":
    main()
