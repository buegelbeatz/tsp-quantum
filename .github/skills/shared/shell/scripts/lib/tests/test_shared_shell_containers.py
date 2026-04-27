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
LIB = ROOT / ".github" / "skills" / "shared/shell" / "scripts" / "lib" / "containers.sh"


def _make_fake_bin(tmp_path: Path, name: str, body: str) -> None:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _detect_with_path(path_dir: Path) -> str:
    env = os.environ.copy()
    env["PATH"] = f"{path_dir}:/usr/bin:/bin"

    result = subprocess.run(
        [
            "bash",
            "-c",
            f"source '{LIB}'; detect_container_tool",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_detect_container_tool_prefers_podman(tmp_path: Path) -> None:
    """TODO: add docstring for test_detect_container_tool_prefers_podman."""
    _make_fake_bin(tmp_path, "podman", "#!/usr/bin/env bash\necho podman\n")
    _make_fake_bin(tmp_path, "apptainer", "#!/usr/bin/env bash\necho apptainer\n")
    _make_fake_bin(
        tmp_path,
        "docker",
        '#!/usr/bin/env bash\nif [[ "$1" == "info" ]]; then exit 0; fi\necho docker\n',
    )

    detected = _detect_with_path(tmp_path)
    assert detected == "podman"


def test_detect_container_tool_prefers_apptainer_over_docker(tmp_path: Path) -> None:
    """TODO: add docstring for test_detect_container_tool_prefers_apptainer_over_docker."""
    _make_fake_bin(tmp_path, "apptainer", "#!/usr/bin/env bash\necho apptainer\n")
    _make_fake_bin(
        tmp_path,
        "docker",
        '#!/usr/bin/env bash\nif [[ "$1" == "info" ]]; then exit 0; fi\necho docker\n',
    )

    detected = _detect_with_path(tmp_path)
    assert detected == "apptainer"


def test_run_in_container_defaults_mount_to_repo_root() -> None:
    """TODO: add docstring for test_run_in_container_defaults_mount_to_repo_root."""
    content = LIB.read_text(encoding="utf-8")

    assert 'repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"' in content
    assert 'mount_root="${CONTAINER_MOUNT_ROOT:-$repo_root}"' in content


def test_run_in_container_supports_platform_override(tmp_path: Path) -> None:
    """run_in_container should pass through CONTAINER_PLATFORM for OCI engines."""
    _make_fake_bin(
        tmp_path,
        "podman",
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"
    env["CONTAINER_PLATFORM"] = "linux/arm64"
    env["CONTAINER_MOUNT_ROOT"] = str(ROOT)

    result = subprocess.run(
        [
            "bash",
            "-c",
            f"source '{LIB}'; run_in_container 'example:latest' echo ok",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--platform" in result.stdout
    assert "linux/arm64" in result.stdout
    assert "example:latest" in result.stdout
