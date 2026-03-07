from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chess
import chess.pgn
import pandas as pd


class ParseError(ValueError):
    pass


@dataclass(slots=True)
class CastleInfo:
    side: str
    move_number: int | None
    rights_lost_before_castling: bool


def _opening_family(first_white_move: str | None) -> str:
    mapping = {
        "e2e4": "e4",
        "d2d4": "d4",
        "g1f3": "Nf3",
        "c2c4": "c4",
        "g2g3": "g3",
    }
    if first_white_move is None:
        return "other"
    return mapping.get(first_white_move, "other")


def _extract_castling_info(game: chess.pgn.Game) -> tuple[CastleInfo, CastleInfo, bool]:
    board = initial_board_from_game(game)
    white_castle: CastleInfo = CastleInfo("none", None, False)
    black_castle: CastleInfo = CastleInfo("none", None, False)
    white_rights_lost = False
    black_rights_lost = False
    central_opened_early = False

    for ply_idx, move in enumerate(game.mainline_moves(), start=1):
        turn = board.turn
        was_castling = board.is_castling(move)
        white_rights_gone = not board.has_kingside_castling_rights(
            chess.WHITE
        ) and not board.has_queenside_castling_rights(chess.WHITE)
        black_rights_gone = not board.has_kingside_castling_rights(
            chess.BLACK
        ) and not board.has_queenside_castling_rights(chess.BLACK)

        if turn == chess.WHITE and white_rights_gone:
            if white_castle.move_number is None:
                white_rights_lost = True
        if turn == chess.BLACK and black_rights_gone:
            if black_castle.move_number is None:
                black_rights_lost = True

        if ply_idx <= 12 and move.uci() in {
            "e2e4",
            "e2e3",
            "d2d4",
            "d2d3",
            "e7e5",
            "e7e6",
            "d7d5",
            "d7d6",
        }:
            central_opened_early = True

        board.push(move)

        if was_castling:
            mv = (ply_idx + 1) // 2
            if turn == chess.WHITE and white_castle.move_number is None:
                side = "kingside" if board.king(chess.WHITE) == chess.G1 else "queenside"
                white_castle = CastleInfo(side, mv, white_rights_lost)
            if turn == chess.BLACK and black_castle.move_number is None:
                side = "kingside" if board.king(chess.BLACK) == chess.G8 else "queenside"
                black_castle = CastleInfo(side, mv, black_rights_lost)

    if white_castle.move_number is None:
        white_castle = CastleInfo("none", None, white_rights_lost)
    if black_castle.move_number is None:
        black_castle = CastleInfo("none", None, black_rights_lost)
    return white_castle, black_castle, central_opened_early


def initial_board_from_game(game: chess.pgn.Game) -> chess.Board:
    fen = game.headers.get("FEN")
    if fen:
        # Treat non-orthodox starts as Chess960 castling semantics.
        parts = fen.split()
        piece_placement = parts[0] if parts else ""
        white_rank = piece_placement.split("/")[-1] if "/" in piece_placement else ""
        black_rank = piece_placement.split("/")[0] if "/" in piece_placement else ""
        chess960 = white_rank != "RNBQKBNR" or black_rank != "rnbqkbnr"
        return chess.Board(fen=fen, chess960=chess960)
    return game.board()


def parse_game(game: chess.pgn.Game, game_id: str, source: str) -> dict[str, Any]:
    moves = list(game.mainline_moves())
    first_white = moves[0].uci() if moves else None
    white_castle, black_castle, central_opened_early = _extract_castling_info(game)
    init_fen = game.headers.get("FEN") or initial_board_from_game(game).fen()
    row: dict[str, Any] = {
        "game_id": game_id,
        "source": source,
        "variant": game.headers.get("Variant", "unknown"),
        "white_engine": game.headers.get("White", "unknown"),
        "black_engine": game.headers.get("Black", "unknown"),
        "result": game.headers.get("Result", "*"),
        "termination": game.headers.get("Termination", "unknown"),
        "ply_count": len(moves),
        "move_count": (len(moves) + 1) // 2,
        "eco": game.headers.get("ECO", ""),
        "initial_fen": init_fen,
        "white_castling_side": white_castle.side,
        "black_castling_side": black_castle.side,
        "white_castling_move": white_castle.move_number,
        "black_castling_move": black_castle.move_number,
        "white_rights_lost_before_castling": white_castle.rights_lost_before_castling,
        "black_rights_lost_before_castling": black_castle.rights_lost_before_castling,
        "opening_family": _opening_family(first_white),
        "central_files_opened_early": central_opened_early,
    }
    return row


def parse_pgn_file(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        idx = 0
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            idx += 1
            rows.append(parse_game(game, f"{path.stem}-{idx}", path.name))
    if not rows:
        raise ParseError(f"No games found in {path}")
    return pd.DataFrame.from_records(rows)


def parse_pgn_paths(paths: list[Path]) -> pd.DataFrame:
    if not paths:
        raise ParseError("No PGN files provided")
    frames = [parse_pgn_file(p) for p in paths]
    return pd.concat(frames, ignore_index=True)
