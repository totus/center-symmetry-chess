#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from chess_variant_research.config import load_probe_config
from chess_variant_research.engines import run_root_probe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    cfg = load_probe_config(args.config)
    df = run_root_probe(cfg)
    print(f"Wrote probe rows={len(df)} -> {cfg.output_csv}")


if __name__ == "__main__":
    main()
