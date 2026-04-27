"""Data -> specification transition implementation."""

from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from artifacts_flow_common import bundle_id, ensure_text, iter_data_bundles, sha256_text
from artifacts_flow_registry import inventory_upsert
from artifacts_flow_paths import specification_path

try:
    import yaml as _yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    _yaml = None


def _active_stage() -> str:
    return (
        (
            os.getenv("DIGITAL_STAGE_CONTEXT", "").strip().lower()
            or os.getenv("STAGE", "").strip().lower()
            or "project"
        )
        .replace(" ", "-")
    )


def _review_dir(spec_root: Path, bundle) -> Path:
    """Return canonical review directory for one bundle under 60-review."""
    artifacts_root = spec_root.parent
    return artifacts_root / "60-review" / bundle.date_key / "agile-coach"


def _agent_review_dir(spec_root: Path, bundle, agent: str) -> Path:
    """Return review directory for one agent under a bundle date."""
    artifacts_root = spec_root.parent
    return artifacts_root / "60-review" / bundle.date_key / agent


def _agent_spec_path(spec_root: Path, bundle, agent: str) -> Path:
    """Return agent-focused specification path (<date>/<agent>/<bundle>.<agent>.specification.md)."""
    return (
        spec_root
        / bundle.date_key
        / agent
        / f"{bundle.item_code}.{agent}.specification.md"
    )


def _runtime_expert_handoff_dir(repo_root: Path, bundle, agent: str) -> Path:
    """Return runtime handoff directory for expert request/response artifacts."""
    handoff_dir = (
        repo_root
        / ".digital-runtime"
        / "handoffs"
        / "specification"
        / bundle.date_key
        / bundle.item_code
        / agent
    )
    handoff_dir.mkdir(parents=True, exist_ok=True)
    return handoff_dir


def _cleanup_legacy_layout(spec_root: Path, bundle) -> None:
    """Remove legacy document-top-level folders superseded by agent-focused layout."""
    legacy_spec_dir = spec_root / bundle.date_key / bundle.item_code
    legacy_review_dir = spec_root.parent / "60-review" / bundle.date_key / bundle.item_code
    for legacy_dir in (legacy_spec_dir, legacy_review_dir):
        if legacy_dir.exists() and legacy_dir.is_dir():
            shutil.rmtree(legacy_dir)


def _bundle_relative_paths(bundle) -> tuple[str, str]:
    """Return repository-relative markdown and metadata references for a bundle."""
    markdown_ref = (
        Path(".digital-artifacts")
        / "10-data"
        / bundle.date_key
        / bundle.item_code
        / bundle.markdown_path.name
    )
    metadata_ref = (
        Path(".digital-artifacts")
        / "10-data"
        / bundle.date_key
        / bundle.item_code
        / bundle.metadata_path.name
    )
    return markdown_ref.as_posix(), metadata_ref.as_posix()


def _read_bundle_metadata(bundle) -> dict[str, object]:
    """Read bundle metadata YAML with a deterministic text fallback."""
    raw = bundle.metadata_path.read_text(encoding="utf-8")
    if _yaml is not None:
        loaded = _yaml.safe_load(raw)
        if isinstance(loaded, dict):
            return loaded

    parsed: dict[str, object] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith("  - ") and current_key:
            parsed.setdefault(current_key, [])
            values = parsed[current_key]
            if isinstance(values, list):
                values.append(line[4:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        normalized_value = value.strip().strip('"')
        parsed[current_key] = normalized_value if normalized_value else []
    return parsed


def _language_gate_lines(bundle) -> list[str]:
    """Build spec-visible language gate status lines from bundle metadata."""
    metadata = _read_bundle_metadata(bundle)
    status = str(metadata.get("language_gate_status", "")).strip() or "unknown"
    note = str(metadata.get("language_gate_note", "")).strip()
    lines = [f"- status: {status}"]
    if note:
        lines.append(f"- note: {note}")
    if status == "failed":
        lines.append(
            "- action: Repair or regenerate canonical English bundle content before relying on this specification for planning promotion."
        )
    return lines


def _source_note_lines(source_text: str, limit: int = 10) -> list[str]:
    """Convert source markdown into concise bullet lines for specification context."""
    blocked_exact = {
        "source",
        "extraction",
        "content",
        "file facts",
        "extracted text",
        "header",
        "scope",
        "source notes",
        "problem statement",
        "user profile & ux",
    }

    blocked_prefixes = (
        "data bundle",
        "source",
        "source_done_file:",
        "source_input_file:",
        "source_fingerprint_sha256:",
        "bundle_id:",
        "created_at:",
        "processed_at:",
        "source_path:",
        "content_hash:",
        "original_filename:",
        "normalized_filename:",
        "classification:",
        "file_format:",
        "extraction_engine:",
        "extraction_status:",
        "file_name:",
        "extension:",
        "size_bytes:",
        "modified_at_epoch:",
        "title:",
        "type:",
    )

    def _normalize_localized_source_line(line: str) -> str:
        lowered = line.lower()
        replacements = (
            (
                "die `/help`-ausgabe",
                "The /help output is the primary discovery interface for available commands.",
            ),
            (
                "die /help-ausgabe",
                "The /help output is the primary discovery interface for available commands.",
            ),
            (
                "vollständige command-übersicht",
                "Provide a complete command overview with one-line explanations for all available prompts.",
            ),
            (
                "kontext-sensitiver einstieg",
                "Provide context-sensitive guidance based on the current stage status.",
            ),
            (
                "keine überladung",
                "Group commands by workflow phase so the help output stays clear and non-overwhelming.",
            ),
            (
                "sofort nutzbar",
                "Make the help flow immediately usable without prior knowledge of the layer model.",
            ),
            (
                "/help listet commands",
                "The current help flow lists commands but does not recommend the next sensible step from the current project state.",
            ),
            (
                "neue nutzer wissen nicht",
                "New users do not know which command to start with for the current project state.",
            ),
            (
                "es gibt kein onboarding-pfad",
                "There is no onboarding path for first-time users.",
            ),
        )
        for needle, replacement in replacements:
            if needle in lowered:
                return replacement
        return line

    def _looks_disallowed_source_line(line: str) -> bool:
        lowered = line.lower()
        german_markers = (
            "verfügbare",
            "vollständige",
            "überladung",
            "womit",
            "sinnvollen",
            "vor-wissen",
            "primäre",
            "nutzer",
            "entwickler",
            "damit",
            "kontext-sensitiver",
            "einstieg",
            "idealerweise",
            "aktuellen",
            "verbesserungsbedarf",
            "übersicht",
            "ausgabe",
        )
        german_stopwords = re.findall(
            r"\b(die|der|das|damit|keine|nicht|neue|muss|wissen|womit|über|für|mit)\b",
            lowered,
        )
        if any(marker in lowered for marker in german_markers):
            return True
        if len(german_stopwords) >= 2:
            return True
        if any(char in line for char in "äöüß"):
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

    lines: list[str] = []
    for raw in source_text.splitlines():
        line = raw.strip().lstrip("-*#> ").strip()
        if not line:
            continue
        line = _normalize_localized_source_line(line)
        lowered = line.lower()
        if lowered in blocked_exact:
            continue
        if lowered.startswith(("todo", "placeholder")):
            continue
        if lowered.startswith(blocked_prefixes):
            continue
        if re.match(r"^\d+\.\s+", line):
            continue
        if re.match(r"^[a-z0-9_\-]+:\s*", lowered):
            continue
        if len(line.split()) == 1 and len(line) < 16:
            continue
        if "inventory.md" in lowered:
            continue
        if lowered.startswith("stakeholder map"):
            continue
        if "|" in line and line.count("|") >= 2:
            continue
        if any(
            token in lowered
            for token in (
                "interne entwickler",
                "der primäre zugang",
                "der nutzer gibt",
                "abgeschlossen",
            )
        ):
            continue
        if _looks_disallowed_source_line(line):
            continue
        line = line.replace("**", "").replace("`", "").strip()
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _unique_preserve_order(values: list[str]) -> list[str]:
    """Deduplicate text items while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _bundle_synthesis_lines(source_text: str) -> tuple[list[str], list[str]]:
    """Build bundle-specific problem and scope lines from source evidence."""
    notes = _unique_preserve_order(_source_note_lines(source_text, limit=40))
    if not notes:
        return (
            [
                "Holistic synthesis from all relevant expert and reviewer perspectives.",
                "Contradictions and unknowns are surfaced as explicit blockers.",
            ],
            ["- Define thematic outcomes across the full context of all source notes."],
        )

    sentence_like = [
        line
        for line in notes
        if len(line.split()) >= 8
        and not line.endswith(":")
        and not line.rstrip().endswith("?")
        and not line.lower().startswith(("is this", "does it", "what is"))
    ]

    def _priority(line: str) -> int:
        lower = line.lower()
        score = 0
        if "how can" in lower:
            score += 8
        if "core problem" in lower:
            score += 6
        if "replace missing expertise" in lower or "virtual" in lower:
            score += 5
        if "stage" in lower and "decision" in lower:
            score += 4
        if "problem" in lower:
            score += 2
        return score

    ranked = sorted(sentence_like, key=_priority, reverse=True)
    sentence_like = [line for line in ranked if _priority(line) > 0] + [
        line for line in ranked if _priority(line) == 0
    ]
    focus_pool = sentence_like or notes

    def _compact(line: str, max_len: int = 180) -> str:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[: max_len - 1].rstrip() + "…"

    problem_lines = [f"Core problem: {_compact(focus_pool[0])}"]
    if len(focus_pool) > 1:
        problem_lines.append(f"Supporting evidence: {_compact(focus_pool[1])}")

    scope_items = [f"- Focus on: {_compact(line, max_len=220)}" for line in focus_pool[:3]]
    return problem_lines, scope_items


def _parse_role_agents(role_file: Path) -> list[str]:
    """Extract frontmatter agents list from a role file."""
    if not role_file.exists():
        return []
    text = role_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    in_agents = False
    agents: list[str] = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("agents:"):
            in_agents = True
            continue
        if in_agents and stripped.startswith("-"):
            agents.append(stripped[1:].strip())
            continue
        if in_agents and stripped and not stripped.startswith("-"):
            in_agents = False
    return agents


def _review_agents(repo_root: Path) -> list[str]:
    """Return agents that are in both generic-expert and generic-review roles."""
    expert_agents = _parse_role_agents(
        repo_root / ".github" / "agents" / "roles" / "generic-expert.agent.md"
    )
    review_agents = set(
        _parse_role_agents(
            repo_root / ".github" / "agents" / "roles" / "generic-review.agent.md"
        )
    )
    merged = [agent for agent in expert_agents if agent in review_agents]
    if not merged:
        merged = expert_agents
    seen: set[str] = set()
    result: list[str] = []
    for name in merged:
        normalized = name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _agent_keyword_map() -> dict[str, tuple[str, ...]]:
    return {
        "platform-architect": (
            "architecture",
            "platform",
            "system",
            "service",
            "integration",
            "design",
        ),
        "security-expert": ("security", "auth", "token", "risk", "privacy"),
        "quality-expert": ("quality", "test", "coverage", "validation", "criteria"),
        "container-expert": ("container", "docker", "kubernetes", "deployment"),
        "kubernetes-expert": ("kubernetes", "cluster", "namespace", "helm", "k3s"),
        "ai-expert": ("ai", "llm", "model", "inference", "prompt"),
        "mcp-expert": ("mcp", "tool", "server", "integration"),
        "quantum-expert": ("quantum", "qubit", "qsharp"),
        "ux-designer": ("ux", "user", "form", "screen", "flow", "accessibility"),
    }


def _agent_focus(agent: str) -> str:
    focus_map = {
        "platform-architect": "Platform strategy, interfaces, and cross-system consistency",
        "security-expert": "Threat model, controls, and residual risk",
        "quality-expert": "Testability, quality gates, and acceptance measurability",
        "container-expert": "Containerization and runtime portability",
        "kubernetes-expert": "Cluster operability and workload topology",
        "ai-expert": "Model/data assumptions and AI integration viability",
        "mcp-expert": "Tooling interface contracts and MCP compatibility",
        "quantum-expert": "Quantum relevance and feasibility assessment",
        "ux-designer": "User flow clarity, accessibility, and interaction quality",
    }
    return focus_map.get(agent, "Expert analysis and recommendation")


def _agent_assignee_hint(agent: str) -> str:
    if agent == "ux-designer":
        return "ux-designer"
    if agent in {"quality-expert", "security-expert"}:
        return agent
    return "agile-coach"


def _score_agent_review(agent: str, source_text: str) -> tuple[int, str, str]:
    """Return (score, recommendation, applicability)."""
    lower = source_text.lower()
    keywords = _agent_keyword_map().get(agent, ())
    hits = sum(1 for key in keywords if key in lower)

    if hits == 0:
        return 3, "proceed-with-conditions", "not-relevant"

    if hits >= 3:
        return 4, "proceed", "relevant"
    if hits >= 1:
        return 3, "proceed-with-conditions", "relevant"
    return 2, "stop-and-clarify", "relevant"


def _select_relevant_review_agents(
    repo_root: Path,
    source_text: str,
) -> tuple[list[str], list[str]]:
    """Return selected and skipped expert agents for one source block."""
    candidates = _review_agents(repo_root)
    if not candidates:
        candidates = [
            "platform-architect",
            "quality-expert",
            "security-expert",
            "ux-designer",
            "quantum-expert",
        ]
    selected: list[str] = []
    skipped: list[str] = []

    for agent in candidates:
        _, _, applicability = _score_agent_review(agent, source_text)
        if applicability == "relevant":
            selected.append(agent)
        else:
            skipped.append(agent)

    if not selected and candidates:
        if "quality-expert" in candidates:
            selected = ["quality-expert"]
            skipped = [agent for agent in candidates if agent != "quality-expert"]
        else:
            selected = [candidates[0]]
            skipped = [agent for agent in candidates if agent != candidates[0]]

    return selected, skipped


def _confidence_label(score: int) -> str:
    if score >= 4:
        return "high"
    if score == 3:
        return "medium"
    return "low"


def _review_scenario(score: int, recommendation: str, applicability: str) -> tuple[str, str]:
    """Return scenario classification and rationale for review artifacts."""
    if recommendation == "stop-and-clarify" or score <= 2:
        return (
            "cannot-start",
            "Insufficient evidence for reliable story/task execution; clarification is required.",
        )
    if score >= 5 and recommendation == "proceed" and applicability == "relevant":
        return (
            "completed",
            "Expert perspective indicates no remaining blockers in this domain slice.",
        )
    return (
        "startable",
        "Evidence is actionable and can be translated into delivery-ready stories/tasks.",
    )


def _agent_mapping_contract(agent: str, score: int, applicability: str) -> dict[str, object]:
    """Return expert-to-coach mapping contract for story/task formulability."""
    role = agent.strip().lower()
    if applicability == "not-relevant":
        return {
            "can_story": "no",
            "can_task": "no",
            "required_fields": [
                "Domain trigger keywords for this expert role",
                "Concrete scope signal tied to stage goals",
            ],
            "missing_information": [
                f"No strong {role} signal found in normalized source bundle.",
                "Cross-role dependency evidence is missing for this domain.",
            ],
            "questions": [
                f"Which explicit requirement should be owned by {role} in this stage?",
                "Should this review role be skipped for this bundle in future runs?",
            ],
        }

    base_required = [
        "Concrete problem statement with measurable impact",
        "In-scope and out-of-scope boundaries",
        "At least one testable acceptance criterion",
    ]
    role_required = {
        "ux-designer": ["User segment/persona", "Accessibility acceptance criterion (WCAG 2.2 AA)"],
        "security-expert": ["Threat/risk statement", "Security control expectation"],
        "quality-expert": ["Verification evidence plan", "Quality gate condition"],
        "platform-architect": ["Architectural boundary", "Integration dependency"],
    }
    required_fields = [*base_required, *role_required.get(role, ["Role-specific constraint"])]

    can_task = "yes" if score >= 3 else "no"
    return {
        "can_story": "yes",
        "can_task": can_task,
        "required_fields": required_fields,
        "missing_information": (
            [
                "Task-level implementation detail is too thin for reliable execution.",
                "Owner handoff criteria require sharper boundaries.",
            ]
            if can_task == "no"
            else ["No blocking information gaps from this expert perspective."]
        ),
        "questions": [
            "Which acceptance criterion should become the first executable task?",
            "Who is the final owner for unresolved domain-specific blockers?",
        ],
    }


def _agent_review_markdown(
    template_text: str,
    *,
    stage: str,
    agent: str,
    bundle,
    score: int,
    recommendation: str,
    applicability: str,
    request_path: Path,
    response_path: Path,
    agent_spec_path: Path,
) -> str:
    confidence = _confidence_label(score)
    coverage_problem = "[x]" if score >= 3 else "[ ]"
    coverage_constraints = "[x]" if score >= 3 else "[ ]"
    coverage_stakeholders = "[x]" if score >= 2 else "[ ]"
    coverage_success = "[x]" if score >= 3 else "[ ]"

    dimension_rows = "\n".join(
        [
            f"| Problem clarity | {score} | Source bundle {bundle_id(bundle)} analyzed by {agent} |",
            f"| Scope clarity | {score} | Scope interpretation based on extracted evidence |",
            f"| Constraint clarity | {max(1, score - 1)} | Constraints need iterative hardening where evidence is thin |",
            f"| Stakeholder clarity | {max(2, score)} | Stakeholder assumptions documented for agile-coach consolidation |",
            f"| Delivery readiness | {score} | Recommendation is {recommendation} |",
            f"| Risk clarity | {max(1, score - 1)} | Risk posture requires agile-coach synthesis |",
        ]
    )

    request_rel = request_path.as_posix()
    response_rel = response_path.as_posix()
    spec_rel = agent_spec_path.as_posix()
    scenario, scenario_rationale = _review_scenario(score, recommendation, applicability)
    mapping = _agent_mapping_contract(agent, score, applicability)

    scenario_output = {
        "cannot-start": [
            "- Checklist and score-improvement questions are mandatory before planning transition.",
            "- Provide explicit blocker ownership for each unresolved item.",
        ],
        "startable": [
            "- Checklist, scoring summary, and feature suggestions should be handed to agile-coach.",
            "- At least one executable task candidate should be proposed.",
        ],
        "completed": [
            "- Focus on optimization questions and next-step feature opportunities.",
            "- Preserve evidence for retrospective and quality traceability.",
        ],
    }

    rendered = template_text
    rendered = rendered.replace("{{stage}}", stage)
    rendered = rendered.replace("{{agent_role}}", agent)
    rendered = rendered.replace("{{date}}", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    rendered = rendered.replace("bundle_ids: []", f'bundle_ids:\n  - "{bundle_id(bundle)}"')
    rendered = rendered.replace("status: pending", "status: completed")
    rendered = rendered.replace(
        '- recommendation: proceed / proceed-with-conditions / stop-and-clarify',
        f"- recommendation: {recommendation}",
    )
    rendered = rendered.replace("- confidence_score: 1-5", f"- confidence_score: {score}")
    rendered = rendered.replace(
        '- one_line_rationale: ""',
        f'- one_line_rationale: "{agent} assessed applicability as {applicability} with confidence {confidence}."',
    )
    rendered = rendered.replace(
        "| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |",
        dimension_rows,
    )
    rendered = rendered.replace("| Problem statement | [ ] | |", f"| Problem statement | {coverage_problem} | |")
    rendered = rendered.replace("| Stakeholders | [ ] | |", f"| Stakeholders | {coverage_stakeholders} | |")
    rendered = rendered.replace("| Constraints | [ ] | |", f"| Constraints | {coverage_constraints} | |")
    rendered = rendered.replace("| Success criteria | [ ] | |", f"| Success criteria | {coverage_success} | |")
    rendered = rendered.replace("- Spec file: (path or \"none\")", f"- Spec file: {spec_rel}")
    rendered = rendered.replace(
        "- Coverage assessment: incomplete / partial / sufficient",
        "- Coverage assessment: sufficient" if score >= 4 else "- Coverage assessment: partial",
    )
    rendered += "\n\n## Handoff Trace\n"
    rendered += f"- expert_request: {request_rel}\n"
    rendered += f"- expert_response: {response_rel}\n"
    rendered += f"- applicability: {applicability}\n"
    rendered += "\n## Scenario Classification\n"
    rendered += f"- scenario: {scenario}\n"
    rendered += f"- scenario_rationale: {scenario_rationale}\n"
    rendered += "\n## Story/Task Mapping (Expert -> Agile Coach)\n"
    rendered += f"- can_formulate_story: {mapping['can_story']}\n"
    rendered += f"- can_formulate_task: {mapping['can_task']}\n"
    rendered += "- required_fields:\n"
    rendered += "\n".join(f"  - {item}" for item in mapping["required_fields"]) + "\n"
    rendered += "- coach_feedback_missing_information:\n"
    rendered += "\n".join(f"  - {item}" for item in mapping["missing_information"]) + "\n"
    rendered += "- coach_feedback_questions:\n"
    rendered += "\n".join(f"  - {item}" for item in mapping["questions"]) + "\n"
    rendered += "\n## Dynamic Output (Scenario-specific)\n"
    rendered += f"### {scenario}\n\n"
    rendered += "\n".join(scenario_output[scenario]) + "\n"
    if applicability == "not-relevant":
        rendered += "- not_relevant_reason: UX focus not required by current source evidence.\n"
    return rendered


def _expert_request_yaml(
    *,
    request_id: str,
    to_role: str,
    stage: str,
    bundle,
    source_markdown: str,
    stage_instruction: str,
    source_artifacts: list[str] | None = None,
) -> str:
    notes = _source_note_lines(source_markdown, limit=5)
    context_lines = [
        f"stage={stage}",
        f"bundle={bundle_id(bundle)}",
        "goal=produce expert+review assessment with scoring and recommendation",
    ]
    assumptions = [
        "Source bundle is normalized to English and can be evaluated holistically.",
        "Review should include explicit recommendation and confidence.",
    ]
    questions = [
        "Which stage criteria are currently satisfied from your domain perspective?",
        "Which blockers or risks prevent progression?",
    ]

    artifact_lines = (
        source_artifacts
        if source_artifacts
        else [
            (
                Path(".digital-artifacts")
                / "10-data"
                / bundle.date_key
                / bundle.item_code
                / bundle.markdown_path.name
            ).as_posix()
        ]
    )

    return "\n".join(
        [
            "schema: expert_request_v1",
            f'request_id: "{request_id}"',
            'from_role: "agile-coach"',
            f'to_role: "{to_role}"',
            f'goal: "Assess {bundle_id(bundle)} for stage {stage} and provide recommendation with confidence score."',
            "current_state:",
            f'  stage: "{stage}"',
            f'  bundle: "{bundle_id(bundle)}"',
            "  artifacts:",
            *[f'    - "{path}"' for path in artifact_lines],
            "context:",
            *[f'  - "{entry}"' for entry in context_lines],
            "assumptions:",
            *[f'  - "{entry}"' for entry in assumptions],
            "open_questions:",
            *[f'  - "{entry}"' for entry in questions],
            "artifacts:",
            f'  - "stage_instruction: {stage_instruction}"',
            *[f'  - "source_note: {line}"' for line in notes],
        ]
    )


def _expert_response_yaml(
    *,
    request_id: str,
    from_role: str,
    stage: str,
    bundle,
    score: int,
    recommendation: str,
    review_path: Path,
    spec_path: Path,
) -> str:
    confidence = _confidence_label(score)
    summary = (
        f"{from_role} assessed bundle {bundle_id(bundle)} for stage {stage} with score {score}/5."
    )
    recs = [
        f"Maintain recommendation '{recommendation}' until blocker status changes.",
        "Use this review during agile-coach cumulative readiness synthesis.",
    ]
    assumptions = [
        "Assessment is based on currently available source evidence.",
        "Cross-team dependencies may adjust final planning structure.",
    ]
    questions = [
        "Are there unresolved cross-bundle dependencies affecting this recommendation?",
        "Should additional stakeholder clarification be requested before planning?",
    ]

    return "\n".join(
        [
            "schema: expert_response_v1",
            f'request_id: "{request_id}"',
            f'from_role: "{from_role}"',
            'to_role: "agile-coach"',
            f'summary: "{summary}"',
            f"confidence: {confidence}",
            "recommendations:",
            *[f'  - "{entry}"' for entry in recs],
            "assumptions:",
            *[f'  - "{entry}"' for entry in assumptions],
            "open_questions:",
            *[f'  - "{entry}"' for entry in questions],
            "artifacts:",
            f'  - "review: {review_path.as_posix()}"',
            f'  - "spec: {spec_path.as_posix()}"',
            f'  - "score: {score}"',
            f'  - "recommendation: {recommendation}"',
        ]
    )


def _agent_spec_markdown(
    *,
    stage: str,
    agent: str,
    bundle,
    source_text: str,
    score: int,
    recommendation: str,
    response_path: Path,
) -> str:
    source_digest = sha256_text(source_text.strip() or "")
    notes = _source_note_lines(source_text, limit=8)
    focus = _agent_focus(agent)
    return "\n".join(
        [
            f"# Expert Specification {bundle.item_code} — {agent}",
            "",
            "## Header",
            f"- stage: {stage}",
            f"- bundle: {bundle_id(bundle)}",
            f"- expert_agent: {agent}",
            f"- source_sha256: {source_digest}",
            f"- focus_area: {focus}",
            "",
            "## Expert Recommendation",
            f"- recommendation: {recommendation}",
            f"- confidence_score: {score}",
            f"- assignee_hint: {_agent_assignee_hint(agent)}",
            "",
            "## Domain Assessment",
            f"- {focus}",
            "- Identify constraints, dependencies, and implementation caveats from full-context reading.",
            "",
            "## Cross-References",
            "- Add references to related bundle topics that may block or enable progress.",
            "",
            "## Source Notes",
            *([f"- {line}" for line in notes] if notes else ["- No extracted content available."]),
            "",
            "## Handoff Trace",
            f"- expert_response: {response_path.as_posix()}",
            "",
        ]
    )


def _cumulated_review_markdown(
    template_text: str,
    *,
    stage: str,
    agent_rows: list[dict[str, object]],
    skipped_agents: list[str] | None = None,
) -> str:
    if not agent_rows:
        avg = 1
        recommendation = "stop-and-clarify"
        scenario = "cannot-start"
        scenario_rationale = "No expert rows available; stage cannot proceed." 
    else:
        avg_float = sum(int(row["score"]) for row in agent_rows) / len(agent_rows)
        avg = int(round(avg_float))
        if avg >= 4:
            recommendation = "proceed"
        elif avg >= 3:
            recommendation = "proceed-with-conditions"
        else:
            recommendation = "stop-and-clarify"
        if recommendation == "stop-and-clarify":
            scenario = "cannot-start"
            scenario_rationale = "Aggregated review indicates blocking gaps."
        elif avg >= 5:
            scenario = "completed"
            scenario_rationale = "All expert dimensions score at completion-level confidence."
        else:
            scenario = "startable"
            scenario_rationale = "Aggregated review supports planning start with manageable conditions."

    dim_lines = "\n".join(
        [
            f"| Problem clarity | {avg} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Derived from expert review set |",
            f"| Scope clarity | {avg} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Derived from expert review set |",
            f"| Constraint clarity | {max(1, avg - 1)} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Constraints consolidated from domain reviews |",
            f"| Stakeholder clarity | {avg} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Stakeholder implications extracted from reviews |",
            f"| Delivery readiness | {avg} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Recommendation synthesis from all experts |",
            f"| Risk clarity | {max(1, avg - 1)} | {min(int(r['score']) for r in agent_rows) if agent_rows else 1} | Risk and blocker notes merged |",
        ]
    )

    summary_rows = "\n".join(
        [
            f"| {row['agent']} | {row['recommendation']} | {row['score']} | {row['finding']} |"
            for row in agent_rows
        ]
    )

    open_questions: list[str] = []
    for row in agent_rows:
        open_questions.extend(str(item) for item in row.get("questions", []))
    open_questions = _unique_preserve_order(open_questions)
    if not open_questions:
        open_questions = [
            "Confirm cross-bundle dependencies before final planning freeze.",
            "Validate ownership for unresolved blockers with agile-coach.",
        ]
    if recommendation == "proceed":
        open_questions = ["No blocking open questions remain."]

    gap_analysis: list[str] = []
    for row in agent_rows:
        gap_analysis.extend(str(item) for item in row.get("missing_information", []))
    gap_analysis = _unique_preserve_order(gap_analysis)
    if not gap_analysis:
        gap_analysis = ["No blocking information gaps remain from selected expert roles."]

    skipped = _unique_preserve_order(skipped_agents or [])

    rendered = template_text
    rendered = rendered.replace("{{stage}}", stage)
    rendered = rendered.replace(
        "{{date}}", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    rendered = rendered.replace("agent_reviews: []", "agent_reviews:\n" + "\n".join(f'  - "{row["agent"]}"' for row in agent_rows))
    rendered = rendered.replace("readiness: pending", f"readiness: {'ready' if recommendation != 'stop-and-clarify' else 'blocked'}")
    rendered = rendered.replace(
        "| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |",
        dim_lines,
    )
    rendered = rendered.replace(
        "- recommendation: proceed / proceed-with-conditions / stop-and-clarify",
        f"- recommendation: {recommendation}",
    )
    rendered = rendered.replace("- confidence_score: 1-5", f"- confidence_score: {avg}")
    rendered += "\n\n## Agent Summary\n"
    rendered += "| Agent | Recommendation | Confidence | Key Finding |\n"
    rendered += "|-------|------------------|------------|-------------|\n"
    rendered += summary_rows + "\n"

    rendered += "\n\n## Open Questions\n"
    rendered += "\n".join(f"- {q}" for q in open_questions)
    rendered += "\n"
    rendered += "\n## Gap Analysis\n"
    rendered += "\n".join(f"- {item}" for item in gap_analysis)
    rendered += "\n"
    rendered += "\n## Expert Scope Filter\n"
    if skipped:
        rendered += "Skipped expert roles for this source block:\n"
        rendered += "\n".join(f"- {agent}" for agent in skipped)
        rendered += "\n"
    else:
        rendered += "- All configured expert roles were relevant for this source block.\n"
    rendered += "\n## Scenario Classification\n"
    rendered += f"- scenario: {scenario}\n"
    rendered += f"- scenario_rationale: {scenario_rationale}\n"
    rendered += "\n## Dynamic Output (Scenario-specific)\n"
    if scenario == "cannot-start":
        rendered += "### cannot-start\n\n"
        rendered += "- Checklist, scoring, and targeted clarification questions are required before planning.\n"
    elif scenario == "completed":
        rendered += "### completed\n\n"
        rendered += "- Focus on optimization questions and additional feature opportunities.\n"
    else:
        rendered += "### startable\n\n"
        rendered += "- Provide checklist, scoring, and feature suggestions for immediate project launch.\n"
    return rendered


def _build_primary_specification_markdown(bundle, source_text: str) -> str:
    """Build primary specification markdown used as canonical synthesized spec."""
    source_digest = sha256_text(source_text.strip() or "")
    markdown_ref, metadata_ref = _bundle_relative_paths(bundle)
    source_lines = _source_note_lines(source_text)
    problem_lines, scope_items = _bundle_synthesis_lines(source_text)
    language_gate = _language_gate_lines(bundle)
    return "\n".join(
        [
            f"# Specification {bundle.item_code}",
            "",
            "## Header",
            f"- data_bundle: {bundle.date_key}/{bundle.item_code}",
            f"- markdown: {markdown_ref}",
            f"- metadata: {metadata_ref}",
            f"- source_sha256: {source_digest}",
            "- single_point_of_truth_board: refs/board/*",
            "- single_point_of_truth_wiki: docs/wiki/",
            "- external_sync_provider: github (optional; may differ in derived layers)",
            "",
            "## Synthesized Problem Statement",
            *[f"- {line}" for line in problem_lines],
            "",
            "## Scope",
            "### In Scope",
            *scope_items,
            "",
            "### Out of Scope",
            "- Exclude assumptions without supporting evidence.",
            "",
            "## Acceptance Criteria",
            "- [ ] At least one thematic epic can be derived from aggregated context.",
            "- [ ] Blocking contradictions are either resolved or tracked with owners.",
            "- [ ] Recommendations and confidence from expert reviews are consolidated.",
            "",
            "## Language Gate",
            *language_gate,
            "",
            "## Source Notes",
            *([f"- {line}" for line in source_lines] if source_lines else ["- No extracted content available."]),
            "",
        ]
    )


def _process_spec_bundle(
    *,
    spec_root: Path,
    bundle,
    source_text: str,
    spec_inventory_template: Path,
    review_text: str,
) -> tuple[int, int]:
    """Process one bundle and attach the date-level cumulative review."""
    review_root = _review_dir(spec_root, bundle)

    created_count = 0
    touched_count = 0

    primary_spec_path = specification_path(spec_root, bundle)
    primary_spec_exists = primary_spec_path.exists()
    ensure_text(primary_spec_path, _build_primary_specification_markdown(bundle, source_text))
    if not primary_spec_exists:
        created_count += 1
    touched_count += 1

    bundle_review_path = review_root / f"{bundle.item_code}.REVIEW.md"
    bundle_review_exists = bundle_review_path.exists()
    ensure_text(
        bundle_review_path,
        review_text,
    )
    touched_count += 1
    created_count += (0 if bundle_review_exists else 1)

    inventory_upsert(
        spec_root / "INVENTORY.md",
        spec_inventory_template,
        bundle_id(bundle),
        {
            "status": "specification-created",
            "paths": [
                primary_spec_path.as_posix(),
                bundle_review_path.as_posix(),
            ],
        },
    )

    return created_count, touched_count


def _build_block_bundle(date_key: str) -> SimpleNamespace:
    """Create a synthetic bundle object used for date-level block reviews."""
    return SimpleNamespace(
        item_code="BLOCK",
        date_key=date_key,
        markdown_path=Path("BLOCK.md"),
        metadata_path=Path("BLOCK.yaml"),
    )


def _bundle_markdown_rel_path(bundle) -> str:
    """Return repository-relative bundle markdown path."""
    return (
        Path(".digital-artifacts")
        / "10-data"
        / bundle.date_key
        / bundle.item_code
        / bundle.markdown_path.name
    ).as_posix()


def _process_review_block(
    *,
    repo_root: Path,
    spec_root: Path,
    date_key: str,
    bundles: list,
    source_by_bundle: dict[str, str],
    agent_review_template: str,
    cumulated_review_template: str,
) -> tuple[str, int, int]:
    """Generate one consolidated expert review set for all bundles of one date."""
    stage = _active_stage()
    block_bundle = _build_block_bundle(date_key)
    review_root = spec_root.parent / "60-review" / date_key / "agile-coach"

    source_parts: list[str] = []
    for bundle in bundles:
        identifier = bundle_id(bundle)
        source_parts.append(f"## {identifier}\n{source_by_bundle.get(identifier, '').strip()}")
    combined_source = "\n\n".join(source_parts).strip()

    selected_agents, skipped_agents = _select_relevant_review_agents(
        repo_root,
        combined_source,
    )
    source_artifacts = [_bundle_markdown_rel_path(bundle) for bundle in bundles]

    stage_instruction = (
        repo_root
        / ".github"
        / "instructions"
        / "stages"
        / f"{ {'exploration': '00-exploration', 'project': '05-project'}.get(stage, '05-project') }.instructions.md"
    )
    stage_instruction_ref = stage_instruction.as_posix()

    created_count = 0
    touched_count = 0
    agent_rows: list[dict[str, object]] = []
    for agent in selected_agents:
        agent_review_dir = spec_root.parent / "60-review" / date_key / agent
        handoff_dir = _runtime_expert_handoff_dir(repo_root, block_bundle, agent)
        request_id = f"{stage}-{date_key}-{block_bundle.item_code}-{agent}".replace("_", "-")
        request_path = handoff_dir / f"{request_id}.expert_request.yaml"
        response_path = handoff_dir / f"{request_id}.expert_response.yaml"

        score, recommendation, applicability = _score_agent_review(agent, combined_source)
        mapping = _agent_mapping_contract(agent, score, applicability)
        agent_spec_path = _agent_spec_path(spec_root, block_bundle, agent)
        agent_review_path = agent_review_dir / f"{block_bundle.item_code}.{agent}.review.md"

        request_exists = request_path.exists()
        response_exists = response_path.exists()
        agent_spec_exists = agent_spec_path.exists()
        agent_review_exists = agent_review_path.exists()

        ensure_text(
            request_path,
            _expert_request_yaml(
                request_id=request_id,
                to_role=agent,
                stage=stage,
                bundle=block_bundle,
                source_markdown=combined_source,
                stage_instruction=stage_instruction_ref,
                source_artifacts=source_artifacts,
            ),
        )
        ensure_text(
            response_path,
            _expert_response_yaml(
                request_id=request_id,
                from_role=agent,
                stage=stage,
                bundle=block_bundle,
                score=score,
                recommendation=recommendation,
                review_path=agent_review_path,
                spec_path=agent_spec_path,
            ),
        )
        ensure_text(
            agent_spec_path,
            _agent_spec_markdown(
                stage=stage,
                agent=agent,
                bundle=block_bundle,
                source_text=combined_source,
                score=score,
                recommendation=recommendation,
                response_path=response_path,
            ),
        )
        ensure_text(
            agent_review_path,
            _agent_review_markdown(
                agent_review_template,
                stage=stage,
                agent=agent,
                bundle=block_bundle,
                score=score,
                recommendation=recommendation,
                applicability=applicability,
                request_path=request_path,
                response_path=response_path,
                agent_spec_path=agent_spec_path,
            ),
        )

        touched_count += 4
        created_count += (0 if request_exists else 1)
        created_count += (0 if response_exists else 1)
        created_count += (0 if agent_spec_exists else 1)
        created_count += (0 if agent_review_exists else 1)

        agent_rows.append(
            {
                "agent": agent,
                "score": score,
                "recommendation": recommendation,
                "finding": f"{agent} assessed the full source block as {applicability}",
                "missing_information": list(mapping.get("missing_information", [])),
                "questions": list(mapping.get("questions", [])),
            }
        )

    block_review_text = _cumulated_review_markdown(
        cumulated_review_template,
        stage=stage,
        agent_rows=agent_rows,
        skipped_agents=skipped_agents,
    )
    block_review_path = review_root / "BLOCK.REVIEW.md"
    block_review_exists = block_review_path.exists()
    ensure_text(block_review_path, block_review_text)
    touched_count += 1
    created_count += (0 if block_review_exists else 1)

    return block_review_text, created_count, touched_count


def run_data_to_specification_impl(repo_root: Path) -> dict[str, int]:
    """Create or refresh specifications from normalized data bundles."""
    artifacts_root = repo_root / ".digital-artifacts"
    data_root = artifacts_root / "10-data"
    spec_root = artifacts_root / "30-specification"
    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    spec_inventory_template = template_root / "30-specification" / "INVENTORY.template.md"

    stages_template_root = repo_root / ".github" / "skills" / "stages-action" / "templates"
    agent_review_template = (stages_template_root / "agent-review.md").read_text(
        encoding="utf-8"
    )
    cumulated_review_template = (stages_template_root / "cumulated-review.md").read_text(
        encoding="utf-8"
    )

    bundles = list(iter_data_bundles(data_root))
    bundles_by_date: dict[str, list] = defaultdict(list)
    source_by_bundle: dict[str, str] = {}
    for bundle in bundles:
        bundles_by_date[bundle.date_key].append(bundle)
        source_by_bundle[bundle_id(bundle)] = bundle.markdown_path.read_text(encoding="utf-8")

    total_created = 0
    total_touched = 0
    for date_key, date_bundles in sorted(bundles_by_date.items()):
        block_review_text, block_created, block_touched = _process_review_block(
            repo_root=repo_root,
            spec_root=spec_root,
            date_key=date_key,
            bundles=date_bundles,
            source_by_bundle=source_by_bundle,
            agent_review_template=agent_review_template,
            cumulated_review_template=cumulated_review_template,
        )
        total_created += block_created
        total_touched += block_touched

        for bundle in date_bundles:
            created, touched = _process_spec_bundle(
                spec_root=spec_root,
                bundle=bundle,
                source_text=source_by_bundle[bundle_id(bundle)],
                spec_inventory_template=spec_inventory_template,
                review_text=block_review_text,
            )
            total_created += created
            total_touched += touched
            _cleanup_legacy_layout(spec_root, bundle)

    return {"touched": total_touched, "created": total_created}
