# layer: digital-generic-team

.PHONY: guard-no-root-venv preflight update test quality layer-venv-sync bootstrap-venv help \
	quality-fix chrome powerpoint pull quality-expert \
	cleanup \
	runtime-gc \
	audit-on audit-off audit-amend \
	scaffold-prompt scaffold-agent scaffold-instruction scaffold-skill scaffold-handoff \
	mcp-vscode-disable mcp-vscode-enable mcp-vscode-status \
        artifacts-testdata-2-input artifacts-input-2-data \
        artifacts-data-2-specification artifacts-specification-2-stage artifacts-specification-2-planning \
	stages stages-action roles board stage-board board-sync layers distribution \
	workflow-code-debt stage-completion-gate \
	board-cleanup \
	container-publish-validate \
	exploration project project-e2e \
	check-delivery-work \
	sprints sprint \
	sync-master push-all

_QUALITY_RUN_TOOL := .github/skills/shared/runtime/scripts/run-tool.sh
_QUALITY_VENV_SYNC := .github/skills/shared/runtime/scripts/runtime/layer-venv-sync.sh
_QUALITY_EXPERT_SCRIPT := .github/skills/quality-expert/scripts/quality-expert-session.sh
_QUALITY_EXPERT_ORCHESTRATOR_SCRIPT := .github/skills/quality-expert/scripts/quality-expert-orchestrator.sh
_QUALITY_SCAN_CMD := env QUALITY_EXPERT_MODE=scan bash $(_QUALITY_EXPERT_ORCHESTRATOR_SCRIPT)
_QUALITY_FIX_CMD := env QUALITY_EXPERT_MODE=fix bash $(_QUALITY_EXPERT_ORCHESTRATOR_SCRIPT)
_PROMPT_INVOKE_SCRIPT := .github/hooks/prompt-invoke.sh
_AUDIT_TOGGLE_SCRIPT := .github/skills/shared/orchestration/scripts/task-audit-toggle.sh
_AUDIT_LOG_SCRIPT := .github/skills/shared/orchestration/scripts/task-audit-log.sh
_ARTIFACTS_SCRIPTS_DIR := .github/skills/artifacts/scripts
_PROMPT_PULL_SCRIPT := .github/skills/shared/delivery/scripts/prompt-pull.sh
_PROMPT_CHROME_SCRIPT := .github/skills/mcp/scripts/mcp-google-homepages.py
_POWERPOINT_SCRIPT := .github/skills/powerpoint/scripts/powerpoint.sh
_BOARD_TICKET_SCRIPT := .github/skills/board/scripts/board-ticket.sh
_BOARD_SHOW_SCRIPT := .github/skills/board/scripts/board-show.py
_BOARD_CLEANUP_SCRIPT := .github/skills/board/scripts/board-cleanup.sh
_LAYER_QUALITY_RUNTIME := .github/skills/shared/orchestration/scripts/layer_quality_runtime.py
_LAYER_QUALITY_FIX_SCRIPT := .github/skills/shared/orchestration/scripts/layer_quality_fix.sh
_MCP_VSCODE_GEN_SCRIPT := .github/skills/mcp/scripts/mcp-gen-vscode-config.sh
_SCAFFOLD_SCRIPT_DIR := .github/skills/shared/local-command-orchestration/scripts
_STAGES_ACTION_SCRIPT := .github/skills/stages-action/scripts/stages-action.sh
_STAGE_COMPLETION_VALIDATE_SCRIPT := .github/skills/stages-action/scripts/validate_stage_completion_report.py
_CONTAINER_PUBLISH_SCRIPT := .github/skills/container-publish/scripts/container_publish.py
_PREFLIGHT_SCRIPT := .github/skills/shared/runtime/scripts/preflight-check.sh
_RUNTIME_GC_SCRIPT := .github/skills/shared/runtime/scripts/runtime/runtime-gc.sh
_CLEANUP_SCRIPT := .github/skills/shared/orchestration/scripts/cleanup.sh
_CLEANUP_E2E_SCRIPT := .github/skills/shared/orchestration/scripts/cleanup-e2e.sh
_PROJECT_E2E_SCRIPT := .github/skills/stages-action/scripts/project-e2e.sh
_CHECK_DELIVERY_WORK_SCRIPT := .github/skills/stages-action/scripts/check-delivery-work.sh

update: guard-no-root-venv ## Refresh .github/ and .claude/ from inherited layers (use /update command in Claude)
	@bash update.sh

preflight: ## Validate all prerequisites (python3, git, docker|podman, gh, .env+GH_TOKEN)
	@PREFLIGHT_REPO_ROOT="$${PREFLIGHT_REPO_ROOT:-$$(pwd)}" bash $(_PREFLIGHT_SCRIPT)

runtime-gc: ## Clean eligible .digital-runtime artifacts (MODE=dry-run|apply, default dry-run)
	@bash $(_RUNTIME_GC_SCRIPT) --repo-root "$$(pwd)" --mode "$${MODE:-dry-run}"

cleanup: preflight ## Cleanup local board/sprint/wiki artifacts and mandatory GitHub resources
	@target_repo_root="$${TARGET_REPO_ROOT:-$${DIGITAL_TARGET_REPO_ROOT:-$$(pwd)}}"; \
	 target_repo_slug="$${TARGET_REPO_SLUG:-$${DIGITAL_TARGET_REPO_SLUG:-}}"; \
	 TARGET_REPO_ROOT="$$target_repo_root" DIGITAL_TARGET_REPO_ROOT="$$target_repo_root" \
	 TARGET_REPO_SLUG="$$target_repo_slug" DIGITAL_TARGET_REPO_SLUG="$$target_repo_slug" \
	 bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name cleanup --summary "/cleanup" -- \
	  bash $(_CLEANUP_SCRIPT) \
	    --repo-root "$$target_repo_root" \
	    --dry-run "$${DRY_RUN:-0}" \
	    --confirm "$${CONFIRM:-1}" \
	    --github "1" \
	    --remote "1" \
	    --board "$${BOARD:-}"

guard-no-root-venv:
	@if [[ -d .venv ]]; then \
	  echo "ERROR: repository-root .venv is forbidden in this layer." >&2; \
	  echo "Use .digital-runtime/layers/python-runtime/venv (make layer-venv-sync)." >&2; \
	  echo "Cleanup: git clean -fdx .venv" >&2; \
	  exit 2; \
	fi

bootstrap-venv: guard-no-root-venv
	@mkdir -p .digital-runtime/layers/python-runtime && \
	 if [[ ! -x ".digital-runtime/layers/python-runtime/venv/bin/python3" ]]; then \
	   python3 -m venv .digital-runtime/layers/python-runtime/venv || exit 1; \
	 fi

layer-venv-sync: bootstrap-venv
	@DIGITAL_TEAM_LAYER_ID=python-runtime DIGITAL_TEAM_VENV_SYNC_HIDE_CONTEXT=1 bash $(_QUALITY_VENV_SYNC) .github/skills

test: preflight layer-venv-sync ## Run repository unit tests
	@DIGITAL_TEAM_TEST_RUNTIME=$${DIGITAL_TEAM_TEST_RUNTIME:-container} \
	  DIGITAL_TEAM_TEST_TARGET="$${DIGITAL_TEAM_TEST_TARGET:-.github/skills .tests}" \
	  bash .github/skills/shared/local-command-orchestration/scripts/run-tests.sh
	@bash $(_CLEANUP_E2E_SCRIPT) \
	  --repo-root "$$(pwd)" \
	  --github-test "$${GITHUB_TEST:-0}"
	@echo "INFO total=make-test complete=1"

quality: preflight layer-venv-sync ## Canonical quality workflow and report (tests/coverage/lint/typing/security)
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name quality --summary "/quality -> quality-expert-orchestrator" -- \
	  $(_QUALITY_SCAN_CMD)

quality-expert: preflight layer-venv-sync
	@RUN_TOOL_PREFER_CONTAINER=1 bash $(_QUALITY_EXPERT_SCRIPT)

quality-fix: preflight layer-venv-sync ## Canonical /quality-fix remediation workflow from the current report
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name quality-fix --summary "/quality-fix -> quality-expert-orchestrator" -- \
	  $(_QUALITY_FIX_CMD)

audit-on:
	@bash $(_AUDIT_TOGGLE_SCRIPT) --state on

audit-off:
	@bash $(_AUDIT_TOGGLE_SCRIPT) --state off

audit-amend:
	@[[ -n "$(MESSAGE_ID)" ]] || (printf 'MESSAGE_ID is required, e.g. make audit-amend MESSAGE_ID=my-session HANDOFF_FILE=path/to/handoff.yaml\n' >&2; exit 2)
	@bash $(_AUDIT_LOG_SCRIPT) --mode amend --message-id "$(MESSAGE_ID)" \
	  $(if $(HANDOFF_FILE),--handoff-file "$(HANDOFF_FILE)") \
	  $(if $(COMMUNICATION_FLOW),--communication-flow "$(COMMUNICATION_FLOW)") \
	  $(if $(ASSUMPTIONS),--assumptions "$(ASSUMPTIONS)") \
	  $(if $(OPEN_QUESTIONS),--open-questions "$(OPEN_QUESTIONS)")

scaffold-prompt:
	@PROMPT_NAME="$(PROMPT_NAME)" PROMPT_PURPOSE="$(PROMPT_PURPOSE)" bash $(_SCAFFOLD_SCRIPT_DIR)/prompt-scaffold.sh

scaffold-agent:
	@AGENT_NAME="$(AGENT_NAME)" AGENT_PURPOSE="$(AGENT_PURPOSE)" bash $(_SCAFFOLD_SCRIPT_DIR)/agent-scaffold.sh

scaffold-instruction:
	@INSTRUCTION_CATEGORY="$(INSTRUCTION_CATEGORY)" INSTRUCTION_NAME="$(INSTRUCTION_NAME)" INSTRUCTION_PURPOSE="$(INSTRUCTION_PURPOSE)" bash $(_SCAFFOLD_SCRIPT_DIR)/instruction-scaffold.sh

scaffold-skill:
	@SKILL_NAME="$(SKILL_NAME)" SKILL_PURPOSE="$(SKILL_PURPOSE)" bash $(_SCAFFOLD_SCRIPT_DIR)/skill-scaffold.sh

scaffold-handoff:
	@HANDOFF_NAME="$(HANDOFF_NAME)" HANDOFF_SCHEMA="$(HANDOFF_SCHEMA)" bash $(_SCAFFOLD_SCRIPT_DIR)/handoff-scaffold.sh

mcp-vscode-disable:
	@MCP_VSCODE_MODE=disabled bash $(_MCP_VSCODE_GEN_SCRIPT)

mcp-vscode-enable:
	@[[ -n "$(MCP_SERVERS)" ]] || (echo "MCP_SERVERS is required, e.g. MCP_SERVERS=fetch,git" >&2; exit 2)
	@MCP_VSCODE_MODE=allowlist MCP_VSCODE_SERVERS="$(MCP_SERVERS)" bash $(_MCP_VSCODE_GEN_SCRIPT)

mcp-vscode-status:
	@bash .github/skills/shared/runtime/scripts/run-tool.sh \
	  python3 -c "import json; from pathlib import Path; p=Path('.vscode/mcp.json'); d=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'servers': {}}; s=sorted((d.get('servers') or {}).keys()); print('mcp.json servers:', ', '.join(s) if s else '(none)')"

artifacts-testdata-2-input:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name artifacts-testdata-2-input --summary "/artifacts-testdata-2-input" -- \
	  bash $(_ARTIFACTS_SCRIPTS_DIR)/artifacts-testdata-2-input.sh

artifacts-input-2-data:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name artifacts-input-2-data --summary "/artifacts-input-2-data" -- \
	  bash $(_ARTIFACTS_SCRIPTS_DIR)/artifacts-input-2-data.sh

artifacts-data-2-specification:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name artifacts-data-2-specification --summary "/artifacts-data-2-specification" -- \
	  bash $(_ARTIFACTS_SCRIPTS_DIR)/artifacts-data-2-specification.sh

artifacts-specification-2-stage:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name artifacts-specification-2-stage --summary "/artifacts-specification-2-stage" -- \
	  bash $(_ARTIFACTS_SCRIPTS_DIR)/artifacts-specification-2-stage.sh

artifacts-specification-2-planning:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name artifacts-specification-2-planning --summary "/artifacts-specification-2-planning" -- \
	  bash $(_ARTIFACTS_SCRIPTS_DIR)/artifacts-specification-2-planning.sh

pull: preflight ## Run the pull/delivery workflow (use /pull in Claude)
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name pull --summary "/pull" -- \
	  bash $(_PROMPT_PULL_SCRIPT)

stages:
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 .github/skills/shared/runtime/scripts/update_runtime.py list-stages .github .; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 .github/skills/shared/runtime/scripts/update_runtime.py list-stages .github .; \
	fi

stages-action: preflight
	@[[ -n "$(STAGE)" ]] || (echo "STAGE is required, e.g. make stages-action STAGE=project" >&2; exit 2)
	@target_repo_root="$${TARGET_REPO_ROOT:-$${DIGITAL_TARGET_REPO_ROOT:-$$(pwd)}}"; \
	 target_repo_slug="$${TARGET_REPO_SLUG:-$${DIGITAL_TARGET_REPO_SLUG:-}}"; \
	 TARGET_REPO_ROOT="$$target_repo_root" DIGITAL_TARGET_REPO_ROOT="$$target_repo_root" \
	 TARGET_REPO_SLUG="$$target_repo_slug" DIGITAL_TARGET_REPO_SLUG="$$target_repo_slug" \
	 bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name stages-action --summary "/stages-action stage=$(STAGE)" -- \
	  bash $(_STAGES_ACTION_SCRIPT) "$(STAGE)"

exploration: preflight ## Run exploration stage workflow with full prompt-audit tracing
	@target_repo_root="$${TARGET_REPO_ROOT:-$${DIGITAL_TARGET_REPO_ROOT:-$$(pwd)}}"; \
	 target_repo_slug="$${TARGET_REPO_SLUG:-$${DIGITAL_TARGET_REPO_SLUG:-}}"; \
	 TARGET_REPO_ROOT="$$target_repo_root" DIGITAL_TARGET_REPO_ROOT="$$target_repo_root" \
	 TARGET_REPO_SLUG="$$target_repo_slug" DIGITAL_TARGET_REPO_SLUG="$$target_repo_slug" \
	 bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name exploration --summary "/exploration" -- \
	  bash $(_STAGES_ACTION_SCRIPT) exploration

project: preflight ## Run /project as thin frontdoor; stage orchestration lives in stages-action skill runtime
	@target_repo_root="$${TARGET_REPO_ROOT:-$${DIGITAL_TARGET_REPO_ROOT:-$$(pwd)}}"; \
	 target_repo_slug="$${TARGET_REPO_SLUG:-$${DIGITAL_TARGET_REPO_SLUG:-}}"; \
	 TARGET_REPO_ROOT="$$target_repo_root" DIGITAL_TARGET_REPO_ROOT="$$target_repo_root" \
	 TARGET_REPO_SLUG="$$target_repo_slug" DIGITAL_TARGET_REPO_SLUG="$$target_repo_slug" \
	 bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name project --summary "/project" -- \
	  bash $(_STAGES_ACTION_SCRIPT) project

check-delivery-work: preflight ## Scan runtime handoffs for pending delivery work (default STAGE=project)
	@stage="$${STAGE:-project}"; \
	bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name check-delivery-work --summary "/check-delivery-work stage=$$stage" -- \
	  env CHECK_DELIVERY_WORK_EXIT_PENDING=0 bash $(_CHECK_DELIVERY_WORK_SCRIPT) "$$stage"

project-e2e: preflight ## Run isolated /project E2E in temp clone under .digital-runtime
	@bash $(_PROJECT_E2E_SCRIPT) \
	  --repo-root "$$(pwd)" \
	  --github-test "$${GITHUB_TEST:-0}"

diagrams: ## Render all docs/diagrams/mermaid/*.mmd sources to SVG in docs/images/mermaid/
	@echo "[diagrams] Rendering mermaid source files -> docs/images/mermaid/"
	@mkdir -p docs/images/mermaid
	@rendered=0; failed=0; \
	for f in docs/diagrams/mermaid/*.mmd; do \
	  [ -f "$$f" ] || continue; \
	  name=$$(basename "$$f" .mmd); \
	  if command -v mmdc >/dev/null 2>&1; then \
	    mmdc -i "$$f" -o "docs/images/mermaid/$${name}.svg" -b white && rendered=$$((rendered+1)) || failed=$$((failed+1)); \
	  else \
	    bash .github/skills/shared/shell/scripts/run-tool.sh mmdc -i "$$f" -o "docs/images/mermaid/$${name}.svg" -b white && rendered=$$((rendered+1)) || failed=$$((failed+1)); \
	  fi; \
	done; \
	echo "[diagrams] rendered=$${rendered} failed=$${failed}"

roles:
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 .github/skills/shared/orchestration/scripts/roles_tree.py; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 .github/skills/shared/orchestration/scripts/roles_tree.py; \
	fi

layers:
	@mode="$${LAYERS_MODE:-auto}"; \
	if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 .github/skills/layers/scripts/layers-tree.py --mode "$$mode" --recent-md "$${LAYERS_RECENT_MD:-20}" .; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 .github/skills/layers/scripts/layers-tree.py --mode "$$mode" --recent-md "$${LAYERS_RECENT_MD:-20}" .; \
	fi

distribution: layer-venv-sync
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 .github/skills/distribution/scripts/distribution.py .; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 .github/skills/distribution/scripts/distribution.py .; \
	fi

workflow-code-debt: layer-venv-sync
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 .github/skills/distribution/scripts/workflow_code_debt.py --repo-root . --record --check-monotonic; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 .github/skills/distribution/scripts/workflow_code_debt.py --repo-root . --record --check-monotonic; \
	fi

stage-completion-gate:
	@DRY_RUN=1 bash $(_STAGES_ACTION_SCRIPT) project
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 $(_STAGE_COMPLETION_VALIDATE_SCRIPT) --repo-root . --stage project; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 $(_STAGE_COMPLETION_VALIDATE_SCRIPT) --repo-root . --stage project; \
	fi

container-publish-validate: layer-venv-sync
	@if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 $(_CONTAINER_PUBLISH_SCRIPT) validate .digital-team/container-publish.yaml .; \
	else \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh python3 $(_CONTAINER_PUBLISH_SCRIPT) validate .digital-team/container-publish.yaml .; \
	fi

board-sync:
	@bash $(_BOARD_TICKET_SCRIPT) fetch --all || echo "WARNING: Could not fetch from remote"

board-cleanup:
	@board_name="$(BOARD)"; \
	if [[ -z "$$board_name" ]]; then \
	  if [[ -t 0 ]]; then \
	    read -r -p "board-cleanup: BOARD is required. Enter board name: " board_name; \
	  else \
	    echo "board-cleanup: BOARD is required (e.g. make board-cleanup BOARD=project)" >&2; \
	    exit 2; \
	  fi; \
	fi; \
	[[ -n "$$board_name" ]] || { echo "board-cleanup: empty BOARD is not allowed" >&2; exit 2; }; \
	cleanup_args="--board $$board_name"; \
	if [[ "$(REMOTE)" != "0" ]]; then cleanup_args="$$cleanup_args --remote"; fi; \
	if [[ "$(DRY_RUN)" == "1" ]]; then \
	  echo "board-cleanup: dry-run mode (set DRY_RUN=0 or omit to delete refs)"; \
	else \
	  if [[ "$(CONFIRM)" != "1" ]]; then \
	    if [[ -t 0 ]]; then \
	      read -r -p "Type DELETE to confirm cleanup for board '$$board_name': " confirm; \
	      [[ "$$confirm" == "DELETE" ]] || { echo "board-cleanup: aborted" >&2; exit 2; }; \
	    else \
	      echo "board-cleanup: non-interactive mode requires CONFIRM=1" >&2; \
	      exit 2; \
	    fi; \
	  fi; \
	  cleanup_args="$$cleanup_args --yes"; \
	fi; \
	bash $(_BOARD_CLEANUP_SCRIPT) $$cleanup_args

board: preflight guard-no-root-venv layer-venv-sync ## Show board in terminal; default all boards, or BOARD=<name>
	@bash $(_BOARD_TICKET_SCRIPT) fetch --all || echo "WARNING: Could not fetch from remote"
	@BOARD_FLAG="$${BOARD:+--board $$BOARD}"; \
	if [[ -z "$$BOARD_FLAG" ]]; then BOARD_FLAG="--all"; fi; \
	if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG; \
	elif [[ -x .digital-runtime/layers/digital-generic-team/bin/python3 ]]; then \
	  .digital-runtime/layers/digital-generic-team/bin/python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG; \
	else \
	  python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG; \
	fi

issues: preflight guard-no-root-venv layer-venv-sync ## Show full ticket details (AC, DoD, sprint); BOARD=<name> optional
	@bash $(_BOARD_TICKET_SCRIPT) fetch --all 2>/dev/null || true
	@BOARD_FLAG="$${BOARD:+--board $$BOARD}"; \
	if [[ -z "$$BOARD_FLAG" ]]; then BOARD_FLAG="--all"; fi; \
	if [[ -x .digital-runtime/layers/python-runtime/venv/bin/python3 ]]; then \
	  .digital-runtime/layers/python-runtime/venv/bin/python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG --issues; \
	elif [[ -x .digital-runtime/layers/digital-generic-team/bin/python3 ]]; then \
	  .digital-runtime/layers/digital-generic-team/bin/python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG --issues; \
	else \
	  python3 $(_BOARD_SHOW_SCRIPT) $$BOARD_FLAG --issues; \
	fi

sprint-create: preflight ## Create a new sprint; usage: make sprint-create SPRINT=<sprint-id> GOAL="<goal text>"
	@[[ -n "$(SPRINT)" ]] || (echo "SPRINT is required, e.g. make sprint-create SPRINT=sprint-01 GOAL='...' " >&2; exit 2)
	@[[ -n "$(GOAL)"   ]] || (echo "GOAL is required, e.g. make sprint-create SPRINT=sprint-01 GOAL='Fix login flow'" >&2; exit 2)
	@bash $(_BOARD_TICKET_SCRIPT) sprint-create "$(SPRINT)" "$(GOAL)"

sprints: preflight ## List all sprints
	@BOARD_NAME="$(if $(BOARD),$(BOARD),project)" bash $(_BOARD_TICKET_SCRIPT) sprint-list

sprint: preflight ## Show one sprint; usage: make sprint SPRINT=<sprint-id>
	@[[ -n "$(SPRINT)" ]] || (echo "SPRINT is required, e.g. make sprint SPRINT=sprint-01" >&2; exit 2)
	@BOARD_NAME="$(if $(BOARD),$(BOARD),project)" bash $(_BOARD_TICKET_SCRIPT) sprint-show "$(SPRINT)"

sprint-close: preflight ## Close an open sprint; usage: make sprint-close SPRINT=<sprint-id>
	@[[ -n "$(SPRINT)" ]] || (echo "SPRINT is required, e.g. make sprint-close SPRINT=sprint-01" >&2; exit 2)
	@BOARD_NAME="$(if $(BOARD),$(BOARD),project)" bash $(_BOARD_TICKET_SCRIPT) sprint-close "$(SPRINT)"

stage-board:
	@[[ -n "$(STAGE)" ]] || (echo "STAGE is required, e.g. make stage-board STAGE=project" >&2; exit 2)
	@$(MAKE) board BOARD="$(STAGE)"

%-board:
	@$(MAKE) board BOARD="$*"

chrome:
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name chrome --summary "/chrome" -- \
	  bash .github/skills/shared/runtime/scripts/run-tool.sh \
	    python3 $(_PROMPT_CHROME_SCRIPT)

powerpoint: preflight layer-venv-sync ## Build deterministic PowerPoint deck from SOURCE (use /powerpoint in chat)
	@bash $(_PROMPT_INVOKE_SCRIPT) --prompt-name powerpoint --summary "/powerpoint -> powerpoint-skill" -- \
	  env SOURCE="$(SOURCE)" LAYER="$(LAYER)" bash $(_POWERPOINT_SCRIPT)

sync-master:
	@echo "[progress] Checking out master branch..."
	@git checkout master
	@echo "[progress] Pulling latest from origin (GitHub)..."
	@git pull origin master
	@echo "[progress] Pushing to origin (GitHub)..."
	@git push origin master
	@echo "[progress] Pushing to internal (Bitbucket)..."
	@git push internal master
	@echo "[✓] Master synchronized to both repositories"

push-all:
	@echo "[progress] Pushing all branches to origin (GitHub)..."
	@git push --all origin
	@echo "[progress] Pushing all branches to internal (Bitbucket)..."
	@git push --all internal
	@echo "[✓] All branches pushed to both repositories"

help: ## Show available targets
	@grep -hE '^[a-zA-Z0-9_.-]+:.*## ' $(MAKEFILE_LIST) >/dev/null && \
	echo "" && \
	echo "Core targets:" && \
	echo "  help                           Show this curated target list" && \
	echo "  project                        Run /project stage workflow" && \
	echo "  exploration                    Run /exploration stage workflow" && \
	echo "  test                           Run repository unit/integration tests" && \
	echo "  board                          Show board overview (BOARD=<name> optional)" && \
	echo "  issues                         Show full ticket details (AC/DoD/sprint)" && \
	echo "  sprints                        List all sprints" && \
	echo "  cleanup                        Cleanup board/sprints/issues/wiki (runs destructive by default)" && \
	echo "  update                         Refresh .github/.claude from layers" && \
	echo "  layers                         Show layer tree and overrides" && \
	echo "  roles                          Show role-to-agent mapping" && \
	echo "  audit-on/off                   Toggle prompt/task audit logging" && \
	echo "" && \
	echo "Hint: sprint lifecycle and preflight commands remain internal/automation-facing and are intentionally hidden from curated help."