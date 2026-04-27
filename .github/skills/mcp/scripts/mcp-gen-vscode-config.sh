#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Generate the .vscode/mcp.json configuration file from the MCP server registry CSV.
#   Produces a validated config structure for VS Code MCP extension integration.
# Security:
#   Reads and validates the server registry CSV before writing the output file.
#   Writes only to .vscode/mcp.json; does not expose secrets or tokens.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v git >/dev/null 2>&1; then
    REPO_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel)"
else
    REPO_ROOT="$(cd "$SKILL_DIR/../../../.." && pwd)"
fi
REGISTRY_PATH="${MCP_REGISTRY_CSV:-$SKILL_DIR/metadata/mcp-servers.csv}"
OUTPUT_PATH="${MCP_VSCODE_CONFIG:-$REPO_ROOT/.vscode/mcp.json}"
MODE="${MCP_VSCODE_MODE:-disabled}"
ALLOWLIST="${MCP_VSCODE_SERVERS:-}"

if [[ "$MODE" != "disabled" && "$MODE" != "all" && "$MODE" != "allowlist" ]]; then
    echo "Unsupported MCP_VSCODE_MODE: $MODE (allowed: disabled, all, allowlist)" >&2
    exit 2
fi

if [[ "$MODE" == "allowlist" && -z "$ALLOWLIST" ]]; then
    echo "MCP_VSCODE_SERVERS is required when MCP_VSCODE_MODE=allowlist" >&2
    exit 2
fi

[[ -f "$REGISTRY_PATH" ]] || { echo "Registry not found: $REGISTRY_PATH" >&2; exit 2; }

mkdir -p "$(dirname "$OUTPUT_PATH")"

python3 - <<'PY' "$REGISTRY_PATH" "$OUTPUT_PATH" "$MODE" "$ALLOWLIST"
import csv
import json
import os
import shlex
import sys

registry_path, output_path, mode, allowlist_csv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
allowlist = {item.strip() for item in allowlist_csv.split(',') if item.strip()}
servers = {}
with open(registry_path, encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter=";")
    for row in reader:
        server_id = (row.get("server_id") or "").strip()
        command = (row.get("image_or_command") or "").strip()
        if not server_id or not command:
            continue
        if mode == "disabled":
            continue
        if mode == "allowlist" and server_id not in allowlist:
            continue
        parts = shlex.split(command)
        servers[server_id] = {
            "type": "stdio",
            "command": parts[0],
            "args": parts[1:],
        }

if mode == "allowlist":
    unknown = sorted(allowlist - set(servers.keys()))
    if unknown:
        raise SystemExit(f"Unknown MCP server ids in allowlist: {', '.join(unknown)}")

payload = {"servers": servers}
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")

print(f"generated: {output_path}")
print(f"servers: {len(servers)}")
print(f"mode: {mode}")
PY
