from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("workflow_code_debt", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow_code_debt"] = module
    spec.loader.exec_module(module)
    return module


def test_scan_snapshot_counts_only_tracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tracked = repo / ".github/skills/artifacts/scripts/artifacts_flow_alpha.py"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("a = 1\n# comment\n\nif a:\n    pass\n", encoding="utf-8")

    ignored_test = repo / ".github/skills/artifacts/scripts/tests/test_artifacts_flow_alpha.py"
    ignored_test.parent.mkdir(parents=True, exist_ok=True)
    ignored_test.write_text("print('x')\n", encoding="utf-8")

    module = _load_module(
        Path(__file__).resolve().parents[1] / "workflow_code_debt.py",
    )
    snapshot = module.scan_snapshot(repo)

    assert snapshot.file_count == 1
    assert snapshot.total_decision_lines == 3


def test_monotonic_check_detects_regression(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tracked = repo / ".github/skills/artifacts/scripts/artifacts_flow_beta.py"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("x = 1\n", encoding="utf-8")

    history = repo / ".digital-artifacts/70-audits/workflow-code-debt/history.csv"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(
        "timestamp,file_count,total_decision_lines,repo_root\n"
        "2026-04-19T00:00:00+00:00,1,0,/tmp/repo\n",
        encoding="utf-8",
    )

    module = _load_module(
        Path(__file__).resolve().parents[1] / "workflow_code_debt.py",
    )
    snapshot = module.scan_snapshot(repo)
    previous = module.read_previous_total(history)

    assert previous == 0
    assert snapshot.total_decision_lines > previous
