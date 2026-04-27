from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT = ROOT / ".github" / "skills" / "shared" / "shell" / "scripts" / "guard-direct-tool-calls.py"
ALLOWLIST = ROOT / ".github" / "skills" / "shared" / "shell" / "scripts" / "metadata" / "direct-tool-allowlist.txt"


def test_direct_tool_guard_passes_for_repository_state() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo-root", str(ROOT), "--allowlist", str(ALLOWLIST)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "guard passed" in result.stdout.lower()


def test_direct_tool_guard_flags_unallowlisted_call(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    script_dir = repo_root / ".github" / "scripts"
    script_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (script_dir / "demo.sh").write_text("#!/usr/bin/env bash\npython3 demo.py\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True, text=True)

    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo-root", str(repo_root), "--allowlist", str(allowlist)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert ".github/scripts/demo.sh:2: direct python3 invocation" in result.stderr