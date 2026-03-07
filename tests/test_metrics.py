import pandas as pd

from chess_variant_research.metrics import summarize_games


def test_metrics_summary() -> None:
    df = pd.DataFrame(
        [
            {
                "game_id": "1",
                "variant": "swapped_white",
                "result": "1-0",
                "white_castling_side": "kingside",
                "black_castling_side": "none",
                "white_castling_move": 8,
                "black_castling_move": None,
                "move_count": 40,
            },
            {
                "game_id": "2",
                "variant": "swapped_white",
                "result": "1/2-1/2",
                "white_castling_side": "none",
                "black_castling_side": "queenside",
                "white_castling_move": None,
                "black_castling_move": 12,
                "move_count": 60,
            },
        ]
    )
    out = summarize_games(df)
    assert len(out) == 1
    assert out.iloc[0]["games"] == 2
    assert out.iloc[0]["white_win_rate"] == 0.5
