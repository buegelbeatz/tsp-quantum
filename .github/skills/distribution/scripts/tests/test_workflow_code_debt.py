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


def test_summarize_top_tracked_files_orders_by_net_lines(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    file_small = repo / ".github/skills/artifacts/scripts/artifacts_flow_small.py"
    file_large = repo / ".github/skills/artifacts/scripts/artifacts_flow_large.py"
    file_small.parent.mkdir(parents=True, exist_ok=True)
    file_small.write_text("a = 1\n", encoding="utf-8")
    file_large.write_text("a = 1\nb = 2\nif a:\n    pass\n", encoding="utf-8")

    module = _load_module(Path(__file__).resolve().parents[1] / "workflow_code_debt.py")
    top = module.summarize_top_tracked_files(repo, limit=2)

    assert len(top) == 2
    assert top[0][0].endswith("artifacts_flow_large.py")
    assert top[0][1] >= top[1][1]


def test_load_targets_reads_csv_contract(tmp_path: Path) -> None:
    targets_file = tmp_path / "workflow_code_debt_targets.csv"
    targets_file.write_text(
        "path,target_lines,due\n"
        ".github/skills/artifacts/scripts/artifacts_flow.py,1500,2026-06-01\n",
        encoding="utf-8",
    )

    module = _load_module(Path(__file__).resolve().parents[1] / "workflow_code_debt.py")
    targets = module.load_targets(targets_file)

    assert targets[".github/skills/artifacts/scripts/artifacts_flow.py"] == (1500, "2026-06-01")


def test_write_report_includes_target_kpis_and_table(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tracked_a = repo / ".github/skills/artifacts/scripts/artifacts_flow.py"
    tracked_b = repo / ".github/skills/stages-action/scripts/stages-action.sh"
    tracked_a.parent.mkdir(parents=True, exist_ok=True)
    tracked_b.parent.mkdir(parents=True, exist_ok=True)
    tracked_a.write_text("\n".join(["a = 1"] * 80) + "\n", encoding="utf-8")
    tracked_b.write_text("\n".join(["b = 1"] * 40) + "\n", encoding="utf-8")

    targets_file = tmp_path / "workflow_code_debt_targets.csv"
    targets_file.write_text(
        "path,target_lines,due\n"
        ".github/skills/artifacts/scripts/artifacts_flow.py,75,2020-06-01\n"
        ".github/skills/stages-action/scripts/stages-action.sh,50,2026-06-01\n",
        encoding="utf-8",
    )

    history = tmp_path / "history.csv"
    history.write_text(
        "timestamp,file_count,total_decision_lines,repo_root\n"
        "2026-04-19T00:00:00+00:00,2,110,/tmp/repo\n",
        encoding="utf-8",
    )

    report = tmp_path / "latest.md"
    module = _load_module(Path(__file__).resolve().parents[1] / "workflow_code_debt.py")

    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "workflow_code_debt.py",
            "--repo-root",
            str(repo),
            "--history-path",
            str(history),
            "--report-path",
            str(report),
            "--targets-path",
            str(targets_file),
        ]
        assert module.main() == 0
    finally:
        sys.argv = old_argv

    content = report.read_text(encoding="utf-8")

    assert "- targeted_top_files: 2" in content
    assert "- over_target_top_files: 1" in content
    assert "| file | net_lines | target_lines | remaining_to_target | due |" in content
    assert "| .github/skills/artifacts/scripts/artifacts_flow.py | 80 | 75 | 5 | 2020-06-01 |" in content
