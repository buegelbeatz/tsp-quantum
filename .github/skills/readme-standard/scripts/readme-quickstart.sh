#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Derive the correct QuickStart clone-run-clean block for a digital-* repository
#   by reading .git/config (origin URL) and .digital-team/layers.yaml (parent chain).
#   Emits Markdown-formatted blocks for both public and private (GH_TOKEN) access patterns.
#   Supports GitHub HTTP(S) remotes. Bitbucket SSH/HTTP support is marked for future extension.
# Security:
#   Reads only local git metadata — no network calls, no credential exposure.
#   Token values are never emitted; only the ${GH_TOKEN} / ${BB_TOKEN} variable reference is output.

TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

GIT_CONFIG="$TARGET_DIR/.git/config"
LAYERS_YAML="$TARGET_DIR/.digital-team/layers.yaml"

# --- Helpers -----------------------------------------------------------------

die() { echo "readme-quickstart: ERROR: $*" >&2; exit 1; }

# Extract the origin URL from .git/config
get_origin_url() {
  local config="$1"
  [[ -f "$config" ]] || die ".git/config not found at $config"
  # Parse [remote "origin"] url = ... (BSD awk compatible — no \s)
  awk '/^\[remote "origin"\]/{found=1; next}
       found && /^[ \t]*url[ \t]*=[ \t]*/{
         sub(/^[ \t]*url[ \t]*=[ \t]*/, ""); print; found=0
       }
       found && /^\[/{found=0}' "$config" | tr -d '[:space:]'
}

# Detect git host from URL
detect_host() {
  local url="$1"
  case "$url" in
    *github.com*) echo "github" ;;
    *bitbucket.org*|*bitbucket.biscrum.com*) echo "bitbucket" ;;
    *) echo "unknown" ;;
  esac
}

# Extract org/repo slug from a GitHub HTTPS or SSH URL
extract_github_slug() {
  local url="$1"
  # https://github.com/org/repo.git  or  git@github.com:org/repo.git
  echo "$url" \
    | sed 's|https://github.com/||' \
    | sed 's|git@github.com:||' \
    | sed 's|\.git$||'
}

# Extract org/repo slug from a Bitbucket URL
extract_bitbucket_slug() {
  local url="$1"
  echo "$url" \
    | sed 's|https://[^/]*/||' \
    | sed 's|git@[^:]*:||' \
    | sed 's|ssh://[^/]*/||' \
    | sed 's|\.git$||'
}

# Read parent layers from layers.yaml (requires yq or python3 fallback)
get_parent_layers() {
  local yaml="$1"
  [[ -f "$yaml" ]] || { echo ""; return; }

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$yaml" <<'PYEOF'
import sys, re

yaml_file = sys.argv[1]
with open(yaml_file) as f:
    content = f.read()

# Minimal YAML list parser for layers: [{name: x, source: y}, ...]
layers = []
in_layers = False
current = {}
for line in content.splitlines():
    stripped = line.strip()
    if stripped.startswith('layers:'):
        in_layers = True
        continue
    if in_layers:
        if stripped.startswith('- name:'):
            if current:
                layers.append(current)
            current = {'name': stripped[len('- name:'):].strip()}
        elif stripped.startswith('name:') and not stripped.startswith('- name:'):
            current['name'] = stripped[len('name:'):].strip()
        elif stripped.startswith('source:'):
            current['source'] = stripped[len('source:'):].strip()
        elif stripped.startswith('visibility:'):
            current['visibility'] = stripped[len('visibility:'):].strip()
        elif stripped and not stripped.startswith('#') and not stripped.startswith('-'):
            if stripped[0].isalpha() and ':' not in stripped:
                in_layers = False
if current:
    layers.append(current)

for layer in layers:
    name = layer.get('name', '')
    source = layer.get('source', '')
    visibility = layer.get('visibility', 'public')
    print(f"{name}|{source}|{visibility}")
PYEOF
  else
    echo ""
  fi
}

# Derive a safe temp directory name from a repo URL or name
temp_name() {
  local url="$1"
  basename "$url" .git | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9-\n' '-' | sed 's/-*$//'
}

# --- Main --------------------------------------------------------------------

ORIGIN_URL="$(get_origin_url "$GIT_CONFIG")"
HOST="$(detect_host "$ORIGIN_URL")"

echo "## QuickStart"
echo ""
echo "### Pre-run workspace setup"
echo '```bash'
echo "mkdir myapp && cd myapp && git init"
echo '```'
echo ""

# Emit parent layer install steps first (from layers.yaml)
PARENT_LAYERS="$(get_parent_layers "$LAYERS_YAML")"
if [[ -n "$PARENT_LAYERS" ]]; then
  echo "Install the parent layer(s) in order before bootstrapping this repository:"
  echo ""
  step=1
  while IFS='|' read -r layer_name layer_source layer_visibility; do
    [[ -z "$layer_name" ]] && continue
    tmp_name="$(temp_name "${layer_source:-$layer_name}")"
    echo "### Step $step: Install \`$layer_name\`"
    echo ""

    case "$(detect_host "${layer_source:-}")" in
      github)
        slug="$(extract_github_slug "${layer_source}")"
        echo "**Public repo:**"
        echo '```bash'
        echo "git clone --depth 1 https://github.com/${slug}.git /tmp/${tmp_name} \\"
        echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
        echo "  && rm -rf /tmp/${tmp_name}"
        echo '```'
        echo ""
        if [[ "$layer_visibility" == "private" ]]; then
          echo "**Private repo** (set \`GH_TOKEN\` — classic PAT with \`repo\` scope, or Fine-grained with \`Contents: read\`):"
          echo '```bash'
          echo "export GH_TOKEN=ghp_xxx"
          echo ""
          echo "git clone --depth 1 https://x-access-token:\${GH_TOKEN}@github.com/${slug}.git /tmp/${tmp_name} \\"
          echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
          echo "  && rm -rf /tmp/${tmp_name}"
          echo '```'
          echo ""
        fi
        ;;
      bitbucket)
        slug="$(extract_bitbucket_slug "${layer_source}")"
        echo "> **Bitbucket** — SSH (preferred):"
        echo '```bash'
        echo "git clone --depth 1 git@bitbucket.org:${slug}.git /tmp/${tmp_name} \\"
        echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
        echo "  && rm -rf /tmp/${tmp_name}"
        echo '```'
        echo ""
        echo "> **Bitbucket** — HTTP (token-based):"
        echo '```bash'
        echo "export BB_TOKEN=<your-bitbucket-app-password>"
        echo ""
        echo "git clone --depth 1 https://x-token-auth:\${BB_TOKEN}@bitbucket.org/${slug}.git /tmp/${tmp_name} \\"
        echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
        echo "  && rm -rf /tmp/${tmp_name}"
        echo '```'
        echo ""
        ;;
      *)
        echo '```bash'
        echo "git clone --depth 1 ${layer_source} /tmp/${tmp_name} \\"
        echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
        echo "  && rm -rf /tmp/${tmp_name}"
        echo '```'
        echo ""
        ;;
    esac
    step=$((step + 1))
  done <<< "$PARENT_LAYERS"
fi

# Emit the current repo's own QuickStart
REPO_NAME="$(basename "$TARGET_DIR")"
tmp_name="$(temp_name "$ORIGIN_URL")"

echo "### Install \`$REPO_NAME\`"
echo ""

case "$HOST" in
  github)
    slug="$(extract_github_slug "$ORIGIN_URL")"
    echo "**Public repo:**"
    echo '```bash'
    echo "git clone --depth 1 https://github.com/${slug}.git /tmp/${tmp_name} \\"
    echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
    echo "  && rm -rf /tmp/${tmp_name}"
    echo '```'
    echo ""
    echo "**Private repo** (set \`GH_TOKEN\` — classic PAT with \`repo\` scope, or Fine-grained with \`Contents: read\`):"
    echo '```bash'
    echo "export GH_TOKEN=ghp_xxx"
    echo ""
    echo "git clone --depth 1 https://x-access-token:\${GH_TOKEN}@github.com/${slug}.git /tmp/${tmp_name} \\"
    echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
    echo "  && rm -rf /tmp/${tmp_name}"
    echo '```'
    ;;
  bitbucket)
    slug="$(extract_bitbucket_slug "$ORIGIN_URL")"
    echo "> **Bitbucket** — SSH (preferred):"
    echo '```bash'
    echo "git clone --depth 1 git@bitbucket.org:${slug}.git /tmp/${tmp_name} \\"
    echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
    echo "  && rm -rf /tmp/${tmp_name}"
    echo '```'
    echo ""
    echo "> **Bitbucket** — HTTP (token-based):"
    echo '```bash'
    echo "export BB_TOKEN=<your-bitbucket-app-password>"
    echo ""
    echo "git clone --depth 1 https://x-token-auth:\${BB_TOKEN}@bitbucket.org/${slug}.git /tmp/${tmp_name} \\"
    echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
    echo "  && rm -rf /tmp/${tmp_name}"
    echo '```'
    ;;
  *)
    echo '```bash'
    echo "git clone --depth 1 ${ORIGIN_URL} /tmp/${tmp_name} \\"
    echo "  && bash /tmp/${tmp_name}/install.sh \"\$PWD\" \\"
    echo "  && rm -rf /tmp/${tmp_name}"
    echo '```'
    ;;
esac

echo ""
echo "---"
