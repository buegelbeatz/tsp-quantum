#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute artifact-register workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# Purpose:
#   Register a new artifact in the artifact registry with versioning metadata.

artifact_name=""
artifact_type=""
version=""
location=""
format=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      artifact_name="${2:-}"
      shift 2
      ;;
    --type)
      artifact_type="${2:-}"
      shift 2
      ;;
    --version)
      version="${2:-}"
      shift 2
      ;;
    --location)
      location="${2:-}"
      shift 2
      ;;
    --format)
      format="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$artifact_name" ]] || { echo "--name is required" >&2; exit 2; }
[[ -n "$artifact_type" ]] || { echo "--type is required" >&2; exit 2; }
[[ -n "$version" ]] || { echo "--version is required" >&2; exit 2; }
[[ -n "$location" ]] || { echo "--location is required" >&2; exit 2; }
[[ -n "$format" ]] || { echo "--format is required" >&2; exit 2; }

cat <<EOF
api_version: "v1"
kind: "artifact_registry_event"
stage: "registered"
artifact_name: "${artifact_name}"
artifact_type: "${artifact_type}"
version: "${version}"
location: "${location}"
format: "${format}"
registered_at: "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
status: "ok"
message: "Artifact registered in registry"
EOF
