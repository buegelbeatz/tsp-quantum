"""Tests for mcp-chrome-ensure.sh — Chrome profile readiness and auto-launch script."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from mcp_test_support import ENSURE_CHROME_SCRIPT, ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_chrome(
    tmp_path: Path,
    name: str = "google-chrome",
    version: str = "Google Chrome Beta 144.0.0.0",
) -> Path:
    """Create a minimal fake Chrome binary that responds to --version."""
    binary = tmp_path / name
    binary.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'if [[ "${{1:-}}" == "--version" ]]; then printf "{version}\\n"; exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return binary


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the ensure script with optional env overrides."""
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    return subprocess.run(
        ["bash", str(ENSURE_CHROME_SCRIPT), *args],
        cwd=ROOT,
        env=base_env,
        text=True,
        capture_output=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Script existence and executable
# ---------------------------------------------------------------------------


def test_ensure_chrome_script_exists() -> None:
    """The mcp-chrome-ensure.sh file must exist and be executable."""
    assert ENSURE_CHROME_SCRIPT.exists(), "mcp-chrome-ensure.sh not found"
    assert ENSURE_CHROME_SCRIPT.stat().st_mode & stat.S_IEXEC, (
        "mcp-chrome-ensure.sh is not executable"
    )


# ---------------------------------------------------------------------------
# --check mode: structured output format
# ---------------------------------------------------------------------------


def test_check_mode_outputs_structured_yaml_without_chrome(tmp_path: Path) -> None:
    """--check must emit structured YAML even when Chrome binary is absent."""
    result = _run(["--check"], env={"CHROME_BIN": str(tmp_path / "nonexistent-chrome")})

    assert 'api_version: "v1"' in result.stdout
    assert 'kind: "mcp_chrome_ensure"' in result.stdout
    assert "chrome_available: false" in result.stdout
    assert 'status: "fail"' in result.stdout
    assert result.returncode == 1


def test_check_mode_reports_ok_with_fake_chrome_and_fake_cdp(tmp_path: Path) -> None:
    """--check reports ok when Chrome binary exists and CDP curl succeeds via fake."""
    fake_chrome = _fake_chrome(tmp_path)

    # Fake curl that simulates a reachable CDP endpoint
    fake_curl = tmp_path / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "$*" == *"json/version"* ]]; then\n'
        '  printf \'{"Browser":"Chrome/144.0.0.0","webSocketDebuggerUrl":"ws://localhost:9222/devtools/browser/abc"}\'\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_curl.chmod(fake_curl.stat().st_mode | stat.S_IEXEC)

    env = {
        "CHROME_BIN": str(fake_chrome),
        "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
    }
    result = _run(["--check"], env=env)

    assert 'status: "ok"' in result.stdout
    assert "chrome_available: true" in result.stdout
    assert "chrome_debugging: true" in result.stdout
    assert result.returncode == 0


def test_check_mode_reports_warn_when_chrome_present_but_cdp_unreachable(
    tmp_path: Path,
) -> None:
    """--check reports warn when Chrome binary is found but CDP port is not reachable."""
    fake_chrome = _fake_chrome(tmp_path)

    # Fake curl that always fails (simulates CDP not running)
    fake_curl = tmp_path / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nexit 1\n",
        encoding="utf-8",
    )
    fake_curl.chmod(fake_curl.stat().st_mode | stat.S_IEXEC)

    env = {
        "CHROME_BIN": str(fake_chrome),
        "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
    }
    result = _run(["--check"], env=env)

    assert 'status: "warn"' in result.stdout
    assert "chrome_available: true" in result.stdout
    assert "chrome_debugging: false" in result.stdout
    # warn is not a hard failure
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# --check mode: profile fields
# ---------------------------------------------------------------------------


def test_check_mode_reports_profile_name_and_path(tmp_path: Path) -> None:
    """--check must include profile_name and profile_path in output."""
    result = _run(
        ["--check", "--profile", "my-test-profile"],
        env={"CHROME_BIN": str(tmp_path / "none")},
    )

    assert 'profile_name: "my-test-profile"' in result.stdout
    assert "my-test-profile" in result.stdout  # path also contains profile name


def test_check_mode_detects_existing_profile_directory(tmp_path: Path) -> None:
    """profile_exists must be true when the profile directory exists."""
    fake_chrome = _fake_chrome(tmp_path)

    # Create a fake profile directory under HOME so the script finds it
    fake_profile = tmp_path / "vscode"
    fake_profile.mkdir()

    result = _run(
        ["--check"],
        env={
            "CHROME_BIN": str(fake_chrome),
            "HOME": str(tmp_path),
            "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
        },
    )

    assert "profile_exists:" in result.stdout


# ---------------------------------------------------------------------------
# --guidance mode
# ---------------------------------------------------------------------------


def test_guidance_mode_prints_human_readable_instructions() -> None:
    """--guidance must print setup steps without structured YAML output."""
    result = _run(["--guidance"])

    assert result.returncode == 0
    assert "Step 1" in result.stdout
    assert "Chrome Beta" in result.stdout
    assert "--remote-debugging-port" in result.stdout
    assert "--profile-directory" in result.stdout
    assert "vscode" in result.stdout
    assert "curl http://localhost" in result.stdout
    # Must NOT emit YAML api_version header
    assert "api_version" not in result.stdout


def test_guidance_mode_respects_custom_port_and_profile() -> None:
    """--guidance must embed custom port and profile name."""
    result = _run(["--guidance", "--port", "19222", "--profile", "copilot"])

    assert "19222" in result.stdout
    assert "copilot" in result.stdout
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# --ensure mode: fails gracefully when Chrome missing
# ---------------------------------------------------------------------------


def test_ensure_mode_fails_with_guidance_when_no_chrome(tmp_path: Path) -> None:
    """--ensure exits non-zero and emits guidance when Chrome binary is absent."""
    result = _run(["--ensure"], env={"CHROME_BIN": str(tmp_path / "nonexistent")})

    assert result.returncode != 0
    # Guidance is emitted to stderr
    assert "Step 1" in result.stderr or "Chrome Beta" in result.stderr


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


def test_chrome_vscode_profile_env_variable(tmp_path: Path) -> None:
    """CHROME_VSCODE_PROFILE env var must override default profile name."""
    result = _run(
        ["--check"],
        env={
            "CHROME_BIN": str(tmp_path / "none"),
            "CHROME_VSCODE_PROFILE": "my-custom-profile",
        },
    )

    assert 'profile_name: "my-custom-profile"' in result.stdout
    assert "my-custom-profile" in result.stdout


def test_chrome_cdp_port_env_variable(tmp_path: Path) -> None:
    """CHROME_CDP_PORT env var must override default port."""
    result = _run(
        ["--check"],
        env={"CHROME_BIN": str(tmp_path / "none"), "CHROME_CDP_PORT": "18888"},
    )

    assert "cdp_port: 18888" in result.stdout


# ---------------------------------------------------------------------------
# Unknown argument handling
# ---------------------------------------------------------------------------


def test_unknown_argument_exits_2() -> None:
    """Unrecognized arguments must cause exit code 2."""
    result = _run(["--unknown-flag"])
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# CDP port override
# ---------------------------------------------------------------------------


def test_cdp_port_override_reflected_in_output(tmp_path: Path) -> None:
    """Custom --port value must appear in structured output."""
    result = _run(
        ["--check", "--port", "19222"], env={"CHROME_BIN": str(tmp_path / "none")}
    )

    assert "cdp_port: 19222" in result.stdout
