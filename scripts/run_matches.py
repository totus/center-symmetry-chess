#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from chess_variant_research.config import load_match_config
from chess_variant_research.matches import run_selfplay_matches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    cfg = load_match_config(args.config)
    out = run_selfplay_matches(cfg)
    print(f"Wrote PGN -> {out}")


if __name__ == "__main__":
    main()
