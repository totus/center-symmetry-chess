from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VariantName = Literal["orthodox", "swapped_white", "swapped_black", "swapped_both"]


@dataclass(slots=True)
class EngineConfig:
    name: str
    path: Path
    threads: int = 1
    hash_mb: int = 128
    extra_options: dict[str, str | int | bool] | None = None


@dataclass(slots=True)
class ProbeConfig:
    variant: VariantName
    engine: EngineConfig
    depth: int | None = 16
    movetime_ms: int | None = None
    multipv: int = 1
    positions: list[str] | None = None
    output_csv: Path = Path("data/processed/root_probe.csv")


@dataclass(slots=True)
class MatchConfig:
    variant: VariantName
    engine: EngineConfig
    games: int
    tc: str
    parallel_games: int | None = None
    max_plies: int = 400
    seed: int = 42
    output_pgn: Path = Path("data/raw/matches.pgn")
    output_log: Path = Path("data/raw/matches.log")
