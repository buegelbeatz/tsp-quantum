#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Utility helpers for prompt-invoke parsing and metadata extraction.
# Security:
#   Reads repository-local markdown and command text only.

now_ms() {
  perl -MTime::HiRes=time -e 'printf("%.0f\n", time()*1000)'
}

add_unique_csv() {
  local value="$1"
  local current="$2"
  [[ -n "$value" ]] || { printf '%s' "$current"; return 0; }
  if [[ -z "$current" ]]; then
    printf '%s' "$value"
    return 0
  fi
  if [[ ",${current}," == *",${value},"* ]]; then
    printf '%s' "$current"
  else
    printf '%s, %s' "$current" "$value"
  fi
}

extract_dependencies_from_skill() {
  local skill_md="$1"
  [[ -f "$skill_md" ]] || return 0
  awk '
    BEGIN { in_deps=0 }
    /^##[[:space:]]+Dependencies/ { in_deps=1; next }
    /^##[[:space:]]+/ { if (in_deps) exit; next }
    {
      if (!in_deps) next
      if ($0 ~ /^[[:space:]]*-[[:space:]]+/) {
        line=$0
        gsub(/`/, "", line)
        sub(/^[[:space:]]*-[[:space:]]+/, "", line)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        n=split(line, parts, "/")
        print parts[n]
      }
    }
  ' "$skill_md"
}

extract_instruction_paths_from_file() {
  local source_file="$1"
  [[ -f "$source_file" ]] || return 0
  grep -Eo '\.github/instructions/[A-Za-z0-9_./-]+\.instructions\.md' "$source_file" 2>/dev/null \
    | sed -E 's#^.*/\.github/instructions/##' \
    | sort -u
}

append_instruction_hints_for_skill() {
  local skill_name="$1"
  case "$skill_name" in
    quality-expert)
      instructions_trace="$(add_unique_csv "quality-expert/cleancode.instructions.md" "$instructions_trace")"
      instructions_trace="$(add_unique_csv "quality-expert/designpatterns.instructions.md" "$instructions_trace")"
      instructions_trace="$(add_unique_csv "quality-expert/documentation.instructions.md" "$instructions_trace")"
      instructions_trace="$(add_unique_csv "test-expert/testing.instructions.md" "$instructions_trace")"
      ;;
    prompt-quality|prompt-quality-fix|shared/orchestration)
      instructions_trace="$(add_unique_csv "shared/handoff.instructions.md" "$instructions_trace")"
      instructions_trace="$(add_unique_csv "governance-layer/prompt-governance.instructions.md" "$instructions_trace")"
      instructions_trace="$(add_unique_csv "quality-expert/documentation.instructions.md" "$instructions_trace")"
      ;;
    mcp|prompt-chrome)
      instructions_trace="$(add_unique_csv "network-expert/app-http.instructions.md" "$instructions_trace")"
      ;;
  esac
}

extract_mcp_endpoints_from_command() {
  local command_text="$1"
  printf '%s\n' "$command_text" | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i == "--server-id" && i < NF) {
          print "server:" $(i + 1)
        }
        if ($i == "--tool" && i < NF) {
          print "tool:" $(i + 1)
        }
        if ($i ~ /^https?:\/\// || $i ~ /^wss?:\/\// || $i ~ /^mcp:\/\//) {
          print $i
        }
      }
    }
  ' | sort -u
}
