"""Specification -> stage transition implementation."""

from __future__ import annotations

import re
from pathlib import Path

from artifact_runtime import write_latest_snapshot
from artifacts_flow_common import (
    bundle_id,
    ensure_text,
    iter_data_bundles,
    sha256_text,
    stage_readiness,
    timestamp,
)
from artifacts_flow_registry import inventory_upsert
from artifacts_flow_paths import (
    canonical_stage_doc_name,
    specification_path,
    stage_doc_path,
)


def _extract_section(markdown_text: str, heading: str) -> str:
    """Extract a markdown section body without the heading line."""
    def _normalize_heading_name(value: str) -> str:
        stripped = value.strip().lower()
        stripped = re.sub(r"^\d+[a-z]?\.\s*", "", stripped)
        return stripped

    lines = markdown_text.splitlines()
    in_section = False
    collected: list[str] = []
    expected = _normalize_heading_name(heading)
    for line in lines:
        if line.startswith("## "):
            current = _normalize_heading_name(line[3:])
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


def _clean_markdown_lines(section_text: str) -> list[str]:
    """Normalize markdown lines and remove generic placeholder content."""
    blocked_tokens = (
        "define the explicitly included outcomes",
        "define explicit exclusions",
        "criterion 1",
        "criterion 2",
        "criterion 3",
        "todo",
        "holistic synthesis from all relevant expert and reviewer perspectives",
        "contradictions and unknowns are surfaced as explicit blockers",
        "these questions are currently either delayed",
        "ideas linger too long in raw idea status",
          "primary discovery interface",
          "/help output",
          "command overview",
          "context-sensitive guidance",
          "stage transitions are decided intuitively",
          "discovery interface for available commands",
          "provide a complete command overview",
          "provide context-sensitive guidance",
          "available commands",
     )

    def _looks_disallowed_summary(line: str) -> bool:
        lowered = line.lower()
        german_stopwords = re.findall(
            r"\b(die|der|das|damit|keine|nicht|neue|muss|wissen|womit|über|für|mit|ohne|statt|von|bis|kann|jederzeit|und)\b",
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
                "fachurteile",
                "personalaufbau",
                "beauftragung",
                "ideen-eingang",
                "stage-entscheidung",
            )
        ):
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
        if any(
            phrase in lowered
            for phrase in (
                "it defines the exit gates that must be met",
                "there are no external clients",
                "there is deliberately no external sponsor or customer",
                "acts as the client, user, and operator",
                "team is represented digitally",
            )
        ):
            return True
        return False

    cleaned: list[str] = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[\-*]+\s*", "", line).strip()
        line = re.sub(
            r"^(primary finding:|secondary finding:|core problem:|supporting evidence:|address:|focus on:)\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )
        line = line.replace("**", "").replace("`", "").strip()
        lowered = line.lower()
        if any(token in lowered for token in blocked_tokens):
            continue
        if line.startswith("### "):
            continue
        if line.startswith("`STATE_"):
            continue
        if any(
            token in lowered
            for token in (
                "interne entwickler",
                "der primäre zugang",
                "der nutzer gibt",
                "teammitglieder,",
                "stakeholder map",
                "self-managed virtual team",
                "user profile & ux",
                "it is itself a stakeholder",
                "demands consistent artifact storage",
                "improves through each self-application",
            )
        ):
            continue
        if _looks_disallowed_summary(line):
            continue
        if "|" in line and line.count("|") >= 2:
            continue
        if line:
            cleaned.append(line)
    return cleaned


def _extract_scope_subsection(spec_text: str, heading: str) -> list[str]:
    """Extract list-like lines from a scope subsection (e.g., In Scope)."""
    scope_text = _extract_section(spec_text, "Scope")
    if not scope_text:
        return []

    lines = scope_text.splitlines()
    in_target = False
    collected: list[str] = []
    target = heading.strip().lower()
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("### "):
            current = stripped[4:].strip().lower()
            if in_target and current != target:
                break
            in_target = current == target
            continue
        if in_target and stripped:
            collected.append(stripped)
    return _clean_markdown_lines("\n".join(collected))


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Deduplicate a list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _lowercase_first(text: str) -> str:
    """Lowercase the first character without changing the remaining text."""
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped[:1].lower() + stripped[1:]


def _ensure_sentence(text: str) -> str:
    """Ensure a text fragment ends as a sentence."""
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.endswith((".", "!", "?")):
        return stripped
    return f"{stripped}."


def _join_phrases(phrases: list[str]) -> str:
    """Join short phrases into a readable English list."""
    normalized = [item.strip().rstrip(".") for item in phrases if item.strip()]
    if not normalized:
        return ""
    if len(normalized) == 1:
        return normalized[0]
    if len(normalized) == 2:
        return f"{normalized[0]} and {normalized[1]}"
    return f"{', '.join(normalized[:-1])}, and {normalized[-1]}"


def _rewrite_context_line(line: str) -> str:
    """Rewrite raw problem statements into stakeholder-readable context lines."""
    lowered = line.strip().lower()
    if "either delayed" in lowered and "unstructured manner" in lowered:
        return "Important project questions still lack a fast and consistent evaluation path."
    if "ideas linger too long in raw idea status" in lowered:
        return "Promising ideas stay in intake too long instead of moving into scoped project work."
    if lowered.startswith("how can "):
        return _ensure_sentence(
            "Key design question: " + line.strip().rstrip("?")
        )
    return _ensure_sentence(line)


def _stage_purpose_summary(stage_title: str, stage_meta: dict[str, str]) -> str:
    """Build a concise stage-purpose paragraph from instruction metadata."""
    purpose_bullets = _dedupe_preserve_order(_bullet_lines(stage_meta.get("purpose", "")))
    if purpose_bullets:
        headline = _join_phrases(
            [_lowercase_first(item) for item in purpose_bullets[:3]]
        )
        return _ensure_sentence(f"The {stage_title} stage exists to {headline}")

    purpose_lines = _clean_markdown_lines(stage_meta.get("purpose", ""))
    if purpose_lines:
        return _ensure_sentence(purpose_lines[0])

    description = stage_meta.get("description", "").strip()
    if description:
        if description.lower() == stage_title.lower():
            return _ensure_sentence(
                f"The {stage_title} stage aligns validated context into a coherent, delivery-ready project report."
            )
        return _ensure_sentence(
            f"The {stage_title} stage is responsible for {description.rstrip('.')}."
        )

    return _ensure_sentence(
        f"The {stage_title} stage prepares clear, review-backed work for downstream delivery."
    )


def _stage_focus_summary(goals: list[str]) -> str:
    """Build a short paragraph that summarizes the current focus."""
    focus_items = [_lowercase_first(item) for item in goals[:3] if item.strip()]
    if not focus_items:
        return "This cycle focuses on turning validated input into planning-ready work with explicit ownership and boundaries."
    return _ensure_sentence(f"This cycle aims to ensure that {_join_phrases(focus_items)}")


def _frontmatter_value(markdown_text: str, key: str) -> str:
    """Return a simple frontmatter scalar value when present."""
    if not markdown_text.startswith("---\n"):
        return ""
    lines = markdown_text.splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def _review_list_section(review_text: str, heading: str) -> list[str]:
    """Return cleaned bullet lines from a named review section."""
    return _clean_markdown_lines(_extract_section(review_text, heading))


def _review_signal_lines(bundle, review_text: str) -> list[str]:
    """Build bundle-scoped review signal lines for the canonical stage document."""
    recommendation = ""
    scenario = ""
    rationale = ""
    for raw in review_text.splitlines():
        line = raw.strip()
        if line.startswith("- recommendation:"):
            recommendation = line.split(":", 1)[1].strip()
        elif line.startswith("- scenario:"):
            scenario = line.split(":", 1)[1].strip()
        elif line.startswith("- scenario_rationale:"):
            rationale = line.split(":", 1)[1].strip()

    gap_items = _review_list_section(review_text, "Gap Analysis")
    if not gap_items:
        gap_items = _bullet_lines(_extract_section(review_text, "Gap Analysis"))

    lead = f"{bundle_id(bundle)}: recommendation={recommendation or 'unknown'}"
    if scenario:
        lead += f", scenario={scenario}"
    lines = [lead]
    if rationale:
        lines.append(f"{bundle_id(bundle)}: rationale={rationale}")
    if gap_items:
        lines.append(f"{bundle_id(bundle)}: first_gap={gap_items[0]}")
    return lines


def _review_ready(review_text: str) -> tuple[bool, list[str]]:
    """Evaluate whether a cumulated review permits stage creation."""
    issues: list[str] = []
    status = _frontmatter_value(review_text, "status").lower()
    readiness = _frontmatter_value(review_text, "readiness").lower()
    recommendation_match = re.search(
        r"^- recommendation:\s*(.+)$", review_text, flags=re.MULTILINE
    )
    recommendation = (
        recommendation_match.group(1).strip().lower() if recommendation_match else ""
    )

    if status in {"pending", "awaiting-expert-review-feedback", "awaiting-review"}:
        issues.append(f"review status is {status}")
    if readiness in {"pending", "blocked"}:
        issues.append(f"review readiness is {readiness}")
    if recommendation not in {"proceed", "proceed-with-conditions"}:
        issues.append(
            "review recommendation is missing or blocks progress"
            if not recommendation
            else f"review recommendation is {recommendation}"
        )
    return len(issues) == 0, issues


def _load_stage_metadata(repo_root: Path, stage: str) -> dict[str, str]:
    """Load simple metadata from the stage instruction frontmatter."""
    stages_dir = repo_root / ".github" / "instructions" / "stages"
    safe_stage = stage.strip().lower()
    for instruction_path in sorted(stages_dir.glob("*.instructions.md")):
        text = instruction_path.read_text(encoding="utf-8")
        if _frontmatter_value(text, "command").strip().lower() != safe_stage:
            continue
        return {
            "command": safe_stage,
            "stage_id": _frontmatter_value(text, "stage-id"),
            "description": _frontmatter_value(text, "description"),
            "name": _frontmatter_value(text, "name"),
            "purpose": _extract_section(text, "Purpose"),
            "requirements": _extract_section(text, "Requirements"),
            "readiness": _extract_section(text, "Readiness Check (for agents)"),
        }
    return {
        "command": safe_stage,
        "stage_id": "",
        "description": safe_stage.title(),
        "name": safe_stage.title(),
        "purpose": "",
        "requirements": "",
        "readiness": "",
    }


def _stage_title(stage: str) -> str:
    """Return a human-readable stage title."""
    return stage.replace("-", " ").strip().title()


def _collect_spec_content(
    ready_specs: list[dict[str, object]],
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str], list[str], list[str]]:
    """Collect vision, goals, scope, constraints, stakeholders, and open questions from specs."""
    vision_inputs: list[str] = []
    goal_items: list[str] = []
    constraint_items: list[str] = []
    in_scope_items: list[str] = []
    out_scope_items: list[str] = []
    stakeholder_rows: list[str] = []
    open_questions: list[str] = []
    review_signals: list[str] = []

    for item in ready_specs:
        spec_text = str(item["spec_text"])
        problem_section = _extract_section(spec_text, "Synthesized Problem Statement")
        if not problem_section:
            problem_section = _extract_section(spec_text, "Problem")
        vision_inputs.extend(_clean_markdown_lines(problem_section))

        in_scope_items.extend(_extract_scope_subsection(spec_text, "In Scope"))
        out_scope_items.extend(_extract_scope_subsection(spec_text, "Out of Scope"))

        goal_items.extend(
            _bullet_lines(_extract_section(spec_text, "Acceptance Criteria"))
        )
        constraint_items.extend(
            _bullet_lines(_extract_section(spec_text, "Constraints"))
        )
        stakeholders = _extract_section(spec_text, "Stakeholders")
        if stakeholders:
            stakeholder_rows.append(
                f"| Source bundle | {bundle_id(item['bundle'])} | See source specification |"  # type: ignore[arg-type]
            )
        review_text = str(item["review_text"])
        review_signals.extend(_review_signal_lines(item["bundle"], review_text))
        open_questions.extend(
            _bullet_lines(_extract_section(review_text, "Open Questions"))
        )
        open_questions.extend(
            _bullet_lines(_extract_section(review_text, "Gap Analysis"))
        )

    return (
        vision_inputs,
        goal_items,
        constraint_items,
        in_scope_items,
        out_scope_items,
        stakeholder_rows,
        open_questions,
        review_signals,
    )


def _normalize_spec_content(
    vision_inputs: list[str],
    goal_items: list[str],
    constraint_items: list[str],
    in_scope_items: list[str],
    out_scope_items: list[str],
    stage_meta: dict[str, str],
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    """Normalize and deduplicate collected spec content."""
    context_lines = _dedupe_preserve_order(
        [_rewrite_context_line(p.strip()) for p in vision_inputs if p.strip()]
    )
    goals = _dedupe_preserve_order(
        [
            re.sub(r"^\[\s*[x ]\s*\]\s*", "", item).strip()
            for item in goal_items
            if "criterion" not in item.lower() and "todo" not in item.lower()
        ]
    )[:8]
    constraints = _dedupe_preserve_order(
        [item for item in constraint_items if "todo" not in item.lower()]
    )
    if stage_meta.get("requirements"):
        constraints.extend(_bullet_lines(stage_meta["requirements"]))
    constraints = _dedupe_preserve_order(constraints)
    in_scope = _dedupe_preserve_order(in_scope_items)
    out_scope = _dedupe_preserve_order(out_scope_items)
    readiness_items = _dedupe_preserve_order(
        _bullet_lines(stage_meta.get("readiness", ""))
    )

    return context_lines, goals, constraints, in_scope, out_scope, readiness_items


def _build_stage_frontmatter(
    stage: str,
    stage_meta: dict[str, str],
    date_value: str,
    source_bundles: list[str],
    ready_specs: list[dict[str, object]],
    blocked_bundle_ids: list[str],
    stage_status: str,
    ready_for_planning: bool,
    gate_reason: str,
) -> list[str]:
    """Build YAML frontmatter for stage document."""
    digest_source = "\n".join(
        [
            stage,
            date_value,
            *source_bundles,
            *[str(item["spec_path"]) for item in ready_specs],
        ]
    )
    synthesis_digest = sha256_text(digest_source)
    return [
        "---",
        f'stage: "{stage}"',
        f'stage_id: "{stage_meta.get("stage_id", "")}"',
        f'created: "{date_value}"',
        "board_type: github",
        'board_id: ""',
        'board_url: ""',
        'wiki_url: ""',
        'single_point_of_truth_board: "refs/board/*"',
        'single_point_of_truth_wiki: "docs/wiki/"',
        'external_system_provider: "github"',
        f'synthesis_sha256: "{synthesis_digest}"',
        f"status: {stage_status}",
        f"ready_for_planning: {'true' if ready_for_planning else 'false'}",
        f'gate_reason: "{gate_reason}"',
        f"selected_bundle_count: {len(source_bundles)}",
        f"blocked_bundle_count: {len(blocked_bundle_ids)}",
        "blocked_bundle_ids:" if blocked_bundle_ids else "blocked_bundle_ids: []",
        *(
            [f'  - "{item}"' for item in blocked_bundle_ids]
            if blocked_bundle_ids
            else []
        ),
        "history:",
        f'  - date: "{date_value}"',
        '    change: "Synthesized canonical stage document from ready specifications"',
        '    author: "agile-coach"',
        "layer: digital-generic-team",
        "source_bundles:" if source_bundles else "source_bundles: []",
        *([f'  - "{item}"' for item in source_bundles] if source_bundles else []),
        "---",
    ]


def _build_vision_section(
    stage_title: str,
    stage_meta: dict[str, str],
    goals: list[str],
) -> list[str]:
    """Build vision section."""
    vision_content = [
        _stage_purpose_summary(stage_title, stage_meta),
        _stage_focus_summary(goals),
    ]
    return ["## Vision", "", *vision_content, ""]


def _build_context_section(context_lines: list[str]) -> list[str]:
    """Build stakeholder-readable current context section."""
    context_content = (
        [f"- {item}" for item in context_lines[:4]]
        if context_lines
        else [
            "- Current context is being consolidated from the available expert specifications.",
        ]
    )
    return ["## Current Context", "", *context_content, ""]


def _build_goals_section(goals: list[str]) -> list[str]:
    """Build goals section."""
    goals_content = (
        [f"- {item}" for item in goals]
        if goals
        else [
            "- Define measurable delivery outcomes for this stage.",
            "- Translate approved specifications into executable planning artifacts.",
        ]
    )
    return ["## Goals", "", *goals_content, ""]


def _build_constraints_section(constraints: list[str]) -> list[str]:
    """Build constraints section."""
    constraints_content = (
        [f"- {item}" for item in constraints]
        if constraints
        else [
            "- Proceed only with specifications that have a positive cumulated review.",
            "- Keep all downstream artifacts in English.",
        ]
    )
    return ["## Constraints", "", *constraints_content, ""]


def _build_scope_boundaries_section(
    in_scope: list[str], out_scope: list[str]
) -> list[str]:
    """Build explicit scope boundaries section."""
    in_scope_content = (
        [f"- {item}" for item in in_scope]
        if in_scope
        else ["- Convert validated project themes into planning-ready epics and task handoffs."]
    )
    out_scope_content = (
        [f"- {item}" for item in out_scope]
        if out_scope
        else ["- Accept unsupported assumptions as canonical project decisions."]
    )
    return [
        "## Scope Boundaries",
        "",
        "### In Scope",
        "",
        *in_scope_content,
        "",
        "### Out of Scope",
        "",
        *out_scope_content,
        "",
    ]


def _build_stakeholders_section(stakeholder_rows: list[str]) -> list[str]:
    """Build stakeholders section."""
    stakeholders_content = (
        stakeholder_rows
        if stakeholder_rows
        else ["| Delivery owner | Assigned via planning artifacts | refs/board/<stage> and planning tickets |"]
    )
    return [
        "## Stakeholders",
        "",
        "| Role | Name/Team | Contact |",
        "|------|-----------|---------|",
        *stakeholders_content,
        "",
    ]


def _build_readiness_section(readiness_items: list[str]) -> list[str]:
    """Build definition of done section."""
    dod_content = (
        [f"- {item}" for item in readiness_items]
        if readiness_items
        else [
            "- Canonical stage document is current.",
            "- Planning artifacts exist for every ready source specification.",
            "- Dispatch trace is recorded for delivery handoff.",
        ]
    )
    return ["## Definition of Done", "", *dod_content, ""]


def _build_review_signals_section(review_signals: list[str]) -> list[str]:
    """Build a compact review-signals section from cumulated review outputs."""
    signal_lines = (
        [f"- {item}" for item in review_signals]
        if review_signals
        else ["- No review signals were extracted from the current specification set."]
    )
    return ["## Review Signals", "", *signal_lines, ""]


def _build_source_specs_section(ready_specs: list[dict[str, object]]) -> list[str]:
    """Build source specifications section."""
    spec_lines: list[str] = []
    for item in ready_specs:
        bundle = item["bundle"]
        spec_rel = specification_path(
            Path(".digital-artifacts") / "30-specification", bundle
        )
        spec_lines.append(f"- {bundle_id(bundle)} -> {spec_rel.as_posix()}")

    if not spec_lines:
        spec_lines = [
            "- No source specifications are available yet for this stage run.",
            "- Run input/data/specification prompts first to create planning-ready inputs.",
        ]

    return [
        "## Source Specifications",
        "",
        *spec_lines,
        "",
    ]


def _build_open_questions_section(open_questions: list[str]) -> list[str]:
    """Build open questions section."""
    questions_content = (
        [f"- {item}" for item in open_questions]
        if open_questions
        else ["- No blocking open questions remain in the current cumulated reviews."]
    )
    return ["## Open Questions", "", *questions_content, ""]


def _build_history_section(date_value: str) -> list[str]:
    """Build history section."""
    return [
        "## History",
        "",
        "| Date | Change | Author |",
        "|------|--------|--------|",
        f"| {date_value} | Synthesized canonical stage document from ready specifications | agile-coach |",
        "",
    ]


def _build_stage_sections(
    stage_title: str,
    stage_meta: dict[str, str],
    context_lines: list[str],
    goals: list[str],
    constraints: list[str],
    in_scope: list[str],
    out_scope: list[str],
    stakeholder_rows: list[str],
    readiness_items: list[str],
    review_signals: list[str],
    open_questions: list[str],
    ready_specs: list[dict[str, object]],
    date_value: str,
    _blocked_specs: list[dict[str, object]],
) -> list[str]:
    """Build all markdown sections for stage document."""
    return [
        "",
        f"# {stage_title}",
        "",
        *_build_vision_section(stage_title, stage_meta, goals),
        *_build_context_section(context_lines),
        *_build_goals_section(goals),
        *_build_scope_boundaries_section(in_scope, out_scope),
        *_build_constraints_section(constraints),
        *_build_stakeholders_section(stakeholder_rows),
        *_build_readiness_section(readiness_items),
        *_build_review_signals_section(review_signals),
        *_build_source_specs_section(ready_specs),
        *_build_open_questions_section(open_questions),
        *_build_history_section(date_value),
    ]


def _stage_document_content(
    stage: str,
    stage_meta: dict[str, str],
    stage_specs: list[dict[str, object]],
    blocked_specs: list[dict[str, object]],
) -> str:
    """Build the canonical stage document from all ready specifications."""
    stage_title = _stage_title(stage)
    date_value = timestamp()
    source_bundles = [bundle_id(item["bundle"]) for item in stage_specs]  # type: ignore[arg-type]
    blocked_bundle_ids = [
        str(item.get("bundle_id", "")).strip()
        for item in blocked_specs
        if str(item.get("bundle_id", "")).strip()
    ]
    has_ready_specs = bool(stage_specs)
    ready_for_planning = has_ready_specs or not blocked_specs
    stage_status = "active" if ready_for_planning else "in-progress"
    if not has_ready_specs and not blocked_specs:
        gate_reason = "stage has no specification bundles to plan"
    elif ready_for_planning and blocked_bundle_ids:
        gate_reason = "stage is ready for planning with quarantined blocked bundles"
    elif ready_for_planning:
        gate_reason = "stage is ready for planning"
    else:
        gate_reason = "stage blocked: missing readiness evidence from expert cumulated reviews"

    (
        vision_inputs,
        goal_items,
        constraint_items,
        in_scope_items,
        out_scope_items,
        stakeholder_rows,
        open_questions,
        review_signals,
    ) = _collect_spec_content(stage_specs)
    context_lines, goals, constraints, in_scope, out_scope, readiness_items = _normalize_spec_content(
        vision_inputs,
        goal_items,
        constraint_items,
        in_scope_items,
        out_scope_items,
        stage_meta,
    )
    open_questions = _dedupe_preserve_order(open_questions)

    frontmatter = _build_stage_frontmatter(
        stage,
        stage_meta,
        date_value,
        source_bundles,
        stage_specs,
        blocked_bundle_ids,
        stage_status,
        ready_for_planning,
        gate_reason,
    )
    sections = _build_stage_sections(
        stage_title,
        stage_meta,
        context_lines,
        goals,
        constraints,
        in_scope,
        out_scope,
        stakeholder_rows,
        readiness_items,
        review_signals,
        open_questions,
        stage_specs,
        date_value,
        blocked_specs,
    )

    readiness_summary = [
        "## Specification Readiness Summary",
        "",
        f"- ready_specifications: {len(stage_specs)}",
        f"- blocked_specifications: {len(blocked_specs)}",
        f"- selected_bundle_count: {len(source_bundles)}",
        f"- blocked_bundle_count: {len(blocked_bundle_ids)}",
        f"- stage_status: {stage_status}",
        f"- ready_for_planning: {'true' if ready_for_planning else 'false'}",
        f"- gate_reason: {gate_reason}",
        "",
    ]
    if blocked_specs:
        readiness_summary.extend(
            [
                "### Blocking Gaps",
                "",
                f"- blocked_bundle_ids: {', '.join(blocked_bundle_ids)}",
                "",
                *[
                    f"- {item['bundle_id']}: {'; '.join(item['issues']) if item['issues'] else 'unspecified'}"  # type: ignore[index]
                    for item in blocked_specs
                ],
                "",
            ]
        )

    return "\n".join([*frontmatter, *sections, *readiness_summary])


def _stage_readiness_report(
    stage: str,
    ready_specs: list[dict[str, object]],
    blocked_specs: list[dict[str, object]],
) -> str:
    """Build a stage readiness report when the stage cannot proceed."""
    blocked_bundle_ids = [
        str(item.get("bundle_id", "")).strip()
        for item in blocked_specs
        if str(item.get("bundle_id", "")).strip()
    ]
    return "\n".join(
        [
            f"# Stage Readiness Report: {_stage_title(stage)}",
            "",
            f"- generated_at: {timestamp()}",
            f"- ready_specifications: {len(ready_specs)}",
            f"- blocked_specifications: {len(blocked_specs)}",
            f"- selected_bundle_count: {len(ready_specs)}",
            f"- blocked_bundle_count: {len(blocked_specs)}",
            (
                f"- blocked_bundle_ids: {', '.join(blocked_bundle_ids)}"
                if blocked_bundle_ids
                else "- blocked_bundle_ids: none"
            ),
            "- decision: stop-and-clarify",
            "- next_action: resolve blocked bundles and rerun /project",
            "",
            "## Blockers",
            "",
            *(
                [
                    f"- {item['bundle_id']}: {'; '.join(item['issues'])}"  # type: ignore[arg-type]
                    for item in blocked_specs
                ]
                if blocked_specs
                else ["- No blocked specifications were evaluated."]
            ),
            "",
            "## Ready Specifications",
            "",
            *(
                [f"- {bundle_id(item['bundle'])}" for item in ready_specs]  # type: ignore[arg-type]
                if ready_specs
                else ["- None"]
            ),
            "",
        ]
    )


def _evaluate_bundle_readiness(
    bundle, spec_root: Path
) -> tuple[bool, str, str, list[str]]:
    """Evaluate bundle readiness and return (is_ready, spec_text, review_text, issues)."""
    spec_path = specification_path(spec_root, bundle)
    if not spec_path.exists():
        return False, "", "", []

    spec_text = spec_path.read_text(encoding="utf-8")
    is_ready, missing = stage_readiness(spec_text)
    language_gate_status = ""
    in_language_gate = False
    for line in spec_text.splitlines():
        if line.startswith("## "):
            in_language_gate = line[3:].strip().lower() == "language gate"
            continue
        if not in_language_gate:
            continue
        status_match = re.match(r"^- status:\s*(.+)$", line.strip(), flags=re.IGNORECASE)
        if status_match:
            language_gate_status = status_match.group(1).strip().lower()
            break
    if language_gate_status == "failed":
        missing.append("language gate failed for canonical specification content")

    review_path = (
        spec_root.parent
        / "60-review"
        / bundle.date_key
        / "agile-coach"
        / f"{bundle.item_code}.REVIEW.md"
    )
    legacy_review_path = (
        spec_root.parent / "60-review" / bundle.date_key / bundle.item_code / "REVIEW.md"
    )
    review_text = ""
    effective_review_path = review_path if review_path.exists() else legacy_review_path
    if effective_review_path.exists():
        review_text = effective_review_path.read_text(encoding="utf-8")
        rec_match = re.search(
            r"^- recommendation:\s*(.+)$", review_text, flags=re.MULTILINE
        )
        recommendation = rec_match.group(1).strip().lower() if rec_match else ""
        if recommendation not in {"proceed", "proceed-with-conditions"}:
            missing.append(
                "cumulated review recommendation blocks progress"
                if recommendation
                else "cumulated review recommendation is missing"
            )
        conf_match = re.search(
            r"^- confidence_score:\s*(\d+)", review_text, flags=re.MULTILINE
        )
        confidence = int(conf_match.group(1)) if conf_match else 0
        if confidence < 3:
            missing.append("cumulated review confidence score is below 3")
    else:
        missing.append("cumulated review file is missing")

    return len(missing) == 0 and is_ready, spec_text, review_text, missing


def _finalize_stage_result(
    stage_root: Path,
    stage_inventory_template: Path,
    stage: str,
    stage_meta: dict[str, str],
    stage_specs: list,
    blocked_specs: list,
) -> dict[str, int]:
    """Finalize canonical stage document and return result counts."""

    stage_path = stage_doc_path(stage_root, stage)
    legacy_readiness_path = stage_root / f"READINESS_{canonical_stage_doc_name(stage)}"
    if legacy_readiness_path.exists():
        legacy_readiness_path.unlink()

    ensure_text(
        stage_path,
        _stage_document_content(stage, stage_meta, stage_specs, blocked_specs),
    )

    inventory_upsert(
        stage_root / "INVENTORY.md",
        stage_inventory_template,
        stage.strip().lower(),
        {"status": f"stage-{stage}-ready", "paths": [stage_path.as_posix()]},
    )
    write_latest_snapshot(stage_root / "LATEST.md", stage_path)

    return {"ready": len(stage_specs), "skipped": len(blocked_specs)}


def run_specification_to_stage_impl(repo_root: Path, stage: str) -> dict[str, int]:
    """Create or refresh the canonical stage document when readiness is sufficient."""
    artifacts_root = repo_root / ".digital-artifacts"
    data_root = artifacts_root / "10-data"
    spec_root = artifacts_root / "30-specification"
    stage_root = artifacts_root / "40-stage"
    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    stage_inventory_template = template_root / "40-stage" / "INVENTORY.template.md"

    stage_specs: list[dict[str, object]] = []
    blocked_specs: list[dict[str, object]] = []
    stage_meta = _load_stage_metadata(repo_root, stage)

    for bundle in iter_data_bundles(data_root):
        is_ready, spec_text, review_text, issues = _evaluate_bundle_readiness(
            bundle, spec_root
        )

        if not is_ready:
            blocked_specs.append({"bundle_id": bundle_id(bundle), "issues": issues})
            continue

        stage_specs.append(
            {
                "bundle": bundle,
                "spec_path": specification_path(spec_root, bundle),
                "spec_text": spec_text,
                "review_text": review_text,
            }
        )

    return _finalize_stage_result(
        stage_root,
        stage_inventory_template,
        stage,
        stage_meta,
        stage_specs,
        blocked_specs,
    )
