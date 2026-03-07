import chess
import chess.pgn

from chess_variant_research.matches import _pgn_variant_header


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
