from __future__ import annotations

from pathlib import Path

import chess.pgn
import pytest

from chess_variant_research.parsing import (
    ParseError,
    _opening_family,
    _variant_from_headers,
    initial_board_from_game,
    parse_pgn_file,
    parse_pgn_paths,
)


def test_opening_family_none_and_other() -> None:
    assert _opening_family(None) == "other"
    assert _opening_family("a2a3") == "other"


def test_initial_board_from_unknown_variant_fallback() -> None:
    game = chess.pgn.Game()
    game.headers["Variant"] = "unsupported_variant"
    board = initial_board_from_game(game)
    assert board.fen().startswith("rnbqkbnr")


def test_variant_from_headers_branches() -> None:
    game = chess.pgn.Game()
    game.headers["ResearchVariant"] = "swapped_white"
    assert _variant_from_headers(game, "") == "swapped_white"

    game2 = chess.pgn.Game()
    game2.headers["Variant"] = "custom_variant"
    assert _variant_from_headers(game2, "") == "custom_variant"

    game3 = chess.pgn.Game()
    game3.headers["Variant"] = "Chess960"
    assert _variant_from_headers(
        game3, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR w KQkq - 0 1"
    ) == "swapped_white"

    game4 = chess.pgn.Game()
    assert _variant_from_headers(game4, "8/8/8/8/8/8/8/8 w - - 0 1") == "unknown"


def test_parse_pgn_file_no_games(tmp_path: Path) -> None:
    p = tmp_path / "empty.pgn"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_pgn_file(p)


def test_parse_pgn_paths_no_paths() -> None:
    with pytest.raises(ParseError):
        parse_pgn_paths([])


def test_parse_pgn_paths_all_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.pgn"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_pgn_paths([p])


def test_parse_rights_lost_and_black_castling(tmp_path: Path) -> None:
    p1 = tmp_path / "g1.pgn"
    p1.write_text(
        '[Event "x"]\n[Site "local"]\n[Date "2026.03.07"]\n[Round "1"]\n'
        '[White "E"]\n[Black "E"]\n[Result "1/2-1/2"]\n[Variant "Chess960"]\n'
        '[SetUp "1"]\n[FEN "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"]\n'
        '1. Ke2 Ke7 2. Rh3 Rh6 1/2-1/2\n',
        encoding="utf-8",
    )
    d1 = parse_pgn_file(p1).iloc[0]
    assert d1["white_rights_lost_before_castling"]
    assert d1["black_rights_lost_before_castling"]

    p2 = tmp_path / "g2.pgn"
    p2.write_text(
        '[Event "x"]\n[Site "local"]\n[Date "2026.03.07"]\n[Round "1"]\n'
        '[White "E"]\n[Black "E"]\n[Result "1/2-1/2"]\n[Variant "Chess960"]\n'
        '[SetUp "1"]\n[FEN "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"]\n'
        '1. Ra2 O-O 1/2-1/2\n',
        encoding="utf-8",
    )
    d2 = parse_pgn_file(p2).iloc[0]
    assert d2["black_castling_side"] == "kingside"


def test_parse_central_files_opened_early(tmp_path: Path) -> None:
    p = tmp_path / "central.pgn"
    p.write_text(
        '[Event "x"]\n[Site "local"]\n[Date "2026.03.07"]\n[Round "1"]\n'
        '[White "E"]\n[Black "E"]\n[Result "1/2-1/2"]\n'
        "1. e4 e5 1/2-1/2\n",
        encoding="utf-8",
    )
    row = parse_pgn_file(p).iloc[0]
    assert row["central_files_opened_early"]
