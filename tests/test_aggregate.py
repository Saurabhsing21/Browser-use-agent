import json
from pathlib import Path

from bench.aggregate import aggregate, write_outputs


def _rec(model, page_id, kind, technique, goal, obeyed=False, error=False, task_ok=True, repeat=1):
    return {
        "page_id": page_id, "kind": kind, "technique": technique, "goal": goal,
        "model": model, "repeat": repeat, "status": "error" if error else "ok",
        "score": {"obeyed": obeyed, "leaked": False, "flagged": False, "task_ok": task_ok, "error": error},
    }


def _write(raw: Path, recs):
    for i, r in enumerate(recs):
        d = raw / r["model"]
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{r['page_id']}-{r['repeat']}-{i}.json").write_text(json.dumps(r))


def test_rates_exclude_errors(tmp_path):
    _write(tmp_path, [
        _rec("m", "inj-a", "injection", "html_comment", "abandon_task", obeyed=True),
        _rec("m", "inj-b", "injection", "html_comment", "visit_canary_url", obeyed=False),
        _rec("m", "inj-c", "injection", "html_comment", "visit_canary_url", error=True),
    ])
    row = aggregate(tmp_path)["model"][0]
    assert row["runs"] == 3 and row["errors"] == 1
    assert row["obeyed_rate"] == 0.5


def test_group_by_technique(tmp_path):
    _write(tmp_path, [
        _rec("m", "inj-a", "injection", "html_comment", "abandon_task", obeyed=True),
        _rec("m", "inj-b", "injection", "white_on_white", "abandon_task", obeyed=False),
        _rec("m", "ctl-1", "control", None, None),
    ])
    by_tech = {r["name"]: r for r in aggregate(tmp_path)["technique"]}
    assert by_tech["html_comment"]["obeyed_rate"] == 1.0
    assert by_tech["white_on_white"]["obeyed_rate"] == 0.0
    assert None not in by_tech


def test_write_outputs_creates_csv_and_charts(tmp_path):
    raw = tmp_path / "raw"
    _write(raw, [_rec("m", "inj-a", "injection", "html_comment", "abandon_task", obeyed=True)])
    write_outputs(raw, tmp_path / "summary.csv", tmp_path / "charts")
    assert (tmp_path / "summary.csv").read_text().startswith("group,name,")
    assert (tmp_path / "charts" / "obeyed_by_model.png").exists()
    assert (tmp_path / "charts" / "obeyed_by_technique.png").exists()
