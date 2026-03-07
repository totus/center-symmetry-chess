import chess

from chess_variant_research.fen import START_FENS, board_for_variant, validate_fen


def test_start_fens_are_valid() -> None:
    for fen in START_FENS.values():
        validate_fen(fen)


def test_swapped_white_king_position() -> None:
    board = board_for_variant("swapped_white")
    assert board.piece_at(chess.parse_square("d1")).symbol() == "K"
    assert board.piece_at(chess.parse_square("e1")).symbol() == "Q"
