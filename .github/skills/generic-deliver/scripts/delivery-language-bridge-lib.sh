#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Shared helper functions for language bridge detection and risk profiles.
# Security:
#   Pure local transformations; no external IO or network access.

risk_note_for_language() {
  case "$1" in
    python) echo "Type safety and dependency drift risks; enforce typing and tests." ;;
    typescript) echo "Runtime/compile mismatch risk; enforce strict typing and build checks." ;;
    bash) echo "Portability and quoting risks; enforce shellcheck-style safety and strict modes." ;;
    java) echo "Binary compatibility and dependency scope risks; enforce reproducible builds." ;;
    rust) echo "Feature-flag and ownership-complexity risks; enforce clippy and tests." ;;
    groovy) echo "Runtime DSL ambiguity risks; enforce deterministic pipeline contracts." ;;
    r) echo "Statistical reproducibility and package-version risks; enforce pinned environments." ;;
    *) echo "Unknown language risk profile; use conservative defaults and strict review." ;;
  esac
}

detect_languages_from_git() {
  local workspace="$1"
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    case "$file" in
      *.py) echo "python" ;;
      *.ts|*.tsx|*.js|*.jsx) echo "typescript" ;;
      *.sh) echo "bash" ;;
      *.java) echo "java" ;;
      *.rs) echo "rust" ;;
      *.groovy) echo "groovy" ;;
      *.R|*.r) echo "r" ;;
    esac
  done < <(git -C "$workspace" ls-files 2>/dev/null || true)
}

normalize_languages() {
  printf '%s\n' "$@" | sed '/^$/d' | awk '{print tolower($0)}' | sort -u
}

emit_bridge_contract() {
  local mode="$1"
  local workspace="$2"
  local instruction_root="$3"
  shift 3
  local detected_languages=("$@")

  local status="ok"
  printf 'api_version: "v1"\n'
  printf 'kind: "language_expert_bridge"\n'
  printf 'mode: "%s"\n' "$mode"
  printf 'workspace: "%s"\n' "$workspace"
  printf 'instruction_root: "%s"\n' "$instruction_root"
  printf 'detected_languages:\n'
  for language in "${detected_languages[@]}"; do
    printf '  - "%s"\n' "$language"
  done

  printf 'recommendations:\n'
  for language in "${detected_languages[@]}"; do
    local instruction_file=""
    local confidence="medium"
    if [[ -n "$instruction_root" && -f "$instruction_root/$language.instructions.md" ]]; then
      instruction_file="$instruction_root/$language.instructions.md"
      confidence="high"
    else
      status="warn"
    fi
    printf '  - language: "%s"\n' "$language"
    printf '    instruction: "%s"\n' "$instruction_file"
    printf '    conventions: "Apply language expert instructions before implementation and review."\n'
    printf '    risk_notes: "%s"\n' "$(risk_note_for_language "$language")"
    printf '    confidence: "%s"\n' "$confidence"
  done

  printf 'status: "%s"\n' "$status"
  printf 'conflict_resolution:\n'
  printf '  - "Project-level copilot instructions override generic language guidance."\n'
  printf '  - "Language-specific guidance overrides generic coding defaults for that language."\n'
  printf '  - "When multiple languages are present, apply guidance per touched file extension."\n'
}