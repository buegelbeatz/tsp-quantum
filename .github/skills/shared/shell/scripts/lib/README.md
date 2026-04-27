---
layer: digital-generic-team
---
# Shared Shell Library API

## Purpose

This document provides a concise function-level API map for the shared shell libraries.
Use these functions instead of duplicating shell logic across agents and scripts.

## Source Files

- `common.sh`
- `containers.sh`
- `tools.sh`
- `governance.sh`

---

## `common.sh`

- `log_info <message>`: Print informational log messages to stdout.
- `log_warn <message>`: Print warning messages to stderr.
- `log_error <message>`: Print error messages to stderr.
- `die <message>`: Print error and terminate with exit code `1`.
- `detect_os`: Return normalized OS identifier (`mac`, `linux`, `windows`, `unknown`).
- `repo_root`: Return current git repository root path.
- `require_file <path>`: Fail if the given file path does not exist.

---

## `containers.sh`

- `is_engine_available <engine>`: Check if a specific container engine is available and usable.
- `detect_container_tool`: Detect runtime in required priority order (`podman` > `apptainer/singularity` > `docker`).
- `run_in_container <image> <cmd> [args...]`: Execute command in detected runtime with workspace bind mount.

---

## `tools.sh`

- `csv_get_row_by_name <csv_file> <tool_name>`: Return first matching tool row from metadata CSV.
- `csv_get_field <row> <index>`: Return a comma-separated field by 1-based index.
- `tool_exists <tool_name>`: Check local binary availability via `command -v`.
- `get_tool_min_version <csv_file> <tool_name>`: Return minimum required version from metadata.
- `get_tool_public_container <csv_file> <tool_name>`: Return fallback public container image.
- `get_tool_install_help <csv_file> <tool_name> <os>`: Return OS-specific installation help text.
- `get_installed_version <tool_name>`: Resolve installed version string for known tools.
- `check_tool_local <csv_file> <tool_name>`: Validate local presence and version (`0=ok`, `1=missing`, `2=too-old`).

---

## `governance.sh`

- `check_permission <permissions_csv> <role> <operation>`: Validate that the role is allowed for the operation in a semicolon-separated permission matrix.
- `validate_handoff <payload_path> <schema_path>`: Validate required handoff fields against schema `required` entries.

---

## Integration Example

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/tools.sh"
source "${SCRIPT_DIR}/containers.sh"

if tool_exists python3; then
  python3 --version
else
  run_in_container python:3.11-slim python3 --version
fi
```

## Policy Notes

- Keep all shell comments and documentation in English.
- Prefer local tools first; use container fallback only when needed.
- Do not add duplicate helpers when an equivalent shared function exists.
