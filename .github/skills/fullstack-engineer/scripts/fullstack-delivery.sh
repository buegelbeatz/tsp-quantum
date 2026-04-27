#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Orchestrate fullstack delivery lifecycle using generic delivery wrappers.
# Security:
#   Uses validated script arguments and delegates to governed wrapper scripts.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
generic_dir="${script_dir}/../../generic-deliver/scripts"

role="fullstack-engineer"
ticket_id=""
slug=""
base_ref="master"
review_report=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ticket-id)
      ticket_id="${2:-}"
      shift 2
      ;;
    --slug)
      slug="${2:-}"
      shift 2
      ;;
    --base-ref)
      base_ref="${2:-master}"
      shift 2
      ;;
    --review-report)
      review_report="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$ticket_id" ]] || { echo "--ticket-id is required" >&2; exit 2; }
[[ -n "$slug" ]] || { echo "--slug is required" >&2; exit 2; }

prefix_output="$(${generic_dir}/delivery-prefix.sh --role "${role}" --ticket-id "${ticket_id}" --slug "${slug}")"
branch_name="$(printf '%s\n' "${prefix_output}" | sed -n 's/^branch_name: "\(.*\)"/\1/p')"
[[ -n "${branch_name}" ]] || { echo "Failed to derive branch_name from prefix output" >&2; exit 1; }

postfix_output="$(${generic_dir}/delivery-postfix.sh --role "${role}" --branch "${branch_name}" --base-ref "${base_ref}" --review-report "${review_report}")"

cat <<EOF
api_version: "v1"
kind: "fullstack_delivery"
status: "ok"
role: "${role}"
ticket_id: "${ticket_id}"
branch_name: "${branch_name}"
prefix:
$(printf '%s\n' "${prefix_output}" | sed 's/^/  /')
postfix:
$(printf '%s\n' "${postfix_output}" | sed 's/^/  /')
EOF
