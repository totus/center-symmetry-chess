from __future__ import annotations

import random
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from .fen import board_for_variant, get_start_fen
from .schemas import MatchConfig
from .utils import ensure_dir, utc_ts


class MatchError(RuntimeError):
    pass


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


def run_selfplay_matches(cfg: MatchConfig) -> Path:
    if not cfg.engine.path.exists():
        raise MatchError(f"Engine binary not found: {cfg.engine.path}")

    ensure_dir(cfg.output_pgn.parent)
    ensure_dir(cfg.output_log.parent)

    base, inc = _parse_tc(cfg.tc)
    rng = random.Random(cfg.seed)
    start_fen = get_start_fen(cfg.variant)

    with (
        chess.engine.SimpleEngine.popen_uci(str(cfg.engine.path)) as engine,
        cfg.output_pgn.open("w", encoding="utf-8") as pgn_file,
        cfg.output_log.open("w", encoding="utf-8") as log_file,
    ):
        try:
            engine.configure({"Threads": cfg.engine.threads, "Hash": cfg.engine.hash_mb})
        except chess.engine.EngineError:
            pass

        for game_idx in range(1, cfg.games + 1):
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

    return cfg.output_pgn


def maybe_run_fastchess(_config_path: Path) -> None:
    # Placeholder for future fastchess integration.
    return None
