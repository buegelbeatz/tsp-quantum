from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT = ROOT / ".github" / "skills" / "shared/shell" / "scripts" / "run-tool.sh"


def test_run_tool_auto_registers_unknown_tool(tmp_path: Path) -> None:
    """TODO: add docstring for test_run_tool_auto_registers_unknown_tool."""
    csv_file = tmp_path / "tools.csv"
    csv_file.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["TOOL_REGISTRY_CSV"] = str(csv_file)
    env["PATH"] = "/usr/bin:/bin"

    result = subprocess.run(
        ["bash", str(SCRIPT), "unknown-tool", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    csv_text = csv_file.read_text(encoding="utf-8")
    assert "unknown-tool,unknown" in csv_text
    assert "not available locally and no container engine found" in result.stderr


def test_run_tool_honors_platform_specific_container_mapping(tmp_path: Path) -> None:
    """run-tool should select the platform-specific image from tools.csv."""
    csv_file = tmp_path / "tools.csv"
    csv_file.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n"
        "demo,1.0,default=ghcr.io/example/demo:latest;linux/amd64=ghcr.io/example/demo:amd64;linux/arm64=ghcr.io/example/demo:arm64,Install demo on macOS,Install demo on Windows\n",
        encoding="utf-8",
    )

    podman = tmp_path / "podman"
    podman.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == "run" ]]; then\n'
        "  shift\n"
        "  printf '%s\\n' \"$@\"\n"
        "  exit 0\n"
        "fi\n"
        "printf 'podman %s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    podman.chmod(0o755)

    env = os.environ.copy()
    env["TOOL_REGISTRY_CSV"] = str(csv_file)
    env["CONTAINER_PLATFORM"] = "linux/amd64"
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"

    result = subprocess.run(
        ["bash", str(SCRIPT), "demo", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--platform" in result.stdout
    assert "linux/amd64" in result.stdout
    assert "ghcr.io/example/demo:amd64" in result.stdout


def test_run_tool_logs_into_ghcr_before_container_execution(tmp_path: Path) -> None:
    """run-tool should authenticate podman against ghcr.io when GHCR_TOKEN is configured."""
    csv_file = tmp_path / "tools.csv"
    csv_file.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n"
        "demo,1.0,ghcr.io/example/demo:latest,Install demo on macOS,Install demo on Windows\n",
        encoding="utf-8",
    )

    log_file = tmp_path / "podman.log"
    podman = tmp_path / "podman"
    podman.write_text(
        "#!/usr/bin/env bash\n"
        f"echo \"$*\" >> {log_file}\n"
        'if [[ "$1" == "login" ]]; then\n'
        "  cat >/dev/null\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "run" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    podman.chmod(0o755)

    env = os.environ.copy()
    env["TOOL_REGISTRY_CSV"] = str(csv_file)
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"
    env["GHCR_TOKEN"] = "ghcr-token"
    env["GHCR_NAMESPACE"] = "ghcr.io/acme"
    env["DIGITAL_TEAM_SKIP_DOTENV"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT), "demo", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    log_text = log_file.read_text(encoding="utf-8")
    assert "login ghcr.io -u acme --password-stdin" in log_text
    assert "run --rm" in log_text


def test_run_tool_prefers_container_when_local_and_container_are_available(tmp_path: Path) -> None:
    """run-tool should use the registry first when container-first is active."""
    csv_file = tmp_path / "tools.csv"
    csv_file.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n"
        "demo,2.45,ghcr.io/example/demo:latest,brew install demo,winget install Demo.Tool\n",
        encoding="utf-8",
    )

    demo = tmp_path / "demo"
    demo.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'demo-local %s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    demo.chmod(0o755)

    podman = tmp_path / "podman"
    podman.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == "run" ]]; then\n'
        "  printf 'container-run %s\\n' \"$*\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    podman.chmod(0o755)

    env = os.environ.copy()
    env["TOOL_REGISTRY_CSV"] = str(csv_file)
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"
    env["RUN_TOOL_PREFER_CONTAINER"] = "1"
    env["DIGITAL_TEAM_SKIP_DOTENV"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT), "demo", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "container-run run --rm" in result.stdout
    assert "demo-local" not in result.stdout


def test_run_tool_uses_local_when_container_preference_is_disabled(tmp_path: Path) -> None:
    """run-tool should support an explicit local override for bootstrapping flows."""
    csv_file = tmp_path / "tools.csv"
    csv_file.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n"
        "demo,2.45,ghcr.io/example/demo:latest,brew install demo,winget install Demo.Tool\n",
        encoding="utf-8",
    )

    demo = tmp_path / "demo"
    demo.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'demo-local %s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    demo.chmod(0o755)

    podman = tmp_path / "podman"
    podman.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'container-should-not-run %s\\n' \"$*\" >&2\n"
        "exit 99\n",
        encoding="utf-8",
    )
    podman.chmod(0o755)

    env = os.environ.copy()
    env["TOOL_REGISTRY_CSV"] = str(csv_file)
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"
    env["RUN_TOOL_PREFER_CONTAINER"] = "0"
    env["DIGITAL_TEAM_SKIP_DOTENV"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT), "demo", "--version"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "demo-local --version" in result.stdout
    assert "container-should-not-run" not in result.stderr
