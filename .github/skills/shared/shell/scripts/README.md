---
layer: digital-generic-team
---
# Shared Shell Scripts

## Purpose

This directory contains reusable shell tooling for cross-agent execution with container-first behavior and a local fallback for controlled exceptions.

## Normative Policy

- Repository code must invoke external CLI tools through `run-tool.sh` or a thin wrapper built on the same tool registry.
- Every non-standard CLI dependency must be registered in `metadata/tools.csv` with install guidance and, where possible, a public container image.
- Direct `subprocess` execution of non-standard host binaries is not allowed when the shared/shell path can be used instead.
- Registry-backed container execution is the default path for registered tools. Local execution is a fallback or an explicit bootstrap override.
- Prefer multi-architecture container images. If a tool requires different images for `linux/arm64` and `linux/amd64`, encode that in `metadata/tools.csv` using `default=...;linux/arm64=...;linux/amd64=...`.
- `CONTAINER_PLATFORM` may be set to force Docker/Podman execution for a specific architecture, which is useful on Apple Silicon workstations that occasionally need `linux/amd64` images.

## Components

- `run-tool.sh` — entry script for tool execution.
- `lib/common.sh` — logging, OS detection, repository helpers, `.env` auto-load.
- `lib/tools.sh` — CSV-driven tool metadata and version checks.
- `lib/containers.sh` — container detection and runtime execution wrappers.
- `runtime/layer-venv-sync.sh` — shared layer dependency merge + venv hash cache sync.
- `metadata/tools.csv` — tool catalog (minimum versions, container images, OS install hints).
- `metadata/direct-tool-allowlist.txt` — explicit bootstrap exceptions for guarded direct tool calls.
- `guard-direct-tool-calls.py` — repository guard for unregistered direct CLI invocations in `.github/*.sh`.

## Runtime Priority

Container fallback order is fixed:

1. `podman`
2. `apptainer` / `singularity`
3. `docker`

## Usage

Run a tool through the registry-backed wrapper. It will use the configured container image first unless explicitly overridden:

```bash
./run-tool.sh python3 --version
./run-tool.sh ruff check .
```

## Integration Pattern

Source reusable libraries in other scripts:

```bash
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/tools.sh"
source "${SCRIPT_DIR}/lib/containers.sh"
```

## Environment

- `TOOL_REGISTRY_CSV` (optional): override default `tools.csv` path.
- `CONTAINER_PLATFORM` (optional): request a specific OCI platform such as `linux/arm64` or `linux/amd64` for Docker/Podman runs.

## Security Notes

- No credentials are embedded in scripts.
- Containers are executed with `--rm` where applicable.
- The repository root is mounted to `/workspace` during container fallback so `.env`, `.digital-runtime`, and repo-local scripts remain available.
