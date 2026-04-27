#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Collect and render results from asynchronously started quality gates.
# Security:
#   Reads temporary state files only from the current process temp directory.

collect_parallel_sections() {
  local slug
  for state_file in "$PARALLEL_STATE_DIR"/*.pid; do
    [[ -f "$state_file" ]] || continue
    slug="$(basename "$state_file" .pid)"

    local step_pid output_file started_at step_index total_steps title exit_code output elapsed
    step_pid="$(cat "$PARALLEL_STATE_DIR/$slug.pid")"
    output_file="$(cat "$PARALLEL_STATE_DIR/$slug.output")"
    started_at="$(cat "$PARALLEL_STATE_DIR/$slug.start")"
    step_index="$(cat "$PARALLEL_STATE_DIR/$slug.idx")"
    total_steps="$(cat "$PARALLEL_STATE_DIR/$slug.total")"
    title="$(cat "$PARALLEL_STATE_DIR/$slug.title")"
    exit_code=0

    while kill -0 "$step_pid" 2>/dev/null; do
      sleep 10
      kill -0 "$step_pid" 2>/dev/null || break
      elapsed=$(( $(date +%s) - started_at ))
      printf '[progress][quality-expert-session] step=%s/%s action=%s status=running elapsed=%ss\n' "$step_index" "$total_steps" "$slug" "$elapsed"
    done

    wait "$step_pid" || exit_code=$?
    output="$(cat "$output_file" 2>/dev/null || echo '')"
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
      printf '[progress][quality-expert-session] step=%s/%s action=%s status=done elapsed=%ss\n' "$step_index" "$total_steps" "$slug" "$elapsed"
    else
      printf '[progress][quality-expert-session] step=%s/%s action=%s status=fail elapsed=%ss exit=%s\n' "$step_index" "$total_steps" "$slug" "$elapsed" "$exit_code"
    fi

    rm -f "$PARALLEL_STATE_DIR/$slug".*
  done
}