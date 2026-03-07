from __future__ import annotations

from pathlib import Path

import pytest

from chess_variant_research.fen import get_start_fen, load_fen_file


def test_get_start_fen_invalid() -> None:
    with pytest.raises(ValueError):
        get_start_fen("bad" )  # type: ignore[arg-type]


def test_load_fen_file(tmp_path: Path) -> None:
    p = tmp_path / "x.fen"
    p.write_text("8/8/8/8/8/8/8/8 w - - 0 1\n", encoding="utf-8")
    assert load_fen_file(p).startswith("8/8/8")
