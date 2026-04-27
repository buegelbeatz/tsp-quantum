<!-- layer: digital-generic-team -->
# /help Prompt

Show only the list of available slash prompts with a one-line purpose.

## Available prompts

- `/help` — list all available prompts and what they do.
- `/quality` — scan the active repository layer (auto-detected via git-tracked-state), produce a tabular overview of open findings, and stop at an approval gate before any remediation.
- `/quality-fix` — work through the findings reported by `/quality`, request guidance for extensive refactorings when needed, and then re-check deltas.
- `/audit-on` — enable repository-local prompt/task audit logging and keep entries under `.digital-artifacts/70-audits/`.
- `/audit-off` — disable repository-local prompt/task audit logging for wrapped prompt and task hook flows.
- `/roles` — discover and display all generic roles, their assigned agents, and all unassigned agents in a deterministic tree.
- `/roles-add` generic="<role>" agent="<agent>" — assign an existing agent to a generic role by updating the role's YAML frontmatter.
- `/roles-remove` generic="<role>" agent="<agent>" — remove an existing agent assignment from a generic role and show the refreshed role tree.
- `/cleanup` — run repository cleanup for board/sprint/wiki artifacts and optional GitHub resources.
- `/update` — execute one deterministic layer update cycle with optional focused verification; accepts `source="<path-or-url>"`.
- `/stages` — list all available stages with their status (active/available) and source layer.
- `/board` — display the lifecycle board for the current stage; accepts `--board <name>` to specify a board explicitly.
- `/distribution` — show a line-distribution table for all tracked repository assets grouped by skill/layer.
- `/layers` — render a colour-coded layer tree for all `.github/` assets in the repository.
<!-- stages:start -->
- `/exploration` — run the **Exploration** stage workflow (alias for `/stages-action stage="exploration"`, source: `digital-generic-team`).
- `/project` — run the **Project** stage workflow (alias for `/stages-action stage="project"`, source: `digital-generic-team`).
<!-- stages:end -->
<!-- stages-board:start -->
- `/exploration-board` — show the **Exploration** lifecycle board (alias for `/board --board exploration`, source: `digital-generic-team`).
- `/project-board` — show the **Project** lifecycle board (alias for `/board --board project`, source: `digital-generic-team`).
<!-- stages-board:end -->
## Output style

- Keep output concise and prompt-focused.
- Do not print unrelated make/bootstrap command catalogs in `/help` output.
