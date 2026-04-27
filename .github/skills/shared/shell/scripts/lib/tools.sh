#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Provide CSV-backed tool discovery and version helper functions.
# Security:
#   Performs read-only metadata lookups and avoids executing untrusted input.

# =============================================================================
# Enterprise Shared Shell Library: tools.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Provide metadata-backed tool discovery and version helpers.
#
# CSV Schema (`tools.csv`):
#   tool_name,min_version,public_container,version_args,version_regex,install_help_mac,install_help_windows
#
# public_container supports either:
#   - a plain image reference, e.g. `python:3.14-slim`
#   - a semicolon-separated platform map, e.g.
#     `default=python:3.14-slim;linux/arm64=python:3.14-slim;linux/amd64=python:3.14-slim`
#
# Notes:
#   - Container-first execution is decided in run-tool.sh.
#   - This library only answers metadata and local capability checks.
# =============================================================================

# shellcheck shell=bash
set -euo pipefail

TOOLS_CSV_DEFAULT=".github/skills/shared/shell/scripts/metadata/tools.csv"

csv_get_row_by_name() {
  local csv_file="$1"
  local tool_name="$2"
  awk -F',' -v name="$tool_name" '
    NR == 1 { next }
    $1 == name { print; exit }
  ' "$csv_file"
}

csv_get_field() {
  local row="$1"
  local index="$2"
  printf '%s\n' "$row" | awk -F',' -v idx="$index" '{ print $idx }'
}

tool_exists() {
  command -v "$1" >/dev/null 2>&1
}

version_meets_requirement() {
  local installed="$1"
  local required="$2"

  [[ -n "$installed" && -n "$required" ]] || return 1
  [[ "$required" == "unknown" ]] && return 0

  local lowest
  lowest="$(printf '%s\n%s\n' "$installed" "$required" | sort -V | head -n1)"
  [[ "$lowest" == "$required" ]]
}

get_tool_min_version() {
  local csv_file="$1"
  local tool_name="$2"
  local row="$(csv_get_row_by_name "$csv_file" "$tool_name")"
  csv_get_field "$row" 2
}

get_tool_public_container() {
  local csv_file="$1"
  local tool_name="$2"
  local row="$(csv_get_row_by_name "$csv_file" "$tool_name")"
  local image_spec
  image_spec="$(csv_get_field "$row" 3)"

  if [[ "$image_spec" != *"="* ]]; then
    printf '%s\n' "$image_spec"
    return 0
  fi

  local requested_platform="${CONTAINER_PLATFORM:-}"
  local default_image=""
  local IFS_BACKUP="$IFS"
  local entry key value
  IFS=';'
  for entry in $image_spec; do
    IFS="$IFS_BACKUP"
    key="${entry%%=*}"
    value="${entry#*=}"
    if [[ -n "$requested_platform" && "$key" == "$requested_platform" ]]; then
      printf '%s\n' "$value"
      return 0
    fi
    if [[ "$key" == "default" ]]; then
      default_image="$value"
    fi
    IFS=';'
  done
  IFS="$IFS_BACKUP"

  printf '%s\n' "$default_image"
}

get_tool_version_args() {
  local csv_file="$1"
  local tool_name="$2"
  local row="$(csv_get_row_by_name "$csv_file" "$tool_name")"
  csv_get_field "$row" 4
}

get_tool_version_regex() {
  local csv_file="$1"
  local tool_name="$2"
  local row="$(csv_get_row_by_name "$csv_file" "$tool_name")"
  csv_get_field "$row" 5
}

get_tool_install_help() {
  local csv_file="$1"
  local tool_name="$2"
  local os_name="$3"
  local row="$(csv_get_row_by_name "$csv_file" "$tool_name")"
  case "$os_name" in
    mac) csv_get_field "$row" 6 ;;
    windows) csv_get_field "$row" 7 ;;
    linux) echo "Install $tool_name using your Linux distribution package manager." ;;
    *) echo "Install $tool_name manually for your platform." ;;
  esac
}

get_installed_version() {
  local csv_file="$1"
  local tool_name="$2"
  local version_args version_regex
  version_args="$(get_tool_version_args "$csv_file" "$tool_name")"
  version_regex="$(get_tool_version_regex "$csv_file" "$tool_name")"

  [[ -n "$version_args" ]] || version_args="--version"
  [[ -n "$version_regex" ]] || version_regex='[0-9]+\.[0-9]+(\.[0-9]+)?'

  local args=()
  # shellcheck disable=SC2206
  args=($version_args)

  local raw
  raw="$($tool_name "${args[@]}" 2>&1 || true)"
  printf '%s\n' "$raw" | grep -oE "$version_regex" | head -n1
}

check_tool_local() {
  local csv_file="$1"
  local tool_name="$2"

  if ! tool_exists "$tool_name"; then
    return 1
  fi

  local required="$(get_tool_min_version "$csv_file" "$tool_name")"
  local installed="$(get_installed_version "$csv_file" "$tool_name")"

  if [[ -z "$required" || -z "$installed" ]]; then
    return 0
  fi

  if ! version_meets_requirement "$installed" "$required"; then
    return 2
  fi

  return 0
}
