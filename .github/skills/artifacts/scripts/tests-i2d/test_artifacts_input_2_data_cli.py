"""Unit tests for artifacts_input_2_data CLI entrypoint."""

from __future__ import annotations

from importlib import import_module
import sys
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

artifacts_input_2_data = import_module("artifacts_input_2_data")


def test_main_writes_audit_for_no_input_run(tmp_path: Path) -> None:
    """No-op ingest runs should still create a traceable audit entry."""
    repo_root = tmp_path
    (repo_root / ".digital-artifacts" / "00-input").mkdir(parents=True)

    result = artifacts_input_2_data.main(
        ["--repo-root", str(repo_root), "--date", "2025-07-01"]
    )

    audit_file = (
        repo_root
        / ".digital-artifacts"
        / "70-audits"
        / "2025-07-01"
        / "00000-artifacts-input-2-data.md"
    )
    assert result == 0
    assert audit_file.exists()

    content = audit_file.read_text(encoding="utf-8")
    assert "No input files were discovered" in content
    assert "- processed: 0" in content
    assert "- skipped: 0" in content
    assert "- failed: 0" in content
