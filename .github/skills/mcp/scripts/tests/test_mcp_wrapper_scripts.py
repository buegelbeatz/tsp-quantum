"""Tests for MCP wrapper scripts, registry defaults, and update integration."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from mcp_test_support import (
    CHECK_CHROME_SCRIPT,
    PAPER_SEARCH_WRAPPER_SCRIPT,
    REGISTRY_FILE,
    ROOT,
    UPDATE_SCRIPT,
)


def test_default_registry_contains_initial_servers() -> None:
    """Verify the default MCP registry still lists the required initial servers."""

    raw = REGISTRY_FILE.read_text(encoding="utf-8").strip().splitlines()
    header, rows = raw[0], raw[1:]

    assert (
        header == "server_id;image_or_command;transport;domain;description;prompt_owner"
    )
    for server_id in ("paper-search", "chrome-devtools", "fetch", "memory"):
        assert any(line.startswith(f"{server_id};") for line in rows)
    assert "skills/mcp/scripts/mcp-paper-search.sh" in next(
        line for line in rows if line.startswith("paper-search;")
    )
    assert "@modelcontextprotocol/server-fetch" in next(
        line for line in rows if line.startswith("fetch;")
    )
    assert "@modelcontextprotocol/server-memory" in next(
        line for line in rows if line.startswith("memory;")
    )
    # Removed servers must NOT appear in the registry
    for removed_id in ("math-mcp", "git", "sequential-thinking"):
        assert not any(line.startswith(f"{removed_id};") for line in rows), (
            f"{removed_id} must be removed from registry"
        )


def test_chrome_devtools_check_reports_ok_with_fake_binaries(tmp_path: Path) -> None:
    """Verify Chrome DevTools check reports ok for fake npx and chrome binaries."""

    fake_npx = tmp_path / "npx"
    fake_npx.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\nif [[ "${1:-}" == "-y" ]]; then shift; fi\nif [[ "${1:-}" == "chrome-devtools-mcp@latest" && "${2:-}" == "--help" ]]; then exit 0; fi\nexit 0\n',
        encoding="utf-8",
    )
    fake_npx.chmod(fake_npx.stat().st_mode | stat.S_IEXEC)

    fake_chrome = tmp_path / "google-chrome"
    fake_chrome.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\nif [[ "${1:-}" == "--version" ]]; then printf \'Google Chrome 144.0.0.0\\n\'; exit 0; fi\nexit 0\n',
        encoding="utf-8",
    )
    fake_chrome.chmod(fake_chrome.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["NPX_BIN"] = str(fake_npx)
    env["CHROME_BIN"] = str(fake_chrome)
    result = subprocess.run(
        ["bash", str(CHECK_CHROME_SCRIPT), "--probe-package"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'kind: "mcp_chrome_devtools_check"' in result.stdout
    assert 'status: "ok"' in result.stdout
    assert "probe_ok: true" in result.stdout


def test_paper_search_wrapper_is_container_first_runtime_script() -> None:
    """Verify the paper-search wrapper retains container-first runtime behavior markers."""

    content = PAPER_SEARCH_WRAPPER_SCRIPT.read_text(encoding="utf-8")
    assert 'source "$MCP_LIB_DIR/mcp-paper-search-lib.sh"' in content
    helper_content = (
        PAPER_SEARCH_WRAPPER_SCRIPT.parent / "lib" / "mcp-paper-search-lib.sh"
    ).read_text(encoding="utf-8")
    for token in (
        "venv-container-paper-search",
        "requirements.merged.txt",
        "-m paper_search_mcp.server",
        "bootstrap still running",
        "bootstrap timeout reached",
        "local defender/proxy rules may block outbound URLs",
    ):
        assert token in helper_content
    assert "BOOTSTRAP_VERBOSE=0" in content
    assert "--verbose" in content
    assert "DIGITAL_MCP_BOOTSTRAP_TIMEOUT_SECONDS" in helper_content
    assert "DIGITAL_MCP_VERBOSE" in helper_content
    assert "--quiet" in content


def test_update_script_synchronizes_mcp_config() -> None:
    """Verify root update script still regenerates VS Code MCP configuration."""

    content = UPDATE_SCRIPT.read_text(encoding="utf-8")
    assert "skills/mcp/scripts/mcp-gen-vscode-config.sh" in content
    assert "regenerated .vscode/mcp.json" in content
