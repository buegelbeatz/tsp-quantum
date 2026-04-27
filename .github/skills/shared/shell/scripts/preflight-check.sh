#!/usr/bin/env bash
# layer: digital-generic-team
# preflight-check.sh
# Validates that all local prerequisites are present and correctly configured
# before running workflow targets (make test, make board, ...).
#
# Exit codes:
#   0  — all checks pass
#   2  — one or more prerequisites are missing or misconfigured
#
# Usage:
#   bash .github/skills/shared/shell/scripts/preflight-check.sh
#   PREFLIGHT_REPO_ROOT=/path/to/repo bash preflight-check.sh
#
# Information Flow:
#   producer:  operator / CI environment
#   consumer:  Makefile workflow targets (test, quality, board, pull, …)
#   trigger:   invoked as a Make prerequisite before any substantive action
#   payload:   pass/fail for python3 ≥3.11, git ≥2.40, docker|podman,
#              gh ≥2.45, .env present, GH_TOKEN non-empty,
#              and container image availability for registered tools

set -uo pipefail

# ── Color helpers ─────────────────────────────────────────────────────────────
_tty_colors() {
  if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'
    YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
  else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
  fi
}
_tty_colors

_ok()   { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
_fail() { printf "${RED}[✗]${NC} %s\n" "$*" >&2; }
_warn() { printf "${YELLOW}[!]${NC} %s\n" "$*" >&2; }
_hint() { printf "    ${CYAN}→${NC} %s\n" "$*" >&2; }

# ── Platform detection ────────────────────────────────────────────────────────
_detect_os() {
  case "$(uname -s 2>/dev/null)" in
    Darwin)  echo "macos" ;;
    Linux)
      if grep -qi fedora /etc/os-release 2>/dev/null || [[ -f /etc/fedora-release ]]; then
        echo "fedora"
      elif grep -qi ubuntu /etc/os-release 2>/dev/null || [[ -f /etc/debian_version ]]; then
        echo "ubuntu"
      else
        echo "linux"
      fi
      ;;
    MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

_install_hint() {
  local tool="$1"
  local os
  os=$(_detect_os)
  case "$tool" in
    python3)
      case "$os" in
        macos)   _hint "macOS:    brew install python@3.11" ;;
        ubuntu)  _hint "Ubuntu:   sudo apt-get install -y python3.11 python3.11-venv" ;;
        fedora)  _hint "Fedora:   sudo dnf install -y python3.11" ;;
        windows) _hint "Windows:  winget install Python.Python.3.11" ;;
        *)       _hint "See https://www.python.org/downloads/" ;;
      esac
      ;;
    git)
      case "$os" in
        macos)   _hint "macOS:    brew install git" ;;
        ubuntu)  _hint "Ubuntu:   sudo apt-get install -y git" ;;
        fedora)  _hint "Fedora:   sudo dnf install -y git" ;;
        windows) _hint "Windows:  winget install Git.Git" ;;
        *)       _hint "See https://git-scm.com/downloads" ;;
      esac
      ;;
    docker)
      case "$os" in
        macos)   _hint "macOS:    brew install --cask docker  (Docker Desktop)" ;;
        ubuntu)  _hint "Ubuntu:   https://docs.docker.com/engine/install/ubuntu/" ;;
        fedora)  _hint "Fedora:   sudo dnf install -y moby-engine" ;;
        windows) _hint "Windows:  winget install Docker.DockerDesktop" ;;
        *)       _hint "See https://docs.docker.com/get-docker/" ;;
      esac
      ;;
    podman)
      case "$os" in
        macos)   _hint "macOS:    brew install podman" ;;
        ubuntu)  _hint "Ubuntu:   sudo apt-get install -y podman" ;;
        fedora)  _hint "Fedora:   sudo dnf install -y podman" ;;
        windows) _hint "Windows:  winget install RedHat.Podman" ;;
        *)       _hint "See https://podman.io/getting-started/installation" ;;
      esac
      ;;
    gh)
      case "$os" in
        macos)   _hint "macOS:    brew install gh" ;;
        ubuntu)  _hint "Ubuntu:   sudo apt-get install -y gh  (or GitHub deb repo)" ;;
        fedora)  _hint "Fedora:   sudo dnf install -y gh" ;;
        windows) _hint "Windows:  winget install GitHub.cli" ;;
        *)       _hint "See https://cli.github.com/manual/installation" ;;
      esac
      ;;
  esac
}

# ── Version comparison ────────────────────────────────────────────────────────
# Returns 0 if $1 (actual) >= $2 (minimum), normalized as X.Y.Z
_version_ge() {
  local actual="$1" minimum="$2"
  # Pad both to 3 components
  local a1 a2 a3 m1 m2 m3
  IFS=. read -r a1 a2 a3 <<< "${actual}.0.0"
  IFS=. read -r m1 m2 m3 <<< "${minimum}.0.0"
  a1=${a1:-0}; a2=${a2:-0}; a3=${a3:-0}
  m1=${m1:-0}; m2=${m2:-0}; m3=${m3:-0}
  if   (( a1 > m1 )); then return 0
  elif (( a1 < m1 )); then return 1
  elif (( a2 > m2 )); then return 0
  elif (( a2 < m2 )); then return 1
  elif (( a3 >= m3 )); then return 0
  else return 1
  fi
}

_extract_version() {
  echo "$1" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1
}

# ── Individual checks ─────────────────────────────────────────────────────────
FAILURES=0
PREFLIGHT_CONTAINER_ENGINE=""

_check_python3() {
  if ! command -v python3 &>/dev/null; then
    _fail "python3 not found  (required: >= 3.11)"
    _install_hint python3
    FAILURES=$(( FAILURES + 1 ))
    return
  fi
  local raw ver
  raw=$(python3 --version 2>&1)
  ver=$(_extract_version "$raw")
  if _version_ge "$ver" "3.11"; then
    _ok "python3 $ver  (>= 3.11)"
  else
    _fail "python3 $ver is too old  (required: >= 3.11)"
    _install_hint python3
    FAILURES=$(( FAILURES + 1 ))
  fi
}

_check_git() {
  if ! command -v git &>/dev/null; then
    _fail "git not found  (required: >= 2.40)"
    _install_hint git
    FAILURES=$(( FAILURES + 1 ))
    return
  fi
  local raw ver
  raw=$(git --version 2>&1)
  ver=$(_extract_version "$raw")
  if _version_ge "$ver" "2.40"; then
    _ok "git $ver  (>= 2.40)"
  else
    _fail "git $ver is too old  (required: >= 2.40)"
    _install_hint git
    FAILURES=$(( FAILURES + 1 ))
  fi
}

_check_container_runtime() {
  local found=0
  if command -v docker &>/dev/null; then
    local raw ver
    raw=$(docker --version 2>&1)
    ver=$(_extract_version "$raw")
    _ok "docker $ver found"
    found=1
    [[ -z "$PREFLIGHT_CONTAINER_ENGINE" ]] && PREFLIGHT_CONTAINER_ENGINE="docker"
  fi
  if command -v podman &>/dev/null; then
    local raw ver
    raw=$(podman --version 2>&1)
    ver=$(_extract_version "$raw")
    _ok "podman $ver found"
    found=1
    PREFLIGHT_CONTAINER_ENGINE="podman"
  fi
  if [[ $found -eq 0 ]]; then
    _fail "No container runtime found  (docker or podman required)"
    _warn "Install docker:"
    _install_hint docker
    _warn "Or install podman:"
    _install_hint podman
    FAILURES=$(( FAILURES + 1 ))
  fi
}

_resolve_default_image_from_spec() {
  local image_spec="$1"

  if [[ -z "$image_spec" ]]; then
    return 1
  fi

  if [[ "$image_spec" != *"="* ]]; then
    printf '%s\n' "$image_spec"
    return 0
  fi

  local entry
  local default_image=""
  local IFS_BACKUP="$IFS"
  IFS=';'
  for entry in $image_spec; do
    IFS="$IFS_BACKUP"
    if [[ "${entry%%=*}" == "default" ]]; then
      default_image="${entry#*=}"
      break
    fi
    IFS=';'
  done
  IFS="$IFS_BACKUP"

  [[ -n "$default_image" ]] || return 1
  printf '%s\n' "$default_image"
}

_image_in_list() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

_check_container_images_available() {
  local repo_root="$1"
  local validate_images="${PREFLIGHT_VALIDATE_CONTAINER_IMAGES:-1}"
  local tools_csv="$repo_root/.github/skills/shared/shell/scripts/metadata/tools.csv"

  if [[ "$validate_images" != "1" ]]; then
    _warn "Skipping container image availability checks (PREFLIGHT_VALIDATE_CONTAINER_IMAGES=$validate_images)"
    return
  fi

  [[ -f "$tools_csv" ]] || {
    _fail "tools.csv not found for image availability checks: $tools_csv"
    FAILURES=$(( FAILURES + 1 ))
    return
  }

  if [[ -z "$PREFLIGHT_CONTAINER_ENGINE" ]]; then
    _warn "No container engine selected; skipping image checks"
    return
  fi

  local images=()
  local image_count=0
  local line image_spec image
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == tool_name,* ]] && continue
    image_spec="$(printf '%s\n' "$line" | awk -F',' '{print $3}')"
    image="$(_resolve_default_image_from_spec "$image_spec" 2>/dev/null || true)"
    [[ -n "$image" ]] || continue
    if [[ $image_count -eq 0 ]]; then
      images+=("$image")
      image_count=1
    elif ! _image_in_list "$image" "${images[@]}"; then
      images+=("$image")
      image_count=$(( image_count + 1 ))
    fi
  done < "$tools_csv"

  local image_failures=0
  local container_tool="$PREFLIGHT_CONTAINER_ENGINE"
  local current
  if [[ $image_count -eq 0 ]]; then
    _warn "No container images resolved from tools.csv; skipping image checks"
    return
  fi

  # Authenticate to GHCR if token is available (reads GHCR_TOKEN from environment)
  local ghcr_token="${GHCR_TOKEN:-}"
  if [[ -n "$ghcr_token" ]]; then
    local ghcr_namespace="${GHCR_NAMESPACE:-}"
    local ghcr_user="${ghcr_namespace#ghcr.io/}"
    ghcr_user="${ghcr_user%%/*}"
    if [[ -n "$ghcr_user" ]]; then
      if printf '%s\n' "$ghcr_token" | "$container_tool" login ghcr.io -u "$ghcr_user" --password-stdin >/dev/null 2>&1; then
        _ok "authenticated to ghcr.io as $ghcr_user"
      else
        _warn "GHCR login failed for $ghcr_user; clearing credentials so public pulls remain unaffected"
        "$container_tool" logout ghcr.io >/dev/null 2>&1 || true
      fi
    fi
  fi

  for current in "${images[@]}"; do
    if [[ "$container_tool" == "podman" ]]; then
      if podman image exists "$current" >/dev/null 2>&1 || podman pull "$current" >/dev/null 2>&1; then
        _ok "container image available: $current"
      else
        _fail "container image unavailable: $current"
        image_failures=$(( image_failures + 1 ))
      fi
    else
      if docker image inspect "$current" >/dev/null 2>&1 || docker pull "$current" >/dev/null 2>&1; then
        _ok "container image available: $current"
      else
        _fail "container image unavailable: $current"
        image_failures=$(( image_failures + 1 ))
      fi
    fi
  done

  if [[ $image_failures -gt 0 ]]; then
    _hint "Pre-pull images or fix registry access before running workflows."
    FAILURES=$(( FAILURES + image_failures ))
  fi
}

_check_gh() {
  if ! command -v gh &>/dev/null; then
    _fail "gh (GitHub CLI) not found  (required: >= 2.45)"
    _install_hint gh
    FAILURES=$(( FAILURES + 1 ))
    return
  fi
  local raw ver
  raw=$(gh --version 2>&1 | head -1)
  ver=$(_extract_version "$raw")
  if _version_ge "$ver" "2.45"; then
    _ok "gh $ver  (>= 2.45)"
  else
    _fail "gh $ver is too old  (required: >= 2.45)"
    _install_hint gh
    FAILURES=$(( FAILURES + 1 ))
  fi
}

_check_env_file() {
  local repo_root="$1"
  local env_file="$repo_root/.env"

  if [[ ! -f "$env_file" ]]; then
    _fail ".env not found at $env_file"
    _hint "Copy the template:   cp .env.example .env"
    _hint "Then fill in:        GH_TOKEN=ghp_yourtoken  (mandatory)"
    FAILURES=$(( FAILURES + 1 ))
    return
  fi
  _ok ".env file exists"

  # Check that GH_TOKEN is non-empty (strip quotes and whitespace)
  local gh_token
  gh_token=$(grep -E '^GH_TOKEN=' "$env_file" 2>/dev/null | head -1 \
    | cut -d= -f2- | tr -d '"'"'" | tr -d ' ' | tr -d $'\t')
  if [[ -z "$gh_token" ]]; then
    _fail "GH_TOKEN is missing or empty in .env  (mandatory)"
    _hint "Add to .env:     GH_TOKEN=ghp_yourtoken"
    _hint "Required scopes: repo, project, read:org, read:discussion"
    _hint "Create at:       https://github.com/settings/tokens"
    FAILURES=$(( FAILURES + 1 ))
  else
    _ok "GH_TOKEN is set"
  fi
}

_check_no_root_venv() {
  local repo_root="$1"
  if [[ -d "$repo_root/.venv" ]]; then
    _fail "repository-root .venv is forbidden in this layer"
    _hint "Use .digital-runtime/layers/python-runtime/venv only"
    _hint "Cleanup: rm -rf .venv"
    FAILURES=$(( FAILURES + 1 ))
    return
  fi
  _ok "No forbidden repository-root .venv detected"
}

_check_direct_tool_guard() {
  local repo_root="$1"
  local guard_script="$repo_root/.github/skills/shared/shell/scripts/guard-direct-tool-calls.py"
  local allowlist="$repo_root/.github/skills/shared/shell/scripts/metadata/direct-tool-allowlist.txt"

  if python3 "$guard_script" --repo-root "$repo_root" --allowlist "$allowlist" >/dev/null 2>&1; then
    _ok "Direct tool invocation guard passed"
    return
  fi

  _fail "Direct tool invocation guard failed"
  _hint "Run: python3 $guard_script --repo-root $repo_root --allowlist $allowlist"
  FAILURES=$(( FAILURES + 1 ))
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  local repo_root="${PREFLIGHT_REPO_ROOT:-$PWD}"

  printf "\nPreflight checks — validating prerequisites\n"
  printf "============================================\n"

  _check_python3
  _check_git
  _check_container_runtime
  _check_gh
  _check_env_file "$repo_root"
  _check_no_root_venv "$repo_root"
  _check_container_images_available "$repo_root"
  _check_direct_tool_guard "$repo_root"

  printf "\n"
  if [[ $FAILURES -eq 0 ]]; then
    _ok "All prerequisites satisfied — ready to run."
    printf "\n"
    exit 0
  else
    _fail "$FAILURES prerequisite(s) failed — resolve the issues above before continuing."
    printf "\n"
    exit 2
  fi
}

main "$@"
