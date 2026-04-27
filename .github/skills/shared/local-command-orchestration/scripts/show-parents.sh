#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Execute show-parents workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

set -euo pipefail

# Purpose:
#	Display the parent chain tree structure for the current repository,
#	showing both .git/config remotes and template-source.env references.

repo_root="$(pwd -P)"
bootstrap_lib="$repo_root/.digital-team/scripts/lib/bootstrap-common.sh"

if [[ ! -f "$bootstrap_lib" ]]; then
	printf '%s\n' "[ERROR] bootstrap-common.sh not found at $bootstrap_lib" >&2
	exit 1
fi

# shellcheck disable=SC1090
source "$bootstrap_lib"

dt_show_parent_tree "$repo_root"
