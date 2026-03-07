#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from chess_variant_research.config import load_match_config
from chess_variant_research.host import detect_host_resources, recommend_parallel_games


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/match_swapped_white.yaml"))
    args = parser.parse_args()

    cfg = load_match_config(args.config)
    host = detect_host_resources()
    recommended = recommend_parallel_games(
        games=cfg.games,
        engine_threads=cfg.engine.threads,
        hash_mb=cfg.engine.hash_mb,
        requested_parallel_games=cfg.parallel_games,
        host=host,
    )

    print(f"config={args.config}")
    print(f"logical_cpus={host.logical_cpus}")
    print(f"total_memory_mb={host.total_memory_mb}")
    print(f"engine_threads={cfg.engine.threads}")
    print(f"engine_hash_mb={cfg.engine.hash_mb}")
    print(f"games={cfg.games}")
    parallel_cfg = cfg.parallel_games if cfg.parallel_games is not None else "auto"
    print(f"parallel_games_config={parallel_cfg}")
    print(f"parallel_games_effective={recommended}")


if __name__ == "__main__":
    main()
