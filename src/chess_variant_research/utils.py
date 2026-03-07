from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def utc_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_table(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
