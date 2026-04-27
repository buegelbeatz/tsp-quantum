from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "runtime" / "runtime-gc.sh"


def _run_gc(repo_root: Path, mode: str = "dry-run") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            "--repo-root",
            str(repo_root),
            "--mode",
            mode,
            "--short-ttl-days",
            "7",
            "--medium-ttl-days",
            "30",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _set_old_mtime(path: Path, seconds_old: int = 10 * 86400) -> None:
    now = int(Path(__file__).stat().st_mtime)
    old = now - seconds_old
    os.utime(path, (old, old))


def test_runtime_gc_dry_run_reports_candidate_without_deletion(tmp_path: Path) -> None:
    runtime_tmp = tmp_path / ".digital-runtime" / "tmp"
    runtime_tmp.mkdir(parents=True)
    stale_file = runtime_tmp / "old.txt"
    stale_file.write_text("stale", encoding="utf-8")
    _set_old_mtime(stale_file)

    result = _run_gc(tmp_path, mode="dry-run")

    assert "status: ok" in result.stdout
    assert "mode: dry-run" in result.stdout
    assert "candidate_count: 1" in result.stdout
    assert stale_file.exists()


def test_runtime_gc_apply_deletes_candidate(tmp_path: Path) -> None:
    runtime_tmp = tmp_path / ".digital-runtime" / "tmp"
    runtime_tmp.mkdir(parents=True)
    stale_file = runtime_tmp / "old.txt"
    stale_file.write_text("stale", encoding="utf-8")
    _set_old_mtime(stale_file)

    result = _run_gc(tmp_path, mode="apply")

    assert "status: ok" in result.stdout
    assert "mode: apply" in result.stdout
    assert "removed_count: 1" in result.stdout
    assert not stale_file.exists()
