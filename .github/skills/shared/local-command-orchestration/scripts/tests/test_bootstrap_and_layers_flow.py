from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "update.sh").exists() and (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
INSTALL_SCRIPT = ROOT / "install.sh"
EXTEND_SCRIPT = ROOT / "extend.sh"
LAYERS_TREE_SCRIPT = ROOT / ".github" / "skills" / "layers" / "scripts" / "layers-tree.py"


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_install_script_supports_skip_initial_update_for_app_bootstrap(tmp_path: Path) -> None:
    """install.sh should support DIGITAL_SKIP_INITIAL_UPDATE and still scaffold app bootstrap files."""
    app_target = tmp_path / "app-repo"
    app_target.mkdir(parents=True)

    source_path = str(ROOT)
    expected_layer_name = Path(source_path).name

    result = _run(
        ["/bin/bash", str(INSTALL_SCRIPT), str(app_target)],
        cwd=ROOT,
        env={
            "DIGITAL_LAYER_SOURCE": source_path,
            "DIGITAL_SKIP_INITIAL_UPDATE": "1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "skipped (DIGITAL_SKIP_INITIAL_UPDATE=1)" in result.stdout

    layers_yaml = app_target / ".digital-team" / "layers.yaml"
    assert layers_yaml.exists()
    layers_content = layers_yaml.read_text(encoding="utf-8")
    assert f"- name: {expected_layer_name}" in layers_content
    assert f"source: {source_path}" in layers_content

    assert (app_target / "update.sh").exists()
    assert not (app_target / "install.sh").exists()
    assert not (app_target / "extend.sh").exists()


def test_extend_script_supports_skip_initial_update_for_layer_bootstrap(tmp_path: Path) -> None:
    """extend.sh should support DIGITAL_SKIP_INITIAL_UPDATE and scaffold extendable layer files."""
    layer_target = tmp_path / "layer-repo"
    layer_target.mkdir(parents=True)

    source_path = str(ROOT)
    expected_layer_name = Path(source_path).name

    result = _run(
        ["/bin/bash", str(EXTEND_SCRIPT), str(layer_target)],
        cwd=ROOT,
        env={
            "DIGITAL_LAYER_SOURCE": source_path,
            "DIGITAL_SKIP_INITIAL_UPDATE": "1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "skipped (DIGITAL_SKIP_INITIAL_UPDATE=1)" in result.stdout

    layers_yaml = layer_target / ".digital-team" / "layers.yaml"
    assert layers_yaml.exists()
    layers_content = layers_yaml.read_text(encoding="utf-8")
    assert f"- name: {expected_layer_name}" in layers_content
    assert f"source: {source_path}" in layers_content

    assert (layer_target / "update.sh").exists()
    assert (layer_target / "install.sh").exists()
    assert (layer_target / "extend.sh").exists()


def test_layers_tree_keeps_parent_files_at_l0_when_origin_points_to_parent(tmp_path: Path) -> None:
    """layers-tree should not misclassify inherited parent files as current layer when origin still points to parent."""
    repo_dir = tmp_path / "child-layer"
    (repo_dir / ".digital-team").mkdir(parents=True)
    (repo_dir / ".github" / "agents").mkdir(parents=True)

    (repo_dir / ".digital-team" / "layers.yaml").write_text(
        "layers:\n  - name: digital-generic-team\n    source: /tmp/digital-generic-team\n",
        encoding="utf-8",
    )
    (repo_dir / ".github" / "agents" / "agile-coach.agent.md").write_text(
        "---\nname: agile-coach\nlayer: digital-generic-team\n---\n",
        encoding="utf-8",
    )

    _run(["git", "init"], cwd=repo_dir)
    _run(
        ["git", "remote", "add", "origin", "https://github.com/example/digital-generic-team.git"],
        cwd=repo_dir,
    )

    render = _run(
        [sys.executable, str(LAYERS_TREE_SCRIPT), "--mode", "full", str(repo_dir)],
        cwd=ROOT,
    )

    assert render.returncode == 0, render.stderr
    ansi_free = re.sub(r"\x1b\[[0-9;]*m", "", render.stdout)
    assert re.search(r"\[L0\].*agile-coach\.agent\.md", ansi_free)
