---
name: mcp
description: Launch MCP servers and call tools via registry-driven runtime configuration.
layer: digital-generic-team
---

# Skill: MCP

This skill launches MCP servers on demand and invokes requested tools.

## Capabilities

- Read server registry from `metadata/mcp-servers.csv`.
- Validate requested server id and requested tool.
- Execute registry-backed server command locally.
- Emit structured YAML output for orchestration.
- Generate `.vscode/mcp.json` from registry entries.

## Scripts

- `scripts/mcp-launch.sh`
- `scripts/mcp-gen-vscode-config.sh`
- `scripts/mcp-check-chrome-devtools.sh`
- `scripts/mcp-paper-search.sh`

## Registry

`metadata/mcp-servers.csv` defines available MCP servers:

`server_id;image_or_command;transport;domain;description`

## Permission expectation

Role-level authorization is enforced by caller workflows before invoking this skill.
