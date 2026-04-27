#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Runtime helpers for quality-expert-session gate execution and report output.
# Security:
#   Executes only local quality commands and writes state into ephemeral temp files.

require_runtime_package() {
  local package_name="$1"
  if ! "$RUNTIME_VENV_PYTHON" -m pip show "$package_name" >/dev/null 2>&1; then
    echo "quality-expert: required package '$package_name' is missing in layer venv" >&2
    echo "quality-expert: run 'make layer-venv-sync' to install merged skill requirements." >&2
    exit 1
  fi
}

append_section() {
  local title="$1"
  local command="$2"
  local step_index="$3"
  local total_steps="$4"
  local run_mode="${5:-sequential}"
  local exit_code=0
  local output_file
  local output
  local started_at
  local elapsed=0
  local section_slug
  local step_pid

  section_slug="$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]' | tr ' >=/' '----' | tr -cd 'a-z0-9-')"
  output_file="$(mktemp)"
  started_at="$(date +%s)"

  printf '[progress][quality-expert-session] step=%s/%s action=%s status=start\n' "$step_index" "$total_steps" "$section_slug"

  (
    bash "$GATE_RUNNER" "$section_slug" "$command" "$REPO_ROOT" "$COVERAGE_FILE_PATH"
  ) >"$output_file" 2>&1 &
  step_pid=$!

  if [[ "$run_mode" == "parallel" ]]; then
    echo "$step_pid" > "$PARALLEL_STATE_DIR/$section_slug.pid"
    echo "$output_file" > "$PARALLEL_STATE_DIR/$section_slug.output"
    echo "$started_at" > "$PARALLEL_STATE_DIR/$section_slug.start"
    echo "$step_index" > "$PARALLEL_STATE_DIR/$section_slug.idx"
    echo "$total_steps" > "$PARALLEL_STATE_DIR/$section_slug.total"
    echo "$title" > "$PARALLEL_STATE_DIR/$section_slug.title"
    return 0
  fi

  while kill -0 "$step_pid" 2>/dev/null; do
    sleep 10
    kill -0 "$step_pid" 2>/dev/null || break
    elapsed=$(( $(date +%s) - started_at ))
    printf '[progress][quality-expert-session] step=%s/%s action=%s status=running elapsed=%ss\n' "$step_index" "$total_steps" "$section_slug" "$elapsed"
  done

  wait "$step_pid" || exit_code=$?
  output="$(cat "$output_file")"
  rm -f "$output_file"
  elapsed=$(( $(date +%s) - started_at ))

  {
    printf '## %s\n\n' "$title"
    printf '```\n%s\n```\n\n' "$output"
    if [[ "$exit_code" -eq 0 ]]; then
      printf '[PASS] %s\n\n' "$title"
    else
      printf '[FAIL] %s\n\n' "$title"
      overall_fail=1
    fi
  } >> "$CANONICAL_REPORT"

  if [[ "$exit_code" -eq 0 ]]; then
    printf '[progress][quality-expert-session] step=%s/%s action=%s status=done elapsed=%ss\n' "$step_index" "$total_steps" "$section_slug" "$elapsed"
  else
    printf '[progress][quality-expert-session] step=%s/%s action=%s status=fail elapsed=%ss exit=%s\n' "$step_index" "$total_steps" "$section_slug" "$elapsed" "$exit_code"
  fi
}
