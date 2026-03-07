from pathlib import Path

import pytest

from chess_variant_research.config import (
    ConfigError,
    load_match_config,
    load_probe_config,
    parse_variant,
)


def test_load_match_config_auto_parallel(tmp_path: Path) -> None:
    cfg_file = tmp_path / "match.yaml"
    cfg_file.write_text(
        """
variant: swapped_white
engine:
  name: fairy-stockfish
  path: engines/bin/fairy-stockfish
games: 20
tc: 5+0.05
parallel_games: auto
""".strip(),
        encoding="utf-8",
    )
    cfg = load_match_config(cfg_file)
    assert cfg.parallel_games is None


def test_load_match_config_numeric_parallel(tmp_path: Path) -> None:
    cfg_file = tmp_path / "match.yaml"
    cfg_file.write_text(
        """
variant: swapped_white
engine:
  name: fairy-stockfish
  path: engines/bin/fairy-stockfish
games: 20
tc: 5+0.05
parallel_games: 6
""".strip(),
        encoding="utf-8",
    )
    cfg = load_match_config(cfg_file)
    assert cfg.parallel_games == 6


def test_parse_variant_valid_and_invalid() -> None:
    assert parse_variant("orthodox") == "orthodox"
    with pytest.raises(ConfigError):
        parse_variant("invalid")


def test_load_probe_config_requires_engine(tmp_path: Path) -> None:
    p = tmp_path / "probe.yaml"
    p.write_text("variant: swapped_white\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_probe_config(p)


def test_load_probe_config_success(tmp_path: Path) -> None:
    p = tmp_path / "probe.yaml"
    p.write_text(
        """
variant: swapped_white
engine:
  name: e
  path: engines/bin/fairy-stockfish
depth: 8
movetime_ms: 20
multipv: 2
positions:
  - rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1
""".strip(),
        encoding="utf-8",
    )
    cfg = load_probe_config(p)
    assert cfg.depth == 8
    assert cfg.multipv == 2
