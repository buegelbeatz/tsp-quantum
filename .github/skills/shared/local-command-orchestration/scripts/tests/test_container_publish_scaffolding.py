from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "update.sh").exists() and (
            candidate / ".github" / "root-config"
        ).exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()


def test_root_config_contains_container_publish_scaffold() -> None:
    """TODO: add docstring for test_root_config_contains_container_publish_scaffold."""
    scaffold = (
        ROOT / ".github" / "root-config" / ".digital-team" / "container-publish.yaml"
    )
    content = scaffold.read_text(encoding="utf-8")

    assert "version: 1" in content
    assert "enabled: false" in content
    assert "images:" in content
    assert "docs_globs:" in content


def test_root_config_contains_container_publish_workflow() -> None:
    """TODO: add docstring for test_root_config_contains_container_publish_workflow."""
    workflow = (
        ROOT
        / ".github"
        / "root-config"
        / ".github"
        / "workflows"
        / "container-publish.yml"
    )
    content = workflow.read_text(encoding="utf-8")

    assert "docker/build-push-action@v6" in content
    assert "oras-project/setup-oras@v1" in content
    assert "package-docs" in content


def test_root_config_contains_quality_gate_workflow() -> None:
    """Quality gate workflow must enforce KPI and stage completion checks."""
    workflow = (
        ROOT
        / ".github"
        / "root-config"
        / ".github"
        / "workflows"
        / "quality-gates.yml"
    )
    content = workflow.read_text(encoding="utf-8")

    assert "name: quality-gates" in content
    assert "pull_request:" in content
    assert "make workflow-code-debt" in content
    assert "make stage-completion-gate" in content
