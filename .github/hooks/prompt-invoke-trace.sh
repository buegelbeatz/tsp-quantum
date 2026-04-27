#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Build trace metadata passed to post-message audit hook.
# Security:
#   Only inspects repository-local prompt/skill/agent files and runtime command text.

build_execution_stack() {
  execution_stack="prompt=${prompt_name} -> wrapper=prompt-invoke -> command=$*"
  if [[ -f "$prompt_file" ]]; then
    execution_stack="${execution_stack} -> source=.github/prompts/${prompt_name}.prompt.md"
  fi
  # Prompt-wrapper skill (skills/prompt-<name>/SKILL.md) does NOT exist in this repo model.
  # Canonical skills are referenced from the prompt file's execution contract instead.
  if [[ -f "$prompt_skill_file" ]]; then
    execution_stack="${execution_stack} -> source=.github/skills/prompt-${prompt_name}/SKILL.md"
  fi
}

build_skills_trace() {
  skills_trace=""
  if [[ -d "$prompt_skill_dir" ]]; then
    skills_trace="$(add_unique_csv "prompt-${prompt_name}" "$skills_trace")"
  fi
  while IFS= read -r dep_skill; do
    [[ -n "$dep_skill" ]] || continue
    skills_trace="$(add_unique_csv "$dep_skill" "$skills_trace")"
  done < <(extract_dependencies_from_skill "$prompt_skill_file")

  while IFS= read -r cmd_skill; do
    [[ -n "$cmd_skill" ]] || continue
    skills_trace="$(add_unique_csv "$cmd_skill" "$skills_trace")"
  done < <(printf '%s\n' "$*" | sed -nE 's#.*\.github/skills/([^/]+)/.*#\1#p')

  if [[ "$summary" == *"quality-expert"* || "$*" == *"quality-expert"* ]]; then
    skills_trace="$(add_unique_csv "quality-expert" "$skills_trace")"
  fi
  if [[ "$summary" == *"layer-quality"* || "$*" == *"layer_quality"* ]]; then
    skills_trace="$(add_unique_csv "shared/orchestration" "$skills_trace")"
  fi
  skills_trace="$(add_unique_csv "shared/task-orchestration" "$skills_trace")"
  skills_trace="$(add_unique_csv "shared/shell" "$skills_trace")"
}

build_agents_trace() {
  agents_trace="copilot"
  if [[ "$prompt_name" == "powerpoint" ]]; then
    agents_trace="$(add_unique_csv "ux-designer" "$agents_trace")"
    return
  fi
  local agent_context=""
  if [[ -f "$prompt_file" ]]; then
    agent_context+=" $(cat "$prompt_file")"
  fi
  if [[ -f "$prompt_skill_file" ]]; then
    agent_context+=" $(cat "$prompt_skill_file")"
  fi
  agent_context+=" ${summary} $*"

  for agent_file in "$repo_root"/.github/agents/*.agent.md; do
    [[ -f "$agent_file" ]] || continue
    local agent_name="${agent_file##*/}"
    agent_name="${agent_name%.agent.md}"
    if [[ "$agent_context" == *"$agent_name"* ]]; then
      agents_trace="$(add_unique_csv "$agent_name" "$agents_trace")"
    fi
  done
}

build_instructions_trace() {
  instructions_trace="governance-layer/prompt-governance.instructions.md, shared/handoff.instructions.md"
  local source_file=""
  for source_file in "$prompt_file" "$prompt_skill_file"; do
    [[ -f "$source_file" ]] || continue
    while IFS= read -r rel_path; do
      [[ -n "$rel_path" ]] || continue
      instructions_trace="$(add_unique_csv "$rel_path" "$instructions_trace")"
    done < <(extract_instruction_paths_from_file "$source_file")
  done

  while IFS= read -r traced_skill; do
    traced_skill="$(printf '%s' "$traced_skill" | xargs 2>/dev/null || true)"
    [[ -n "$traced_skill" ]] || continue
    append_instruction_hints_for_skill "$traced_skill"
  done < <(printf '%s\n' "$skills_trace" | tr ',' '\n')
}

build_mcp_endpoints_trace() {
  mcp_endpoints_trace=""
  while IFS= read -r mcp_entry; do
    mcp_entry="$(printf '%s' "$mcp_entry" | xargs 2>/dev/null || true)"
    [[ -n "$mcp_entry" ]] || continue
    mcp_endpoints_trace="$(add_unique_csv "$mcp_entry" "$mcp_endpoints_trace")"
  done < <(extract_mcp_endpoints_from_command "$*")
}
