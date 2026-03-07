from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from .fen import board_for_variant, get_start_fen
from .host import detect_host_resources, recommend_parallel_games
from .schemas import MatchConfig
from .utils import ensure_dir, utc_ts


class MatchError(RuntimeError):
    pass


@dataclass(slots=True)
class _ChunkResult:
    worker_idx: int
    games_written: int
    pgn_path: Path
    log_path: Path


def _parse_tc(tc: str) -> tuple[float, float]:
    # format: base+increment in seconds, e.g. 5+0.1
    if "+" not in tc:
        raise MatchError(f"Invalid tc '{tc}'. Expected base+increment")
    base, inc = tc.split("+", maxsplit=1)
    return float(base), float(inc)


def _engine_limit(base_time: float, increment: float) -> chess.engine.Limit:
    return chess.engine.Limit(
        white_clock=base_time,
        black_clock=base_time,
        white_inc=increment,
        black_inc=increment,
    )


def _result_str(board: chess.Board) -> str:
    out = board.outcome(claim_draw=True)
    if out is None:
        return "*"
    return out.result()


def _pgn_variant_header(variant: str) -> str:
    # PGN Variant must be a known variant label for python-chess.
    return "Standard" if variant == "orthodox" else "Chess960"


def _run_match_chunk(
    cfg: MatchConfig,
    games: int,
    round_start: int,
    worker_idx: int,
    worker_seed: int,
    output_pgn: Path,
    output_log: Path,
) -> _ChunkResult:
    ensure_dir(output_pgn.parent)
    ensure_dir(output_log.parent)

    base, inc = _parse_tc(cfg.tc)
    rng = random.Random(worker_seed)
    start_fen = get_start_fen(cfg.variant)

    with (
        chess.engine.SimpleEngine.popen_uci(str(cfg.engine.path)) as engine,
        output_pgn.open("w", encoding="utf-8") as pgn_file,
        output_log.open("w", encoding="utf-8") as log_file,
    ):
        try:
            engine.configure({"Threads": cfg.engine.threads, "Hash": cfg.engine.hash_mb})
        except chess.engine.EngineError:
            pass

        log_file.write(
            f"worker={worker_idx} seed={worker_seed} games={games} round_start={round_start}\n"
        )

        for local_idx in range(games):
            game_idx = round_start + local_idx
            board = board_for_variant(cfg.variant)
            game = chess.pgn.Game()
            game.headers["Event"] = "center-symmetry-selfplay"
            game.headers["Site"] = "local"
            game.headers["Date"] = utc_ts().split("T", maxsplit=1)[0].replace("-", ".")
            game.headers["Round"] = str(game_idx)
            game.headers["White"] = cfg.engine.name
            game.headers["Black"] = cfg.engine.name
            game.headers["Variant"] = _pgn_variant_header(cfg.variant)
            game.headers["ResearchVariant"] = cfg.variant
            game.headers["FEN"] = start_fen
            game.headers["SetUp"] = "1"
            game.headers["TimeControl"] = cfg.tc

            if rng.random() < 0.5:
                game.headers["ColorOrder"] = "WB"
            else:
                game.headers["ColorOrder"] = "BW"

            node: chess.pgn.GameNode = game
            for _ in range(cfg.max_plies):
                if board.is_game_over(claim_draw=True):
                    break
                res = engine.play(board, _engine_limit(base, inc), info=chess.engine.INFO_NONE)
                if res.move is None:
                    break
                board.push(res.move)
                node = node.add_variation(res.move)

            result = _result_str(board)
            if result == "*":
                # Keep downstream stats stable when a plies cap is reached.
                result = "1/2-1/2"
                game.headers["Termination"] = "MAX_PLIES_ADJUDICATED_DRAW"
            else:
                outcome = board.outcome(claim_draw=True)
                if outcome:
                    game.headers["Termination"] = outcome.termination.name
            game.headers["Result"] = result
            pgn_file.write(str(game))
            pgn_file.write("\n\n")
            log_file.write(f"game={game_idx} result={result} plies={board.ply()}\n")

    return _ChunkResult(
        worker_idx=worker_idx,
        games_written=games,
        pgn_path=output_pgn,
        log_path=output_log,
    )


def _chunk_sizes(total_games: int, workers: int) -> list[int]:
    base = total_games // workers
    remainder = total_games % workers
    return [base + (1 if idx < remainder else 0) for idx in range(workers)]


def _merge_files(parts: list[Path], target: Path) -> None:
    ensure_dir(target.parent)
    with target.open("w", encoding="utf-8") as out:
        for part in parts:
            text = part.read_text(encoding="utf-8")
            if not text:
                continue
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")


def run_selfplay_matches(cfg: MatchConfig) -> Path:
    if not cfg.engine.path.exists():
        raise MatchError(f"Engine binary not found: {cfg.engine.path}")
    if cfg.games <= 0:
        raise MatchError("games must be > 0")

    ensure_dir(cfg.output_pgn.parent)
    ensure_dir(cfg.output_log.parent)

    host = detect_host_resources()
    workers = recommend_parallel_games(
        games=cfg.games,
        engine_threads=cfg.engine.threads,
        hash_mb=cfg.engine.hash_mb,
        requested_parallel_games=cfg.parallel_games,
        host=host,
    )

    if workers <= 1:
        _run_match_chunk(
            cfg=cfg,
            games=cfg.games,
            round_start=1,
            worker_idx=1,
            worker_seed=cfg.seed,
            output_pgn=cfg.output_pgn,
            output_log=cfg.output_log,
        )
        return cfg.output_pgn

    sizes = _chunk_sizes(cfg.games, workers)
    round_cursor = 1
    futures = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for worker_idx, games_in_chunk in enumerate(sizes, start=1):
            if games_in_chunk <= 0:
                continue
            pgn_part = Path(f"{cfg.output_pgn}.part{worker_idx}")
            log_part = Path(f"{cfg.output_log}.part{worker_idx}")
            worker_seed = cfg.seed + (worker_idx * 1_000_003)
            futures.append(
                pool.submit(
                    _run_match_chunk,
                    cfg,
                    games_in_chunk,
                    round_cursor,
                    worker_idx,
                    worker_seed,
                    pgn_part,
                    log_part,
                )
            )
            round_cursor += games_in_chunk

        results: list[_ChunkResult] = []
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item.worker_idx)

    _merge_files([res.pgn_path for res in results], cfg.output_pgn)
    _merge_files([res.log_path for res in results], cfg.output_log)

    with cfg.output_log.open("a", encoding="utf-8") as log_file:
        log_file.write(
            "summary "
            f"workers={workers} logical_cpus={host.logical_cpus} "
            f"memory_mb={host.total_memory_mb} games={cfg.games}\n"
        )

    for res in results:
        res.pgn_path.unlink(missing_ok=True)
        res.log_path.unlink(missing_ok=True)

    return cfg.output_pgn


def maybe_run_fastchess(_config_path: Path) -> None:
    # Placeholder for future fastchess integration.
    return None
