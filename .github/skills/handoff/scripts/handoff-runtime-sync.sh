#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Synchronize canonical handoff schemas into .digital-runtime layer storage.
#   Creates runtime handoff folder, copies schema files, removes stale runtime entries,
#   and writes a deterministic handoff index with checksums.
# Security:
#   Operates only on repository-local paths. No network calls, no dynamic execution,
#   and no parsing of untrusted input beyond local file names.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: handoff-runtime-sync.sh [--repo-root <path>] [--layer <name>]

Options:
  --repo-root <path>   Repository root (default: git root from cwd, fallback script git root)
  --layer <name>       Runtime layer name (default: HANDOFF_RUNTIME_LAYER env, then copilot-instructions layer, then digital-generic-team)
EOF
}

detect_repo_root() {
  if git -C "$PWD" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$PWD" rev-parse --show-toplevel
    return 0
  fi
  if git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$SCRIPT_DIR" rev-parse --show-toplevel
    return 0
  fi
  return 1
}

detect_layer_name() {
  local repo_root="$1"
  if [[ -n "${HANDOFF_RUNTIME_LAYER:-}" ]]; then
    printf '%s\n' "$HANDOFF_RUNTIME_LAYER"
    return 0
  fi

  local copilot_file="$repo_root/.github/copilot-instructions.md"
  if [[ -f "$copilot_file" ]]; then
    local layer
    layer="$(awk '/^layer:/{print $2; exit}' "$copilot_file" | tr -d '\r' || true)"
    if [[ -n "$layer" ]]; then
      printf '%s\n' "$layer"
      return 0
    fi
  fi

  printf '%s\n' "digital-generic-team"
}

checksum_sha256() {
  local file_path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file_path" | awk '{print $1}'
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file_path" | awk '{print $1}'
    return 0
  fi
  if command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$file_path" | awk '{print $NF}'
    return 0
  fi
  echo "handoff-runtime-sync: ERROR: no SHA-256 tool available (sha256sum/shasum/openssl)" >&2
  return 2
}

REPO_ROOT=""
LAYER_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:-}"
      shift 2
      ;;
    --layer)
      LAYER_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "handoff-runtime-sync: ERROR: unknown argument '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(detect_repo_root)" || {
    echo "handoff-runtime-sync: ERROR: cannot resolve repository root" >&2
    exit 2
  }
fi

if [[ -z "$LAYER_NAME" ]]; then
  LAYER_NAME="$(detect_layer_name "$REPO_ROOT")"
fi

SOURCE_DIR="$REPO_ROOT/.github/handoffs"
TARGET_DIR="$REPO_ROOT/.digital-runtime/layers/$LAYER_NAME/handoffs"
INDEX_FILE="$TARGET_DIR/handoff-index.tsv"

[[ -d "$SOURCE_DIR" ]] || {
  echo "handoff-runtime-sync: ERROR: source directory not found: $SOURCE_DIR" >&2
  exit 2
}

mkdir -p "$TARGET_DIR"

canonical_list_file="$(mktemp)"
trap 'rm -f "$canonical_list_file"' EXIT

copied=0
while IFS= read -r src; do
  file_name="$(basename "$src")"
  printf '%s\n' "$file_name" >> "$canonical_list_file"
  cp "$src" "$TARGET_DIR/$file_name"
  copied=$((copied + 1))
done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.schema.yaml' | sort)

removed=0
while IFS= read -r runtime_file; do
  runtime_name="$(basename "$runtime_file")"
  if ! grep -Fxq "$runtime_name" "$canonical_list_file"; then
    rm -f "$runtime_file"
    removed=$((removed + 1))
  fi
done < <(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.schema.yaml' | sort)

{
  echo -e "schema\tfile\tsha256"
  while IFS= read -r file_path; do
    schema_name="$(awk '/^schema:/{print $2; exit}' "$file_path" | tr -d '\r' || true)"
    file_name="$(basename "$file_path")"
    digest="$(checksum_sha256 "$file_path")"
    echo -e "${schema_name}\t${file_name}\t${digest}"
  done < <(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.schema.yaml' | sort)
} > "$INDEX_FILE"

echo "handoff-runtime-sync: layer=$LAYER_NAME copied=$copied removed_stale=$removed index=$INDEX_FILE"
