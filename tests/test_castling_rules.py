import chess


def test_swapped_white_castling_destinations() -> None:
    board = chess.Board("8/8/8/8/8/8/8/R2K3R w KQ - 0 1", chess960=True)
    ks = chess.Move.from_uci("d1h1")
    qs = chess.Move.from_uci("d1a1")

    assert ks in board.legal_moves
    assert qs in board.legal_moves

    b1 = board.copy()
    b1.push(ks)
    assert b1.king(chess.WHITE) == chess.G1
    assert b1.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)

    b2 = board.copy()
    b2.push(qs)
    assert b2.king(chess.WHITE) == chess.C1
    assert b2.piece_at(chess.D1) == chess.Piece(chess.ROOK, chess.WHITE)


def test_castling_through_check_disallowed() -> None:
    board = chess.Board("8/8/8/8/8/8/6r1/R2KQ2R w KQ - 0 1", chess960=True)
    assert chess.Move.from_uci("d1h1") not in board.legal_moves
