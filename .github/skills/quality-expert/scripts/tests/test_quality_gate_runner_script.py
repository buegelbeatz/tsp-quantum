"""Unit tests for quality-gate-runner.sh container mount and path safety."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Locate repository root by searching for .github/skills marker."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "quality-expert"
    / "scripts"
    / "quality-gate-runner.sh"
)


def test_quality_gate_runner_uses_rw_workspace_mount() -> None:
    """Ensure the container mount keeps repo workspace writable."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"-v" "$repo_root:$work_dir:rw"' in content


def test_quality_gate_runner_avoids_host_workspace_absolute_mkdir() -> None:
    """Ensure host-side mkdir uses repository path and not absolute /workspace."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert (
        'mkdir -p "${coverage_file%/*}" "$repo_root/.tests/python/reports"' in content
    )
    assert (
        'mkdir -p "${coverage_file%/*}" "${work_dir}/.tests/python/reports"'
        not in content
    )


def test_quality_gate_runner_maps_coverage_file_into_container_workspace() -> None:
    """Ensure coverage file env var uses the mounted workspace path in containers."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'container_coverage_file="${coverage_file/#$repo_root/$work_dir}"' in content
    assert 'container_opts+=("-e" "COVERAGE_FILE=$container_coverage_file")' in content


def test_quality_gate_runner_sets_human_readable_container_name() -> None:
    """Ensure quality containers get a readable dt-* name prefix."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'container_name="dt-${sanitized_gate}-$$-$(date +%s)"' in content
    assert '"--name" "$container_name"' in content


def test_quality_gate_runner_supports_force_local_override() -> None:
    """Ensure local runtime can be forced to avoid repeated container startup overhead."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'force_local="${QUALITY_GATE_FORCE_LOCAL:-0}"' in content
    assert 'if [[ "$force_local" == "1" ]]; then' in content
