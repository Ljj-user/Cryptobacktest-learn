import json
import os
from datetime import datetime, timezone
from typing import Dict

import pandas as pd


def _json_default(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return str(obj)


def create_run_dir(experiments_dir: str, strategy_key: str) -> str:
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{strategy_key}"
    run_dir = os.path.join(experiments_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def save_run_artifacts(
    run_dir: str, config: Dict, stats: Dict, trades: pd.DataFrame, equity_curve: pd.DataFrame
) -> None:
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2, default=_json_default)

    with open(os.path.join(run_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=_json_default)

    trades.to_csv(os.path.join(run_dir, "trades.csv"), index=False)
    equity_curve.to_csv(os.path.join(run_dir, "equity.csv"), index=True)


def append_run_index(experiments_dir: str, row: Dict) -> None:
    os.makedirs(experiments_dir, exist_ok=True)
    index_path = os.path.join(experiments_dir, "runs.jsonl")
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")


def load_recent_runs(experiments_dir: str, strategy: str, limit: int = 5):
    index_path = os.path.join(experiments_dir, "runs.jsonl")
    if not os.path.exists(index_path):
        return []
    rows = []
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("strategy") == strategy:
                rows.append(row)
    rows = rows[-limit:]
    compare = []
    for i, r in enumerate(rows, start=1):
        compare.append(
            {
                "Run": f"{i}",
                "Return [%]": round(float(r.get("Return [%]", 0.0)), 3),
                "Max. Drawdown [%]": round(float(r.get("Max. Drawdown [%]", 0.0)), 3),
                "Win Rate [%]": round(float(r.get("Win Rate [%]", 0.0)), 3),
                "Sharpe Ratio": round(float(r.get("Sharpe Ratio", 0.0)), 3),
                "# Trades": int(r.get("# Trades", 0)),
            }
        )
    return compare
