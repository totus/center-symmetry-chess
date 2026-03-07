from pathlib import Path

from chess_variant_research.parsing import parse_pgn_file


def test_parse_single_game(tmp_path: Path) -> None:
    pgn = tmp_path / "g.pgn"
    pgn.write_text(
        '[Event "x"]\n[Site "local"]\n[Date "2026.03.07"]\n[Round "1"]\n'
        '[White "E"]\n[Black "E"]\n[Result "1-0"]\n[Variant "Chess960"]\n'
        '[ResearchVariant "swapped_white"]\n'
        '[SetUp "1"]\n[FEN "8/8/8/8/8/8/8/R2K3R w KQ - 0 1"]\n'
        '1. O-O 1-0\n',
        encoding="utf-8",
    )
    df = parse_pgn_file(pgn)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["variant"] == "swapped_white"
    assert row["opening_family"] == "other"
    assert row["white_castling_side"] == "kingside"
