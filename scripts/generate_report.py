#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from chess_variant_research.reporting import generate_markdown_report
from chess_variant_research.utils import utc_ts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}

    summary = pd.read_csv(Path(cfg["summary_csv"]))
    openings = pd.read_csv(Path(cfg["openings_csv"])) if "openings_csv" in cfg else pd.DataFrame()
    ratings = pd.read_csv(Path(cfg["ratings_csv"]))

    metadata = {
        "generated_at": utc_ts(),
        "engine_name": cfg.get("engine_name", "unknown"),
        "time_control": cfg.get("time_control", "unknown"),
        "variants": ", ".join(cfg.get("variants", [])) if cfg.get("variants") else "unknown",
    }
    findings = cfg.get("findings", "No findings text provided.")

    out = generate_markdown_report(args.output, metadata, summary, openings, ratings, findings)
    print(f"Wrote report -> {out}")


if __name__ == "__main__":
    main()
