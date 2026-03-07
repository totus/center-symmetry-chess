#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from chess_variant_research.config import load_match_config
from chess_variant_research.matches import run_selfplay_matches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    experiments = raw.get("experiments", [])
    if not experiments:
        raise SystemExit("No experiments found")

    for exp in experiments:
        path = Path(exp["config"])
        cfg = load_match_config(path)
        out = run_selfplay_matches(cfg)
        print(f"completed {path} -> {out}")


if __name__ == "__main__":
    main()
