"""Shared constants and helpers for MCP script tests."""

from __future__ import annotations

import stat
from pathlib import Path


def repo_root() -> Path:
    """Locate repository root by searching for .digital-team directory marker.

    Returns:
        Path: Absolute path to the repository root.

    Raises:
        RuntimeError: If repository root cannot be found.
    """
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = repo_root()
SKILL_DIR = ROOT / ".github" / "skills" / "mcp"
LAUNCH_SCRIPT = SKILL_DIR / "scripts" / "mcp-launch.sh"
GEN_SCRIPT = SKILL_DIR / "scripts" / "mcp-gen-vscode-config.sh"
CHECK_CHROME_SCRIPT = SKILL_DIR / "scripts" / "mcp-check-chrome-devtools.sh"
ENSURE_CHROME_SCRIPT = SKILL_DIR / "scripts" / "mcp-chrome-ensure.sh"
PAPER_SEARCH_WRAPPER_SCRIPT = SKILL_DIR / "scripts" / "mcp-paper-search.sh"
PROXY_WRAPPER_SCRIPT = SKILL_DIR / "scripts" / "mcp-proxy-wrapper.sh"
REGISTRY_FILE = SKILL_DIR / "metadata" / "mcp-servers.csv"
REGISTRY_FILE = SKILL_DIR / "metadata" / "mcp-servers.csv"
UPDATE_SCRIPT = ROOT / "update.sh"


def create_fake_server(tmp_path: Path) -> Path:
    """Create a fake MCP server script for testing tool invocation behavior.

    Args:
        tmp_path: Temporary directory where fake server script will be created.

    Returns:
        Path: Path to the executable fake server script.
    """
    server = tmp_path / "fake_mcp_server.sh"
    server.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${1:-}" == "--list-tools" ]]; then\n'
        "  printf 'echo-tool\\n'\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "--call-tool" ]]; then\n'
        '  tool="${2:-}"\n'
        '  args_flag="${3:-}"\n'
        '  args_file="${4:-}"\n'
        '  if [[ "$tool" != "echo-tool" || "$args_flag" != "--args-file" ]]; then\n'
        "    exit 2\n"
        "  fi\n"
        '  printf \'{"ok": true, "args_file": "%s"}\\n\' "$args_file"\n'
        "  exit 0\n"
        "fi\n"
        "exit 2\n",
        encoding="utf-8",
    )
    server.chmod(server.stat().st_mode | stat.S_IEXEC)
    return server
