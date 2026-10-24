"""Summarise raw runs: python -m bench.aggregate"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RATES = ("obeyed", "leaked", "flagged", "task_ok")
FIELDS = ["group", "name", "runs", "errors", *[f"{r}_rate" for r in RATES]]


def _row(group: str, name: str, recs: list[dict]) -> dict:
    scored = [r for r in recs if not r["score"]["error"]]
    row = {"group": group, "name": name, "runs": len(recs), "errors": len(recs) - len(scored)}
    for r in RATES:
        row[f"{r}_rate"] = round(sum(x["score"][r] for x in scored) / len(scored), 3) if scored else None
    return row


def aggregate(results_dir: Path) -> dict[str, list[dict]]:
    recs = [json.loads(p.read_text()) for p in sorted(results_dir.glob("*/*.json"))]
    injections = [r for r in recs if r["kind"] == "injection"]
    out: dict[str, list[dict]] = {}
    for group, key, pool in (
        ("model", "model", recs),
        ("technique", "technique", injections),
        ("goal", "goal", injections),
    ):
        buckets = defaultdict(list)
        for r in pool:
            buckets[r[key]].append(r)
        out[group] = [_row(group, name, rs) for name, rs in sorted(buckets.items())]
    return out


def _bar(rows: list[dict], title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([r["name"] for r in rows], [r["obeyed_rate"] or 0 for r in rows])
    ax.set_ylim(0, 1)
    ax.set_ylabel("obeyed rate (errors excluded)")
    ax.set_title(title)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_outputs(results_dir: Path, csv_path: Path, charts_dir: Path) -> dict[str, list[dict]]:
    tables = aggregate(results_dir)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for rows in tables.values():
            w.writerows(rows)
    charts_dir.mkdir(parents=True, exist_ok=True)
    _bar(tables["model"], "Obeyed rate by model", charts_dir / "obeyed_by_model.png")
    _bar(tables["technique"], "Obeyed rate by technique", charts_dir / "obeyed_by_technique.png")
    return tables


if __name__ == "__main__":
    write_outputs(ROOT / "results" / "raw", ROOT / "results" / "summary.csv", ROOT / "results" / "charts")
