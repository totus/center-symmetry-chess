from pathlib import Path

from chess_variant_research.config import load_match_config


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
