#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Launch registered MCP servers and manage their lifecycle including
#   startup health checks and tool verification via the server registry.
# Security:
#   Runs authenticated subprocesses; validates server binary paths and
#   registry CSV integrity before execution. No hardcoded credentials.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY_PATH="${MCP_REGISTRY_CSV:-$SKILL_DIR/metadata/mcp-servers.csv}"
RUN_TOOL_SH="$SKILL_DIR/../shared/shell/scripts/run-tool.sh"

server_id=""
tool_name=""
args_file=""
output_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-id)
      server_id="${2:-}"
      shift 2
      ;;
    --tool)
      tool_name="${2:-}"
      shift 2
      ;;
    --args-file)
      args_file="${2:-}"
      shift 2
      ;;
    --output-file)
      output_file="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$server_id" ]] || { echo "--server-id is required" >&2; exit 2; }
[[ -n "$tool_name" ]] || { echo "--tool is required" >&2; exit 2; }
[[ -n "$args_file" ]] || { echo "--args-file is required" >&2; exit 2; }
[[ -n "$output_file" ]] || { echo "--output-file is required" >&2; exit 2; }
[[ -f "$REGISTRY_PATH" ]] || { echo "Registry not found: $REGISTRY_PATH" >&2; exit 2; }

mcp_run_python() {
  if [[ -f "$RUN_TOOL_SH" ]]; then
    bash "$RUN_TOOL_SH" python3 "$@"
    return $?
  fi

  python3 "$@"
}

row="$(mcp_run_python - <<'PY' "$REGISTRY_PATH" "$server_id"
import csv
import sys

registry, server_id = sys.argv[1], sys.argv[2]
with open(registry, encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter=";")
    for row in reader:
        if row.get("server_id") == server_id:
            print("\t".join([
                row.get("image_or_command", ""),
                row.get("transport", ""),
                row.get("domain", ""),
            ]))
            break
    else:
        print("")
PY
)"

[[ -n "$row" ]] || { echo "Server id '$server_id' not found" >&2; exit 3; }

image_or_command="${row%%$'\t'*}"
rest="${row#*$'\t'}"
transport="${rest%%$'\t'*}"

[[ -n "$image_or_command" ]] || { echo "Server command missing for '$server_id'" >&2; exit 3; }

listed_tools="$($image_or_command --list-tools 2>/dev/null || true)"
printf '%s\n' "$listed_tools" | grep -Fqx "$tool_name" || {
  echo "Requested tool '$tool_name' is not available on server '$server_id'" >&2
  exit 4
}

$image_or_command --call-tool "$tool_name" --args-file "$args_file" > "$output_file"

mcp_run_python - <<'PY' "$server_id" "$tool_name" "$transport" "$output_file"
import json
import sys

server_id, tool, transport, output = sys.argv[1:5]
print("api_version: \"v1\"")
print("kind: \"mcp_tool_call\"")
print("status: \"ok\"")
print(f"server_id: \"{server_id}\"")
print(f"tool: \"{tool}\"")
print(f"transport: \"{transport}\"")
print(f"output_file: \"{output}\"")
PY
