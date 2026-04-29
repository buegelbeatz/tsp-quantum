"""Stage -> planning transition implementation."""

from __future__ import annotations

import os
import subprocess
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from artifacts_markdown_registry import (
    PROJECT_ASSESSMENT_ARTIFACT,
    cleanup_legacy_aliases,
    planning_assessment_path as canonical_planning_assessment_path,
)
from artifacts_flow_common import bundle_id, ensure_text, iter_data_bundles, timestamp
from artifacts_flow_github import (
    ensure_planning_issue_assets,
    ensure_stage_primary_assets,
)
from artifacts_flow_registry import inventory_upsert
from artifacts_flow_paths import (
    planning_dispatch_path,
    planning_item_path,
    specification_path,
    stage_doc_path,
)

BOARD_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "board" / "scripts" / "board_config.py"
)
BOARD_CONFIG_SPEC = importlib.util.spec_from_file_location(
    "board_config", BOARD_CONFIG_PATH
)
if (
    BOARD_CONFIG_SPEC is None or BOARD_CONFIG_SPEC.loader is None
):  # pragma: no cover - defensive
    raise RuntimeError(f"Unable to load board config helper from {BOARD_CONFIG_PATH}")
BOARD_CONFIG_MODULE = importlib.util.module_from_spec(BOARD_CONFIG_SPEC)
BOARD_CONFIG_SPEC.loader.exec_module(BOARD_CONFIG_MODULE)
load_board_config = BOARD_CONFIG_MODULE.load_board_config
STANDARDS_SOURCES_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "standards-sources.yaml"
)
PROJECT_ASSESSMENT_FILENAME = PROJECT_ASSESSMENT_ARTIFACT.canonical_filename


def _score_badge(value: int) -> str:
    """Return a compact visual badge for a 1-5 score."""
    score = max(1, min(5, int(value)))
    if score >= 4:
        return "🟢"
    if score == 3:
        return "🟡"
    return "🔴"


def _upsert_assessment_section_in_stage_doc(
    stage_doc: Path,
    scenario: str,
    overall: int,
    dims: dict[str, object],
    checklist_lines: list[str],
    questions: list[str],
    feature_suggestions: list[str],
    stage_gate_context: dict[str, object] | None = None,
) -> None:
    """Insert or replace the project-assessment section in the canonical stage doc."""
    if not stage_doc.exists():
        return

    text = stage_doc.read_text(encoding="utf-8")
    section_lines = [
        "## Project Assessment",
        "",
        f"- generated_at: {timestamp()}",
        f"- scenario: {scenario}",
        "- source: embedded planning assessment",
        "",
        "### Stage Requirement Checklist",
        "",
        *checklist_lines,
        "",
        "### Scorecard",
        "",
        "| Dimension | Score | Status |",
        "|---|---:|:---:|",
        f"| overall | {overall} | {_score_badge(overall)} |",
        f"| problem_clarity | {int(dims.get('problem_clarity', 1))} | {_score_badge(int(dims.get('problem_clarity', 1)))} |",
        f"| scope_clarity | {int(dims.get('scope_clarity', 1))} | {_score_badge(int(dims.get('scope_clarity', 1)))} |",
        f"| task_formulability | {int(dims.get('task_formulability', 1))} | {_score_badge(int(dims.get('task_formulability', 1)))} |",
        f"| constraints_clarity | {int(dims.get('constraints_clarity', 1))} | {_score_badge(int(dims.get('constraints_clarity', 1)))} |",
        f"| owner_clarity | {int(dims.get('owner_clarity', 1))} | {_score_badge(int(dims.get('owner_clarity', 1)))} |",
        "",
        "_Interpretation: 🟢 strong, 🟡 acceptable, 🔴 needs clarification._",
        "",
    ]

    if stage_gate_context:
        gate_reason = str(stage_gate_context.get("gate_reason", "")).strip()
        blocked_bundle_ids = [
            str(item).strip()
            for item in stage_gate_context.get("blocked_bundle_ids", [])
            if str(item).strip()
        ]
        if gate_reason or blocked_bundle_ids:
            section_lines.extend([
                "### Stage Gate Context",
                "",
                f"- gate_reason: {gate_reason or 'not provided'}",
                (
                    f"- blocked_bundle_ids: {', '.join(blocked_bundle_ids)}"
                    if blocked_bundle_ids
                    else "- blocked_bundle_ids: none"
                ),
                "",
            ])

    section_lines.extend([
        "### Improvement Questions (with examples)",
        "",
        *questions,
        "",
        "### Additional Feature Suggestions",
        "",
        *[f"- {item}" for item in feature_suggestions],
        "",
    ])

    section_text = "\n".join(section_lines)

    pattern = re.compile(r"\n## Project Assessment\n.*?(?=\n## |\Z)", flags=re.DOTALL)
    if pattern.search(text):
        updated = pattern.sub("\n" + section_text.rstrip() + "\n", text)
    else:
        updated = text.rstrip() + "\n\n" + section_text

    if updated != text:
        ensure_text(stage_doc, updated)


def _find_stage_instruction_path(repo_root: Path, stage: str) -> Path | None:
    """Return the most likely instruction file path for a stage command."""
    stages_dir = repo_root / ".github" / "instructions" / "stages"
    if not stages_dir.exists():
        return None

    stage_name = stage.strip().lower()
    direct = sorted(stages_dir.glob(f"*-{stage_name}.instructions.md"))
    if direct:
        return direct[0]

    for candidate in sorted(stages_dir.glob("*.instructions.md")):
        text = candidate.read_text(encoding="utf-8")
        if re.search(rf"^command:\s*{re.escape(stage_name)}\s*$", text, flags=re.MULTILINE):
            return candidate
    return None


def _compute_input_helpfulness(
    selected: list[tuple[object, Path, dict[str, object]]],
) -> dict[str, object]:
    """Compute 1-5 helpfulness scoring from available planning inputs."""
    if not selected:
        return {
            "dimensions": {
                "problem_clarity": 1,
                "scope_clarity": 1,
                "task_formulability": 1,
                "constraints_clarity": 1,
                "owner_clarity": 1,
            },
            "overall": 1,
        }

    total = len(selected)
    problem_hits = 0
    scope_hits = 0
    task_hits = 0
    constraint_hits = 0
    owner_hits = 0

    for _, _, inputs in selected:
        problem = str(inputs.get("problem", "")).strip()
        scope = str(inputs.get("scope", "")).strip()
        acceptance = [str(item).strip() for item in inputs.get("acceptance", [])]  # type: ignore[arg-type]
        constraints = [str(item).strip() for item in inputs.get("constraints", [])]  # type: ignore[arg-type]
        role = str(inputs.get("preferred_role", "")).strip().lower()

        if problem and len(problem.split()) >= 4:
            problem_hits += 1
        if scope and len(scope.split()) >= 4:
            scope_hits += 1
        if any(item and len(item.split()) >= 4 for item in acceptance):
            task_hits += 1
        if any(item and len(item.split()) >= 3 for item in constraints):
            constraint_hits += 1
        if role in {"fullstack-engineer", "ux-designer"}:
            owner_hits += 1

    def _to_score(hit_count: int) -> int:
        ratio = hit_count / total
        if ratio >= 0.95:
            return 5
        if ratio >= 0.75:
            return 4
        if ratio >= 0.5:
            return 3
        if ratio > 0:
            return 2
        return 1

    dimensions = {
        "problem_clarity": _to_score(problem_hits),
        "scope_clarity": _to_score(scope_hits),
        "task_formulability": _to_score(task_hits),
        "constraints_clarity": _to_score(constraint_hits),
        "owner_clarity": _to_score(owner_hits),
    }
    overall = int(round(sum(dimensions.values()) / len(dimensions)))
    if dimensions["owner_clarity"] <= 2 or dimensions["scope_clarity"] <= 2:
        overall = min(overall, 2)

    return {"dimensions": dimensions, "overall": max(1, min(5, overall))}


def _collect_planning_item_statuses(stage_planning_root: Path) -> dict[str, int]:
    """Return counts for planning artifacts and completion status."""
    epics = list(stage_planning_root.glob("EPIC_*.md"))
    tasks = list(stage_planning_root.glob("TASK_*.md"))
    done_tasks = 0
    for task_path in tasks:
        text = task_path.read_text(encoding="utf-8")
        status_match = re.search(
            r'^status:\s*"?(?P<status>[a-z\-]+)"?\s*$',
            text,
            flags=re.MULTILINE,
        )
        if status_match and status_match.group("status").strip().lower() == "done":
            done_tasks += 1
    return {
        "epics": len(epics),
        "tasks": len(tasks),
        "tasks_done": done_tasks,
    }


def _scenario_from_counts(epics: int, tasks: int, tasks_done: int) -> str:
    """Classify project readiness scenario."""
    if epics <= 0 or tasks <= 0:
        return "cannot-start"
    if tasks_done >= tasks and tasks > 0:
        return "completed"
    return "startable"


def _improvement_questions_for_gaps(gaps: list[str], overall_score: int) -> list[str]:
    """Build deterministic improvement questions with concrete answer examples."""
    questions: list[str] = []

    gap_map = {
        "required_inputs": (
            "Which stage-required inputs are still missing?",
            "target outcome, confirmed owner, and at least one explicit in-scope and out-of-scope item.",
        ),
        "problem_clarity": (
            "How can the core problem be expressed in 1-2 unambiguous sentences?",
            "'New users cannot find relevant commands, increasing onboarding drop-off.'",
        ),
        "scope_clarity": (
            "Which two scope points are explicitly in-scope and which two are out-of-scope?",
            "In-scope: /help text and routing; Out-of-scope: auth system and new database.",
        ),
        "task_formulability": (
            "Which story/task can be implemented immediately and what is its measurable outcome?",
            "'Task: adapt help text by stage status; Done: 6 tests pass, 0 placeholders in output.'",
        ),
        "constraints_clarity": (
            "Which technical or organizational constraints are mandatory?",
            "'Use existing templates only; do not introduce new external dependencies.'",
        ),
        "owner_clarity": (
            "Who makes the final scope decision when priorities conflict?",
            "'Owner: agile-coach, deputy: platform-architect.'",
        ),
    }

    for key in _dedupe_text(gaps):
        pair = gap_map.get(key)
        if pair:
            questions.append(f"- Question: {pair[0]}\n  Example: {pair[1]}")

    if overall_score <= 2:
        questions.append(
            "- Question: Which three concrete artifacts can raise the score from <=2 to >=3 in the short term?\n"
            "  Example: (1) confirmed owner, (2) explicit scope block, (3) testable acceptance criterion per task."
        )

    if not questions:
        questions.append(
            "- Question: Which quality signals should become mandatory fields so score and checklist remain stable?\n"
            "  Example: owner field, in/out scope, measurable acceptance criterion, risk note."
        )
    return questions


def _feature_suggestions(theme_labels: list[str]) -> list[str]:
    """Return concise feature suggestions based on detected themes."""
    suggestions = [
        "Automatic stage-readiness dashboard with trend view (score, open gaps, blocker age).",
        "Quality linter for planning artifacts (placeholders, missing owners, missing scope boundaries).",
        "Question-catalog assistant with context-aware example answers for each missing criterion.",
    ]
    if any("User Guidance" in label for label in theme_labels):
        suggestions.insert(
            0,
            "Context-sensitive /help mode by stage status (available, in-progress, active).",
        )
    return _dedupe_text(suggestions)[:5]


def _write_project_assessment_report(
    stage: str,
    stage_planning_root: Path,
    scenario: str,
    checklist_lines: list[str],
    scoring: dict[str, object],
    questions: list[str],
    feature_suggestions: list[str],
    stage_gate_context: dict[str, object] | None = None,
) -> Path:
    """Write scenario-specific project assessment report into planning folder."""
    report_path = canonical_planning_assessment_path(stage_planning_root.parent, stage)
    dims = scoring.get("dimensions", {})
    overall = int(scoring.get("overall", 1))
    stage_root = stage_planning_root.parents[1] / "40-stage"

    lines = [
        f"# Project Assessment ({stage})",
        "",
        f"- generated_at: {timestamp()}",
        f"- scenario: {scenario}",
        "",
    ]

    if scenario in {"cannot-start", "startable"}:
        lines.extend([
            "## Stage Requirement Checklist",
            "",
            *checklist_lines,
            "",
            "## Input Helpfulness Score (1-5)",
            "",
            "| Dimension | Score | Status |",
            "|---|---:|:---:|",
            f"| overall | {overall} | {_score_badge(overall)} |",
            f"| problem_clarity | {int(dims.get('problem_clarity', 1))} | {_score_badge(int(dims.get('problem_clarity', 1)))} |",
            f"| scope_clarity | {int(dims.get('scope_clarity', 1))} | {_score_badge(int(dims.get('scope_clarity', 1)))} |",
            f"| task_formulability | {int(dims.get('task_formulability', 1))} | {_score_badge(int(dims.get('task_formulability', 1)))} |",
            f"| constraints_clarity | {int(dims.get('constraints_clarity', 1))} | {_score_badge(int(dims.get('constraints_clarity', 1)))} |",
            f"| owner_clarity | {int(dims.get('owner_clarity', 1))} | {_score_badge(int(dims.get('owner_clarity', 1)))} |",
            "",
            "_Interpretation: 🟢 strong, 🟡 acceptable, 🔴 needs clarification._",
            "",
        ])

    if stage_gate_context:
        gate_reason = str(stage_gate_context.get("gate_reason", "")).strip()
        blocked_bundle_ids = [
            str(item).strip()
            for item in stage_gate_context.get("blocked_bundle_ids", [])
            if str(item).strip()
        ]
        if gate_reason or blocked_bundle_ids:
            lines.extend([
                "## Stage Gate Context",
                "",
                f"- gate_reason: {gate_reason or 'not provided'}",
                (
                    f"- blocked_bundle_ids: {', '.join(blocked_bundle_ids)}"
                    if blocked_bundle_ids
                    else "- blocked_bundle_ids: none"
                ),
                "",
            ])

    lines.extend([
        "## Improvement Questions (with examples)",
        "",
        *questions,
        "",
        "## Additional Feature Suggestions",
        "",
        *[f"- {item}" for item in feature_suggestions],
        "",
    ])

    ensure_text(report_path, "\n".join(lines))
    cleanup_legacy_aliases(report_path, PROJECT_ASSESSMENT_ARTIFACT)

    stage_doc = stage_doc_path(stage_root, stage)
    _upsert_assessment_section_in_stage_doc(
        stage_doc=stage_doc,
        scenario=scenario,
        overall=overall,
        dims=dims if isinstance(dims, dict) else {},
        checklist_lines=checklist_lines,
        questions=questions,
        feature_suggestions=feature_suggestions,
        stage_gate_context=stage_gate_context,
    )

    return report_path


def _resolve_board_for_stage(repo_root: Path, stage: str) -> str:
    """Resolve the board name to use for the current stage."""
    config = load_board_config(repo_root)
    boards = config["git_board"]["boards"]
    normalized_stage = stage.strip().lower()
    if normalized_stage in boards:
        return normalized_stage
    return normalized_stage


def _is_configured_stage_board(repo_root: Path, board_name: str) -> bool:
    """Return True when board_name exists in .digital-team board configuration."""
    config = load_board_config(repo_root)
    boards = config["git_board"]["boards"]
    return board_name in boards


def _extract_section(markdown_text: str, heading: str) -> str:
    """Extract a markdown section body without the heading line."""
    lines = markdown_text.splitlines()
    in_section = False
    collected: list[str] = []
    expected = heading.strip().lower()
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if in_section:
                break
            if current == expected:
                in_section = True
                continue
        if in_section:
            collected.append(line)
    return "\n".join(collected).strip()


def _first_heading(markdown_text: str) -> str:
    """Return the first level-one heading from a markdown document."""
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _bullet_lines(section_text: str) -> list[str]:
    """Extract bullet-style lines from a markdown section."""
    items: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
    return items


def _extract_markdown_bullets(markdown_text: str, heading: str) -> list[str]:
    """Extract markdown bullet items from a given section heading."""
    return [
        re.sub(r"^(\[[ xX]\]\s*)?", "", item).strip()
        for item in _bullet_lines(_extract_section(markdown_text, heading))
        if item.strip()
    ]


def _simple_yaml_value(yaml_text: str, key: str) -> str:
    """Extract a simple scalar value from a lightweight YAML file."""
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+)$", flags=re.MULTILINE)
    match = pattern.search(yaml_text)
    return match.group(1).strip().strip('"') if match else ""


def _stage_badge(stage: str) -> str:
    """Return a stable badge color token for the stage."""
    badges = {
        "exploration": "slate",
        "project": "blue",
        "ideation": "amber",
        "discovery": "cyan",
        "paperfit": "indigo",
        "mvp": "green",
        "pilot": "emerald",
    }
    return badges.get(stage.strip().lower(), "gray")


def _render_template(template_text: str, replacements: dict[str, str]) -> str:
    """Render a simple handlebars-style template with string replacement."""
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _load_standards_sources() -> dict[str, list[str]]:
    """Load standards sources from a lightweight YAML list structure."""
    defaults: dict[str, list[str]] = {
        "scrum_guide": [
            "Scrum Guide (latest): artifact purpose, accountabilities, and increment focus."
        ],
        "iso_25010": [
            "ISO/IEC 25010: non-functional quality model for software requirements."
        ],
        "wcag_22_aa": [
            "WCAG 2.2 AA: accessibility acceptance baseline for UX/UI work."
        ],
        "owasp": ["OWASP ASVS / OWASP Top 10: security requirement baseline."],
        "team_governance": [
            "Team-internal governance: stage gates and delivery evidence in .digital-artifacts."
        ],
        "clean_code": [
            "Clean Code instruction: keep modules cohesive, naming explicit, and behavior testable."
        ],
        "design_patterns": [
            "Design Patterns instruction: prefer explicit, minimal patterns that reduce coupling and support extension."
        ],
    }
    if not STANDARDS_SOURCES_PATH.exists():
        return defaults

    parsed: dict[str, list[str]] = {}
    current_key = ""
    for raw in STANDARDS_SOURCES_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key_match = re.match(r"^([a-zA-Z0-9_]+):\s*$", line)
        if key_match:
            current_key = key_match.group(1)
            parsed.setdefault(current_key, [])
            continue
        if current_key and line.startswith("- "):
            parsed[current_key].append(line[2:].strip())

    if not parsed:
        return defaults
    merged = defaults.copy()
    for key, value in parsed.items():
        if value:
            merged[key] = value
    return merged


def _standard_reference_lines(role: str) -> list[str]:
    """Return deterministic normative reference lines for a role."""
    sources = _load_standards_sources()
    lines: list[str] = []
    lines.extend(sources.get("scrum_guide", []))
    lines.extend(sources.get("team_governance", []))
    lines.extend(sources.get("clean_code", []))
    lines.extend(sources.get("design_patterns", []))
    if role == "ux-designer":
        lines.extend(sources.get("wcag_22_aa", []))
    if role == "fullstack-engineer":
        lines.extend(sources.get("iso_25010", []))
        lines.extend(sources.get("owasp", []))
    if role == "agile-coach":
        lines.extend(sources.get("iso_25010", []))
    return _dedupe_text(lines)


def _role_requirement_markers(role: str) -> list[str]:
    """Return required markers for role-specific task contracts."""
    base = ["Requirement contract:", "Verification plan:"]
    by_role: dict[str, list[str]] = {
        "agile-coach": [
            "Planning governance requirements:",
            "Workflow requirements:",
            "Evidence requirements:",
        ],
        "ux-designer": [
            "UX outcome requirements:",
            "Accessibility requirements:",
            "Validation requirements:",
            "WCAG 2.2 AA",
        ],
        "fullstack-engineer": [
            "Functional requirements:",
            "Non-functional requirements:",
            "Verification requirements:",
        ],
    }
    return [*base, *by_role.get(role, [])]


def _evaluate_task_quality_gate(task_text: str, role: str) -> list[str]:
    """Return missing quality-gate requirements for a task artifact."""
    missing: list[str] = []
    lowered = task_text.lower()
    if "…" in task_text or "..." in task_text:
        missing.append("placeholder:truncated-ellipsis")
    for token in ("todo", "replace this", "address: extraction", "criterion 1"):
        if token in lowered:
            missing.append(f"placeholder:{token}")

    if _contains_notebook_scope(task_text) and _contains_quantum_scope(task_text):
        for marker in (
            "Skill and instruction requirements:",
            "Notebook execution contract:",
            "Quantum analysis contract:",
            "Reusable business logic must remain in src/ modules",
        ):
            if marker not in task_text:
                missing.append(f"missing:{marker}")

    for marker in _role_requirement_markers(role):
        if marker not in task_text:
            missing.append(f"missing:{marker}")
    return missing


def _task_has_requirement_contract(task_text: str) -> bool:
    """Return True when a task artifact declares a requirement contract section."""
    return "Requirement contract:" in task_text


def _enforce_task_quality_gate() -> bool:
    """Return True when strict task contract enforcement is explicitly enabled."""
    value = os.getenv("DIGITAL_ARTIFACTS_ENFORCE_TASK_GATE", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _enforce_implementable_scope_gate(stage: str) -> bool:
    """Return True when stage planning must include at least one actionable implementation task."""
    value = os.getenv("DIGITAL_ARTIFACTS_ENFORCE_IMPLEMENTABLE_SCOPE", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return stage.strip().lower() == "project"


def _task_is_actionable_delivery(task_text: str) -> bool:
    """Return True when task text is a non-blocked actionable delivery contract."""
    status_match = re.search(r'^status:\s*"?(?P<status>[a-z\-]+)"?\s*$', task_text, flags=re.MULTILINE)
    if status_match and status_match.group("status").strip().lower() == "blocked":
        return False

    role_match = re.search(
        r'^assignee_hint:\s*"?(?P<role>[a-z0-9\-]+)"?\s*$',
        task_text,
        flags=re.MULTILINE,
    )
    role = (
        role_match.group("role").strip().lower()
        if role_match
        else "fullstack-engineer"
    )
    if role not in {"fullstack-engineer", "ux-designer"}:
        return False

    if not _task_has_requirement_contract(task_text):
        # Backward-compatible fallback for legacy/minimal templates used in tests.
        return True

    missing = _evaluate_task_quality_gate(task_text, role)
    return not missing


def _apply_blocked_quality_gate(task_text: str, missing: list[str]) -> str:
    """Mark task blocked and append explicit quality-gate blocker details."""
    blocked_text = re.sub(
        r'^status:\s*open\s*$',
        'status: blocked',
        task_text,
        count=1,
        flags=re.MULTILINE,
    )
    blocked_text += "\n\n## Quality Gate Status\n\n"
    blocked_text += "- status: blocked\n"
    blocked_text += "- reason: role requirement contract incomplete\n"
    blocked_text += "- missing:\n"
    blocked_text += "\n".join(f"  - {item}" for item in missing)
    blocked_text += "\n"
    return blocked_text


def _looks_placeholder(text: str) -> bool:
    """Heuristic check for placeholder/TODO-style section content."""
    normalized = text.strip().lower()
    if not normalized:
        return True
    tokens = (
        "todo",
        "summarize",
        "define",
        "replace this",
        "no extracted content",
        "criterion 1",
        "primary finding: extraction",
        "secondary finding: content",
        "address: extraction",
        "address: content",
        "address: file facts",
    )
    return any(token in normalized for token in tokens)


def _dedupe_text(values: list[str]) -> list[str]:
    """Deduplicate text values while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue

        # Normalize near-duplicates from extraction noise (punctuation/casing/spacing).
        canonical = re.sub(r"\s+", " ", normalized).strip().lower()
        canonical = re.sub(r"[\.,;:!\?]+$", "", canonical).strip()
        canonical = re.sub(r"\s*[-–—]+\s*", " ", canonical)
        canonical = re.sub(r"\s+", " ", canonical)

        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(normalized)
    return result


def _compact_issue_line(text: str, max_chars: int = 240) -> str:
    """Normalize one issue line while preserving full planning semantics."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return ""
    sentence_match = re.match(r"^(.*?[\.!?])(\s|$)", normalized)
    if sentence_match and len(sentence_match.group(1)) >= 40:
        normalized = sentence_match.group(1).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip(" .,:;-")


def _clean_acceptance_candidate(text: str) -> str:
    """Return a concise, delivery-suitable acceptance candidate line."""
    candidate = _compact_issue_line(text, max_chars=220)
    lowered = candidate.lower()
    if not candidate:
        return ""
    if candidate.startswith(("🧭", "📘", "📊", "⚙️")):
        return ""
    if any(
        token in lowered
        for token in (
            "enterprise project specification",
            "bundle content",
            "canonical english content",
        )
    ):
        return ""
    return candidate


def _contains_notebook_scope(*texts: str) -> bool:
    """Return True when scope indicates Jupyter/notebook work."""
    corpus = " ".join(texts).lower()
    return any(token in corpus for token in ("notebook", "jupyter", ".ipynb", "ipynb"))


def _contains_quantum_scope(*texts: str) -> bool:
    """Return True when scope indicates quantum implementation work."""
    corpus = " ".join(texts).lower()
    return any(
        token in corpus
        for token in ("quantum", "qiskit", "qaoa", "dqi", "hypergraph", "qubit")
    )


def _skill_instruction_requirements(
    title: str,
    problem: str,
    scope: str,
    acceptance: list[str],
) -> list[str]:
    """Return mandatory skill/instruction requirements for specialized scopes."""
    has_notebook = _contains_notebook_scope(title, problem, scope, *acceptance)
    has_quantum = _contains_quantum_scope(title, problem, scope, *acceptance)
    if not (has_notebook or has_quantum):
        return []

    lines = ["Skill and instruction requirements:"]
    if has_notebook:
        lines.extend(
            [
                "- .github/instructions/data-scientist/jupyter.instructions.md",
                "- .github/instructions/quantum-expert/jupyter-quantum.instructions.md",
                "- Notebook execution contract:",
                "  - Notebook cells must orchestrate experiments, explain methodology, and render decision-ready visuals.",
                "  - Reusable business logic must remain in src/ modules and be imported by notebook cells.",
                "  - Reported tables and charts must be reproducible from code cells in one deterministic run.",
            ]
        )
    if has_quantum:
        lines.extend(
            [
                "- .github/instructions/quantum-expert/quantum-computing.instructions.md",
                "- Quantum analysis contract:",
                "  - Define a classical baseline metric (for example tour length, runtime, approximation quality).",
                "  - Compare at least one quantum-oriented approach against one classical heuristic using the same dataset.",
                "  - Document algorithm assumptions, hardware/simulator limits, and interpretation caveats in plain language.",
            ]
        )
    return lines


def _canonical_issue_text(text: str) -> str:
    """Return a canonical representation for fuzzy duplicate checks."""
    canonical = re.sub(r"\s+", " ", text.strip()).lower()
    canonical = re.sub(r"[\.,;:!\?]+$", "", canonical).strip()
    return canonical


def _is_near_duplicate_text(left: str, right: str) -> bool:
    """Return True when two lines are semantically the same for planning text reuse."""
    a = _canonical_issue_text(left)
    b = _canonical_issue_text(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return a in b or b in a


def _clean_theme_text(text: str) -> str:
    """Normalize noisy multi-line spec text into one concise summary line."""
    def _looks_disallowed_theme_line(line: str) -> bool:
        lowered = line.lower()
        german_stopwords = re.findall(
            r"\b(die|der|das|damit|keine|nicht|neue|muss|wissen|womit|über|für|mit)\b",
            lowered,
        )
        if len(german_stopwords) >= 2 or any(char in line for char in "äöüß"):
            return True
        if any(
            marker in lowered
            for marker in (
                "kontext-sensitiver",
                "einstieg",
                "idealerweise",
                "aktuellen",
                "verbesserungsbedarf",
                "übersicht",
                "ausgabe",
            )
        ):
            return True
        return False

    cleaned_parts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-* ").strip()
        if not line:
            continue
        line = line.replace("**", "").replace("`", "").strip()
        line = re.sub(
            r"^(primary finding:|secondary finding:|core problem:|supporting evidence:|address:|focus on:)\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )
        lower = line.lower()
        if lower.startswith("### "):
            continue
        if lower in {"extraction", "content", "file facts"}:
            continue
        if lower.startswith("address: extraction") or lower.startswith("address: content"):
            continue
        if any(
            token in lower
            for token in (
                "interne entwickler",
                "der primäre zugang",
                "der nutzer gibt",
                "teammitglieder,",
                "stakeholder map",
                "self-managed virtual team",
                "user profile & ux",
            )
        ):
            continue
        if _looks_disallowed_theme_line(line):
            continue
        if "|" in line and line.count("|") >= 2:
            continue
        if ".digital-artifacts/" in line:
            continue
        cleaned_parts.append(line)
    if not cleaned_parts:
        return ""
    return cleaned_parts[0]


def _first_source_note_line(spec_text: str) -> str:
    """Return first meaningful line from Source Notes section as fallback."""
    source_notes = _extract_section(spec_text, "Source Notes")
    for line in source_notes.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if stripped:
            return stripped
    return ""


def _source_note_lines(spec_text: str) -> list[str]:
    """Return normalized bullet lines from Source Notes."""
    lines: list[str] = []
    for line in _extract_section(spec_text, "Source Notes").splitlines():
        stripped = line.strip().lstrip("-* ").strip()
        if stripped:
            lines.append(stripped)
    return lines


def _assignee_hint(spec_text: str) -> str:
    """Extract assignee hint from markdown text when present."""
    match = re.search(
        r"^[-*]\s*assignee_hint:\s*\"?(?P<role>[a-z0-9\-]+)\"?\s*$",
        spec_text,
        flags=re.MULTILINE,
    )
    return match.group("role").strip().lower() if match else ""


def _role_priority(role: str) -> int:
    """Return deterministic priority for delivery-oriented expert roles."""
    priorities = {
        "ux-designer": 0,
        "fullstack-engineer": 1,
        "platform-architect": 2,
        "security-expert": 3,
        "quality-expert": 4,
        "agile-coach": 9,
    }
    return priorities.get(role.strip().lower(), 8)


def _bundle_specification_paths(primary_spec_path: Path, bundle) -> list[Path]:
    """Return all available specification files for one bundle across expert folders."""
    if not primary_spec_path.exists():
        return [primary_spec_path]

    date_root = primary_spec_path.parent.parent
    patterns = [
        f"*/{bundle.item_code}-specification.md",
        f"*/{bundle.item_code}.*.specification.md",
    ]
    candidates: dict[Path, str] = {primary_spec_path: primary_spec_path.parent.name}
    for pattern in patterns:
        for path in date_root.glob(pattern):
            if path.is_file():
                candidates[path] = path.parent.name

    return sorted(
        candidates,
        key=lambda path: (
            _role_priority(candidates[path]),
            candidates[path],
            path.name,
        ),
    )


def _acceptance_is_meta_planning(acceptance: list[str]) -> bool:
    """Return True when acceptance items are governance-only and not deliverable."""
    if not acceptance:
        return True
    meta_markers = (
        "thematic epic",
        "blocking contradictions",
        "recommendations and confidence",
        "expert reviews are consolidated",
        "review-ready",
        "scope boundaries",
    )
    matches = 0
    for item in acceptance:
        lowered = item.lower()
        if any(marker in lowered for marker in meta_markers):
            matches += 1
    return matches == len(acceptance)


def _derive_acceptance_from_source_notes(source_notes: list[str], role: str) -> list[str]:
    """Build actionable acceptance criteria from expert source notes."""
    cleaned = _dedupe_text(
        [
            _clean_acceptance_candidate(note.rstrip(".") + ".")
            for note in source_notes
            if note and len(note.split()) >= 4
        ]
    )
    cleaned = [item for item in cleaned if item]
    if cleaned:
        def _acceptance_priority(item: str) -> int:
            lowered = item.lower()
            score = 0
            # Prefer concrete gaps, actions, and behavior-oriented outcomes.
            if any(
                token in lowered
                for token in (
                    "does not",
                    "there is no",
                    "must",
                    "should",
                    "provide",
                    "group",
                    "onboarding",
                    "next step",
                    "context-sensitive",
                    "stage status",
                )
            ):
                score += 4
            if any(token in lowered for token in ("/help", "command", "prompt")):
                score += 2
            if "this project specification outlines" in lowered:
                score -= 5
            if len(item) > 180:
                score -= 2
            # Penalize generic classification statements.
            if "primary discovery interface" in lowered:
                score -= 3
            return score

        ordered = sorted(cleaned, key=_acceptance_priority, reverse=True)
        selected: list[str] = []
        for item in ordered:
            if item not in selected:
                selected.append(item)
            if len(selected) == 3:
                break
        if selected:
            return selected

    if role == "ux-designer":
        return [
            "Primary user journey is explicit and reviewable.",
            "Accessibility expectations are documented for key interactions.",
            "Validation evidence is attached to the design handoff.",
        ]
    return [
        "Implemented scope is explicit and reviewable.",
        "Quality and security constraints are documented.",
        "Verification evidence is mapped to the delivery handoff.",
    ]


def _preferred_delivery_role(roles: list[str]) -> str:
    """Return the strongest delivery role signal from aggregated specs."""
    delivery_roles = [
        role for role in roles if role in {"ux-designer", "fullstack-engineer"}
    ]
    if not delivery_roles:
        return ""
    return sorted(delivery_roles, key=_role_priority)[0]


def _build_planning_inputs(bundle, spec_path: Path) -> dict[str, object]:
    """Extract structured planning inputs from a specification bundle."""
    spec_paths = _bundle_specification_paths(spec_path, bundle)
    spec_text = spec_path.read_text(encoding="utf-8")
    spec_texts = [
        path.read_text(encoding="utf-8") for path in spec_paths if path.exists()
    ]
    metadata_path = bundle.metadata_path
    metadata_text = (
        metadata_path.read_text(encoding="utf-8") if metadata_path.exists() else ""
    )
    classification = _simple_yaml_value(metadata_text, "classification") or "feature"
    title = _first_heading(spec_text) or f"Work package {bundle.item_code}"

    problem = _extract_section(spec_text, "Synthesized Problem Statement")
    if _looks_placeholder(problem):
        problem = _extract_section(spec_text, "Problem")
    if _looks_placeholder(problem):
        fallback_line = _first_source_note_line(spec_text)
        if fallback_line:
            problem = f"Address source finding: {fallback_line}"

    scope = _extract_section(spec_text, "Scope")
    if _looks_placeholder(scope):
        scope = "Deliver an increment that resolves the synthesized problem with explicit boundaries."

    acceptance: list[str] = []
    constraints: list[str] = []
    assignee_hints: list[str] = []
    source_notes: list[str] = []
    for current_text in spec_texts:
        acceptance.extend(
            re.sub(r"^\[\s*[x ]\s*\]\s*", "", item).strip()
            for item in _bullet_lines(_extract_section(current_text, "Acceptance Criteria"))
        )
        constraints.extend(_bullet_lines(_extract_section(current_text, "Constraints")))
        assignee_hint = _assignee_hint(current_text)
        if assignee_hint:
            assignee_hints.append(assignee_hint)
        source_notes.extend(_source_note_lines(current_text))

    acceptance = [
        item
        for item in _dedupe_text(acceptance)
        if item and "criterion" not in item.lower()
    ]
    constraints = _dedupe_text(constraints)
    preferred_role = _preferred_delivery_role(assignee_hints)
    if _acceptance_is_meta_planning(acceptance):
        acceptance = _derive_acceptance_from_source_notes(source_notes, preferred_role)
    if not acceptance:
        acceptance = _derive_acceptance_from_source_notes(source_notes, preferred_role)
    return {
        "classification": classification.lower(),
        "title": title,
        "problem": problem,
        "scope": scope,
        "acceptance": acceptance,
        "constraints": constraints,
        "preferred_role": preferred_role,
    }


def _normalize_hints(raw_hints: list[str], _spec_path: Path) -> list[str]:
    """Normalize planning hints and provide sensible defaults."""
    if raw_hints:
        cleaned = [item.strip() for item in raw_hints if item.strip() and ".digital-artifacts/" not in item]
        if cleaned:
            return cleaned[:3]
    return [
        "Identify concrete target files before coding and list them in the PR description.",
        "Implement only the approved scope and keep out-of-scope items explicitly deferred.",
        "Add or update automated tests for every changed behavior.",
    ]


def _task_execution_steps(scope_line: str, _acceptance: list[str]) -> list[str]:
    """Build deterministic and actionable execution steps for task artifacts."""
    steps = [f"Implement the approved scope boundary: {scope_line}"]
    for criterion in _acceptance[:5]:
        criterion_line = _compact_issue_line(criterion)
        if criterion_line:
            steps.append(f"Satisfy acceptance criterion: {criterion_line}")
    steps.extend(
        [
            "Document and preserve scope boundaries with explicit in/out decisions.",
            "Verify review-readiness with test and quality evidence before handoff.",
        ]
    )
    return steps


def _is_meta_planning_scope(title: str, problem: str, scope: str) -> bool:
    """Return True when the work is primarily governance/planning orchestration."""
    corpus = " ".join([title, problem, scope]).lower()
    indicators = (
        "governance",
        "operating model",
        "stage",
        "readiness",
        "quality gate",
        "workflow",
        "planning",
        "coordination",
        "stakeholder",
        "decision",
        "role",
        "process",
    )
    matches = sum(1 for token in indicators if token in corpus)
    return matches >= 2


def _is_ux_scope(title: str, problem: str, scope: str) -> bool:
    """Return True when work primarily targets UX/design outcomes."""
    corpus = " ".join([title, problem, scope]).lower()
    indicators = (
        "ux",
        "user",
        "users",
        "user experience",
        "usability",
        "journey",
        "wireframe",
        "prototype",
        "interaction",
        "design",
        "accessibility",
        "wcag",
        "persona",
        "virtual user",
        "scribble",
        "sketch",
        "interview",
        "feedback",
    )
    design_indicators = (
        "wireframe",
        "prototype",
        "interaction",
        "accessibility",
        "wcag",
        "persona",
        "scribble",
        "sketch",
        "interview",
    )
    delivery_command_indicators = (
        "/help",
        "command",
        "commands",
        "prompt",
        "onboarding path",
        "stage status",
        "next step",
        "workflow phase",
    )
    indicator_hits = sum(1 for token in indicators if token in corpus)
    design_hits = sum(1 for token in design_indicators if token in corpus)
    delivery_hits = sum(1 for token in delivery_command_indicators if token in corpus)

    # Command/help implementation should default to delivery unless strong UX design signals exist.
    if delivery_hits >= 2 and design_hits <= 1:
        return False
    return indicator_hits >= 2


def _bundle_reference_paths(stage: str, bundle, _spec_path: Path) -> str:
    """Return deterministic repository-relative reference paths for planning text."""
    return "\n".join(
        [
            f"- Canonical stage page: docs/wiki/{stage.title()}.md",
            f"- Planning theme: {stage.upper()}/{bundle.item_code}",
        ]
    )


def _user_story_line(text: str, fallback: str) -> str:
    """Extract one usable line for user-story clauses."""
    for raw in text.splitlines():
        line = raw.strip().lstrip("-* ").strip()
        line = re.sub(r"^Address:\s*", "", line, flags=re.IGNORECASE)
        line = line.replace("**", "")
        if line:
            return line.rstrip(".")
    return fallback.rstrip(".")


def _derive_theme_focus(
    entries: list[tuple[object, Path, dict[str, object]]],
) -> tuple[str, str]:
    """Return (theme_label, summary_line) from combined bundle semantics."""
    corpus = " ".join(
        [
            str(entry[2].get("title", ""))
            + " "
            + str(entry[2].get("problem", ""))
            + " "
            + str(entry[2].get("scope", ""))
            for entry in entries
        ]
    ).lower()

    themes: list[tuple[str, str, tuple[str, ...]]] = [
        (
            "User Guidance Experience",
            "Improve prompt discovery, onboarding, and next-step guidance for chat-first users.",
            ("help", "command", "prompt", "onboarding", "discovery", "next", "user"),
        ),
        (
            "Team Operating Model",
            "Define how the team compensates missing expertise through virtual expert roles.",
            ("expert", "role", "stakeholder", "team", "virtual"),
        ),
        (
            "Stage Governance",
            "Standardize stage decisions, quality gates, and evidence-based progression.",
            ("stage", "gate", "criteria", "decision", "readiness"),
        ),
        (
            "Delivery Execution",
            "Translate validated requirements into delivery-ready implementation work.",
            ("delivery", "implementation", "workflow", "task", "planning"),
        ),
    ]

    scored: list[tuple[int, str, str]] = []
    for label, summary, keywords in themes:
        score = sum(1 for keyword in keywords if keyword in corpus)
        scored.append((score, label, summary))

    score, label, summary = max(scored, key=lambda item: item[0])
    if score == 0:
        return (
            "Strategic Theme",
            "Consolidate approved specifications into one coherent delivery theme.",
        )
    return label, summary


def _milestone_fields(stage: str, theme_code: str) -> tuple[str, str]:
    """Return deterministic milestone identifier and sprint hint."""
    stage_token = stage.strip().upper() or "PROJECT"
    milestone_id = f"MS-{stage_token}-{theme_code}"
    sprint_hint = f"Sprint candidate for {stage.title()} execution window ({theme_code})."
    return milestone_id, sprint_hint


def _build_core_planning_artifacts(
    stage: str,
    bundle,
    spec_path: Path,
    templates: dict[str, str],
    title: str,
    problem: str,
    scope: str,
    acceptance: list[str],
    hints: list[str],
    milestone_id: str,
    sprint_hint: str,
    preferred_role: str = "",
) -> dict[str, str]:
    """Build epic/story/task artifacts for one bundle."""
    badge = _stage_badge(stage)
    epic_id = f"EPIC-{bundle.item_code}"
    story_id = f"STORY-{bundle.item_code}"
    task_id = f"TASK-{bundle.item_code}"

    outcome_line = _user_story_line(
        problem,
        title,
    )
    planning_focus_line = _user_story_line(
        scope,
        "Translate the approved theme into an executable delivery slice",
    )
    if planning_focus_line.strip().lower() == outcome_line.strip().lower():
        planning_focus_line = "Translate the approved theme into executable delivery work with explicit boundaries"

    story_title = f"Define executable work packages for {title}"
    if "delivery execution" not in title.lower() and "work package" not in title.lower():
        story_title = f"Define executable work packages for {title}"

    epic = _render_template(
        templates["epic"],
        {
            "stage": stage,
            "epic_id": epic_id,
            "title": title,
            "badge_color": badge,
            "agent_role": "agile-coach",
            "date": timestamp(),
            "description": "\n".join(
                [
                    f"- Executive summary: {outcome_line}",
                    (
                        f"- Scope focus: {planning_focus_line}"
                        if planning_focus_line.strip().lower() != outcome_line.strip().lower()
                        else "- Scope focus: Translate the approved theme into delegated delivery work with clear boundaries."
                    ),
                ]
            ),
            "goals": "\n".join(f"- {item}" for item in acceptance[:5]),
            "story_links": f"- {story_id}",
            "milestone_id": milestone_id,
            "sprint_hint": sprint_hint,
        },
    )

    story = _render_template(
        templates["story"],
        {
            "stage": stage,
            "epic_id": epic_id,
            "story_id": story_id,
            "title": story_title,
            "badge_color": badge,
            "agent_role": "agile-coach",
            "date": timestamp(),
            "summary": "\n".join(
                [
                    "- Story outcome: convert the epic into one implementation-ready slice with clear ownership.",
                    f"- Delivery intent: {outcome_line}",
                ]
            ),
            "planning_focus": "\n".join(
                [
                    f"- Scope boundary: {planning_focus_line}",
                    "- Decompose work into one concrete implementation task and explicit acceptance checks.",
                ]
            ),
            "readiness_signals": "\n".join(
                f"- {item}" for item in acceptance[:3]
            ),
            "parent_epic": epic_id,
            "task_links": f"- {task_id}",
            "milestone_id": milestone_id,
            "sprint_hint": sprint_hint,
        },
    )

    relative_refs = _bundle_reference_paths(stage, bundle, spec_path)
    ux_scope = preferred_role == "ux-designer" or _is_ux_scope(title, problem, scope)
    command_delivery_scope = any(
        token in " ".join([title, problem, scope, *acceptance]).lower()
        for token in (
            "/help",
            "command",
            "commands",
            "prompt",
            "stage status",
            "next step",
            "onboarding path",
        )
    )
    task_agent_role = (
        preferred_role
        if preferred_role in {"ux-designer", "fullstack-engineer"}
        else ("ux-designer" if ux_scope else "fullstack-engineer")
    )
    if command_delivery_scope:
        task_agent_role = "fullstack-engineer"
    ux_scope = task_agent_role == "ux-designer"
    task_title = (
        f"Design validated user experience scope for {title}"
        if ux_scope
        else f"Implement approved scope for {title}"
    )
    if ux_scope:
        requirements_block = [
            "Requirement contract:",
            "- UX outcome requirements: define user segment, scenario, and measurable usability target.",
            "- Accessibility requirements: include WCAG 2.2 AA acceptance checks for key interaction paths.",
            "- Validation requirements: provide test protocol (5-user walkthrough, heuristic review, or analytics baseline).",
        ]
    else:
        requirements_block = [
            "Requirement contract:",
            "- Functional requirements: describe expected behavior with explicit input/output and failure conditions.",
            "- Non-functional requirements: state security, performance, and observability constraints.",
            "- Verification requirements: map each key behavior to automated test evidence.",
        ]
    standards_block = ["Normative references:"] + [
        f"- {line}" for line in _standard_reference_lines(task_agent_role)
    ]
    skill_block = _skill_instruction_requirements(title, problem, scope, acceptance)

    execution_steps = (
        [
            f"Design the validated UX scope boundary: {planning_focus_line}",
            f"Deliver the primary UX outcome: {acceptance[0] if acceptance else 'UX flow is testable and understandable.'}",
            f"Document usability and accessibility acceptance evidence: {acceptance[1] if len(acceptance) > 1 else 'Accessibility checks are explicit.'}",
            f"Verify validation-readiness with evidence: {acceptance[2] if len(acceptance) > 2 else 'Validation protocol and findings are attached.'}",
        ]
        if ux_scope
        else _task_execution_steps(planning_focus_line, acceptance)
    )
    delivery_objective_lines = [
        f"- {_compact_issue_line(item)}"
        for item in acceptance[:6]
        if _compact_issue_line(item)
    ]
    if not delivery_objective_lines:
        delivery_objective_lines = ["- Implementation outcome is testable and review-ready."]

    execution_context_candidates = _dedupe_text(
        [
            _compact_issue_line(scope),
            _compact_issue_line(problem),
            _compact_issue_line(title),
        ]
    )
    execution_context_lines = [
        f"- {line}" for line in execution_context_candidates[:3] if line
    ]
    if not execution_context_lines:
        execution_context_lines = [f"- {_compact_issue_line(title) or title}"]
    verification_plan = [
        "- [ ] Add/adjust automated tests that prove the implemented scope.",
        "- [ ] Run `make test` and `make quality` before PR handoff.",
        "- [ ] Attach concrete evidence (logs, screenshots, or diff references) to the PR.",
    ]
    task = _render_template(
        templates["task"],
        {
            "stage": stage,
            "story_id": story_id,
            "task_id": task_id,
            "title": task_title,
            "badge_color": badge,
            "agent_role": task_agent_role,
            "date": timestamp(),
            "description": "\n".join(
                [
                    (
                        f"Deliver the approved UX design scope for theme {bundle.item_code}."
                        if ux_scope
                        else f"Deliver the approved implementation scope for theme {bundle.item_code}."
                    ),
                    "",
                    *requirements_block,
                    "",
                    *standards_block,
                    *( ["", *skill_block] if skill_block else [] ),
                    "",
                    "Delivery objective:",
                    *delivery_objective_lines,
                    "",
                    "Execution context:",
                    *execution_context_lines,
                    "",
                    "Execution plan:",
                    *[
                        f"- [ ] {step}"
                        for step in execution_steps
                    ],
                    "",
                    "Verification plan:",
                    *verification_plan,
                    "",
                    "Canonical references:",
                    relative_refs,
                ]
            ),
            "hints": "\n".join(f"- {item}" for item in hints),
            "acceptance_criteria": "\n".join(
                f"- [ ] {_compact_issue_line(item)}"
                for item in acceptance[:8]
                if _compact_issue_line(item)
            )
            or "- [ ] Acceptance criteria are specified and testable.",
            "milestone_id": milestone_id,
            "sprint_hint": sprint_hint,
            "parent_epic": epic_id,
            "parent_story": story_id,
        },
    )
    return {"epic": epic, "story": story, "task": task}


def _build_bug_planning_artifact(
    stage: str,
    bundle,
    templates: dict[str, str],
    title: str,
    problem: str,
    scope: str,
    acceptance: list[str],
    hints: list[str],
    milestone_id: str,
    sprint_hint: str,
    parent_epic: str = "",
    parent_story: str = "",
) -> str:
    """Build bug artifact for bundles classified as bug."""
    badge = _stage_badge(stage)
    bug_id = f"BUG-{bundle.item_code}"

    problem_lines = _dedupe_text(
        [
            line.strip().lstrip("-* ").strip()
            for line in problem.splitlines()
            if line.strip()
        ]
    )
    scope_lines = _dedupe_text(
        [
            line.strip().lstrip("-* ").strip()
            for line in scope.splitlines()
            if line.strip()
        ]
    )
    concise_problem = _compact_issue_line(problem_lines[0] if problem_lines else title).rstrip(".")
    concise_scope = ""
    for candidate in scope_lines:
        candidate_compact = _compact_issue_line(candidate)
        if candidate_compact.lower() != concise_problem.lower():
            concise_scope = candidate_compact.rstrip(".")
            break

    acceptance_candidates = _dedupe_text([_compact_issue_line(item) for item in acceptance])
    acceptance_filtered: list[str] = []
    for item in acceptance_candidates:
        item_stripped = item.rstrip(".")
        lowered = item_stripped.lower()
        if not item_stripped:
            continue
        if lowered in {concise_problem.lower(), concise_scope.lower()}:
            continue
        acceptance_filtered.append(item_stripped)

    if not acceptance_filtered:
        acceptance_filtered = [
            "Root cause is identified and verified with regression coverage",
        ]

    description_lines = [f"- Symptom: {concise_problem}."]
    if concise_scope:
        description_lines.append(f"- Impact scope: {concise_scope}.")
    if acceptance_filtered:
        description_lines.append(f"- Expected fix outcome: {acceptance_filtered[0]}.")

    return _render_template(
        templates["bug"],
        {
            "stage": stage,
            "bug_id": bug_id,
            "title": f"Resolve {title}",
            "badge_color": badge,
            "agent_role": "quality-expert",
            "date": timestamp(),
            "description": "\n".join(description_lines),
            "acceptance_criteria": "\n".join(
                f"- [ ] {item}" for item in acceptance_filtered
            ),
            "milestone_id": milestone_id,
            "sprint_hint": sprint_hint,
            "hints": "\n".join(f"- {item}" for item in hints),
            "parent_epic": parent_epic,
            "parent_story": parent_story,
        },
    )


def _frontmatter_id(path: Path, key: str) -> str:
    """Extract one frontmatter identifier from a planning artifact."""
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf'^\s*{re.escape(key)}:\s*"?(?P<value>[A-Z0-9\-]+)"?\s*$', text, flags=re.MULTILINE)
    return match.group("value").strip() if match else ""


def _resolve_existing_bug_parents(planning_root: Path, stage: str, item_code: str) -> tuple[str, str]:
    """Resolve existing epic/story identifiers a bug can be attached to."""
    stage_root = planning_root / stage
    if not stage_root.exists():
        return "", ""

    preferred_story = stage_root / f"STORY_{item_code}.md"
    preferred_epic = stage_root / f"EPIC_{item_code}.md"

    story_id = _frontmatter_id(preferred_story, "story_id") if preferred_story.exists() else ""
    epic_id = _frontmatter_id(preferred_epic, "epic_id") if preferred_epic.exists() else ""

    if not story_id:
        story_candidates = sorted(stage_root.glob("STORY_*.md"))
        if story_candidates:
            story_id = _frontmatter_id(story_candidates[0], "story_id")

    if not epic_id:
        epic_candidates = sorted(stage_root.glob("EPIC_*.md"))
        if epic_candidates:
            epic_id = _frontmatter_id(epic_candidates[0], "epic_id")

    return epic_id, story_id


def _build_planning_artifacts(
    stage: str,
    bundle,
    spec_path: Path,
    templates: dict[str, str],
    planning_root: Path,
) -> dict[str, str]:
    """Build template-based planning artifacts for one bundle."""
    inputs = _build_planning_inputs(bundle, spec_path)
    title = str(inputs["title"])
    problem = str(inputs["problem"] or "Address the approved source specification.")
    scope = str(
        inputs["scope"]
        or "Translate the approved source specification into delivery-ready work."
    )
    acceptance = list(inputs["acceptance"])  # type: ignore[call-overload]
    hints = _normalize_hints(list(inputs["constraints"]), spec_path)  # type: ignore[call-overload]
    milestone_id, sprint_hint = _milestone_fields(stage, bundle.item_code)

    if inputs["classification"] == "bug":
        parent_epic, parent_story = _resolve_existing_bug_parents(
            planning_root,
            stage,
            bundle.item_code,
        )
        if parent_epic or parent_story:
            return {
                "bug": _build_bug_planning_artifact(
                    stage,
                    bundle,
                    templates,
                    title,
                    problem,
                    scope,
                    acceptance,
                    hints,
                    milestone_id,
                    sprint_hint,
                    parent_epic=parent_epic,
                    parent_story=parent_story,
                )
            }

    artifacts = _build_core_planning_artifacts(
        stage,
        bundle,
        spec_path,
        templates,
        title,
        problem,
        scope,
        acceptance,
        hints,
        milestone_id,
        sprint_hint,
        str(inputs.get("preferred_role", "")),
    )

    if inputs["classification"] == "bug":
        parent_epic, parent_story = _resolve_existing_bug_parents(
            planning_root,
            stage,
            bundle.item_code,
        )
        artifacts["bug"] = _build_bug_planning_artifact(
            stage,
            bundle,
            templates,
            title,
            problem,
            scope,
            acceptance,
            hints,
            milestone_id,
            sprint_hint,
            parent_epic=parent_epic,
            parent_story=parent_story,
        )
    return artifacts


def _run_command(
    args: list[str], repo_root: Path, *, env: dict[str, str] | None = None
) -> tuple[bool, str]:
    """Run a command and return success plus combined output."""
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            cwd=repo_root,
            env=env,
        )
    except OSError as exc:  # pragma: no cover - defensive runtime fallback
        return False, str(exc)
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return completed.returncode == 0, output


def _board_ticket_exists(repo_root: Path, ticket_id: str) -> bool:
    suffix = f"/{ticket_id}"
    for board in load_board_config(repo_root)["git_board"]["boards"].values():
        ok, output = _run_command(
            [
                "git",
                "for-each-ref",
                "--format=%(refname)",
                f"{board['ref_prefix']}/",
            ],
            repo_root,
        )
        if ok and any(line.strip().endswith(suffix) for line in output.splitlines()):
            return True
    return False


def _board_ticket_ref(repo_root: Path, ticket_id: str) -> str | None:
    """Return the full board ref for a ticket id, if present."""
    suffix = f"/{ticket_id}"
    for board in load_board_config(repo_root)["git_board"]["boards"].values():
        ok, output = _run_command(
            [
                "git",
                "for-each-ref",
                "--format=%(refname)",
                f"{board['ref_prefix']}/",
            ],
            repo_root,
        )
        if not ok:
            continue
        for line in output.splitlines():
            ref = line.strip()
            if ref.endswith(suffix):
                return ref
    return None


def _yaml_quote(value: str) -> str:
    """Return a minimally escaped double-quoted YAML scalar."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _extract_inline_yaml_list(line_value: str) -> list[str]:
    """Extract items from a one-line YAML list representation."""
    stripped = line_value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return []
    raw_items = [item.strip() for item in stripped[1:-1].split(",")]
    return [item.strip('"').strip("'") for item in raw_items if item]


def _extract_yaml_list_field(yaml_text: str, key: str) -> list[str]:
    """Extract list-like values for a top-level YAML key."""
    lines = yaml_text.splitlines()
    inline_pattern = re.compile(rf"^{re.escape(key)}:\s*(\[.*\])\s*$")
    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        inline_match = inline_pattern.match(line)
        if inline_match:
            return _extract_inline_yaml_list(inline_match.group(1))
        if line.strip() != f"{key}:":
            continue
        values: list[str] = []
        for tail in lines[idx + 1 :]:
            if re.match(r"^[^\s].*:", tail):
                break
            stripped = tail.strip()
            if stripped.startswith("-"):
                values.append(stripped[1:].strip().strip('"').strip("'"))
        return [value for value in values if value]
    return []


def _extract_yaml_block_scalar(yaml_text: str, key: str) -> str:
    """Extract a top-level YAML block scalar (key: |) content."""
    lines = yaml_text.splitlines()
    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        if line.strip() != f"{key}: |":
            continue
        block: list[str] = []
        for tail in lines[idx + 1 :]:
            if re.match(r"^[^\s].*:", tail):
                break
            if tail.startswith("  "):
                block.append(tail[2:])
        return "\n".join(block).strip()
    return ""


def _ticket_needs_content_hydration(yaml_text: str) -> bool:
    """Return True when a board ticket misses meaningful description/AC/DoD."""
    description = _extract_yaml_block_scalar(yaml_text, "description")
    acceptance = _extract_yaml_list_field(yaml_text, "acceptance_criteria")
    definition_of_done = _extract_yaml_list_field(yaml_text, "definition_of_done")

    localized_markers = (
        "heute passiert",
        "zu spaet",
        "zu uneinheitlich",
        "zusammenhaengende",
        "ausgangslage",
        "kernproblem",
        "akteptanzkriterien",
    )
    combined_text = "\n".join([description, *acceptance, *definition_of_done]).lower()
    contains_localized_fragments = any(marker in combined_text for marker in localized_markers)

    # If the description still contains full markdown/frontmatter payloads,
    # the issue view becomes redundant and hard to scan.
    description_looks_raw_markdown = (
        description.startswith("---\n")
        or "\n## Acceptance Criteria" in description
        or "\n## Definition of Done" in description
        or "\n## Source Specifications" in description
    )

    description_ok = bool(description) and not description.startswith(
        "Auto-seeded from /project planning flow."
    )
    title_value = _simple_yaml_value(yaml_text, "title")
    title_looks_generic = bool(
        title_value
        and re.match(
            r"^\[[^\]]+\]\s+((task\s+[a-z0-9\-]+)|([a-z0-9\-]+\s+bug))$",
            title_value.strip(),
            flags=re.IGNORECASE,
        )
    )
    if description_looks_raw_markdown:
        return True
    if contains_localized_fragments:
        return True
    return title_looks_generic or not (
        description_ok and bool(acceptance) and bool(definition_of_done)
    )


def _ticket_missing_required_fields(yaml_text: str) -> bool:
    """Return True when required lifecycle fields (assigned/sprint) are unset."""
    assigned = (_simple_yaml_value(yaml_text, "assigned") or "").strip().strip('"')
    sprint = (_simple_yaml_value(yaml_text, "sprint") or "").strip().strip('"')
    missing_assigned = not assigned or assigned.lower() in {"null", "none", "unassigned"}
    missing_sprint = not sprint or sprint.lower() in {"null", "none"}
    return missing_assigned or missing_sprint


def _default_stage_sprint_id(stage: str) -> str:
    """Build a deterministic sprint id for stage-scoped planning tickets."""
    token = (stage.strip() or "project").upper()
    return f"SPRINT-{token}-ACTIVE"


def _hydrate_existing_board_ticket(
    repo_root: Path,
    ticket_id: str,
    title: str,
    description: str,
    acceptance_criteria: list[str] | None,
    definition_of_done: list[str] | None,
    assigned_to: str | None = None,
    sprint_id: str | None = None,
) -> tuple[bool, str]:
    """Update an existing ticket blob with rich content while preserving metadata."""
    ticket_ref = _board_ticket_ref(repo_root, ticket_id)
    if not ticket_ref:
        return False, f"exists-without-ref:{ticket_id}"

    ok, existing_blob = _run_command(["git", "cat-file", "-p", ticket_ref], repo_root)
    if not ok:
        return False, existing_blob or f"failed-to-read:{ticket_ref}"

    needs_content = _ticket_needs_content_hydration(existing_blob)
    missing_required_fields = _ticket_missing_required_fields(existing_blob)
    if not needs_content and not missing_required_fields:
        return False, f"exists:{ticket_id}"

    layer = _simple_yaml_value(existing_blob, "layer") or "digital-generic-team"
    created = _simple_yaml_value(existing_blob, "created") or timestamp()
    assigned = _simple_yaml_value(existing_blob, "assigned") or "null"
    locked_by = _simple_yaml_value(existing_blob, "locked_by") or "null"
    locked_at = _simple_yaml_value(existing_blob, "locked_at") or "null"
    sprint = _simple_yaml_value(existing_blob, "sprint") or "null"
    labels = _extract_yaml_list_field(existing_blob, "labels")

    normalized_assigned = (assigned_to or "").strip() or "fullstack-engineer"
    if assigned.strip().lower() in {"", "null", "none", "unassigned"}:
        assigned = normalized_assigned
    normalized_sprint = (sprint_id or "").strip()
    if not normalized_sprint:
        normalized_sprint = _default_stage_sprint_id(ticket_id.split("-")[0])
    if sprint.strip().lower() in {"", "null", "none"}:
        sprint = normalized_sprint

    resolved_description = description.strip() or "No description provided."
    resolved_acceptance = [
        item.strip()
        for item in (acceptance_criteria or [])
        if item and item.strip()
    ]
    resolved_dod = [
        item.strip()
        for item in (definition_of_done or [])
        if item and item.strip()
    ]
    if not resolved_dod:
        resolved_dod = [
            "PR merged",
            "Tests pass",
            "Human review approval recorded",
        ]

    lines = [
        f"id: {ticket_id}",
        f'title: {_yaml_quote(title)}',
        "description: |",
    ]
    lines.extend(f"  {line}" for line in resolved_description.splitlines())
    lines.extend(
        [
            f"layer: {layer}",
            f"created: {created}",
            f"assigned: {assigned}",
            f"locked_by: {locked_by}",
            f"locked_at: {locked_at}",
        ]
    )
    if labels:
        lines.append("labels:")
        lines.extend(f"  - {_yaml_quote(label)}" for label in labels)
    else:
        lines.append("labels: []")
    if resolved_acceptance:
        lines.append("acceptance_criteria:")
        lines.extend(f"  - {_yaml_quote(item)}" for item in resolved_acceptance)
    else:
        lines.append("acceptance_criteria: []")
    lines.append("definition_of_done:")
    lines.extend(f"  - {_yaml_quote(item)}" for item in resolved_dod)
    lines.append(f"sprint: {sprint}")
    updated_yaml = "\n".join(lines) + "\n"

    try:
        blob_process = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=repo_root,
            text=True,
            input=updated_yaml,
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - defensive runtime fallback
        return False, str(exc)

    if blob_process.returncode != 0:
        output = ((blob_process.stdout or "") + (blob_process.stderr or "")).strip()
        return False, output or f"failed-to-store:{ticket_ref}"

    new_hash = (blob_process.stdout or "").strip()
    ok_update, update_output = _run_command(
        ["git", "update-ref", ticket_ref, new_hash],
        repo_root,
    )
    if not ok_update:
        return False, update_output or f"failed-to-update:{ticket_ref}"

    board_push = os.getenv("BOARD_PUSH", "1").strip().lower()
    if board_push not in {"0", "false", "off", "no"}:
        board_remote = os.getenv("BOARD_REMOTE", "origin")
        remote_ok, _remote_output = _run_command(
            ["git", "remote", "get-url", board_remote],
            repo_root,
        )
        if remote_ok:
            push_ok, push_output = _run_command(
                ["git", "push", board_remote, f"+{ticket_ref}:{ticket_ref}"],
                repo_root,
            )
            if not push_ok:
                return False, push_output or f"failed-to-push:{ticket_ref}"

    return True, f"updated:{ticket_id}"


def _ensure_board_ticket(
    repo_root: Path,
    board_name: str,
    ticket_id: str,
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
    definition_of_done: list[str] | None = None,
    assigned_to: str | None = None,
    sprint_id: str | None = None,
    sprint_goal: str | None = None,
) -> tuple[bool, str]:
    """Create a board ticket when missing and return status details."""
    if _board_ticket_exists(repo_root, ticket_id):
        return _hydrate_existing_board_ticket(
            repo_root,
            ticket_id,
            title,
            description,
            acceptance_criteria,
            definition_of_done,
            assigned_to=assigned_to,
            sprint_id=sprint_id,
        )

    board_script = (
        repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    )
    if not board_script.exists():
        return False, "board-ticket script missing"

    env = os.environ.copy()
    env.setdefault("BOARD_PUSH", "1")
    env.setdefault("BOARD_NAME", board_name)
    env["BOARD_STRICT_CREATE"] = "1"
    env["BOARD_ASSIGNED"] = (assigned_to or "").strip() or "fullstack-engineer"
    env["BOARD_SPRINT"] = (sprint_id or "").strip() or _default_stage_sprint_id(board_name)
    env["BOARD_ENSURE_SPRINT"] = "1"
    env["BOARD_SPRINT_GOAL"] = (
        (sprint_goal or "").strip()
        or f"Auto-created sprint for stage '{board_name}' planning queue"
    )
    if acceptance_criteria:
        env["BOARD_ACCEPTANCE_CRITERIA"] = "\n".join(acceptance_criteria)
    if definition_of_done:
        env["BOARD_DEFINITION_OF_DONE"] = "\n".join(definition_of_done)
    ok, output = _run_command(
        ["bash", str(board_script), "create", ticket_id, title, description],
        repo_root,
        env=env,
    )
    if ok:
        return True, output or f"created:{ticket_id}"
    return False, output or f"failed:{ticket_id}"


def _update_ticket_block_reason(
    repo_root: Path, ticket_ref: str, reason: str
) -> tuple[bool, str]:
    """Persist a blocked-by reason directly on a board ticket blob."""
    ok, existing_blob = _run_command(["git", "cat-file", "-p", ticket_ref], repo_root)
    if not ok:
        return False, existing_blob or f"failed-to-read:{ticket_ref}"

    blocked_value = reason.strip()
    if not blocked_value:
        return False, "empty-block-reason"

    lines = existing_blob.splitlines()
    replaced = False
    for idx, line in enumerate(lines):
        if line.startswith("blocked_by:"):
            lines[idx] = f"blocked_by: {_yaml_quote(blocked_value)}"
            replaced = True
            break
    if not replaced:
        lines.append(f"blocked_by: {_yaml_quote(blocked_value)}")

    updated_yaml = "\n".join(lines).rstrip() + "\n"
    blob_process = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo_root,
        text=True,
        input=updated_yaml,
        capture_output=True,
        check=False,
    )
    if blob_process.returncode != 0:
        output = ((blob_process.stdout or "") + (blob_process.stderr or "")).strip()
        return False, output or f"failed-to-store:{ticket_ref}"

    new_hash = (blob_process.stdout or "").strip()
    ok_update, update_output = _run_command(
        ["git", "update-ref", ticket_ref, new_hash],
        repo_root,
    )
    if not ok_update:
        return False, update_output or f"failed-to-update:{ticket_ref}"

    board_push = os.getenv("BOARD_PUSH", "1").strip().lower()
    if board_push not in {"0", "false", "off", "no"}:
        board_remote = os.getenv("BOARD_REMOTE", "origin")
        remote_ok, _remote_output = _run_command(
            ["git", "remote", "get-url", board_remote],
            repo_root,
        )
        if remote_ok:
            push_ok, push_output = _run_command(
                ["git", "push", board_remote, f"+{ticket_ref}:{ticket_ref}"],
                repo_root,
            )
            if not push_ok:
                return False, push_output or f"failed-to-push:{ticket_ref}"

    return True, f"blocked-reason-updated:{ticket_ref}"


def _block_unspecified_bug_ticket(
    repo_root: Path,
    board_name: str,
    stage: str,
    bundle_item_code: str,
) -> str:
    """Move legacy generic bug tickets to blocked when no bug artifact is actionable."""
    bug_specs = _planning_ticket_specs(
        stage,
        bundle_item_code,
        "feature",
        {"bug"},
    )
    bug_ticket_id = bug_specs.get("bug", ("", ""))[0]
    if not bug_ticket_id:
        return "bug-ticket-skip:no-id"

    is_git_repo, _ = _run_command(["git", "rev-parse", "--is-inside-work-tree"], repo_root)
    if not is_git_repo:
        return f"bug-ticket-skip:board-unavailable:{bug_ticket_id}"

    ticket_ref = _board_ticket_ref(repo_root, bug_ticket_id)
    if not ticket_ref:
        return f"bug-ticket-skip:not-present:{bug_ticket_id}"

    ref_parts = ticket_ref.split("/")
    if len(ref_parts) < 2:
        return f"bug-ticket-skip:invalid-ref:{bug_ticket_id}"
    current_column = ref_parts[-2]
    if current_column == "done":
        return f"bug-ticket-skip:already-done:{bug_ticket_id}"

    board_script = (
        repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    )
    if current_column != "blocked" and board_script.exists():
        env = os.environ.copy()
        env.setdefault("BOARD_PUSH", "1")
        env.setdefault("BOARD_NAME", board_name)
        _run_command(
            [
                "bash",
                str(board_script),
                "move",
                bug_ticket_id,
                current_column,
                "blocked",
            ],
            repo_root,
            env=env,
        )

    blocked_ref = _board_ticket_ref(repo_root, bug_ticket_id)
    if not blocked_ref:
        return f"bug-ticket-blocked:missing-ref:{bug_ticket_id}"

    reason = (
        "Blocked automatically: no dedicated BUG planning artifact exists for this "
        "theme, so delivery scope is not actionable."
    )
    ok_reason, reason_msg = _update_ticket_block_reason(repo_root, blocked_ref, reason)
    if not ok_reason:
        return f"bug-ticket-blocked:reason-failed:{bug_ticket_id}:{reason_msg}"
    return f"bug-ticket-blocked:unspecified:{bug_ticket_id}"


def _ensure_local_board_seed(
    repo_root: Path,
    board_name: str,
    stage: str,
    bundle,
    planning_paths: dict[str, Path],
    classification: str,
) -> tuple[str, list[str], list[str]]:
    """Seed local refs/board tickets when GitHub project sync is unavailable."""
    available_ticket_kinds = set(planning_paths.keys())
    available_ticket_kinds.add("task")
    details: list[str] = []

    if "bug" not in planning_paths:
        bug_gate_status = _block_unspecified_bug_ticket(
            repo_root,
            board_name,
            stage,
            bundle.item_code,
        )
        details.append(bug_gate_status)
        if not bug_gate_status.startswith("bug-ticket-skip:not-present:"):
            available_ticket_kinds.add("bug")

    ticket_specs = _planning_ticket_specs(
        stage,
        bundle.item_code,
        classification,
        available_ticket_kinds,
    )
    sprint_id = _default_stage_sprint_id(stage)
    sprint_goal = f"Stage {stage.title()} planning execution for bundle group {bundle.item_code}"
    assigned_role = "fullstack-engineer"

    for planning_path in planning_paths.values():
        if planning_path is None or not planning_path.exists():
            continue
        planning_text = planning_path.read_text(encoding="utf-8")
        assignee_match = re.search(
            r'^assignee_hint:\s*"?(?P<value>[a-z0-9\-]+)"?\s*$',
            planning_text,
            flags=re.MULTILINE,
        )
        if assignee_match and assignee_match.group("value").strip():
            assigned_role = assignee_match.group("value").strip()
            break
    created_ids: list[str] = []

    def _normalize_localized_ticket_line(line: str) -> str:
        """Normalize known localized fragments into deterministic English text."""
        normalized = line.strip()
        prefix_match = re.match(r"^(?P<prefix>(?:[-*]|\d+\.)\s+)(?P<body>.+)$", normalized)
        prefix = ""
        body = normalized
        if prefix_match:
            prefix = prefix_match.group("prefix")
            body = prefix_match.group("body")

        body = body.replace(":.", ":").replace(",.", ".")
        lowered = body.lower()

        def _restore_with_original_punctuation(replacement: str) -> str:
            trailing = ""
            if body.endswith(":"):
                trailing = ":"
            elif body.endswith("."):
                trailing = "."
            return f"{prefix}{replacement}{trailing}".strip()
        replacements = (
            (
                "heute passiert die bewertung oft",
                "Today, assessment often happens",
            ),
            (
                "zu spaet (wartezeit auf geeignete experten)",
                "too late (waiting time for suitable experts)",
            ),
            (
                "zu uneinheitlich (kein durchgaengiges gate-format)",
                "too inconsistent (no end-to-end gate format)",
            ),
            (
                "problem, stakeholder, kontext und ux sind als zusammenhaengende story dokumentiert",
                "Problem, stakeholders, context, and UX are documented as one coherent story",
            ),
        )
        for needle, replacement in replacements:
            if needle in lowered:
                return _restore_with_original_punctuation(replacement)

        german_markers = (
            "ausgangslage",
            "kernproblem",
            "zusammenhaengende",
            "bewertung",
            "wartezeit",
            "durchgaengiges",
            "spaet",
        )
        if any(marker in lowered for marker in german_markers):
            return f"{prefix}Translated source statement (fallback normalization applied).".strip()
        return f"{prefix}{body}".strip()

    def _normalize_ticket_block(text: str) -> str:
        """Normalize multi-line ticket text while preserving readability."""
        lines = [_normalize_localized_ticket_line(line) for line in text.splitlines()]
        return "\n".join(lines).strip()

    def _normalize_ticket_list(values: list[str]) -> list[str]:
        """Normalize list values used for acceptance criteria and DoD fields."""
        return [_normalize_localized_ticket_line(value) for value in values if value.strip()]

    def _extract_label_bullets(text: str, label: str) -> list[str]:
        """Extract bullets from label-based sections like 'Execution plan:'."""
        lines = text.splitlines()
        label_key = label.strip().lower().rstrip(":")
        collect = False
        collected: list[str] = []
        for raw in lines:
            stripped = raw.strip()
            if not collect:
                if stripped.lower().rstrip(":") == label_key:
                    collect = True
                continue

            if not stripped:
                if collected:
                    break
                continue
            if stripped.startswith("## "):
                break
            if stripped.endswith(":") and not stripped.startswith("-"):
                break
            if re.match(r"^\s*-\s+", raw):
                item = re.sub(r"^\s*-\s*(\[[ xX]\]\s*)?", "", raw).strip()
                if item:
                    collected.append(item)
        return collected

    def _extract_planning_title(path: Path | None) -> str:
        if path is None or not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        title_match = re.search(
            r'^title:\s*"?(?P<value>.+?)"?\s*$',
            text,
            flags=re.MULTILINE,
        )
        if title_match and title_match.group("value").strip():
            return title_match.group("value").strip()
        return ""

    def _ticket_payload(
        ticket_kind: str, fallback_title: str
    ) -> tuple[str, str, list[str], list[str]]:
        planning_path = planning_paths.get(ticket_kind)
        if planning_path is None:
            ticket_title = fallback_title
            source_title = (
                _extract_planning_title(planning_paths.get("task"))
                or _extract_planning_title(planning_paths.get("story"))
                or _extract_planning_title(planning_paths.get("epic"))
            )
            if ticket_kind == "bug" and source_title:
                ticket_title = f"Fix defects in {source_title}"
            return (
                ticket_title,
                (
                    "Auto-seeded delivery ticket. This ticket summarizes approved planning scope "
                    f"for stage '{stage}' and bundle '{bundle.item_code}'. "
                    "Open the matching planning artifacts to inspect detailed implementation steps."
                ),
                [
                    "Implement the approved scope for this ticket.",
                    "Keep behavior aligned with the canonical stage specification.",
                ],
                [
                    "PR merged",
                    "Tests pass",
                    "Human review approval recorded",
                ],
            )

        planning_text = planning_path.read_text(encoding="utf-8")
        ticket_title = _extract_planning_title(planning_path) or fallback_title
        description_section = _extract_section(planning_text, "Description")
        if description_section:
            description_lines = [line.rstrip() for line in description_section.splitlines()]
            description = _normalize_ticket_block("\n".join(description_lines))
        else:
            description = (
                "Auto-seeded delivery ticket. This ticket summarizes approved planning scope "
                f"for stage '{stage}' and bundle '{bundle.item_code}'."
            )
        acceptance = _extract_markdown_bullets(planning_text, "Acceptance Criteria")
        if not acceptance:
            acceptance = _extract_markdown_bullets(planning_text, "Execution plan")
        if not acceptance:
            acceptance = _extract_label_bullets(planning_text, "Execution plan")
        dod = _extract_markdown_bullets(planning_text, "Definition of Done")
        if not dod:
            dod = [
                "PR merged",
                "Tests pass",
                "Human review approval recorded",
            ]
        return (
            ticket_title,
            description,
            _normalize_ticket_list(acceptance),
            _normalize_ticket_list(dod),
        )

    for ticket_kind, (ticket_id, title) in ticket_specs.items():
        ticket_title, description, acceptance, dod = _ticket_payload(ticket_kind, title)
        created, message = _ensure_board_ticket(
            repo_root,
            board_name,
            ticket_id,
            ticket_title,
            description,
            acceptance_criteria=acceptance,
            definition_of_done=dod,
            assigned_to=assigned_role,
            sprint_id=sprint_id,
            sprint_goal=sprint_goal,
        )
        if created:
            created_ids.append(ticket_id)
        details.append(message)

    status = "seeded" if created_ids else "existing"
    return status, created_ids, details


def _planning_ticket_specs(
    stage: str,
    bundle_item_code: str,
    _classification: str,
    artifact_kinds: set[str] | None = None,
) -> dict[str, tuple[str, str]]:
    """Return deterministic local/remote ticket identifiers per planning artifact kind."""
    stage_prefix = (stage.strip()[:3] or "stg").upper()
    ticket_prefix = f"{stage_prefix}-{bundle_item_code}"
    available = artifact_kinds or {"task", "bug"}
    tickets: dict[str, tuple[str, str]] = {}
    if "task" in available:
        tickets["task"] = (
            f"{ticket_prefix}-TASK",
            f"[{stage}] Task {bundle_item_code}",
        )
    if "bug" in available:
        tickets["bug"] = (f"{ticket_prefix}-BUG", f"[{stage}] {bundle_item_code} Bug")
    return tickets


def _build_dispatch_trace_content(
    stage: str,
    bundle,
    stage_path: Path,
    planning_paths: dict[str, Path],
    project_status: str,
    project_message: str,
    board_name: str,
    board_status: str,
    board_tickets: list[str],
    board_details: list[str],
    trigger_state: str,
) -> str:
    """Build dispatch trace markdown content."""
    return "\n".join(
        [
            f"# Delivery Dispatch Trace {bundle.item_code}",
            "",
            f"- stage: {stage}",
            f"- source_stage: {stage_path.as_posix()}",
            *[
                f"- planning_{kind}: {path.as_posix()}"
                for kind, path in sorted(planning_paths.items())
            ],
            f"- github_project_status: {project_status}",
            f"- github_project_message: {project_message}",
            f"- board_name: {board_name}",
            f"- board_seed_status: {board_status}",
            f"- trigger_state: {trigger_state}",
            f"- seeded_board_tickets: {', '.join(board_tickets) if board_tickets else 'none'}",
            "",
            "## Dispatch Notes",
            *(
                [f"- {entry}" for entry in board_details]
                if board_details
                else ["- No additional dispatch notes."]
            ),
            "",
        ]
    )


def _ensure_board_seeding(
    project_status: str,
    repo_root: Path,
    board_name: str,
    stage: str,
    bundle,
    planning_paths: dict[str, Path],
    classification: str,
) -> tuple[str, list, list, str, int]:
    """Always ensure refs/board tickets and return active dispatch state."""
    if not _is_configured_stage_board(repo_root, board_name):
        return (
            "skipped-stage-board-not-configured",
            [],
            [
                f"primary-sync-status:{project_status}",
                f"board-config-missing:{board_name}",
            ],
            "skipped",
            0,
        )

    board_status, board_tickets, board_details = _ensure_local_board_seed(
        repo_root,
        board_name,
        stage,
        bundle,
        planning_paths,
        str(classification),
    )
    board_details = [f"primary-sync-status:{project_status}", *board_details]

    trigger_state = "queued-on-board"
    board_seeded_count = 0
    if board_status in {"seeded", "existing"}:
        trigger_state = "deliveries-triggered"
    if board_status == "seeded":
        board_seeded_count = len(board_tickets)

    return board_status, board_tickets, board_details, trigger_state, board_seeded_count


def _process_planning_bundle(
    repo_root: Path,
    stage: str,
    bundle,
    stage_root: Path,
    planning_root: Path,
    planning_inventory_template: Path,
    templates: dict[str, str],
    *,
    stage_doc_path_fn,
    planning_item_path_fn,
    planning_dispatch_path_fn,
    github_project_sync,
    stage_primary_assets: dict[str, object],
) -> tuple[int, int]:
    """Process one planning bundle; return (created, board_seeded)."""
    stage_path = stage_doc_path_fn(stage_root, stage)
    if not stage_path.exists():
        return 0, 0
    spec_path = (
        specification_path(
            repo_root / ".digital-artifacts" / "30-specification", bundle
        )
    )
    if not spec_path.exists():
        return 0, 0
    project_status, project_message = github_project_sync(stage)
    artifact_contents = _build_planning_artifacts(
        stage,
        bundle,
        spec_path,
        templates,
        planning_root,
    )
    planning_paths = {
        kind: planning_item_path_fn(planning_root, stage, kind, bundle.item_code)
        for kind in artifact_contents
    }
    classification = str(_build_planning_inputs(bundle, spec_path)["classification"])
    board_name = _resolve_board_for_stage(repo_root, stage)

    for kind, content in artifact_contents.items():
        ensure_text(planning_paths[kind], content)

    board_ticket_specs = _planning_ticket_specs(
        stage,
        bundle.item_code,
        classification,
        set(planning_paths.keys()),
    )
    board_ticket_ids = {
        kind: ticket_id
        for kind, (ticket_id, _title) in board_ticket_specs.items()
        if kind in planning_paths
    }

    board_status, board_tickets, board_details, trigger_state, board_seeded_count = (
        _ensure_board_seeding(
            project_status,
            repo_root,
            board_name,
            stage,
            bundle,
            planning_paths,
            classification,
        )
    )

    primary_issue_sync = ensure_planning_issue_assets(
        repo_root,
        stage,
        bundle_id(bundle),
        planning_paths,
        board_ticket_ids,
        stage_primary_assets,
    )
    _wiki_raw = stage_primary_assets.get("wiki")
    wiki_sync = _wiki_raw if isinstance(_wiki_raw, dict) else {}
    board_details.extend(
        [
            f"primary-wiki-status:{wiki_sync.get('status', 'manual-required')}",
            f"primary-wiki-url:{wiki_sync.get('url', '') or 'none'}",
        ]
    )
    _issues_raw = primary_issue_sync.get("issues")
    _issues_dict: dict[str, Any] = _issues_raw if isinstance(_issues_raw, dict) else {}
    for kind, issue_result in sorted(_issues_dict.items()):  # type: ignore[attr-defined]
        board_details.append(
            f"primary-issue-{kind}:{issue_result.get('status', 'manual-required')}:{issue_result.get('url', '') or 'none'}"
        )
        board_details.append(
            f"primary-project-item-{kind}:{issue_result.get('project_item_status', 'skipped')}"
        )

    dispatch_trace_path = planning_dispatch_path_fn(
        planning_root, stage, bundle.item_code
    )
    dispatch_content = _build_dispatch_trace_content(
        stage,
        bundle,
        stage_path,
        planning_paths,
        project_status,
        project_message,
        board_name,
        board_status,
        board_tickets,
        board_details,
        trigger_state,
    )
    ensure_text(dispatch_trace_path, dispatch_content)

    inventory_upsert(
        planning_root / "INVENTORY.md",
        planning_inventory_template,
        bundle_id(bundle),
        {
            "status": f"planning-{stage}-ready",
            "paths": [
                *(path.as_posix() for path in planning_paths.values()),
                dispatch_trace_path.as_posix(),
            ],
        },
    )
    return 1, board_seeded_count


def _load_planning_templates(stage_template_root: Path) -> dict[str, str]:
    """Load planning artifact templates from stage template directory."""
    return {
        "epic": (stage_template_root / "epic.md").read_text(encoding="utf-8"),
        "story": (stage_template_root / "story.md").read_text(encoding="utf-8"),
        "task": (stage_template_root / "task.md").read_text(encoding="utf-8"),
        "bug": (stage_template_root / "bug.md").read_text(encoding="utf-8"),
    }


def _setup_planning_paths(repo_root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Setup and return all planning-related artifact paths."""
    artifacts_root = repo_root / ".digital-artifacts"
    data_root = artifacts_root / "10-data"
    stage_root = artifacts_root / "40-stage"
    planning_root = artifacts_root / "50-planning"
    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    planning_inventory_template = (
        template_root / "50-planning" / "INVENTORY.template.md"
    )
    return (
        data_root,
        stage_root,
        planning_root,
        planning_inventory_template,
        template_root,
        artifacts_root,
    )


def _parse_stage_frontmatter(stage_text: str) -> dict[str, object]:
    """Parse minimal stage frontmatter values needed for planning gating."""
    if not stage_text.startswith("---\n"):
        return {
            "ready_for_planning": False,
            "source_bundles": [],
            "blocked_bundle_ids": [],
            "gate_reason": "",
        }

    end = stage_text.find("\n---\n", 4)
    if end == -1:
        return {
            "ready_for_planning": False,
            "source_bundles": [],
            "blocked_bundle_ids": [],
            "gate_reason": "",
        }

    frontmatter = stage_text[4:end]
    ready_match = re.search(
        r"^ready_for_planning:\s*(true|false)\s*$",
        frontmatter,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    ready = bool(ready_match and ready_match.group(1).lower() == "true")
    gate_match = re.search(
        r'^gate_reason:\s*"?(.*?)"?\s*$',
        frontmatter,
        flags=re.MULTILINE,
    )
    gate_reason = gate_match.group(1).strip() if gate_match else ""

    bundles: list[str] = []
    blocked_bundle_ids: list[str] = []
    lines = frontmatter.splitlines()
    in_bundles = False
    in_blocked_bundles = False
    for line in lines:
        if re.match(r"^source_bundles:\s*$", line.strip()):
            in_bundles = True
            in_blocked_bundles = False
            continue
        if re.match(r"^blocked_bundle_ids:\s*$", line.strip()):
            in_blocked_bundles = True
            in_bundles = False
            continue
        if in_bundles:
            stripped = line.strip()
            if stripped.startswith("- "):
                bundles.append(stripped[2:].strip().strip('"'))
                continue
            if stripped and not stripped.startswith("#"):
                in_bundles = False
        if in_blocked_bundles:
            stripped = line.strip()
            if stripped.startswith("- "):
                blocked_bundle_ids.append(stripped[2:].strip().strip('"'))
                continue
            if stripped and not stripped.startswith("#"):
                in_blocked_bundles = False

    return {
        "ready_for_planning": ready,
        "source_bundles": bundles,
        "blocked_bundle_ids": blocked_bundle_ids,
        "gate_reason": gate_reason,
    }


def run_specification_to_planning_impl(
    repo_root: Path,
    stage: str,
    *,
    github_project_sync,
) -> dict[str, int]:
    """Create planning artifacts when the canonical stage document exists."""
    data_root, stage_root, planning_root, planning_inventory_template, _, _ = (
        _setup_planning_paths(repo_root)
    )
    stage_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    templates = _load_planning_templates(stage_template_root)

    stage_path = stage_doc_path(stage_root, stage)
    stage_planning_root = planning_root / stage
    stage_planning_root.mkdir(parents=True, exist_ok=True)

    default_scoring = {
        "dimensions": {
            "problem_clarity": 1,
            "scope_clarity": 1,
            "task_formulability": 1,
            "constraints_clarity": 1,
            "owner_clarity": 1,
        },
        "overall": 1,
    }
    instruction_path = _find_stage_instruction_path(repo_root, stage)
    required_inputs: list[str] = []
    if instruction_path and instruction_path.exists():
        instruction_text = instruction_path.read_text(encoding="utf-8")
        required_inputs = _extract_markdown_bullets(
            instruction_text,
            "Required Inputs",
        )

    if not stage_path.exists():
        skipped = sum(1 for _ in iter_data_bundles(data_root))
        checklist = [
            "- [ ] Stage document exists in .digital-artifacts/40-stage/",
            *[f"- [ ] Required input: {item}" for item in required_inputs],
        ]
        questions = _improvement_questions_for_gaps(
            ["required_inputs", "problem_clarity", "scope_clarity", "task_formulability", "owner_clarity"],
            1,
        )
        report_path = _write_project_assessment_report(
            stage,
            stage_planning_root,
            "cannot-start",
            checklist,
            default_scoring,
            questions,
            _feature_suggestions([]),
            None,
        )
        return {
            "created": 0,
            "skipped": skipped,
            "board_tickets_seeded": 0,
            "scenario": 0,
            "assessment_path": report_path.as_posix(),
        }

    stage_primary_assets = ensure_stage_primary_assets(repo_root, stage, stage_path)

    stage_text = stage_path.read_text(encoding="utf-8")
    gate = _parse_stage_frontmatter(stage_text)
    if not bool(gate.get("ready_for_planning", False)):
        skipped = sum(1 for _ in iter_data_bundles(data_root))
        checklist = [
            "- [x] Stage document exists.",
            "- [ ] Stage gate ready_for_planning=true",
            *[f"- [ ] Required input: {item}" for item in required_inputs],
        ]
        questions = _improvement_questions_for_gaps(
            ["required_inputs", "scope_clarity", "task_formulability", "owner_clarity"],
            1,
        )
        report_path = _write_project_assessment_report(
            stage,
            stage_planning_root,
            "cannot-start",
            checklist,
            default_scoring,
            questions,
            _feature_suggestions([]),
            {
                "gate_reason": gate.get("gate_reason", ""),
                "blocked_bundle_ids": gate.get("blocked_bundle_ids", []),
            },
        )
        return {
            "created": 0,
            "skipped": skipped,
            "board_tickets_seeded": 0,
            "scenario": 0,
            "assessment_path": report_path.as_posix(),
        }

    source_bundle_ids = set(str(value) for value in gate.get("source_bundles", []))
    selected: list[tuple[object, Path, dict[str, object]]] = []
    for bundle in iter_data_bundles(data_root):
        current_id = bundle_id(bundle)
        if source_bundle_ids and current_id not in source_bundle_ids:
            continue
        spec_path = specification_path(repo_root / ".digital-artifacts" / "30-specification", bundle)
        if not spec_path.exists():
            continue
        selected.append((bundle, spec_path, _build_planning_inputs(bundle, spec_path)))

    if not selected:
        skipped = sum(1 for _ in iter_data_bundles(data_root))
        checklist = [
            "- [x] Stage document exists.",
            "- [x] Stage gate ready_for_planning=true",
            "- [ ] At least one planning-ready specification bundle",
        ]
        questions = _improvement_questions_for_gaps(
            ["problem_clarity", "scope_clarity", "task_formulability", "owner_clarity"],
            1,
        )
        report_path = _write_project_assessment_report(
            stage,
            stage_planning_root,
            "cannot-start",
            checklist,
            default_scoring,
            questions,
            _feature_suggestions([]),
            {
                "gate_reason": gate.get("gate_reason", ""),
                "blocked_bundle_ids": gate.get("blocked_bundle_ids", []),
            },
        )
        return {
            "created": 0,
            "skipped": skipped,
            "board_tickets_seeded": 0,
            "scenario": 0,
            "assessment_path": report_path.as_posix(),
        }

    # Group approved specifications into thematic clusters (not 1:1 per bundle).
    grouped: dict[tuple[str, str], list[tuple[object, Path, dict[str, object]]]] = {}
    for item in selected:
        classification = str(item[2].get("classification", "feature")).lower()
        preferred_role = str(item[2].get("preferred_role", "")).lower()
        grouped.setdefault((classification, preferred_role), []).append(item)

    themes: list[tuple[str, str, str, list[tuple[object, Path, dict[str, object]]]]] = []
    theme_index = 1
    for (classification, preferred_role), items in sorted(grouped.items()):
        batch: list[tuple[object, Path, dict[str, object]]] = []
        for item in items:
            batch.append(item)
            if len(batch) == 3:
                themes.append((f"THM-{theme_index:02d}", classification, preferred_role, batch))
                theme_index += 1
                batch = []
        if batch:
            themes.append((f"THM-{theme_index:02d}", classification, preferred_role, batch))
            theme_index += 1

    created, board_seeded = 0, 0
    actionable_delivery_tasks = 0
    theme_labels_seen: list[str] = []
    project_status, project_message = github_project_sync(stage)
    for theme_code, classification, preferred_role, items in themes:
        bundle_keys = [bundle_id(entry[0]) for entry in items]
        theme_label, theme_summary = _derive_theme_focus(items)
        theme_labels_seen.append(theme_label)
        title = f"{stage.title()} {theme_label} ({theme_code})"
        problems = _dedupe_text(
            [_clean_theme_text(str(entry[2].get("problem", "")).strip()) for entry in items]
        )
        scopes = _dedupe_text(
            [_clean_theme_text(str(entry[2].get("scope", "")).strip()) for entry in items]
        )
        acceptance: list[str] = []
        constraints: list[str] = []
        refs: list[str] = []
        stage_wiki_ref = (Path("docs") / "wiki" / f"{stage.title()}.md").as_posix()
        for bundle, spec_path, inputs in items:
            for criterion in list(inputs.get("acceptance", [])):  # type: ignore[arg-type]
                text = str(criterion).strip()
                if text and text not in acceptance:
                    acceptance.append(text)
            for constraint in list(inputs.get("constraints", [])):  # type: ignore[arg-type]
                text = str(constraint).strip()
                if text and text not in constraints:
                    constraints.append(text)
            refs.append(
                f"- {bundle_id(bundle)} -> consolidated in {stage_wiki_ref}"
            )

        if not acceptance:
            acceptance = [
                "Theme objective is concrete and testable.",
                "Scope boundaries are explicit.",
                "Implementation plan is review-ready.",
            ]

        synthesized_problem = "\n".join([f"- {p}" for p in problems if p][:3])
        if not synthesized_problem:
            synthesized_problem = f"- {theme_summary}"
        synthesized_scope = "\n".join(
            [f"- {s}" for s in scopes if s][:3]
        )
        if not synthesized_scope:
            synthesized_scope = (
                f"- Deliver a coherent increment for bundles: {', '.join(bundle_keys)}\n"
                "- Keep scope bounded to validated constraints and acceptance criteria."
            )
        hints = _normalize_hints(constraints, stage_path)
        milestone_id, sprint_hint = _milestone_fields(stage, theme_code)

        theme_bundle = SimpleNamespace(item_code=theme_code, date_key=stage)
        if classification == "bug":
            parent_epic, parent_story = _resolve_existing_bug_parents(
                planning_root,
                stage,
                theme_code,
            )
            if parent_epic or parent_story:
                artifacts = {
                    "bug": _build_bug_planning_artifact(
                        stage,
                        theme_bundle,
                        templates,
                        title,
                        synthesized_problem,
                        synthesized_scope,
                        acceptance,
                        hints,
                        milestone_id,
                        sprint_hint,
                        parent_epic=parent_epic,
                        parent_story=parent_story,
                    )
                }
            else:
                artifacts = _build_core_planning_artifacts(
                    stage,
                    theme_bundle,
                    stage_path,
                    templates,
                    title,
                    synthesized_problem,
                    synthesized_scope,
                    acceptance,
                    hints,
                    milestone_id,
                    sprint_hint,
                    preferred_role,
                )
                artifacts["bug"] = _build_bug_planning_artifact(
                    stage,
                    theme_bundle,
                    templates,
                    title,
                    synthesized_problem,
                    synthesized_scope,
                    acceptance,
                    hints,
                    milestone_id,
                    sprint_hint,
                )
        else:
            artifacts = _build_core_planning_artifacts(
                stage,
                theme_bundle,
                stage_path,
                templates,
                title,
                synthesized_problem,
                synthesized_scope,
                acceptance,
                hints,
                milestone_id,
                sprint_hint,
                preferred_role,
            )

        planning_paths = {
            kind: planning_item_path(planning_root, stage, kind, theme_code)
            for kind in artifacts
        }
        quality_gate_blocked = False
        if "task" in artifacts:
            task_text = artifacts["task"]
            task_role = "fullstack-engineer"
            role_match = re.search(
                r'^assignee_hint:\s*"?(?P<role>[a-z0-9\-]+)"?\s*$',
                task_text,
                flags=re.MULTILINE,
            )
            if role_match:
                task_role = role_match.group("role")
            if _enforce_task_quality_gate() and _task_has_requirement_contract(task_text):
                missing_markers = _evaluate_task_quality_gate(task_text, task_role)
                if missing_markers:
                    quality_gate_blocked = True
                    artifacts["task"] = _apply_blocked_quality_gate(
                        task_text, missing_markers
                    )
            if _task_is_actionable_delivery(artifacts["task"]):
                actionable_delivery_tasks += 1

        for kind, content in artifacts.items():
            content_with_refs = (
                content
                + "\n\n## Source Specifications\n"
                + "\n".join(refs)
            )
            ensure_text(planning_paths[kind], content_with_refs)

        board_ticket_specs = _planning_ticket_specs(
            stage,
            theme_code,
            classification,
            set(planning_paths.keys()),
        )
        board_ticket_ids = {
            kind: ticket_id
            for kind, (ticket_id, _title) in board_ticket_specs.items()
            if kind in planning_paths
        }
        if quality_gate_blocked:
            board_status = "blocked-quality-gate"
            board_tickets = []
            board_details = [
                "quality-gate:ticket-sync-blocked",
                "quality-gate:role-contract-incomplete",
            ]
            trigger_state = "blocked"
            board_seeded_count = 0
            primary_issue_sync = {"issues": {}}
        else:
            board_status, board_tickets, board_details, trigger_state, board_seeded_count = (
                _ensure_board_seeding(
                    project_status,
                    repo_root,
                    _resolve_board_for_stage(repo_root, stage),
                    stage,
                    theme_bundle,
                    planning_paths,
                    classification,
                )
            )
            board_seeded += board_seeded_count

            primary_issue_sync = ensure_planning_issue_assets(
                repo_root,
                stage,
                f"{stage}:{theme_code}",
                planning_paths,
                board_ticket_ids,
                stage_primary_assets,
            )
        _wiki_raw = stage_primary_assets.get("wiki")
        wiki_sync = _wiki_raw if isinstance(_wiki_raw, dict) else {}
        board_details.extend(
            [
                f"primary-wiki-status:{wiki_sync.get('status', 'manual-required')}",
                f"primary-wiki-url:{wiki_sync.get('url', '') or 'none'}",
            ]
        )
        _issues_raw = primary_issue_sync.get("issues")
        _issues_dict: dict[str, Any] = _issues_raw if isinstance(_issues_raw, dict) else {}
        for kind, issue_result in sorted(_issues_dict.items()):
            board_details.append(
                f"primary-issue-{kind}:{issue_result.get('status', 'manual-required')}:{issue_result.get('url', '') or 'none'}"
            )
            board_details.append(
                f"primary-project-item-{kind}:{issue_result.get('project_item_status', 'skipped')}"
            )

        dispatch_trace_path = planning_dispatch_path(planning_root, stage, theme_code)
        dispatch_content = _build_dispatch_trace_content(
            stage,
            theme_bundle,
            stage_path,
            planning_paths,
            project_status,
            project_message,
            _resolve_board_for_stage(repo_root, stage),
            board_status,
            board_tickets,
            board_details,
            trigger_state,
        )
        ensure_text(dispatch_trace_path, dispatch_content)

        inventory_upsert(
            planning_root / "INVENTORY.md",
            planning_inventory_template,
            f"{stage}:{theme_code}",
            {
                "status": (
                    f"planning-{stage}-blocked"
                    if quality_gate_blocked
                    else f"planning-{stage}-ready"
                ),
                "paths": [
                    *(path.as_posix() for path in planning_paths.values()),
                    dispatch_trace_path.as_posix(),
                ],
            },
        )
        created += 1

    skipped = max(0, sum(1 for _ in iter_data_bundles(data_root)) - len(selected))

    scoring = _compute_input_helpfulness(selected)
    planning_status = _collect_planning_item_statuses(stage_planning_root)
    scenario = _scenario_from_counts(
        planning_status["epics"],
        planning_status["tasks"],
        planning_status["tasks_done"],
    )

    checklist: list[str] = []
    if scenario in {"cannot-start", "startable"}:
        checklist = [
            "- [x] Stage document exists.",
            "- [x] Stage gate ready_for_planning=true",
            *[
                f"- [{'x' if required_inputs else ' '}] Required inputs documented: {item}"
                for item in required_inputs
            ],
            f"- [{'x' if planning_status['epics'] > 0 else ' '}] At least one epic exists",
            f"- [{'x' if planning_status['tasks'] > 0 else ' '}] At least one task exists",
            f"- [{'x' if actionable_delivery_tasks > 0 else ' '}] At least one actionable delivery task exists",
        ]

    gap_keys: list[str] = []
    dims = scoring["dimensions"]  # type: ignore[index]
    if not required_inputs:
        gap_keys.append("required_inputs")
    if int(dims.get("problem_clarity", 1)) <= 2:
        gap_keys.append("problem_clarity")
    if int(dims.get("scope_clarity", 1)) <= 2:
        gap_keys.append("scope_clarity")
    if int(dims.get("task_formulability", 1)) <= 2:
        gap_keys.append("task_formulability")
    if int(dims.get("constraints_clarity", 1)) <= 2:
        gap_keys.append("constraints_clarity")
    if int(dims.get("owner_clarity", 1)) <= 2:
        gap_keys.append("owner_clarity")

    questions = _improvement_questions_for_gaps(gap_keys, int(scoring["overall"]))
    suggestions = _feature_suggestions(theme_labels_seen)
    report_path = _write_project_assessment_report(
        stage,
        stage_planning_root,
        scenario,
        checklist,
        scoring,
        questions,
        suggestions,
        {
            "gate_reason": gate.get("gate_reason", ""),
            "blocked_bundle_ids": gate.get("blocked_bundle_ids", []),
        },
    )

    if _enforce_implementable_scope_gate(stage) and actionable_delivery_tasks == 0:
        raise ValueError(
            "No actionable delivery task generated for stage planning. "
            "Refine specifications with explicit implementable scope before marking stage ready."
        )

    # Re-sync primary stage assets after planning artifacts exist so wiki pages
    # can embed up-to-date epic/story/task hierarchy and visual references.
    if stage_path.exists():
        ensure_stage_primary_assets(repo_root, stage, stage_path)

    return {
        "created": created,
        "skipped": skipped,
        "board_tickets_seeded": board_seeded,
        "scenario": 1 if scenario == "startable" else (2 if scenario == "completed" else 0),
        "assessment_path": report_path.as_posix(),
    }
