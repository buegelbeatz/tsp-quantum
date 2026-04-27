#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Discover language-expert instructions and emit deterministic guidance
#   contract for delivery/review workflows.
# Security:
#   Read-only discovery from workspace files; no network calls.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_PATH="$SCRIPT_DIR/delivery-language-bridge-lib.sh"

if [[ ! -f "$LIB_PATH" ]]; then
  echo "language bridge helper missing: $LIB_PATH" >&2
  exit 1
fi
source "$LIB_PATH"

mode=""
workspace="$(pwd)"
languages_raw=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --workspace)
      workspace="${2:-}"
      shift 2
      ;;
    --languages)
      languages_raw="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ "$mode" == "deliver" || "$mode" == "review" ]] || { echo "--mode must be deliver|review" >&2; exit 2; }
[[ -d "$workspace" ]] || { echo "--workspace must reference a directory" >&2; exit 2; }

instruction_root=""
for candidate in \
  "$workspace/.github/instructions/language-expert"; do
  if [[ -d "$candidate" ]]; then
    instruction_root="$candidate"
    break
  fi
done

declare -a detected_languages=()
if [[ -n "$languages_raw" ]]; then
  IFS=',' read -r -a detected_languages <<<"$languages_raw"
else
  detected_languages=()
  while IFS= read -r language; do
    [[ -z "$language" ]] && continue
    detected_languages+=("$language")
  done < <(detect_languages_from_git "$workspace")
fi

if [[ ${#detected_languages[@]} -eq 0 ]]; then
  detected_languages=(python)
fi

normalized_languages=()
while IFS= read -r language; do
  [[ -z "$language" ]] && continue
  normalized_languages+=("$language")
done < <(normalize_languages "${detected_languages[@]}")
detected_languages=("${normalized_languages[@]}")

emit_bridge_contract "$mode" "$workspace" "$instruction_root" "${detected_languages[@]}"
