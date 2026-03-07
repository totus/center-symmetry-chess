from __future__ import annotations

from pathlib import Path

import chess
import chess.engine
import pandas as pd
import pytest

from chess_variant_research.engines import (
    _configure,
    describe_engine,
    probe_position,
    require_engine_binary,
    run_root_probe,
    write_probe_log,
)
from chess_variant_research.schemas import EngineConfig, ProbeConfig


class _FakeWdl:
    def __init__(self) -> None:
        self.wins = 1
        self.draws = 2
        self.losses = 3

    def white(self) -> _FakeWdl:
        return self


class _FakeEngine:
    def __enter__(self) -> _FakeEngine:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def configure(self, _: object) -> None:
        return None

    def analyse(
        self, board: chess.Board, limit: chess.engine.Limit, multipv: int
    ) -> list[dict[str, object]]:
        move = next(iter(board.legal_moves))
        info = {
            "pv": [move],
            "depth": 10,
            "seldepth": 12,
            "nodes": 1000,
            "nps": 2000,
            "time": 0.1,
            "hashfull": 5,
            "score": chess.engine.PovScore(chess.engine.Cp(34), chess.WHITE),
            "wdl": _FakeWdl(),
        }
        if multipv == 1:
            return [info]
        return [info, {**info, "depth": 9}]


class _FailEngine:
    def configure(self, _: object) -> None:
        raise chess.engine.EngineError("bad")


def test_require_engine_binary(tmp_path: Path) -> None:
    p = tmp_path / "bin"
    p.write_text("x", encoding="utf-8")
    require_engine_binary(p)
    from chess_variant_research.engines import EngineError

    with pytest.raises(EngineError):
        require_engine_binary(tmp_path / "missing")


def test_configure_swallows_engine_error() -> None:
    _configure(_FailEngine(), EngineConfig(name="e", path=Path("x")))


def test_configure_with_extra_options() -> None:
    seen: dict[str, object] = {}

    class E:
        def configure(self, opts: dict[str, object]) -> None:
            seen.update(opts)

    _configure(
        E(),
        EngineConfig(
            name="e",
            path=Path("x"),
            threads=2,
            hash_mb=32,
            extra_options={"Ponder": False},
        ),
    )
    assert seen["Threads"] == 2
    assert seen["Ponder"] is False


def test_probe_position_extracts_fields() -> None:
    board = chess.Board()
    out = probe_position(_FakeEngine(), board, depth=8, movetime_ms=100, multipv=2)
    assert len(out) == 2
    assert out[0]["score_cp"] == 34
    assert out[0]["wdl_w"] == 1


def test_run_root_probe_and_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    eng = tmp_path / "engine"
    eng.write_text("x", encoding="utf-8")
    out = tmp_path / "probe.csv"

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _: _FakeEngine())

    cfg = ProbeConfig(
        variant="swapped_white",
        engine=EngineConfig(name="fake", path=eng, threads=1, hash_mb=16),
        depth=6,
        movetime_ms=10,
        multipv=1,
        output_csv=out,
    )
    df = run_root_probe(cfg)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert out.exists()

    d = describe_engine(cfg.engine)
    assert d["name"] == "fake"

    log_path = tmp_path / "probe.log"
    write_probe_log(log_path, "ok")
    assert log_path.read_text(encoding="utf-8") == "ok"
