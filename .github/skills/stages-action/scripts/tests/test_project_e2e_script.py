from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
MAKEFILE_PATH = ROOT / ".github" / "make" / "commands.mk"
PROJECT_E2E_SCRIPT_PATH = (
    ROOT / ".github" / "skills" / "stages-action" / "scripts" / "project-e2e.sh"
)


def test_makefile_wires_project_e2e_target() -> None:
    content = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "project-e2e: preflight" in content
    assert "@bash $(_PROJECT_E2E_SCRIPT)" in content
    assert '--github-test "$${GITHUB_TEST:-0}"' in content


def test_makefile_wires_check_delivery_work_target() -> None:
    content = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "check-delivery-work: preflight" in content
    assert "--prompt-name check-delivery-work" in content
    assert "bash $(_CHECK_DELIVERY_WORK_SCRIPT)" in content


def test_project_e2e_script_uses_temp_clone_isolation() -> None:
    content = PROJECT_E2E_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "create_temp_clone" in content
    assert ".digital-runtime/e2e-project" in content
    assert "DRY_RUN=1" in content
    assert "project-e2e: local temp clone validation passed" in content
    assert "run_github_temp_cycle" in content
    assert "project-e2e-test-" in content
