#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Wrapper for prompt commands to trigger pre/post-message audit hooks.
# Path policy:
#   .github/ is the runtime source path.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

prompt_name=""
message_id=""
summary=""
execution_stack=""
skills_trace=""
agents_trace=""
instructions_trace=""
communication_flow=""
mcp_endpoints_trace=""
handoff_expected="auto"
declare -a command_args=()

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARGS_LIB="$SCRIPT_DIR/prompt-invoke-args.sh"
HELPERS_LIB="$SCRIPT_DIR/prompt-invoke-helpers.sh"
PATHS_LIB="$SCRIPT_DIR/prompt-invoke-paths.sh"
TRACE_LIB="$SCRIPT_DIR/prompt-invoke-trace.sh"
RUNTIME_LIB="$SCRIPT_DIR/prompt-invoke-runtime.sh"

for helper in "$ARGS_LIB" "$HELPERS_LIB" "$PATHS_LIB" "$TRACE_LIB" "$RUNTIME_LIB"; do
  if [[ ! -f "$helper" ]]; then
    printf '[ERROR] Missing prompt-invoke helper: %s\n' "$helper" >&2
    exit 2
  fi
done

# shellcheck source=/dev/null
source "$ARGS_LIB"
# shellcheck source=/dev/null
source "$HELPERS_LIB"
# shellcheck source=/dev/null
source "$PATHS_LIB"
# shellcheck source=/dev/null
source "$TRACE_LIB"
# shellcheck source=/dev/null
source "$RUNTIME_LIB"

parse_prompt_invoke_args "$@" || exit $?
set -- "${command_args[@]}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Internal-only prompt contract:
# These prompts remain available for orchestrated/runtime workflows, but must not
# be directly invocable by end users in chat context.
readonly INTERNAL_ONLY_PROMPTS=(
  chrome
  powerpoint
  pull
  artifacts-testdata-2-input
  stages-action
  artifacts-data-2-specification
  artifacts-input-2-data
  artifacts-specification-2-planning
  artifacts-specification-2-stage
  readme
)

if [[ "${PROMPT_INTERNAL_CALL:-0}" != "1" ]]; then
  for internal_prompt in "${INTERNAL_ONLY_PROMPTS[@]}"; do
    if [[ "$prompt_name" == "$internal_prompt" ]]; then
      printf '[prompt-invoke] ERROR: /%s is internal-only and not user-invocable.\n' "$prompt_name" >&2
      printf '[prompt-invoke] NEXT: use a user-facing frontdoor prompt (for example /project, /exploration, /quality, /update).\n' >&2
      exit 2
    fi
  done
fi

if [[ -z "$message_id" ]]; then
  message_id="prompt-$(date +%s)-$$"
fi
if [[ -z "$summary" ]]; then
  summary="Prompt: ${prompt_name}"
fi

# /project is the user-facing master flow. Nested prompt invocations inherit this
# context so all audit events append to the same master audit markdown file.
if [[ "$prompt_name" == "project" ]]; then
  export DIGITAL_AUDIT_MASTER_MESSAGE_ID="$message_id"
  export DIGITAL_AUDIT_MASTER_BASENAME="project"
  export DIGITAL_AUDIT_REUSE_LATEST_FOR_BASENAME="1"
fi

prompt_file="$repo_root/.github/prompts/${prompt_name}.prompt.md"
# Prompt-wrapper skill dirs (skills/prompt-<name>/) are NOT required in this repo model.
# The prompt file itself references canonical skills via its execution contract.
# These variables are retained for optional legacy lookup only; gracefully absent is expected.
prompt_skill_dir="$repo_root/.github/skills/prompt-${prompt_name}"
prompt_skill_file="$prompt_skill_dir/SKILL.md"

build_execution_stack "$@"
build_skills_trace "$@"
build_agents_trace "$@"
build_instructions_trace
build_mcp_endpoints_trace "$@"
build_communication_flow

if [[ "$prompt_name" == "quality" || "$prompt_name" == "quality-fix" ]]; then
  handoff_expected="yes"
fi

if ! is_audit_enabled; then
  exec "$@"
fi

run_with_audit_hooks "$@"
