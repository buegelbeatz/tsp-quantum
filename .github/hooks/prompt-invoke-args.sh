#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Parse CLI arguments for prompt-invoke wrapper.
# Security:
#   Validates required flags and command delimiter before execution.

parse_prompt_invoke_args() {
  local command_delimiter_seen=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --prompt-name)
        prompt_name="$2"
        shift 2
        ;;
      --message-id)
        message_id="$2"
        shift 2
        ;;
      --summary)
        summary="$2"
        shift 2
        ;;
      --)
        command_delimiter_seen=1
        shift
        break
        ;;
      *)
        printf '[ERROR] Unknown argument: %s\n' "$1" >&2
        return 2
        ;;
    esac
  done

  if [[ "$command_delimiter_seen" -ne 1 ]]; then
    printf '[ERROR] Missing command after --\n' >&2
    return 2
  fi
  if [[ -z "$prompt_name" ]]; then
    printf '[ERROR] --prompt-name is required\n' >&2
    return 2
  fi
  if [[ $# -eq 0 ]]; then
    printf '[ERROR] Missing command after --\n' >&2
    return 2
  fi

  command_args=("$@")
  return 0
}
