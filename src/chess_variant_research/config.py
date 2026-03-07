from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .schemas import EngineConfig, MatchConfig, ProbeConfig, VariantName


class ConfigError(ValueError):
    pass


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ConfigError(f"Missing required config field: {key}")
    return data[key]


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_engine_config(data: dict[str, Any]) -> EngineConfig:
    return EngineConfig(
        name=str(_require(data, "name")),
        path=Path(str(_require(data, "path"))),
        threads=int(data.get("threads", 1)),
        hash_mb=int(data.get("hash_mb", 128)),
        extra_options=data.get("extra_options"),
    )


def load_probe_config(path: Path) -> ProbeConfig:
    raw = load_yaml(path)
    engine = parse_engine_config(_require(raw, "engine"))
    return ProbeConfig(
        variant=_require(raw, "variant"),
        engine=engine,
        depth=raw.get("depth"),
        movetime_ms=raw.get("movetime_ms"),
        multipv=int(raw.get("multipv", 1)),
        positions=raw.get("positions"),
        output_csv=Path(raw.get("output_csv", "data/processed/root_probe.csv")),
    )


def load_match_config(path: Path) -> MatchConfig:
    raw = load_yaml(path)
    engine = parse_engine_config(_require(raw, "engine"))
    parallel_raw = raw.get("parallel_games")
    parallel_games: int | None
    if parallel_raw is None or str(parallel_raw).lower() == "auto":
        parallel_games = None
    else:
        parallel_games = int(parallel_raw)
    return MatchConfig(
        variant=_require(raw, "variant"),
        engine=engine,
        games=int(_require(raw, "games")),
        tc=str(_require(raw, "tc")),
        parallel_games=parallel_games,
        max_plies=int(raw.get("max_plies", 400)),
        seed=int(raw.get("seed", 42)),
        output_pgn=Path(raw.get("output_pgn", "data/raw/matches.pgn")),
        output_log=Path(raw.get("output_log", "data/raw/matches.log")),
    )


def parse_variant(value: str) -> VariantName:
    allowed: set[str] = {"orthodox", "swapped_white", "swapped_black", "swapped_both"}
    if value not in allowed:
        raise ConfigError(f"Unsupported variant '{value}'. Allowed: {sorted(allowed)}")
    return value  # type: ignore[return-value]
