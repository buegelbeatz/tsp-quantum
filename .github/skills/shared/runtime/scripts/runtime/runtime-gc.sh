#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Safely clean eligible .digital-runtime artifacts with dry-run default behavior.
# Security:
#   Operates only under .digital-runtime and never removes persistent classes.

usage() {
  cat <<'EOF'
Usage: runtime-gc.sh [options]

Options:
  --repo-root <path>          Repository root (default: git root or cwd)
  --mode <dry-run|apply>      Cleanup mode (default: dry-run)
  --short-ttl-days <int>      TTL for tmp/temp (default: 7)
  --medium-ttl-days <int>     TTL for reports/chrome (default: 30)
  --allowlist-file <path>     Optional allowlist file for protected paths
  --help                      Show help
EOF
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mode="dry-run"
short_ttl_days=7
medium_ttl_days=30
allowlist_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      repo_root="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --short-ttl-days)
      short_ttl_days="${2:-}"
      shift 2
      ;;
    --medium-ttl-days)
      medium_ttl_days="${2:-}"
      shift 2
      ;;
    --allowlist-file)
      allowlist_file="${2:-}"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$mode" != "dry-run" && "$mode" != "apply" ]]; then
  echo "[ERROR] --mode must be dry-run or apply (got: $mode)" >&2
  exit 2
fi

runtime_root="$repo_root/.digital-runtime"
reports_dir="$runtime_root/reports"

if [[ ! -d "$runtime_root" ]]; then
  echo "status: ok"
  echo "mode: $mode"
  echo "message: runtime root not found; nothing to clean"
  exit 0
fi

mkdir -p "$reports_dir"

max_report_candidates=80

candidate_count=0
removed_count=0
reclaimed_bytes=0
skipped_pinned_count=0
skipped_active_session_count=0

report_file="$reports_dir/runtime-gc-$(date +%Y%m%d-%H%M%S).log"

declare -a candidates=()
declare -a skipped_pinned=()
declare -a skipped_active=()

declare -a short_dirs=(
  "$runtime_root/tmp"
  "$runtime_root/temp"
)
declare -a medium_dirs=(
  "$runtime_root/reports"
  "$runtime_root/chrome"
)

declare -a persistent_prefixes=(
  "$runtime_root/layers"
  "$runtime_root/handoffs"
)

is_persistent_path() {
  local path="$1"
  local prefix
  for prefix in "${persistent_prefixes[@]}"; do
    [[ "$path" == "$prefix"* ]] && return 0
  done
  return 1
}

path_in_allowlist() {
  local path="$1"
  [[ -n "$allowlist_file" && -f "$allowlist_file" ]] || return 1
  grep -Fqx "$path" "$allowlist_file"
}

is_pinned_path() {
  local path="$1"
  local dir
  dir="$(dirname "$path")"
  [[ -e "$path.pin" || -e "$dir/.pin" ]] && return 0
  path_in_allowlist "$path" && return 0
  return 1
}

is_active_session_path() {
  local path="$1"
  [[ "$path" == "$runtime_root/handoffs/"* ]] && return 0
  return 1
}

path_size_bytes() {
  local path="$1"
  local size_output=""
  if [[ -f "$path" ]]; then
    size_output="$(stat -c %s "$path" 2>/dev/null || true)"
    if [[ "$size_output" =~ ^[0-9]+$ ]]; then
      echo "$size_output"
      return 0
    fi

    size_output="$(stat -f %z "$path" 2>/dev/null || true)"
    if [[ "$size_output" =~ ^[0-9]+$ ]]; then
      echo "$size_output"
      return 0
    fi

    echo 0
  elif [[ -d "$path" ]]; then
    du -sk "$path" 2>/dev/null | awk '{print $1 * 1024}'
  else
    echo 0
  fi
}

maybe_collect_candidate() {
  local path="$1"

  [[ -e "$path" ]] || return 0
  is_persistent_path "$path" && return 0

  if is_pinned_path "$path"; then
    skipped_pinned+=("$path")
    skipped_pinned_count=$((skipped_pinned_count + 1))
    return 0
  fi

  if is_active_session_path "$path"; then
    skipped_active+=("$path")
    skipped_active_session_count=$((skipped_active_session_count + 1))
    return 0
  fi

  candidates+=("$path")
  candidate_count=$((candidate_count + 1))
}

collect_from_dir() {
  local dir="$1"
  local ttl_days="$2"
  [[ -d "$dir" ]] || return 0

  local path
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    maybe_collect_candidate "$path"
  done < <(find "$dir" -mindepth 1 -mtime +"$ttl_days" -print 2>/dev/null | LC_ALL=C sort -u)
}

for d in "${short_dirs[@]}"; do
  collect_from_dir "$d" "$short_ttl_days"
done
for d in "${medium_dirs[@]}"; do
  collect_from_dir "$d" "$medium_ttl_days"
done

{
  echo "status: ok"
  echo "mode: $mode"
  echo "runtime_root: $runtime_root"
  echo "short_ttl_days: $short_ttl_days"
  echo "medium_ttl_days: $medium_ttl_days"
  echo "candidate_count: $candidate_count"
  echo "skipped_pinned_count: $skipped_pinned_count"
  echo "skipped_active_session_count: $skipped_active_session_count"
  echo "report_generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "candidate_sample_limit: $max_report_candidates"
  echo "candidates_sample:"
  if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "  - (none)"
  else
    shown=0
    for c in "${candidates[@]}"; do
      ((shown >= max_report_candidates)) && break
      echo "  - $c"
      shown=$((shown + 1))
    done
    if (( candidate_count > max_report_candidates )); then
      echo "  - ... truncated ..."
    fi
  fi
} | tee "$report_file"

if [[ "$mode" == "apply" ]]; then
  for path in "${candidates[@]}"; do
    size="$(path_size_bytes "$path")"
    if [[ -d "$path" ]]; then
      rm -rf "$path"
    else
      rm -f "$path"
    fi
    removed_count=$((removed_count + 1))
    reclaimed_bytes=$((reclaimed_bytes + size))
  done

  declare -a cleanup_scan_dirs=()
  for candidate_dir in "$runtime_root/tmp" "$runtime_root/temp" "$runtime_root/chrome" "$runtime_root/reports"; do
    [[ -d "$candidate_dir" ]] && cleanup_scan_dirs+=("$candidate_dir")
  done
  if [[ ${#cleanup_scan_dirs[@]} -gt 0 ]]; then
    find "${cleanup_scan_dirs[@]}" -type d -empty 2>/dev/null | LC_ALL=C sort | while IFS= read -r empty_dir; do
      [[ "$empty_dir" == "$reports_dir" ]] && continue
      rmdir "$empty_dir" 2>/dev/null || true
    done
  fi
fi

echo "removed_count: $removed_count" | tee -a "$report_file"
echo "reclaimed_bytes: $reclaimed_bytes" | tee -a "$report_file"
echo "report_file: $report_file"
