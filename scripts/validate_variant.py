#!/usr/bin/env python3
from __future__ import annotations

import argparse

import chess

from chess_variant_research.config import parse_variant
from chess_variant_research.fen import board_for_variant, get_start_fen


def _validate_castling_destinations(variant: str) -> None:
    if variant == "orthodox":
        return

    # White castling destination tests
    b = chess.Board("8/8/8/8/8/8/8/R2K3R w KQ - 0 1", chess960=True)
    ks = chess.Move.from_uci("d1h1")
    qs = chess.Move.from_uci("d1a1")
    if ks not in b.legal_moves or qs not in b.legal_moves:
        raise RuntimeError("Expected castling moves not legal in swapped setup")

    b1 = b.copy()
    b1.push(ks)
    if (
        b1.king(chess.WHITE) != chess.G1
        or b1.piece_at(chess.F1) != chess.Piece(chess.ROOK, chess.WHITE)
    ):
        raise RuntimeError("White O-O landing squares incorrect")

    b2 = b.copy()
    b2.push(qs)
    if (
        b2.king(chess.WHITE) != chess.C1
        or b2.piece_at(chess.D1) != chess.Piece(chess.ROOK, chess.WHITE)
    ):
        raise RuntimeError("White O-O-O landing squares incorrect")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="swapped_white")
    args = parser.parse_args()

    variant = parse_variant(args.variant)
    fen = get_start_fen(variant)
    board = board_for_variant(variant, fen)
    legal_count = board.legal_moves.count()
    if legal_count <= 0:
        raise RuntimeError("No legal moves from starting position")

    _validate_castling_destinations(variant)
    print(f"OK variant={variant} legal_moves={legal_count} fen={fen}")


if __name__ == "__main__":
    main()
