#!/usr/bin/env python
from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ENGINE_ROOT = Path(__file__).resolve().parents[1]

XI_GRID = (0.0, 0.0019, 0.004)
MODEL_WEIGHT_GRID = (0.35, 0.5, 0.65)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tune Dixon-Coles walk-forward xi and model/market blend weight.",
    )
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--warmup-matches", type=int)
    args = parser.parse_args()

    _ensure_engine_path()
    from app.db.session import SessionLocal
    from app.modeling.walkforward import WALKFORWARD_WARMUP_MATCHES, evaluate_walkforward

    warmup_matches = (
        WALKFORWARD_WARMUP_MATCHES
        if args.warmup_matches is None
        else args.warmup_matches
    )
    rows: list[dict[str, Any]] = []
    with SessionLocal() as session:
        for xi in XI_GRID:
            for model_weight in MODEL_WEIGHT_GRID:
                result = evaluate_walkforward(
                    session,
                    limit=args.limit,
                    warmup_matches=warmup_matches,
                    xi=xi,
                    model_weight=model_weight,
                )
                backtest = result["backtest"]
                rows.append(
                    {
                        "xi": xi,
                        "weight": model_weight,
                        "brier": result["brier"],
                        "log_loss": result["log_loss"],
                        "bets": backtest["bets"],
                        "roi": backtest["roi"],
                        "flat_profit": backtest["flat_profit"],
                    }
                )

    rows.sort(key=lambda row: _metric_sort_key(row["log_loss"]))
    _print_table(rows)
    if rows:
        best = rows[0]
        print()
        print(
            "BEST config: "
            f"xi={best['xi']:.4g}, "
            f"model_weight={best['weight']:.2f}, "
            f"log_loss={_format_metric(best['log_loss'])}, "
            f"brier={_format_metric(best['brier'])}, "
            f"bets={best['bets']}, "
            f"roi={_format_metric(best['roi'])}, "
            f"flat_profit={_format_metric(best['flat_profit'])}"
        )


def _ensure_engine_path() -> None:
    if str(ENGINE_ROOT) not in sys.path:
        sys.path.insert(0, str(ENGINE_ROOT))


def _print_table(rows: Iterable[dict[str, Any]]) -> None:
    headers = ("xi", "weight", "brier", "log_loss", "bets", "roi", "flat_profit")
    rendered_rows = [
        (
            f"{row['xi']:.4g}",
            f"{row['weight']:.2f}",
            _format_metric(row["brier"]),
            _format_metric(row["log_loss"]),
            str(row["bets"]),
            _format_metric(row["roi"]),
            _format_metric(row["flat_profit"]),
        )
        for row in rows
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rendered_rows))
        if rendered_rows
        else len(header)
        for index, header in enumerate(headers)
    ]
    print("  ".join(header.rjust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rendered_rows:
        print("  ".join(value.rjust(widths[index]) for index, value in enumerate(row)))


def _format_metric(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return str(value)


def _metric_sort_key(value: Any) -> float:
    if isinstance(value, int | float) and math.isfinite(float(value)):
        return float(value)
    return math.inf


if __name__ == "__main__":
    main()
