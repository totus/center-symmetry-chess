from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from chess_variant_research.utils import ensure_dir, utc_ts, write_table


def test_ensure_dir_and_utc_ts(tmp_path: Path) -> None:
    p = tmp_path / "a" / "b"
    ensure_dir(p)
    assert p.exists()
    assert "T" in utc_ts()


def test_write_table_csv_and_parquet_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    df = pd.DataFrame([{"a": 1}])
    csv_path = tmp_path / "t.csv"
    write_table(df, csv_path)
    assert csv_path.exists()

    called = {"x": False}

    def fake_to_parquet(self: pd.DataFrame, path: Path, index: bool = False) -> None:
        called["x"] = True
        Path(path).write_text("p", encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    pq_path = tmp_path / "t.parquet"
    write_table(df, pq_path)
    assert called["x"]
