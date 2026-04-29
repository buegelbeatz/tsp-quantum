#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# =============================================================================
# Enterprise Script: gh-token-report.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Validate GH_TOKEN presence/scopes and emit a structured YAML report.
#
# Output:
#   - YAML to stdout
#   - YAML report file under `.digital-runtime/github/reports`
# =============================================================================

# Security:
#   Reads token from environment only and writes reports under controlled runtime path.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"
required_scopes_csv="${GH_REQUIRED_SCOPES:-repo,project,read:org,read:discussion}"
IFS=',' read -r -a required_scopes <<< "$required_scopes_csv"

emit_yaml_and_exit() {
  local yaml_content="$1"
  local status_code="$2"

  local report_path
  report_path="$(github_write_yaml_report "gh-token-report" "$yaml_content")"
  printf '%b\nreport_path: "%s"\n' "$yaml_content" "$report_path"
  exit "$status_code"
}

if [[ -z "${GH_TOKEN:-}" && -z "${GITHUB_TOKEN:-}" ]]; then
  missing_yaml="api_version: \"v1\"\nkind: \"gh_token_report\"\nstatus: \"error\"\nmessage: \"GH_TOKEN is not set\"\nrequired_scopes:\n"
  for scope_name in "${required_scopes[@]}"; do
    missing_yaml+="  - \"$scope_name\"\n"
  done
  missing_yaml+="instructions:\n  - \"Create a Personal Access Token in GitHub Settings > Developer settings > Personal access tokens.\"\n  - \"For classic tokens add at least: repo, project, read:org, read:discussion.\"\n  - \"For fine-grained tokens grant repository issues/metadata/wiki write and project read/write where needed.\"\n  - \"Set GH_TOKEN in .env (never commit .env).\""
  emit_yaml_and_exit "$missing_yaml" 1
fi

if [[ -z "${GH_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  export GH_TOKEN="$GITHUB_TOKEN"
fi

api_response="$(github_run_gh api -i /user 2>/dev/null || true)"
if [[ -z "$api_response" ]]; then
  failure_yaml="api_version: \"v1\"\nkind: \"gh_token_report\"\nstatus: \"error\"\nmessage: \"Token check failed via GitHub API\"\ninstructions:\n  - \"Verify GH_TOKEN validity and network access to api.github.com.\""
  emit_yaml_and_exit "$failure_yaml" 1
fi

scopes_line="$(printf '%s\n' "$api_response" | awk 'BEGIN{IGNORECASE=1} /^x-oauth-scopes:/{sub(/^x-oauth-scopes:[[:space:]]*/,""); gsub(/\r/, ""); print; exit}')"
login_name="$(github_run_gh api /user --jq '.login' 2>/dev/null || echo "unknown")"

IFS=',' read -r -a granted_scopes_raw <<< "${scopes_line:-}"
granted_scopes=()
for scope_name in "${granted_scopes_raw[@]+${granted_scopes_raw[@]}}"; do
  trimmed="$(printf '%s' "$scope_name" | sed 's/^ *//;s/ *$//')"
  [[ -n "$trimmed" ]] && granted_scopes+=("$trimmed")
done

missing_scopes=()
for required_scope in "${required_scopes[@]}"; do
  expected="$(printf '%s' "$required_scope" | sed 's/^ *//;s/ *$//')"
  [[ -z "$expected" ]] && continue
  found=0
  for granted_scope in "${granted_scopes[@]+${granted_scopes[@]}}"; do
    if [[ "$granted_scope" == "$expected" ]]; then
      found=1
      break
    fi
  done
  [[ "$found" -eq 0 ]] && missing_scopes+=("$expected")
done

status_value="ok"
if [[ ${#missing_scopes[@]} -gt 0 ]]; then
  status_value="warning"
fi

yaml_output="api_version: \"v1\"\nkind: \"gh_token_report\"\nstatus: \"$status_value\"\nlogin: \"$login_name\"\nrequired_scopes:\n"
for scope_name in "${required_scopes[@]}"; do
  yaml_output+="  - \"$(printf '%s' "$scope_name" | sed 's/^ *//;s/ *$//')\"\n"
done
yaml_output+="granted_scopes:\n"
if [[ ${#granted_scopes[@]} -eq 0 ]]; then
  yaml_output+="  - \"none-detected\"\n"
else
  for scope_name in "${granted_scopes[@]}"; do
    yaml_output+="  - \"$scope_name\"\n"
  done
fi

yaml_output+="missing_scopes:\n"
if [[ ${#missing_scopes[@]} -eq 0 ]]; then
  yaml_output+="  - \"none\"\n"
else
  for scope_name in "${missing_scopes[@]}"; do
    yaml_output+="  - \"$scope_name\"\n"
  done
  yaml_output+="instructions:\n"
  yaml_output+="  - \"Update token scopes in GitHub Developer Settings.\"\n"
  yaml_output+="  - \"Classic token minimum: repo, project, read:org, read:discussion.\"\n"
  yaml_output+="  - \"Fine-grained token: repository issues/wiki metadata write, projects read/write as required.\"\n"
fi
exit_code=0
[[ "$status_value" == "warning" ]] && exit_code=2
emit_yaml_and_exit "$yaml_output" "$exit_code"
