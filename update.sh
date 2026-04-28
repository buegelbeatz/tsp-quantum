#!/usr/bin/env bash

set -euo pipefail

# Purpose:
#   Phase 1 — Refresh .github/ from inherited layers (defined in .digital-team/layers.yaml).
#   Phase 2 — Adapt .claude/ from the updated .github/ (commands, agents, CLAUDE.md).
#
# Usage: Invoke via /update Claude Code command — not directly.
#        bash update.sh [--source=<new-source-for-first-layer>]
#
# Container execution:
#   Python tasks use shared/shell run-tool.sh (container-aware) when available,
#   falling back to local python3. Tool images are defined in
#   .github/skills/shared/shell/scripts/metadata/tools.csv.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LAYERS_YAML="$REPO_ROOT/.digital-team/layers.yaml"
OVERRIDES_YAML="$REPO_ROOT/.digital-team/overrides.yaml"
RUNTIME_DIR="$REPO_ROOT/.digital-runtime"
TEMP_DIR="$RUNTIME_DIR/tmp"
GITHUB_DIR="$REPO_ROOT/.github"
CLAUDE_DIR="$REPO_ROOT/.claude"
UPDATE_RUNTIME_PY="$GITHUB_DIR/skills/shared/runtime/scripts/update_runtime.py"
PATH_GUARD_LIB="$GITHUB_DIR/skills/shared/shell/scripts/lib/path_guard.sh"

if [[ -f "$PATH_GUARD_LIB" ]]; then
    # shellcheck source=/dev/null
    source "$PATH_GUARD_LIB"
fi

# During update phase 1, .github content can be temporarily pruned and recreated.
# If path_guard was sourced from an older layer snapshot, run-tool.sh may disappear
# momentarily and break path normalization. Force a resilient fallback here.
if declare -f _path_guard_realpath >/dev/null 2>&1; then
    _path_guard_realpath() {
        local target="$1"
        local tool_runner
        tool_runner="$GITHUB_DIR/skills/shared/shell/scripts/run-tool.sh"
        if [[ -f "$tool_runner" ]]; then
            bash "$tool_runner" python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$target"
        else
            python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$target"
        fi
    }
fi

# Fallback for bootstrap phase: before .github is materialized in a target repo,
# path_guard.sh is unavailable and safe_mkdir_p would be undefined.
if ! declare -f safe_mkdir_p >/dev/null 2>&1; then
    safe_mkdir_p() {
        local dir_path="$1"
        mkdir -p "$dir_path"
    }
fi

# ── Logging ───────────────────────────────────────────────────────────────────
log()   { printf '[update] %s\n' "$*"; }
warn()  { printf '[update] WARNING: %s\n' "$*" >&2; }
error() { printf '[update] ERROR: %s\n' "$*" >&2; exit 1; }

# ── Container-aware Python runner ─────────────────────────────────────────────
# Uses shared/shell run-tool.sh for container fallback when available.
_SHARED_SHELL="$GITHUB_DIR/skills/shared/shell/scripts"
run_python() {
    if [[ -f "$_SHARED_SHELL/run-tool.sh" ]]; then
        RUN_TOOL_PREFER_CONTAINER=0 SHARED_SHELL_REPO_ROOT="$REPO_ROOT" bash "$_SHARED_SHELL/run-tool.sh" python3 "$@"
    else
        python3 "$@"
    fi
}

# ── Bootstrap guarantee: ensure .digital-runtime/layers/python-runtime/venv exists ──
# This MUST run before any Python calls to guarantee python3 is available.
ensure_bootstrap_venv() {
    local venv_dir="$RUNTIME_DIR/layers/python-runtime"
    local venv_bin="$venv_dir/venv/bin"
    
    # If venv already exists and is healthy, skip
    if [[ -x "$venv_bin/python3" ]]; then
        return 0
    fi
    
    log "bootstrap: creating .digital-runtime/layers/python-runtime/venv..."
    safe_mkdir_p "$venv_dir" "update bootstrap venv"
    python3 -m venv "$venv_dir/venv" 2>&1 || error "failed to create bootstrap venv"
}

ensure_pyyaml() {
    if ! python3 -c "import yaml" 2>/dev/null; then
        log "installing pyyaml..."
        python3 -m pip install --quiet pyyaml
    fi
}

# ── Repo name detection ───────────────────────────────────────────────────────
detect_repo_name() {
    local remote_url
    remote_url="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
    if [[ -n "$remote_url" ]]; then
        basename "$remote_url" .git
        return
    fi
    basename "$REPO_ROOT"
}

# ── Parse layers.yaml → "name|source" per line (bash to avoid bootstrap dependency) ───
get_layers() {
    [[ -f "$LAYERS_YAML" ]] || return 0
    
    # Parse YAML: extract layer name and source pairs
    # Handles format:
    #   layers:
    #   - name: layer-name
    #     source: https://example.com/repo.git
    
    local in_layers=0
    local current_name=""
    local current_source=""
    
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Check if we're in layers section
        if [[ "$line" =~ ^layers: ]]; then
            in_layers=1
            continue
        fi
        
        # If not in layers, skip
        [[ $in_layers -eq 0 ]] && continue
        
        # Parse "- name:" line
        if [[ "$line" =~ ^[[:space:]]*-[[:space:]]+name:[[:space:]]*(.+)$ ]]; then
            # Flush previous entry if complete
            if [[ -n "$current_name" && -n "$current_source" ]]; then
                printf '%s|%s\n' "$current_name" "$current_source"
            fi
            current_name="${BASH_REMATCH[1]}"
            current_source=""
            continue
        fi
        
        # Parse "source:" line
        if [[ "$line" =~ ^[[:space:]]+source:[[:space:]]*(.+)$ ]]; then
            current_source="${BASH_REMATCH[1]}"
            continue
        fi
        
        # Exit layers section if we hit non-indented content
        if [[ "$line" =~ ^[^[:space:]] && ! "$line" =~ ^layers: ]]; then
            in_layers=0
            if [[ -n "$current_name" && -n "$current_source" ]]; then
                printf '%s|%s\n' "$current_name" "$current_source"
            fi
            break
        fi
    done < "$LAYERS_YAML"
    
    # Flush last entry if reached EOF
    if [[ -n "$current_name" && -n "$current_source" ]]; then
        printf '%s|%s\n' "$current_name" "$current_source"
    fi
}

# ── Inject/update layer metadata across supported source files ───────────────
inject_layer_frontmatter() {
    local target_dir="$1" layer_name="$2"
    [[ -d "$target_dir" ]] || return 0
    run_python "$UPDATE_RUNTIME_PY" inject-layer "$target_dir" "$layer_name"
}

write_empty_backup_manifest() {
    local current_repo="$1" manifest_path="$2"
    safe_mkdir_p "$(dirname "$manifest_path")" "write layers manifest"
    printf '{\n  "schema": "local_backup_manifest_v1",\n  "current_repo": "%s",\n  "local_files": [],\n  "untagged_files": []\n}\n' "$current_repo" > "$manifest_path"
}

# ── Remove auto-generated stage prompts before backup ────────────────────────
# Stage prompts (e.g. discovery.prompt.md) are generated from stage instruction
# frontmatter in Phase 4 and must never be treated as authored local overrides.
_prune_generated_stage_prompts() {
    local prompts_dir="$GITHUB_DIR/prompts"
    local stages_dir="$GITHUB_DIR/instructions/stages"
    [[ -d "$prompts_dir" ]] || return 0
    local stage_commands=""
    if [[ -f "$UPDATE_RUNTIME_PY" ]]; then
        stage_commands="$(run_python "$UPDATE_RUNTIME_PY" stage-commands "$GITHUB_DIR" "$(detect_repo_name)" 2>/dev/null || true)"
    fi

    local command pruned=0
    if [[ -n "$stage_commands" ]]; then
        while IFS= read -r command; do
            [[ -z "$command" ]] && continue
            [[ -f "$prompts_dir/${command}.prompt.md" ]] \
                && { rm -f "$prompts_dir/${command}.prompt.md"; pruned=$((pruned+1)); }
            [[ -f "$prompts_dir/${command}-board.prompt.md" ]] \
                && { rm -f "$prompts_dir/${command}-board.prompt.md"; pruned=$((pruned+1)); }
        done <<< "$stage_commands"
    elif [[ -d "$stages_dir" ]]; then
        local stage_file
        while IFS= read -r -d '' stage_file; do
            command=$(grep -m1 '^command:[[:space:]]*' "$stage_file" 2>/dev/null || true)
            command=$(printf '%s' "$command" | sed 's/^command:[[:space:]]*//' | tr -d '[:space:]')
            [[ -z "$command" ]] && continue
            [[ -f "$prompts_dir/${command}.prompt.md" ]] \
                && { rm -f "$prompts_dir/${command}.prompt.md"; pruned=$((pruned+1)); }
            [[ -f "$prompts_dir/${command}-board.prompt.md" ]] \
                && { rm -f "$prompts_dir/${command}-board.prompt.md"; pruned=$((pruned+1)); }
        done < <(find "$stages_dir" -name "*.instructions.md" -type f -print0)
    fi

    [[ $pruned -gt 0 ]] && log "  pruned $pruned generated stage prompt(s) before backup"
    return 0
}

# ── Backup local files (layer == current_repo or no layer key) ───────────────
backup_local_files() {
    local current_repo="$1" backup_dir="$2" manifest_path="$3"
    [[ -d "$GITHUB_DIR" ]] || {
        write_empty_backup_manifest "$current_repo" "$manifest_path"
        return 0
    }
    # Skip if update_runtime.py doesn't exist yet (bootstrap phase)
    [[ -f "$UPDATE_RUNTIME_PY" ]] || {
        write_empty_backup_manifest "$current_repo" "$manifest_path"
        return 0
    }
    safe_mkdir_p "$backup_dir" "backup local files"
    run_python "$UPDATE_RUNTIME_PY" backup-local "$GITHUB_DIR" "$current_repo" "$backup_dir" "$manifest_path"
}

validate_overrides() {
    local current_repo="$1" merged_github_dir="$2" manifest_path="$3"
    # Skip if update_runtime.py doesn't exist yet (bootstrap phase)
    [[ -f "$UPDATE_RUNTIME_PY" ]] || return 0
    [[ -s "$manifest_path" ]] || write_empty_backup_manifest "$current_repo" "$manifest_path"
    run_python "$UPDATE_RUNTIME_PY" validate-overrides "$merged_github_dir" "$manifest_path" "$current_repo" "$OVERRIDES_YAML"
}

# ── Clone or copy a layer source to a destination directory ──────────────────
# If GH_TOKEN / GITHUB_TOKEN is set (or gh CLI is logged in), HTTPS GitHub URLs
# get the token injected so private repos can be cloned without SSH keys.
_resolve_clone_token() {
    [[ -n "${GH_TOKEN:-}"     ]] && { printf '%s' "$GH_TOKEN";     return; }
    [[ -n "${GITHUB_TOKEN:-}" ]] && { printf '%s' "$GITHUB_TOKEN"; return; }
    command -v gh >/dev/null 2>&1 && gh auth token 2>/dev/null || true
}

acquire_layer() {
    local name="$1" source="$2" dest="$3"
    if [[ -d "$source" ]]; then
        log "  layer '$name': copying from local path"
        cp -R "$source/." "$dest/"
    else
        local clone_url="$source"
        if [[ "$source" =~ ^https://github\.com/ ]]; then
            local token
            token="$(_resolve_clone_token)"
            if [[ -n "$token" ]]; then
                clone_url="https://x-access-token:${token}@${source#https://}"
            fi
        fi
        log "  layer '$name': cloning from $source"
        git clone --depth 1 --quiet "$clone_url" "$dest"
    fi
}

# ── Regenerate index.instructions.md in each instructions category ────────────
generate_instruction_indexes() {
    local instructions_dir="$1"
    [[ -d "$instructions_dir" ]] || return 0
    run_python "$UPDATE_RUNTIME_PY" generate-indexes "$instructions_dir"
}

ensure_makefile_commands_include() {
    local makefile_path="$1"
    local include_line="include .github/make/commands.mk"
    local comment_line="# All project make targets are centralized in .github/make/commands.mk."

    [[ -f "$makefile_path" ]] || return 0
    if grep -Fq "$include_line" "$makefile_path"; then
        return 0
    fi

    printf '\n%s\n%s\n' "$comment_line" "$include_line" >> "$makefile_path"
    log "Phase 3: appended commands include to $(basename "$makefile_path")"
}

# ── Phase 2: Adapt .claude/ from .github/ ────────────────────────────────────
adapt_claude_dir() {
    local current_repo="$1"
    log "Phase 2: adapting .claude/ from .github/..."
    safe_mkdir_p "$CLAUDE_DIR/commands" "claude commands directory"
    safe_mkdir_p "$CLAUDE_DIR/agents" "claude agents directory"

    # 1. Prompts → .claude/commands/ (strip .prompt suffix from filename)
    local prompt_count=0
    local generated_commands=()
    if [[ -d "$GITHUB_DIR/prompts" ]]; then
        for f in "$GITHUB_DIR/prompts"/*.prompt.md; do
            [[ -f "$f" ]] || continue
            local base
            base="$(basename "$f" .prompt.md)"
            cp -p "$f" "$CLAUDE_DIR/commands/${base}.md"
            generated_commands+=("${base}.md")
            prompt_count=$((prompt_count + 1))
        done
    fi
    # Prune stale command files that no longer exist as prompt sources.
    local cmd_file cmd_name keep_cmd
    for cmd_file in "$CLAUDE_DIR/commands"/*.md; do
        [[ -f "$cmd_file" ]] || continue
        cmd_name="$(basename "$cmd_file")"
        keep_cmd=0
        for generated in "${generated_commands[@]}"; do
            if [[ "$generated" == "$cmd_name" ]]; then
                keep_cmd=1
                break
            fi
        done
        if [[ "$keep_cmd" -eq 0 ]]; then
            rm -f "$cmd_file"
        fi
    done
    log "  commands: $prompt_count file(s) → .claude/commands/"

    # 2. Agents → .claude/agents/ (strip .agent suffix, transform frontmatter)
    local agent_count=0
    if [[ -d "$GITHUB_DIR/agents" ]]; then
        agent_count="$(run_python "$UPDATE_RUNTIME_PY" transform-agents "$GITHUB_DIR/agents" "$CLAUDE_DIR/agents")"
    fi
    log "  agents: $agent_count file(s) → .claude/agents/"

    # 3. Hooks → .claude/hooks/ adapters + .claude/settings.json
    #    .claude/hooks/*.sh bridge Claude Code JSON-stdin → .github/hooks/ env-var convention.
    #    .github/hooks/ scripts expect DIGITAL_SESSION_ID etc. as env vars (Copilot convention);
    #    Claude Code passes context as JSON on stdin — the adapters translate between the two.
    local hooks_dir="$GITHUB_DIR/hooks"
    local claude_hooks_dir="$CLAUDE_DIR/hooks"
    local settings_file="$CLAUDE_DIR/settings.json"
    if [[ -d "$hooks_dir" ]]; then
        safe_mkdir_p "$claude_hooks_dir" "claude hooks directory"
        run_python "$UPDATE_RUNTIME_PY" generate-hooks "$hooks_dir" "$claude_hooks_dir" "$settings_file" >/dev/null
        log "  hooks: adapter(s) → .claude/hooks/ + .claude/settings.json"
    fi

    # 4. Instructions → .claude/CLAUDE.md via @-imports (no content duplication)
    local claude_md="$CLAUDE_DIR/CLAUDE.md"
    local import_count=0
    import_count="$(run_python "$UPDATE_RUNTIME_PY" generate-claude-md "$GITHUB_DIR/instructions" "$claude_md" "$current_repo")"
    log "  CLAUDE.md: $import_count instruction import(s) → .claude/CLAUDE.md"
}

# ── Phase 3: Root config sync + .vscode regeneration ─────────────────────────
sync_root_files() {
    local root_config_dir="$GITHUB_DIR/root-config"
    [[ -d "$root_config_dir" ]] || { log "Phase 3: no root-config/ found — skipped"; return 0; }

    local count=0
    local skipped_makefile=0
    while IFS= read -r -d '' src; do
        local rel="${src#"$root_config_dir"/}"
        local dest="$REPO_ROOT/$rel"

        if [[ "$rel" == "Makefile" ]] && [[ -f "$dest" ]]; then
            ensure_makefile_commands_include "$dest"
            skipped_makefile=1
            continue
        fi

        if [[ "$rel" == ".digital-team/overrides.yaml" ]] && [[ -f "$dest" ]]; then
            log "Phase 3: kept existing .digital-team/overrides.yaml (no overwrite)"
            continue
        fi

        if [[ "$rel" == ".digital-team/container-publish.yaml" ]] && [[ -f "$dest" ]]; then
            log "Phase 3: kept existing .digital-team/container-publish.yaml (no overwrite)"
            continue
        fi

        safe_mkdir_p "$(dirname "$dest")" "restore local file"
        cp -p "$src" "$dest"
        count=$((count + 1))
    done < <(find "$root_config_dir" -type f -print0)

    if [[ "$skipped_makefile" -eq 1 ]]; then
        log "Phase 3: kept existing root Makefile (no overwrite)"
    fi
    log "Phase 3: deployed $count root config file(s) from .github/root-config/"

    # Regenerate .vscode/mcp.json from MCP server registry
    local mcp_gen="$GITHUB_DIR/skills/mcp/scripts/mcp-gen-vscode-config.sh"
    if [[ -f "$mcp_gen" ]]; then
        MCP_VSCODE_MODE="${MCP_VSCODE_MODE:-disabled}" \
        MCP_VSCODE_SERVERS="${MCP_VSCODE_SERVERS:-}" \
        bash "$mcp_gen" && log "Phase 3: regenerated .vscode/mcp.json (mode=${MCP_VSCODE_MODE:-disabled})"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
main() {
    log "starting (repo: $REPO_ROOT)"

    [[ -f "$LAYERS_YAML" ]] || error ".digital-team/layers.yaml not found — run extend.sh or install.sh first"

    # Bootstrap guarantee: ensure venv exists before any Python calls
    ensure_bootstrap_venv
    ensure_pyyaml
    safe_mkdir_p "$TEMP_DIR" "update temp directory"

    local current_repo
    current_repo="$(detect_repo_name)"
    log "current repo: $current_repo"

    # ── Phase 1: .github/ update ──────────────────────────────────────────────
    local layers_output
    layers_output="$(get_layers)"

    if [[ -z "$layers_output" ]]; then
        log "Phase 1: no parent layers (Layer 0) — injecting layer: tags only"
        inject_layer_frontmatter "$GITHUB_DIR" "$current_repo"
    else
        log "Phase 1: merging parent layers into .github/"

        # Identify and back up local files (strictly layer: == current_repo)
        # Remove auto-generated stage prompts first — they must not be backed up
        _prune_generated_stage_prompts

        local backup_dir="$TEMP_DIR/local-backup"
        local backup_manifest="$TEMP_DIR/local-backup-manifest.json"
        rm -rf "$backup_dir"
        rm -f "$backup_manifest"
        backup_local_files "$current_repo" "$backup_dir" "$backup_manifest"

        # Wipe .github/ and rebuild from layers
        rm -rf "$GITHUB_DIR"
        safe_mkdir_p "$GITHUB_DIR" "rebuild .github directory"

        while IFS='|' read -r layer_name layer_source; do
            [[ -z "$layer_name" ]] && continue
            local layer_temp="$TEMP_DIR/layers/$layer_name"
            rm -rf "$layer_temp"
            safe_mkdir_p "$layer_temp" "layer temp workspace"
            acquire_layer "$layer_name" "$layer_source" "$layer_temp"

            if [[ -d "$layer_temp/.github" ]]; then
                cp -R "$layer_temp/.github/." "$GITHUB_DIR/"
                inject_layer_frontmatter "$GITHUB_DIR" "$layer_name"
                log "  merged '$layer_name'"
            else
                warn "layer '$layer_name' has no .github/ directory — skipped"
            fi
        done <<< "$layers_output"

        # Validate that all local path collisions are declared and based on current parent hashes
        validate_overrides "$current_repo" "$GITHUB_DIR" "$backup_manifest"

        # Re-apply local files on top (local overrides win)
        if [[ -d "$backup_dir" ]] && [[ -n "$(ls -A "$backup_dir" 2>/dev/null)" ]]; then
            cp -R "$backup_dir/." "$GITHUB_DIR/"
            inject_layer_frontmatter "$GITHUB_DIR" "$current_repo"
            log "  restored local files (layer: $current_repo)"
        fi
    fi

    generate_instruction_indexes "$GITHUB_DIR/instructions"
    log "Phase 1: complete"

    # ── Phase 2: .claude/ adaptation ──────────────────────────────────────────
    adapt_claude_dir "$current_repo"
    log "Phase 2: complete"

    # ── Phase 3: root config sync + .vscode ───────────────────────────────────
    sync_root_files
    log "Phase 3: complete"

    # ── Phase 4: dynamic stage prompt generation ──────────────────────────────
    local runtime_py="$GITHUB_DIR/skills/shared/runtime/scripts/update_runtime.py"
    if [[ -f "$runtime_py" ]]; then
        run_python "$runtime_py" generate-stage-prompts "$GITHUB_DIR" "$current_repo"
        run_python "$runtime_py" prune-prompts "$GITHUB_DIR" "$REPO_ROOT"
        log "Phase 4: stage prompts generated"
    else
        warn "Phase 4: skipped (update_runtime.py not found)"
    fi

    run_python "$UPDATE_RUNTIME_PY" report-update "$REPO_ROOT" "$GITHUB_DIR" "$CLAUDE_DIR"

    log "update done (repo=$current_repo)"
}

main "$@"
