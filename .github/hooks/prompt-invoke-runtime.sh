#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Execute wrapped command with optional pre/post audit hooks.
# Security:
#   Resolves and executes repository-local governance and hook scripts only.

is_audit_enabled() {
  if [[ -n "${DIGITAL_AUDIT_ENABLED:-}" ]]; then
    [[ "${DIGITAL_AUDIT_ENABLED}" != "0" ]]
    return
  fi

  local layer_id="${DIGITAL_LAYER_ID:-$(basename "$repo_root") }"
  layer_id="${layer_id% }"
  local state_file="$repo_root/.digital-runtime/layers/$layer_id/audit/state.env"

  if [[ -f "$state_file" ]]; then
    local state_line
    state_line="$(grep -E '^DIGITAL_AUDIT_ENABLED=' "$state_file" 2>/dev/null || true)"
    [[ "$state_line" != "DIGITAL_AUDIT_ENABLED=0" ]]
    return
  fi

  return 0
}

build_communication_flow() {
  communication_flow="user -> copilot: /${prompt_name}"
  declare -a non_copilot_agents=()
  while IFS= read -r _agent_entry; do
    local _agent_name
    _agent_name="$(printf '%s' "$_agent_entry" | xargs 2>/dev/null || true)"
    [[ -z "$_agent_name" || "$_agent_name" == "copilot" ]] && continue
    non_copilot_agents+=("$_agent_name")
  done < <(printf '%s\n' "$agents_trace" | tr ',' '\n')

  if [[ ${#non_copilot_agents[@]} -gt 0 ]]; then
    communication_flow+="; copilot -> ${non_copilot_agents[0]}: invoke"
    if [[ ${#non_copilot_agents[@]} -gt 1 ]]; then
      local i=0
      for ((i=1; i<${#non_copilot_agents[@]}; i++)); do
        local prev_agent="${non_copilot_agents[$((i-1))]}"
        local next_agent="${non_copilot_agents[$i]}"
        communication_flow+="; ${prev_agent} -> ${next_agent}: expert_request_v1"
        communication_flow+="; ${next_agent} --> ${prev_agent}: expert_response_v1"
      done
    fi
    communication_flow+="; ${non_copilot_agents[0]} --> copilot: result"
  fi
  communication_flow+="; copilot -> audit-log: persist"
}

run_with_audit_hooks() {
  local pre_hook post_hook
  local audit_message_id audit_basename
  pre_hook="$(resolve_prompt_hook_path "pre-message.sh" 2>/dev/null || true)"
  post_hook="$(resolve_prompt_hook_path "post-message.sh" 2>/dev/null || true)"

  audit_message_id="${DIGITAL_AUDIT_MASTER_MESSAGE_ID:-$message_id}"
  audit_basename="${DIGITAL_AUDIT_MASTER_BASENAME:-$prompt_name}"

  local t0_ms t1_ms t2_ms
  t0_ms="$(now_ms)"
  t1_ms="$t0_ms"
  t2_ms="$t0_ms"

  local layer_id capture_dir capture_file
  layer_id="${DIGITAL_LAYER_ID:-$(basename "$repo_root") }"
  layer_id="${layer_id% }"
  capture_dir="$repo_root/.digital-runtime/layers/$layer_id/audit/captures"
  capture_file="$capture_dir/${message_id}.env"
  mkdir -p "$capture_dir"
  rm -f "$capture_file"
  export DIGITAL_PROMPT_AUDIT_CAPTURE_FILE="$capture_file"
  if [[ -n "${audit_basename:-}" ]]; then
    export DIGITAL_AUDIT_BASENAME="$audit_basename"
  fi

  if [[ -n "$pre_hook" ]]; then
    bash "$pre_hook" --message-id "$audit_message_id" --summary "$summary" --handoff-expected "$handoff_expected" || true
  fi
  t1_ms="$(now_ms)"

  local exit_code=0
  "$@" || exit_code=$?
  t2_ms="$(now_ms)"

  if [[ $exit_code -ne 0 ]]; then
    local failed_ms
    failed_ms=$((t2_ms - t1_ms))
    printf '[prompt-invoke] ERROR: /%s failed (exit=%s, duration=%sms).\n' "$prompt_name" "$exit_code" "$failed_ms" >&2
    printf '[prompt-invoke] NEXT: check command output above, fix errors, then rerun /%s.\n' "$prompt_name" >&2
  fi

  local artifacts assumptions open_questions flow_append status_summary next_step
  artifacts=""
  assumptions=""
  open_questions=""
  flow_append=""
  status_summary=""
  next_step=""
  if [[ -f "$capture_file" ]]; then
    while IFS='=' read -r key value; do
      [[ -n "$key" ]] || continue
      value="${value%$'\r'}"
      case "$key" in
        AUDIT_ARTIFACTS) artifacts="$value" ;;
        AUDIT_ASSUMPTIONS) assumptions="$value" ;;
        AUDIT_OPEN_QUESTIONS) open_questions="$value" ;;
        AUDIT_COMMUNICATION_FLOW) flow_append="$value" ;;
        AUDIT_STATUS_SUMMARY) status_summary="$value" ;;
        AUDIT_NEXT_STEP) next_step="$value" ;;
      esac
    done < "$capture_file"
  fi

  if [[ -n "$flow_append" ]]; then
    communication_flow+="; ${flow_append}"
  fi

  local status="ok"
  [[ $exit_code -eq 0 ]] || status="error"

  local pre_hook_ms=$((t1_ms - t0_ms))
  local command_ms=$((t2_ms - t1_ms))
  local timing_total_ms=$((t2_ms - t0_ms))

  if [[ -n "$post_hook" ]]; then
    bash "$post_hook" \
      --message-id "$audit_message_id" \
      --summary "$summary" \
      --status "$status" \
      --handoff-expected "$handoff_expected" \
      --timing-total-ms "$timing_total_ms" \
      --timing-pre-hook-ms "$pre_hook_ms" \
      --timing-command-ms "$command_ms" \
      --execution-stack "$execution_stack" \
      --skills-trace "$skills_trace" \
      --agents-trace "$agents_trace" \
      --instructions-trace "$instructions_trace" \
        --artifacts "$artifacts" \
        --assumptions "$assumptions" \
        --open-questions "$open_questions" \
          --status-summary "$status_summary" \
          --next-step "$next_step" \
      --mcp-endpoints-trace "$mcp_endpoints_trace" \
      --communication-flow "$communication_flow" || true
  fi

  exit "$exit_code"
}
