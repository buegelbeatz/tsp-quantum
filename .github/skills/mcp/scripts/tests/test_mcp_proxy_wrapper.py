"""Tests for mcp-proxy-wrapper.sh — proxy detection and env injection."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from mcp_test_support import PROXY_WRAPPER_SCRIPT, ROOT


def _run_wrapper(
    server_id: str,
    cmd: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run proxy wrapper with given server_id and command."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(PROXY_WRAPPER_SCRIPT), server_id, *cmd],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_echo_script(tmp_path: Path, name: str, output: str = "ok") -> Path:
    """Create a simple bash script that prints output and exits 0."""
    script = tmp_path / name
    script.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' '{output}'\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


class TestProxyWrapperDirectMode:
    """Tests for direct (no proxy) mode."""

    def test_direct_mode_when_proxy_disabled(self, tmp_path: Path) -> None:
        """When MCP_PROXY_DISABLED=1, runs in direct mode without proxy detection."""
        echo = _make_echo_script(tmp_path, "server.sh", "direct-ok")
        result = _run_wrapper(
            "test-server",
            [str(echo)],
            env_overrides={"MCP_PROXY_DISABLED": "1"},
        )
        assert result.returncode == 0
        assert "direct-ok" in result.stdout
        assert "mode=direct" in result.stderr
        assert "MCP_PROXY_DISABLED=1" in result.stderr

    def test_direct_mode_when_proxy_unreachable(self, tmp_path: Path) -> None:
        """When proxy host:port is unreachable, falls back to direct mode."""
        server = _make_echo_script(tmp_path, "server.sh", "fallback-ok")
        # Use a port that is guaranteed to be closed
        result = _run_wrapper(
            "test-server",
            [str(server)],
            env_overrides={
                "MCP_PROXY_HOST": "127.0.0.1",
                "MCP_PROXY_PORT": "19999",  # almost certainly unused
                "MCP_PROXY_CHECK_TIMEOUT": "1",
            },
        )
        assert result.returncode == 0
        assert "fallback-ok" in result.stdout
        assert "mode=direct" in result.stderr
        assert "proxy-not-reachable" in result.stderr

    def test_direct_mode_does_not_set_proxy_env(self, tmp_path: Path) -> None:
        """In direct mode, proxy env vars must NOT be injected into the subprocess."""
        env_printer = tmp_path / "print-env.sh"
        env_printer.write_text(
            "#!/usr/bin/env bash\nenv\n",
            encoding="utf-8",
        )
        env_printer.chmod(env_printer.stat().st_mode | stat.S_IEXEC)

        result = _run_wrapper(
            "test-server",
            [str(env_printer)],
            env_overrides={"MCP_PROXY_DISABLED": "1"},
        )
        assert result.returncode == 0
        # ALL_PROXY, HTTP_PROXY, HTTPS_PROXY must not appear in subprocess env
        assert "ALL_PROXY=" not in result.stdout
        assert "HTTP_PROXY=" not in result.stdout
        assert "HTTPS_PROXY=" not in result.stdout


class TestProxyWrapperRequiredMode:
    """Tests for MCP_PROXY_REQUIRED=1 mode."""

    def test_required_mode_fails_when_proxy_unreachable(self, tmp_path: Path) -> None:
        """When MCP_PROXY_REQUIRED=1 and proxy is unreachable, wrapper exits non-zero."""
        echo = _make_echo_script(tmp_path, "server.sh")
        result = _run_wrapper(
            "test-server",
            [str(echo)],
            env_overrides={
                "MCP_PROXY_REQUIRED": "1",
                "MCP_PROXY_HOST": "127.0.0.1",
                "MCP_PROXY_PORT": "19999",
                "MCP_PROXY_CHECK_TIMEOUT": "1",
            },
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr
        assert "not reachable" in result.stderr


class TestProxyWrapperArgPassthrough:
    """Tests that server args and exit codes are preserved."""

    def test_exit_code_passthrough(self, tmp_path: Path) -> None:
        """Wrapper must preserve server exit code exactly."""
        failing = tmp_path / "fail.sh"
        failing.write_text(
            "#!/usr/bin/env bash\nexit 42\n",
            encoding="utf-8",
        )
        failing.chmod(failing.stat().st_mode | stat.S_IEXEC)

        result = _run_wrapper(
            "test-server",
            [str(failing)],
            env_overrides={"MCP_PROXY_DISABLED": "1"},
        )
        assert result.returncode == 42

    def test_args_passthrough(self, tmp_path: Path) -> None:
        """Wrapper must pass all extra args to server command."""
        printer = tmp_path / "args.sh"
        printer.write_text(
            "#!/usr/bin/env bash\nprintf 'ARG:%s\\n' \"$@\"\n",
            encoding="utf-8",
        )
        printer.chmod(printer.stat().st_mode | stat.S_IEXEC)

        result = _run_wrapper(
            "test-server",
            [str(printer), "--foo", "bar", "--baz=qux"],
            env_overrides={"MCP_PROXY_DISABLED": "1"},
        )
        assert result.returncode == 0
        assert "ARG:--foo" in result.stdout
        assert "ARG:bar" in result.stdout
        assert "ARG:--baz=qux" in result.stdout

    def test_usage_error_on_missing_args(self) -> None:
        """Wrapper must exit non-zero and print usage when too few args provided."""
        result = subprocess.run(
            ["bash", str(PROXY_WRAPPER_SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "usage" in result.stderr.lower()


class TestProxyWrapperLogFormat:
    """Tests for diagnostic log output format."""

    def test_log_contains_server_id(self, tmp_path: Path) -> None:
        """Diagnostic log must include server-id for traceability."""
        echo = _make_echo_script(tmp_path, "server.sh")
        result = _run_wrapper(
            "my-test-server",
            [str(echo)],
            env_overrides={"MCP_PROXY_DISABLED": "1"},
        )
        assert "my-test-server" in result.stderr

    def test_log_prefix_is_customizable(self, tmp_path: Path) -> None:
        """MCP_PROXY_LOG_PREFIX must appear in stderr output."""
        echo = _make_echo_script(tmp_path, "server.sh")
        result = _run_wrapper(
            "test-server",
            [str(echo)],
            env_overrides={
                "MCP_PROXY_DISABLED": "1",
                "MCP_PROXY_LOG_PREFIX": "[custom-prefix]",
            },
        )
        assert "[custom-prefix]" in result.stderr
