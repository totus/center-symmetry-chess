from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import chess
import chess.engine
import pandas as pd

from .fen import board_for_variant, chess960_for_variant, get_start_fen
from .schemas import EngineConfig, ProbeConfig
from .utils import ensure_dir, utc_ts, write_table


class EngineError(RuntimeError):
    pass


def require_engine_binary(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise EngineError(f"Engine binary not found: {path}")


def _configure(engine: chess.engine.SimpleEngine, cfg: EngineConfig) -> None:
    opts: dict[str, Any] = {"Threads": cfg.threads, "Hash": cfg.hash_mb}
    if cfg.extra_options:
        opts.update(cfg.extra_options)
    try:
        engine.configure(opts)
    except chess.engine.EngineError:
        pass


def probe_position(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    depth: int | None,
    movetime_ms: int | None,
    multipv: int,
) -> list[dict[str, Any]]:
    limit = chess.engine.Limit(depth=depth, time=(movetime_ms / 1000 if movetime_ms else None))
    result = engine.analyse(board, limit=limit, multipv=multipv)
    rows: list[dict[str, Any]] = []
    seq = result if isinstance(result, list) else [result]
    for idx, info in enumerate(seq, start=1):
        score = info.get("score")
        row: dict[str, Any] = {
            "multipv_rank": idx,
            "pv": " ".join(m.uci() for m in info.get("pv", [])),
            "depth": info.get("depth"),
            "seldepth": info.get("seldepth"),
            "nodes": info.get("nodes"),
            "nps": info.get("nps"),
            "time": info.get("time"),
            "hashfull": info.get("hashfull"),
        }
        if score:
            s = score.white()
            row["score_cp"] = s.score(mate_score=100000)
            row["score_mate"] = s.mate()
        if "wdl" in info:
            wdl = info["wdl"].white()
            row["wdl_w"] = wdl.wins
            row["wdl_d"] = wdl.draws
            row["wdl_l"] = wdl.losses
        rows.append(row)
    return rows


def run_root_probe(cfg: ProbeConfig) -> pd.DataFrame:
    require_engine_binary(cfg.engine.path)
    positions = cfg.positions or [get_start_fen(cfg.variant)]
    records: list[dict[str, Any]] = []
    with chess.engine.SimpleEngine.popen_uci(str(cfg.engine.path)) as engine:
        _configure(engine, cfg.engine)
        for fen in positions:
            board = board_for_variant(cfg.variant, fen)
            for row in probe_position(engine, board, cfg.depth, cfg.movetime_ms, cfg.multipv):
                row.update(
                    {
                        "timestamp": utc_ts(),
                        "variant": cfg.variant,
                        "fen": fen,
                        "chess960": chess960_for_variant(cfg.variant),
                        "engine_name": cfg.engine.name,
                        "engine_path": str(cfg.engine.path),
                    }
                )
                records.append(row)
    df = pd.DataFrame.from_records(records)
    write_table(df, cfg.output_csv)
    return df


def describe_engine(cfg: EngineConfig) -> dict[str, Any]:
    return asdict(cfg)


def write_probe_log(path: Path, message: str) -> None:
    ensure_dir(path.parent)
    path.write_text(message, encoding="utf-8")
