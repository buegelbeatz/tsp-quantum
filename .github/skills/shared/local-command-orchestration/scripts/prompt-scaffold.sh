#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Create a governed slash-prompt scaffold (prompt file + prompt skill)
#   and synchronize prompts/help.prompt.md in one deterministic step.
# Security:
#   Validates prompt identifiers, avoids eval, and writes only inside the
#   repository .github source path.
#
# Scaffold contract — generated files include:
#
#   .github/prompts/$PROMPT_NAME.prompt.md
#     name: prompt-$PROMPT_NAME
#     Run with: make $PROMPT_NAME
#     Use only \`make ...\` invocations for tool/script execution examples.
#
#   .github/skills/prompt-$PROMPT_NAME/SKILL.md
#     ## Dependencies
#     ## Execution contract
#     ## Information flow
#     ## Information Flow
#     ## Documentation contract

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
PROMPTS_DIR="$REPO_ROOT/.github/prompts"
SKILLS_DIR="$REPO_ROOT/.github/skills"
TEMPLATES_DIR="$SCRIPT_DIR/templates"
RENDER_TEMPLATE="$SCRIPT_DIR/render_scaffold_template.py"
PROMPT_NAME="${PROMPT_NAME:-}"
PROMPT_PURPOSE="${PROMPT_PURPOSE:-describe the command purpose}"

progress() {
  local step="$1"
  printf '[progress][prompt-scaffold] %s\n' "$step"
}

if [[ -z "$PROMPT_NAME" ]]; then
  echo "[ERROR] PROMPT_NAME is required (example: make scaffold-prompt PROMPT_NAME=my-command PROMPT_PURPOSE='short purpose')" >&2
  exit 1
fi

if [[ ! "$PROMPT_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[ERROR] PROMPT_NAME must match ^[a-z0-9]+(-[a-z0-9]+)*$" >&2
  exit 1
fi

PROMPT_FILE="$PROMPTS_DIR/$PROMPT_NAME.prompt.md"
SKILL_DIR="$SKILLS_DIR/prompt-$PROMPT_NAME"
SKILL_FILE="$SKILL_DIR/SKILL.md"

if [[ -e "$PROMPT_FILE" ]]; then
  echo "[ERROR] Prompt file already exists: ${PROMPT_FILE#$REPO_ROOT/}" >&2
  exit 1
fi

if [[ -d "$SKILL_DIR" ]]; then
  echo "[ERROR] Prompt skill already exists: ${SKILL_DIR#$REPO_ROOT/}" >&2
  exit 1
fi

progress 'step=1/4 action=create-prompt-file'
mkdir -p "$PROMPTS_DIR"
python3 "$RENDER_TEMPLATE" \
  "$TEMPLATES_DIR/prompt.template.md" \
  "$PROMPT_FILE" \
  "PROMPT_NAME=$PROMPT_NAME" \
  "PROMPT_PURPOSE=$PROMPT_PURPOSE"

progress 'step=2/4 action=create-prompt-skill'
mkdir -p "$SKILL_DIR"
python3 "$RENDER_TEMPLATE" \
  "$TEMPLATES_DIR/prompt-skill.template.md" \
  "$SKILL_FILE" \
  "PROMPT_NAME=$PROMPT_NAME" \
  "PROMPT_PURPOSE=$PROMPT_PURPOSE"

progress 'step=3/4 action=sync-help-prompt'
HELP_FILE="$PROMPTS_DIR/help.prompt.md"
if [[ ! -f "$HELP_FILE" ]]; then
  echo "[ERROR] Missing help prompt file: ${HELP_FILE#$REPO_ROOT/}" >&2
  exit 1
fi

if ! grep -q "\`/$PROMPT_NAME\`" "$HELP_FILE"; then
  python3 "$SCRIPT_DIR/sync_help_prompt_entry.py" "$HELP_FILE" "$PROMPT_NAME" "$PROMPT_PURPOSE"
fi

progress 'step=4/4 action=complete'
printf 'prompt-scaffold: created %s, %s and synced %s\n' \
  "${PROMPT_FILE#$REPO_ROOT/}" \
  "${SKILL_FILE#$REPO_ROOT/}" \
  "${HELP_FILE#$REPO_ROOT/}"
