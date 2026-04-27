#!/bin/bash
# layer: digital-generic-team
# delivery-evidence-integration.sh
# Integrates delivery evidence tracking into the delivery postfix workflow

set -euo pipefail

# Source color output helpers if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

log_info() {
    echo "[info] $*" >&2
}

log_warn() {
    echo "[warn] $*" >&2
}

log_error() {
    echo "[error] $*" >&2
}

# Guardiered Python invocation via run-tool.sh
run_python() {
    bash "$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh" python3 "$@"
}

main() {
    local stage="${1:-project}"
    local task_id="${2:?Task ID is required}"
    local action="${3:-checkpoint}"

    log_info "Delivery Evidence Integration: stage=$stage task=$task_id action=$action"

    # Ensure Python dependencies
    if ! run_python -c "import yaml" 2>/dev/null; then
        log_error "PyYAML not available - delivery tracking skipped"
        return 1
    fi

    # Initialize review directory
    run_python "$SCRIPT_DIR/delivery_evidence_tracker.py" init-review "$stage"

    case "$action" in
        checkpoint)
            log_info "Creating delivery checkpoint for stage=$stage"
            run_python "$SCRIPT_DIR/delivery_evidence_tracker.py" recovery-report "$stage"
            ;;
        verify-recovery)
            log_info "Verifying artifact recovery"
            run_python "$SCRIPT_DIR/delivery_evidence_tracker.py" verify-recovery "$stage" "$task_id"
            ;;
        *)
            log_warn "Unknown action: $action"
            return 1
            ;;
    esac

    log_info "Delivery evidence integration completed"
}

main "$@"
