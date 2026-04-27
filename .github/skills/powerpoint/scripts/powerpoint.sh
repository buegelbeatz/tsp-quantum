#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Build a PowerPoint deck from a source path and ensure a deterministic layer template exists.
# Security:
#   Operates only on repository-local paths and environment-provided parameters.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
RUNTIME_ROOT="${DIGITAL_TEAM_RUNTIME_ROOT:-$REPO_ROOT/.digital-runtime}"
SHARED_LAYER_ID="${DIGITAL_TEAM_SHARED_LAYER_ID:-python-runtime}"
SHARED_VENV_PATH="${DIGITAL_TEAM_SHARED_VENV_PATH:-$RUNTIME_ROOT/layers/$SHARED_LAYER_ID/venv}"

PYTHON_BIN="python3"
if [[ -x "$SHARED_VENV_PATH/bin/python3" ]]; then
  PYTHON_BIN="$SHARED_VENV_PATH/bin/python3"
elif [[ -x "$SHARED_VENV_PATH/bin/python" ]]; then
  PYTHON_BIN="$SHARED_VENV_PATH/bin/python"
fi

SOURCE="${SOURCE:-}"
LAYER="${LAYER:-${DIGITAL_LAYER_ID:-$(basename "$REPO_ROOT")}}"
QUALITY_GATE="${POWERPOINT_QUALITY_GATE:-1}"
QUALITY_STRICT="${POWERPOINT_QUALITY_STRICT:-1}"
QUALITY_MIN_SCORE="${POWERPOINT_QUALITY_MIN_SCORE:-4.0}"
REQUIRE_SCREENSHOTS="${POWERPOINT_REQUIRE_SCREENSHOTS:-1}"

if [[ -z "$SOURCE" ]]; then
  echo "SOURCE is required, example: SOURCE=.digital-artifacts/30-specification" >&2
  exit 2
fi

"$PYTHON_BIN" "$SCRIPT_DIR/create_standard_template.py" --repo-root "$REPO_ROOT" --layer "$LAYER" >/dev/null
build_payload="$($PYTHON_BIN "$SCRIPT_DIR/build_from_source.py" --repo-root "$REPO_ROOT" --layer "$LAYER" --source "$SOURCE")"
printf '%s\n' "$build_payload"

if [[ "$QUALITY_GATE" == "0" ]]; then
  exit 0
fi

generated_deck="$($PYTHON_BIN -c 'import json,sys; print(json.loads(sys.stdin.read())["output"])' <<< "$build_payload")"
template_deck="$($PYTHON_BIN -c 'import json,sys; print(json.loads(sys.stdin.read())["template"])' <<< "$build_payload")"
deck_slug="$(basename "$generated_deck" .pptx)"

if [[ "$REQUIRE_SCREENSHOTS" == "1" ]]; then
  screenshot_dir="$REPO_ROOT/docs/powerpoints/.test/$deck_slug"
  "$PYTHON_BIN" "$SCRIPT_DIR/render_slide_screenshots.py" --input "$generated_deck" --output-dir "$screenshot_dir" >/dev/null
  printf '{"status":"ok","screenshots":"%s"}\n' "$screenshot_dir"
fi

date_stamp="$(date -u +%Y-%m-%d)"
report_dir="$REPO_ROOT/.digital-artifacts/60-review/powerpoint/$date_stamp"
review_json="$report_dir/${deck_slug}-quality-review.json"
review_md="$report_dir/${deck_slug}-quality-review.md"

review_args=(
  "$SCRIPT_DIR/review_generated_deck.py"
  --deck "$generated_deck"
  --template "$template_deck"
  --min-score "$QUALITY_MIN_SCORE"
  --report-json "$review_json"
  --report-md "$review_md"
)

if [[ "$QUALITY_STRICT" != "0" ]]; then
  review_args+=(--strict)
fi

"$PYTHON_BIN" "${review_args[@]}"
