#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Provide YAML/report helper functions for GitHub shared shell workflows.
# Security:
#   Writes runtime artifacts only under controlled runtime paths and avoids repo persistence.

# shellcheck shell=bash

github_json_to_yaml() {
  python3 -c '
import json
import sys


def quote_string(value: str) -> str:
  escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
  return f"\"{escaped}\""


def emit(node, indent=0):
  prefix = "  " * indent
  if isinstance(node, dict):
    if not node:
      print(f"{prefix}{{}}")
      return
    for key, value in node.items():
      if isinstance(value, (dict, list)):
        print(f"{prefix}{key}:")
        emit(value, indent + 1)
      else:
        print(f"{prefix}{key}: {scalar(value)}")
  elif isinstance(node, list):
    if not node:
      print(f"{prefix}[]")
      return
    for item in node:
      if isinstance(item, (dict, list)):
        print(f"{prefix}-")
        emit(item, indent + 1)
      else:
        print(f"{prefix}- {scalar(item)}")
  else:
    print(f"{prefix}{scalar(node)}")


def scalar(value):
  if value is None:
    return "null"
  if isinstance(value, bool):
    return "true" if value else "false"
  if isinstance(value, (int, float)):
    return str(value)
  return quote_string(str(value))


payload = json.loads(sys.stdin.read())
emit(payload)
'
}


github_write_yaml_report() {
  local report_name="$1"
  local yaml_content="$2"

  ensure_github_runtime_dirs
  local timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  local report_path="$GITHUB_REPORT_DIR/${report_name}-${timestamp}.yaml"
  printf '%s\n' "$yaml_content" > "$report_path"
  printf '%s\n' "$report_path"
}


github_wiki_cache_path() {
  local repo_slug="$1"
  local normalized="${repo_slug//\//__}"
  printf '%s/%s.wiki' "$GITHUB_WIKI_CACHE_DIR" "$normalized"
}