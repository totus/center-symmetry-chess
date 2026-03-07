from __future__ import annotations

from pathlib import Path

import chess

from .schemas import VariantName

START_FENS: dict[VariantName, str] = {
    "orthodox": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "swapped_white": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1",
    "swapped_black": "rnbkqbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "swapped_both": "rnbkqbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1",
}


def get_start_fen(variant: VariantName) -> str:
    try:
        return START_FENS[variant]
    except KeyError as exc:
        raise ValueError(f"Unsupported variant: {variant}") from exc


def chess960_for_variant(variant: VariantName) -> bool:
    return variant != "orthodox"


def validate_fen(fen: str) -> None:
    board = chess.Board(fen=fen, chess960=True)
    board.status()


def board_for_variant(variant: VariantName, fen: str | None = None) -> chess.Board:
    base = fen or get_start_fen(variant)
    validate_fen(base)
    return chess.Board(fen=base, chess960=chess960_for_variant(variant))


def load_fen_file(path: Path) -> str:
    fen = path.read_text(encoding="utf-8").strip()
    validate_fen(fen)
    return fen
