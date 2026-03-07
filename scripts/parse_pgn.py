#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from chess_variant_research.parsing import parse_pgn_paths
from chess_variant_research.utils import write_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.input.is_dir():
        paths = sorted(args.input.glob("*.pgn"))
    else:
        paths = [args.input]
    df = parse_pgn_paths(paths)
    write_table(df, args.output)
    print(f"Parsed games={len(df)} -> {args.output}")


if __name__ == "__main__":
    main()
