#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the task hooks install workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Installs lightweight git hooks that delegate to task hook runner.

repo_root="$(pwd)"
hooks_dir="${repo_root}/.git/hooks"
script_root="$(cd "$(dirname "$0")" && pwd)"
runner="${script_root}/task-hooks-run.sh"

if [[ ! -d "${repo_root}/.git" ]]; then
  cat <<'EOF'
api_version: "v1"
kind: "task_hooks_install"
status: "error"
error: "not_a_git_repository"
EOF
  exit 1
fi

mkdir -p "$hooks_dir"

cat >"$hooks_dir/pre-commit" <<EOF
#!/usr/bin/env bash
set -euo pipefail
bash "$runner" --hook pre-commit --task-id "\${DIGITAL_TASK_ID:-hook-task}" --role "developer" --action "pre-commit" --mode short || true
exit 0
EOF

cat >"$hooks_dir/post-commit" <<EOF
#!/usr/bin/env bash
set -euo pipefail
bash "$runner" --hook post-commit --task-id "\${DIGITAL_TASK_ID:-hook-task}" --role "developer" --action "post-commit" --mode short || true
exit 0
EOF

chmod +x "$hooks_dir/pre-commit" "$hooks_dir/post-commit"

cat <<EOF
api_version: "v1"
kind: "task_hooks_install"
status: "ok"
hooks_dir: "${hooks_dir}"
installed_hooks:
  - "pre-commit"
  - "post-commit"
EOF
