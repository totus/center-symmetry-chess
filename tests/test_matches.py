from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import chess
import chess.pgn
import pytest

from chess_variant_research.matches import (
    MatchError,
    _chunk_sizes,
    _ChunkResult,
    _collect_pgn_games,
    _engine_limit,
    _merge_files,
    _merge_log_shards,
    _merge_pgn_shards,
    _missing_rounds,
    _parse_round,
    _parse_tc,
    _pgn_variant_header,
    _plan_missing_chunks,
    _ranges_from_rounds,
    _result_str,
    _run_match_chunk,
    _shard_paths,
    maybe_run_fastchess,
    run_selfplay_matches,
)
from chess_variant_research.schemas import EngineConfig, MatchConfig


def _game_text(round_number: int, variant: str = "swapped_white") -> str:
    game = chess.pgn.Game()
    game.headers["Event"] = "center-symmetry-selfplay"
    game.headers["Site"] = "local"
    game.headers["Date"] = "2026.03.09"
    game.headers["Round"] = str(round_number)
    game.headers["White"] = "e"
    game.headers["Black"] = "e"
    game.headers["Variant"] = _pgn_variant_header(variant)
    game.headers["ResearchVariant"] = variant
    game.headers["FEN"] = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1"
    game.headers["SetUp"] = "1"
    game.headers["Result"] = "1/2-1/2"
    return str(game) + "\n\n"


def _games_text(round_start: int, games: int) -> str:
    return "".join(
        _game_text(round_number)
        for round_number in range(round_start, round_start + games)
    )


def test_pgn_variant_header_mapping() -> None:
    assert _pgn_variant_header("orthodox") == "Standard"
    assert _pgn_variant_header("swapped_white") == "Chess960"


def test_standard_and_chess960_headers_are_accepted() -> None:
    g1 = chess.pgn.Game()
    g1.headers["Variant"] = _pgn_variant_header("orthodox")
    assert isinstance(g1.board(), chess.Board)

    g2 = chess.pgn.Game()
    g2.headers["Variant"] = _pgn_variant_header("swapped_white")
    g2.headers["SetUp"] = "1"
    g2.headers["FEN"] = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1"
    b2 = g2.board()
    assert isinstance(b2, chess.Board)
    assert b2.chess960


def test_parse_tc_and_result_helpers() -> None:
    assert _parse_tc("5+0.1") == (5.0, 0.1)
    with pytest.raises(MatchError):
        _parse_tc("bad")
    assert _engine_limit(1.0, 0.1).white_clock == 1.0
    board = chess.Board()
    assert _result_str(board) == "*"
    board = chess.Board("7k/7Q/7K/8/8/8/8/8 b - - 0 1")
    assert _result_str(board) == "1-0"


def test_chunk_sizes() -> None:
    assert _chunk_sizes(8, 3) == [3, 3, 2]
    assert _chunk_sizes(2, 4) == [1, 1, 0, 0]


def test_merge_files(tmp_path: Path) -> None:
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    out = tmp_path / "out.txt"
    p1.write_text("hello\n", encoding="utf-8")
    p2.write_text("world", encoding="utf-8")
    _merge_files([p1, p2], out)
    assert out.read_text(encoding="utf-8") == "hello\nworld\n"


def test_resume_helpers_basic(tmp_path: Path) -> None:
    assert _missing_rounds(4, {1, 3}) == [2, 4]
    assert _ranges_from_rounds([]) == []
    assert _ranges_from_rounds([1, 2, 4]) == [(1, 2), (4, 1)]
    assert _plan_missing_chunks([], 4) == []
    assert _plan_missing_chunks([1, 2, 3, 4], 2) == [(1, 2), (3, 2)]

    p = tmp_path / "o.pgn"
    (tmp_path / "o.pgn.part1").write_text("", encoding="utf-8")
    assert _shard_paths(p) == [tmp_path / "o.pgn.part1"]


def test_parse_round_and_collect_game_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(MatchError):
        _parse_round("bad", tmp_path / "x.pgn")

    bad = tmp_path / "bad.pgn"
    bad.write_text("x", encoding="utf-8")

    class FakeGame:
        headers = {"Event": "x"}

    calls = iter([FakeGame(), None])
    monkeypatch.setattr(
        "chess_variant_research.matches.chess.pgn.read_game",
        lambda fh: next(calls),
    )
    with pytest.raises(MatchError):
        _collect_pgn_games(bad)


def test_collect_games_deduplicates_rounds(tmp_path: Path) -> None:
    p = tmp_path / "dup.pgn"
    p.write_text(_game_text(1) + _game_text(1) + _game_text(2), encoding="utf-8")
    games = _collect_pgn_games(p)
    assert set(games) == {1, 2}


def test_merge_shards_helpers(tmp_path: Path) -> None:
    p1 = tmp_path / "a.pgn"
    p2 = tmp_path / "b.pgn"
    out = tmp_path / "out.pgn"
    p1.write_text(_game_text(1), encoding="utf-8")
    p2.write_text(_game_text(2), encoding="utf-8")
    merged = _merge_pgn_shards(out, [p1, p2])
    assert merged == {1, 2}

    l1 = tmp_path / "a.log"
    l2 = tmp_path / "b.log"
    l1.write_text("a", encoding="utf-8")
    l2.write_text("b\n", encoding="utf-8")
    out_log = tmp_path / "out.log"
    _merge_log_shards(out_log, [l1, l2], summary="summary")
    assert out_log.read_text(encoding="utf-8") == "a\nb\nsummary\n"


def _cfg(tmp_path: Path, games: int = 2) -> MatchConfig:
    engine_path = tmp_path / "engine.bin"
    engine_path.write_text("x", encoding="utf-8")
    return MatchConfig(
        variant="swapped_white",
        engine=EngineConfig(name="e", path=engine_path, threads=1, hash_mb=16),
        games=games,
        tc="0.01+0",
        max_plies=4,
        seed=7,
        output_pgn=tmp_path / "o.pgn",
        output_log=tmp_path / "o.log",
    )


def test_run_selfplay_matches_single_worker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=2)

    def fake_recommend(**_: object) -> int:
        return 1

    def fake_chunk(
        cfg: MatchConfig,
        games: int,
        round_start: int,
        worker_idx: int,
        worker_seed: int,
        output_pgn: Path,
        output_log: Path,
    ) -> _ChunkResult:
        output_pgn.write_text(_games_text(round_start, games), encoding="utf-8")
        output_log.write_text(f"worker={worker_idx}\n", encoding="utf-8")
        return _ChunkResult(worker_idx, games, output_pgn, output_log)

    monkeypatch.setattr("chess_variant_research.matches.recommend_parallel_games", fake_recommend)
    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fake_chunk)
    out = run_selfplay_matches(cfg)
    assert out == cfg.output_pgn
    assert cfg.output_pgn.read_text(encoding="utf-8").count("[Event") == 2


def test_run_selfplay_matches_parallel_merges_parts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=3)

    class FakeFuture:
        def __init__(self, value: object) -> None:
            self._value = value

        def result(self) -> object:
            return self._value

    class FakePool:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> FakePool:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def submit(self, fn: object, *args: object) -> FakeFuture:
            value = fn(*args)  # type: ignore[misc]
            return FakeFuture(value)

    monkeypatch.setattr("chess_variant_research.matches.recommend_parallel_games", lambda **_: 2)
    monkeypatch.setattr("chess_variant_research.matches.ProcessPoolExecutor", FakePool)
    monkeypatch.setattr("chess_variant_research.matches.as_completed", lambda futures: futures)

    def fake_chunk(
        cfg: MatchConfig,
        games: int,
        round_start: int,
        worker_idx: int,
        worker_seed: int,
        output_pgn: Path,
        output_log: Path,
    ) -> _ChunkResult:
        output_pgn.write_text(_games_text(round_start, games), encoding="utf-8")
        output_log.write_text(f"log={worker_seed}\n", encoding="utf-8")
        return _ChunkResult(
            worker_idx=worker_idx, games_written=games, pgn_path=output_pgn, log_path=output_log
        )

    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fake_chunk)
    out = run_selfplay_matches(cfg)
    assert out == cfg.output_pgn
    assert cfg.output_pgn.read_text(encoding="utf-8").count("[Event") == 3
    assert "summary workers=2" in cfg.output_log.read_text(encoding="utf-8")


def test_run_match_chunk_with_fake_engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = _cfg(tmp_path, games=1)

    class FakeEngine:
        def __enter__(self) -> FakeEngine:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def configure(self, _: object) -> None:
            return None

        def play(self, board: chess.Board, limit: chess.engine.Limit, info: object) -> object:
            return SimpleNamespace(move=next(iter(board.legal_moves)))

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _: FakeEngine())
    result = _run_match_chunk(
        cfg=cfg,
        games=1,
        round_start=1,
        worker_idx=1,
        worker_seed=1,
        output_pgn=cfg.output_pgn,
        output_log=cfg.output_log,
    )
    assert result.games_written == 1
    assert "[Variant \"Chess960\"]" in cfg.output_pgn.read_text(encoding="utf-8")


def test_run_match_chunk_engine_error_and_none_move(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=1)

    class FakeEngine:
        def __enter__(self) -> FakeEngine:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def configure(self, _: object) -> None:
            raise chess.engine.EngineError("x")

        def play(self, board: chess.Board, limit: chess.engine.Limit, info: object) -> object:
            return SimpleNamespace(move=None)

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _: FakeEngine())
    monkeypatch.setattr("chess_variant_research.matches.random.Random.random", lambda _: 0.9)
    _run_match_chunk(
        cfg=cfg,
        games=1,
        round_start=1,
        worker_idx=1,
        worker_seed=1,
        output_pgn=cfg.output_pgn,
        output_log=cfg.output_log,
    )
    text = cfg.output_pgn.read_text(encoding="utf-8")
    assert "ColorOrder \"BW\"" in text


def test_run_match_chunk_finished_game_sets_termination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=1)

    class FakeEngine:
        def __enter__(self) -> FakeEngine:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def configure(self, _: object) -> None:
            return None

        def play(self, board: chess.Board, limit: chess.engine.Limit, info: object) -> object:
            return SimpleNamespace(move=None)

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _: FakeEngine())
    monkeypatch.setattr(
        "chess_variant_research.matches.board_for_variant",
        lambda _: chess.Board("7k/7Q/7K/8/8/8/8/8 b - - 0 1"),
    )
    _run_match_chunk(
        cfg=cfg,
        games=1,
        round_start=1,
        worker_idx=1,
        worker_seed=1,
        output_pgn=cfg.output_pgn,
        output_log=cfg.output_log,
    )
    assert "Termination" in cfg.output_pgn.read_text(encoding="utf-8")


def test_run_selfplay_matches_errors(tmp_path: Path) -> None:
    cfg_missing = MatchConfig(
        variant="swapped_white",
        engine=EngineConfig(name="e", path=tmp_path / "missing"),
        games=1,
        tc="0.01+0",
    )
    with pytest.raises(MatchError):
        run_selfplay_matches(cfg_missing)

    p = tmp_path / "engine.bin"
    p.write_text("x", encoding="utf-8")
    cfg_bad_games = MatchConfig(
        variant="swapped_white",
        engine=EngineConfig(name="e", path=p),
        games=0,
        tc="0.01+0",
    )
    with pytest.raises(MatchError):
        run_selfplay_matches(cfg_bad_games)


def test_run_selfplay_matches_parallel_with_zero_chunks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=1)

    class FakeFuture:
        def __init__(self, value: _ChunkResult) -> None:
            self._value = value

        def result(self) -> _ChunkResult:
            return self._value

    class FakePool:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> FakePool:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def submit(self, fn: object, *args: object) -> FakeFuture:
            value = fn(*args)  # type: ignore[misc]
            return FakeFuture(value)

    monkeypatch.setattr("chess_variant_research.matches.recommend_parallel_games", lambda **_: 3)
    monkeypatch.setattr("chess_variant_research.matches.ProcessPoolExecutor", FakePool)
    monkeypatch.setattr("chess_variant_research.matches.as_completed", lambda futures: futures)

    def fake_chunk(
        cfg: MatchConfig,
        games: int,
        round_start: int,
        worker_idx: int,
        worker_seed: int,
        output_pgn: Path,
        output_log: Path,
    ) -> _ChunkResult:
        output_pgn.write_text(_games_text(round_start, games), encoding="utf-8")
        output_log.write_text("y\n", encoding="utf-8")
        return _ChunkResult(worker_idx, games, output_pgn, output_log)

    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fake_chunk)
    run_selfplay_matches(cfg)
    assert cfg.output_pgn.exists()


def test_run_selfplay_matches_resumes_from_partial_shards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=4)
    cfg.output_pgn.write_text(_game_text(1), encoding="utf-8")
    cfg.output_log.write_text("old-log\n", encoding="utf-8")
    (tmp_path / "o.pgn.part1").write_text(_game_text(2), encoding="utf-8")
    (tmp_path / "o.log.part1").write_text("part-log\n", encoding="utf-8")

    class FakeFuture:
        def __init__(self, value: _ChunkResult) -> None:
            self._value = value

        def result(self) -> _ChunkResult:
            return self._value

    class FakePool:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> FakePool:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def submit(self, fn: object, *args: object) -> FakeFuture:
            value = fn(*args)  # type: ignore[misc]
            return FakeFuture(value)

    monkeypatch.setattr("chess_variant_research.matches.recommend_parallel_games", lambda **_: 2)
    monkeypatch.setattr("chess_variant_research.matches.ProcessPoolExecutor", FakePool)
    monkeypatch.setattr("chess_variant_research.matches.as_completed", lambda futures: futures)

    def fake_chunk(
        cfg: MatchConfig,
        games: int,
        round_start: int,
        worker_idx: int,
        worker_seed: int,
        output_pgn: Path,
        output_log: Path,
    ) -> _ChunkResult:
        output_pgn.write_text(_games_text(round_start, games), encoding="utf-8")
        output_log.write_text(f"resume={worker_idx}\n", encoding="utf-8")
        return _ChunkResult(worker_idx, games, output_pgn, output_log)

    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fake_chunk)
    run_selfplay_matches(cfg)
    assert cfg.output_pgn.read_text(encoding="utf-8").count("[Event") == 4
    assert "old-log" in cfg.output_log.read_text(encoding="utf-8")
    assert not (tmp_path / "o.pgn.part1").exists()
    assert not (tmp_path / "o.log.part1").exists()


def test_run_selfplay_matches_skips_completed_resume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=3)
    cfg.output_pgn.write_text(_game_text(1), encoding="utf-8")
    cfg.output_log.write_text("old\n", encoding="utf-8")
    (tmp_path / "o.pgn.part1").write_text(_game_text(2) + _game_text(3), encoding="utf-8")
    (tmp_path / "o.log.part1").write_text("part\n", encoding="utf-8")

    def fail_chunk(**_: object) -> _ChunkResult:
        raise AssertionError("should not run new chunks")

    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fail_chunk)
    run_selfplay_matches(cfg)
    assert cfg.output_pgn.read_text(encoding="utf-8").count("[Event") == 3
    assert "part" in cfg.output_log.read_text(encoding="utf-8")
    assert not (tmp_path / "o.pgn.part1").exists()


def test_run_selfplay_matches_merge_count_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=2)
    cfg.output_pgn.write_text(_game_text(1) + _game_text(2), encoding="utf-8")

    monkeypatch.setattr(
        "chess_variant_research.matches._merge_pgn_shards",
        lambda target, shards: {1},
    )
    with pytest.raises(MatchError):
        run_selfplay_matches(cfg)


def test_run_selfplay_matches_merge_count_guard_after_resume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _cfg(tmp_path, games=2)

    def fake_chunk(
        cfg: MatchConfig,
        games: int,
        round_start: int,
        worker_idx: int,
        worker_seed: int,
        output_pgn: Path,
        output_log: Path,
    ) -> _ChunkResult:
        output_pgn.write_text(_games_text(round_start, games), encoding="utf-8")
        output_log.write_text("log\n", encoding="utf-8")
        return _ChunkResult(worker_idx, games, output_pgn, output_log)

    monkeypatch.setattr("chess_variant_research.matches.recommend_parallel_games", lambda **_: 1)
    monkeypatch.setattr("chess_variant_research.matches._run_match_chunk", fake_chunk)
    monkeypatch.setattr(
        "chess_variant_research.matches._merge_pgn_shards",
        lambda target, shards: {1},
    )
    with pytest.raises(MatchError):
        run_selfplay_matches(cfg)


def test_merge_files_skips_empty(tmp_path: Path) -> None:
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    out = tmp_path / "out"
    p1.write_text("", encoding="utf-8")
    p2.write_text("x", encoding="utf-8")
    _merge_files([p1, p2], out)
    assert out.read_text(encoding="utf-8") == "x\n"


def test_maybe_run_fastchess_noop(tmp_path: Path) -> None:
    assert maybe_run_fastchess(tmp_path / "x") is None
