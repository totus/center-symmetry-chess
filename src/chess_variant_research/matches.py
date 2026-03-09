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


@dataclass(slots=True)
class _ExistingShard:
    path: Path
    rounds: set[int]


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


def _shard_paths(target: Path) -> list[Path]:
    pattern = f"{target.name}.part*"
    return sorted(target.parent.glob(pattern))


def _parse_round(value: str, path: Path) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise MatchError(f"Invalid Round header '{value}' in {path}") from exc


def _collect_pgn_games(path: Path) -> dict[int, str]:
    games: dict[int, str] = {}
    if not path.exists() or path.stat().st_size == 0:
        return games

    with path.open("r", encoding="utf-8") as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            round_value = game.headers.get("Round")
            if round_value is None:
                raise MatchError(f"Missing Round header in {path}")
            round_number = _parse_round(round_value, path)
            if round_number in games:
                continue
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            games[round_number] = game.accept(exporter).strip() + "\n\n"

    return games


def _existing_pgn_shards(cfg: MatchConfig) -> list[_ExistingShard]:
    shards: list[_ExistingShard] = []
    candidates = [cfg.output_pgn, *_shard_paths(cfg.output_pgn)]
    for path in candidates:
        rounds = set(_collect_pgn_games(path))
        if rounds:
            shards.append(_ExistingShard(path=path, rounds=rounds))
    return shards


def _missing_rounds(total_games: int, completed_rounds: set[int]) -> list[int]:
    return [
        round_number
        for round_number in range(1, total_games + 1)
        if round_number not in completed_rounds
    ]


def _ranges_from_rounds(rounds: list[int]) -> list[tuple[int, int]]:
    if not rounds:
        return []

    ranges: list[tuple[int, int]] = []
    start = rounds[0]
    prev = rounds[0]
    for round_number in rounds[1:]:
        if round_number == prev + 1:
            prev = round_number
            continue
        ranges.append((start, prev - start + 1))
        start = round_number
        prev = round_number
    ranges.append((start, prev - start + 1))
    return ranges


def _plan_missing_chunks(missing_rounds: list[int], workers: int) -> list[tuple[int, int]]:
    ranges = _ranges_from_rounds(missing_rounds)
    if not ranges:
        return []

    # Preserve gaps from resumed runs, but split long contiguous runs so fresh
    # runs can still use multiple workers.
    while len(ranges) < workers:
        split_idx = -1
        split_len = 1
        for idx, (_, count) in enumerate(ranges):
            if count > split_len:
                split_idx = idx
                split_len = count
        if split_idx < 0:
            break

        start, count = ranges.pop(split_idx)
        left = count // 2
        right = count - left
        ranges.insert(split_idx, (start + left, right))
        ranges.insert(split_idx, (start, left))

    return ranges


def _merge_pgn_shards(target: Path, shards: list[Path]) -> set[int]:
    merged: dict[int, str] = {}
    for shard in shards:
        for round_number, text in _collect_pgn_games(shard).items():
            merged.setdefault(round_number, text)

    ensure_dir(target.parent)
    with target.open("w", encoding="utf-8") as out:
        for round_number in sorted(merged):
            out.write(merged[round_number])

    return set(merged)


def _merge_log_shards(target: Path, shards: list[Path], summary: str | None = None) -> None:
    texts = []
    for shard in shards:
        if not shard.exists() or shard.stat().st_size == 0:
            continue
        texts.append(shard.read_text(encoding="utf-8"))

    ensure_dir(target.parent)
    with target.open("w", encoding="utf-8") as out:
        for text in texts:
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")
        if summary:
            out.write(summary)
            if not summary.endswith("\n"):
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

    existing_pgn_shards = _existing_pgn_shards(cfg)
    completed_rounds = {
        round_number for shard in existing_pgn_shards for round_number in shard.rounds
    }
    missing_rounds = _missing_rounds(cfg.games, completed_rounds)

    if not missing_rounds:
        merged_rounds = _merge_pgn_shards(
            cfg.output_pgn, [cfg.output_pgn, *_shard_paths(cfg.output_pgn)]
        )
        if len(merged_rounds) != cfg.games:
            raise MatchError(
                f"Expected {cfg.games} merged games in {cfg.output_pgn}, found {len(merged_rounds)}"
            )
        _merge_log_shards(
            cfg.output_log,
            [cfg.output_log, *_shard_paths(cfg.output_log)],
            summary=(
                "summary "
                f"workers=0 logical_cpus={host.logical_cpus} "
                f"memory_mb={host.total_memory_mb} games={cfg.games} resumed=true"
            ),
        )
        for part in _shard_paths(cfg.output_pgn):
            part.unlink(missing_ok=True)
        for part in _shard_paths(cfg.output_log):
            part.unlink(missing_ok=True)
        return cfg.output_pgn

    missing_ranges = _plan_missing_chunks(missing_rounds, workers)
    worker_count = min(workers, len(missing_ranges))
    futures = []
    if worker_count == 1:
        results = []
        for worker_idx, (round_start, games_in_chunk) in enumerate(missing_ranges, start=1):
            pgn_part = Path(f"{cfg.output_pgn}.resume{worker_idx}")
            log_part = Path(f"{cfg.output_log}.resume{worker_idx}")
            worker_seed = cfg.seed + (worker_idx * 1_000_003)
            results.append(
                _run_match_chunk(
                    cfg,
                    games_in_chunk,
                    round_start,
                    worker_idx,
                    worker_seed,
                    pgn_part,
                    log_part,
                )
            )
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as pool:
            for worker_idx, (round_start, games_in_chunk) in enumerate(missing_ranges, start=1):
                pgn_part = Path(f"{cfg.output_pgn}.resume{worker_idx}")
                log_part = Path(f"{cfg.output_log}.resume{worker_idx}")
                worker_seed = cfg.seed + (worker_idx * 1_000_003)
                futures.append(
                    pool.submit(
                        _run_match_chunk,
                        cfg,
                        games_in_chunk,
                        round_start,
                        worker_idx,
                        worker_seed,
                        pgn_part,
                        log_part,
                    )
                )

            results = []
            for future in as_completed(futures):
                results.append(future.result())

    results.sort(key=lambda item: item.worker_idx)

    merged_rounds = _merge_pgn_shards(
        cfg.output_pgn,
        [cfg.output_pgn, *_shard_paths(cfg.output_pgn), *[res.pgn_path for res in results]],
    )
    if len(merged_rounds) != cfg.games:
        raise MatchError(
            f"Expected {cfg.games} merged games in {cfg.output_pgn}, found {len(merged_rounds)}"
        )
    _merge_log_shards(
        cfg.output_log,
        [cfg.output_log, *_shard_paths(cfg.output_log), *[res.log_path for res in results]],
        summary=(
            "summary "
            f"workers={worker_count} logical_cpus={host.logical_cpus} "
            f"memory_mb={host.total_memory_mb} games={cfg.games} resumed=true"
        ),
    )

    for res in results:
        res.pgn_path.unlink(missing_ok=True)
        res.log_path.unlink(missing_ok=True)
    for part in _shard_paths(cfg.output_pgn):
        part.unlink(missing_ok=True)
    for part in _shard_paths(cfg.output_log):
        part.unlink(missing_ok=True)

    return cfg.output_pgn


def maybe_run_fastchess(_config_path: Path) -> None:
    # Placeholder for future fastchess integration.
    return None
