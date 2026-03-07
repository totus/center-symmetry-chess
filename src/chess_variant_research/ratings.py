from __future__ import annotations

import math

import pandas as pd
from scipy.stats import norm

from .metrics import add_score_columns


def score_to_elo(score: float) -> float:
    eps = 1e-9
    s = min(max(score, eps), 1 - eps)
    return -400.0 * math.log10((1.0 / s) - 1.0)


def elo_ci_from_scores(scores: pd.Series, alpha: float = 0.05) -> tuple[float, float]:
    n = len(scores)
    if n == 0:
        return float("nan"), float("nan")
    mean = float(scores.mean())
    std = float(scores.std(ddof=1)) if n > 1 else 0.0
    z = norm.ppf(1 - alpha / 2)
    se = std / math.sqrt(n) if n > 1 else 0.0
    lo_s = max(1e-9, mean - z * se)
    hi_s = min(1 - 1e-9, mean + z * se)
    return score_to_elo(lo_s), score_to_elo(hi_s)


def estimate_elo_by_variant(df: pd.DataFrame) -> pd.DataFrame:
    data = add_score_columns(df)
    rows: list[dict[str, float | str | int]] = []
    for variant, g in data.groupby("variant", dropna=False):
        scores = g["white_score"].dropna()
        if len(scores) == 0:
            rows.append(
                {
                    "variant": str(variant),
                    "games": int(len(g)),
                    "score": float("nan"),
                    "elo_diff": float("nan"),
                    "elo_ci_low": float("nan"),
                    "elo_ci_high": float("nan"),
                    "likelihood_superiority": float("nan"),
                }
            )
            continue
        score = float(scores.mean())
        elo = score_to_elo(score)
        ci_lo, ci_hi = elo_ci_from_scores(scores)
        los = float((scores > 0.5).mean())
        rows.append(
            {
                "variant": str(variant),
                "games": int(len(g)),
                "score": score,
                "elo_diff": elo,
                "elo_ci_low": ci_lo,
                "elo_ci_high": ci_hi,
                "likelihood_superiority": los,
            }
        )
    return pd.DataFrame(rows)
