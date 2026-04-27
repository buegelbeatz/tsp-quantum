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
LIB = (
    ROOT / ".github" / "skills" / "shared/shell" / "scripts" / "lib" / "github-yaml.sh"
)
GITHUB_LIB = (
    ROOT / ".github" / "skills" / "shared/shell" / "scripts" / "lib" / "github.sh"
)


def test_github_json_to_yaml_converts_nested_payload() -> None:
    """TODO: add docstring for test_github_json_to_yaml_converts_nested_payload."""
    command = (
        f"source '{LIB}'; "
        'printf \'%s\' \'{"kind":"demo","items":[{"id":1,"name":"A"}]}\' | github_json_to_yaml'
    )
    result = subprocess.run(
        ["bash", "-c", f"export DIGITAL_TEAM_SKIP_DOTENV=1; {command}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'kind: "demo"' in result.stdout
    assert "items:" in result.stdout
    assert "-\n    id: 1" in result.stdout or "id: 1" in result.stdout


def test_github_json_to_yaml_does_not_use_argv_payload() -> None:
    """TODO: add docstring for test_github_json_to_yaml_does_not_use_argv_payload."""
    content = LIB.read_text(encoding="utf-8")
    assert "sys.argv[1]" not in content
    assert "sys.stdin.read()" in content


def test_github_run_git_rejects_unsupported_token_characters() -> None:
    """TODO: add docstring for test_github_run_git_rejects_unsupported_token_characters."""
    command = (
        f"source '{GITHUB_LIB}'; "
        "github_run_tool() { :; }; "
        "GH_TOKEN=$'bad\\nvalue'; "
        "github_run_git status"
    )
    result = subprocess.run(
        ["bash", "-c", f"export DIGITAL_TEAM_SKIP_DOTENV=1; {command}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "unsupported characters" in result.stderr
