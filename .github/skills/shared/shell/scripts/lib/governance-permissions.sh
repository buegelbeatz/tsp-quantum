#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Provide permission matrix evaluation helpers for role-based operations.
# Security:
#   Reads repository-local CSV files only and performs deterministic lookups.

# shellcheck shell=bash

check_permission() {
  local permissions_csv="$1"
  local role="$2"
  local operation="$3"
  [[ -f "$permissions_csv" ]] || {
    log_error "Permissions file not found: $permissions_csv"
    return 1
  }
  local header
  header="$(head -n1 "$permissions_csv")"
  local role_index=0
  IFS=';' read -r -a columns <<< "$header"
  for i in "${!columns[@]}"; do
    if [[ "${columns[$i]}" == "$role" ]]; then
      role_index="$i"
      break
    fi
  done
  [[ "$role_index" -gt 0 ]] || {
    log_error "Role not found in permissions matrix: $role"
    return 1
  }
  local matched_line
  matched_line="$(awk -F';' -v op="$operation" 'NR>1 && $1==op {print $0; exit}' "$permissions_csv")"
  [[ -n "$matched_line" ]] || {
    log_error "Operation not found in permissions matrix: $operation"
    return 1
  }
  IFS=';' read -r -a values <<< "$matched_line"
  local permission_value="${values[$role_index]}"
  if [[ "$permission_value" == "1" ]]; then
    return 0
  fi
  log_error "Permission denied for role=$role operation=$operation"
  return 1
}