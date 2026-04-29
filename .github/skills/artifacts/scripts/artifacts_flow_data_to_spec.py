"""Data -> specification transition implementation."""

from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from artifacts_flow_common import bundle_id, ensure_text, iter_data_bundles, sha256_text
from artifacts_flow_registry import inventory_upsert
from artifacts_flow_paths import specification_path

try:
    import yaml as _yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    _yaml = None


_REVIEW_QUESTION_BANK_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "digital-artifacts"
    / "30-specification"
    / "REVIEW_QUESTION_BANK.yaml"
)

_EXPERT_ROUTING_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "expert-routing.yaml"
)


@lru_cache(maxsize=1)
def _review_question_bank() -> dict[str, object]:
    """Load the review question bank from skill templates (with safe fallback)."""
    if _yaml is None or not _REVIEW_QUESTION_BANK_PATH.exists():
        return {}

    raw = _REVIEW_QUESTION_BANK_PATH.read_text(encoding="utf-8")
    loaded = _yaml.safe_load(raw)
    if isinstance(loaded, dict):
        return loaded
    return {}


def _review_bank_role(role: str) -> dict[str, object]:
    """Return role-specific review bank section."""
    bank = _review_question_bank()
    roles = bank.get("roles", {}) if isinstance(bank, dict) else {}
    if isinstance(roles, dict):
        entry = roles.get(role, {})
        if isinstance(entry, dict):
            return entry
    return {}


@lru_cache(maxsize=1)
def _expert_routing_config() -> dict[str, object]:
    """Load expert routing/scoring config from YAML with safe fallback."""
    if _yaml is None or not _EXPERT_ROUTING_PATH.exists():
        return {}

    raw = _EXPERT_ROUTING_PATH.read_text(encoding="utf-8")
    loaded = _yaml.safe_load(raw)
    if isinstance(loaded, dict):
        return loaded
    return {}


def _routing_role_config(role: str) -> dict[str, object]:
    """Return role-specific routing config section."""
    cfg = _expert_routing_config()
    roles = cfg.get("roles", {}) if isinstance(cfg, dict) else {}
    if isinstance(roles, dict):
        entry = roles.get(role, {})
        if isinstance(entry, dict):
            return entry
    return {}


def _routing_profiles() -> dict[str, dict[str, object]]:
    """Return configured domain routing profiles."""
    cfg = _expert_routing_config()
    raw_profiles = cfg.get("domain_profiles", {}) if isinstance(cfg, dict) else {}
    if not isinstance(raw_profiles, dict):
        return {}
    profiles: dict[str, dict[str, object]] = {}
    for key, value in raw_profiles.items():
        if isinstance(value, dict):
            profiles[str(key)] = value
    return profiles


def _scoring_specificity_tokens() -> tuple[str, ...]:
    """Return generic specificity tokens from routing config (with fallback)."""
    defaults = (
        "baseline",
        "metric",
        "acceptance",
        "constraint",
        "owner",
        "risk",
        "evidence",
        "evaluation",
    )
    cfg = _expert_routing_config()
    scoring = cfg.get("scoring", {}) if isinstance(cfg, dict) else {}
    if not isinstance(scoring, dict):
        return defaults
    raw = scoring.get("specificity_tokens", [])
    if not isinstance(raw, list):
        return defaults
    tokens = tuple(str(item).strip().lower() for item in raw if str(item).strip())
    return tokens or defaults


def _scoring_role_bonus_tokens(agent: str) -> tuple[str, ...]:
    """Return role-specific bonus tokens from routing config (with fallback)."""
    fallback_map = {
        "quantum-expert": (
            "qaoa",
            "vqe",
            "qubo",
            "quantum annealing",
            "grover",
            "qiskit",
            "classical baseline",
        ),
        "quality-expert": (
            "test",
            "reproducible",
            "reproducibility",
            "validation",
            "benchmark",
            "notebook",
        ),
        "ux-designer": (
            "user",
            "ux",
            "readability",
            "visualization",
            "explainability",
        ),
    }
    cfg = _expert_routing_config()
    scoring = cfg.get("scoring", {}) if isinstance(cfg, dict) else {}
    if not isinstance(scoring, dict):
        return fallback_map.get(agent, ())
    role_bonus = scoring.get("role_bonus_tokens", {})
    if not isinstance(role_bonus, dict):
        return fallback_map.get(agent, ())
    raw_tokens = role_bonus.get(agent, [])
    if not isinstance(raw_tokens, list):
        return fallback_map.get(agent, ())
    tokens = tuple(str(item).strip().lower() for item in raw_tokens if str(item).strip())
    return tokens or fallback_map.get(agent, ())


def _quantum_topic_catalog() -> tuple[list[tuple[str, str]], list[str]]:
    """Return quantum topic token catalog and defaults from routing config."""
    default_catalog = [
        ("qaoa", "QAOA"),
        ("vqe", "VQE"),
        ("qubo", "QUBO"),
        ("quantum annealing", "Quantum Annealing"),
        ("grover", "Grover-style Search"),
        ("qiskit", "Qiskit Circuit Workflow"),
    ]
    default_fallbacks = ["QAOA", "VQE", "Quantum Annealing"]

    cfg = _expert_routing_config()
    topic_catalog = cfg.get("topic_catalog", {}) if isinstance(cfg, dict) else {}
    if not isinstance(topic_catalog, dict):
        return default_catalog, default_fallbacks

    quantum_catalog = topic_catalog.get("quantum_algorithms", {})
    if not isinstance(quantum_catalog, dict):
        return default_catalog, default_fallbacks

    mapped: list[tuple[str, str]] = []
    raw_entries = quantum_catalog.get("token_to_label", [])
    if isinstance(raw_entries, list):
        for entry in raw_entries:
            if isinstance(entry, dict):
                token = str(entry.get("token", "")).strip().lower()
                label = str(entry.get("label", "")).strip()
                if token and label:
                    mapped.append((token, label))

    raw_defaults = quantum_catalog.get("defaults", [])
    defaults = [str(item).strip() for item in raw_defaults if str(item).strip()] if isinstance(raw_defaults, list) else []

    return (mapped or default_catalog), (defaults or default_fallbacks)


def _render_review_templates(values: list[str], replacements: dict[str, str]) -> list[str]:
    """Render placeholder-based review templates with deterministic replacement."""
    rendered: list[str] = []
    for item in values:
        line = item
        for key, value in replacements.items():
            line = line.replace(f"{{{key}}}", value)
        rendered.append(line)
    return rendered


def _active_stage() -> str:
    return (
        (
            os.getenv("DIGITAL_STAGE_CONTEXT", "").strip().lower()
            or os.getenv("STAGE", "").strip().lower()
            or "project"
        )
        .replace(" ", "-")
    )


def _enable_topic_handoffs() -> bool:
    """Return True when optional topic-level expert handoffs are enabled."""
    value = os.getenv("DIGITAL_ENABLE_TOPIC_HANDOFFS", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


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
        "enterprise project specification",
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
        if line.startswith(("🧭", "📘", "📊", "⚙️")):
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

    def _compact(line: str, max_len: int = 260) -> str:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[:max_len].rstrip(" .,:;-")

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
    """Return role keywords from routing config with deterministic fallback."""
    defaults = {
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
    cfg = _expert_routing_config()
    roles = cfg.get("roles", {}) if isinstance(cfg, dict) else {}
    if not isinstance(roles, dict):
        return defaults

    mapped: dict[str, tuple[str, ...]] = {}
    for role, default_keywords in defaults.items():
        role_cfg = roles.get(role, {})
        if isinstance(role_cfg, dict):
            raw_keywords = role_cfg.get("keywords", [])
            if isinstance(raw_keywords, list):
                keywords = tuple(str(item).strip().lower() for item in raw_keywords if str(item).strip())
                if keywords:
                    mapped[role] = keywords
                    continue
        mapped[role] = default_keywords
    return mapped


def _agent_focus(agent: str) -> str:
    role_cfg = _routing_role_config(agent)
    focus = role_cfg.get("focus") if isinstance(role_cfg, dict) else None
    if isinstance(focus, str) and focus.strip():
        return focus.strip()

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


def _agent_evidence_line(agent: str, source_text: str) -> str:
    """Return the strongest source note matching the expert role."""
    keywords = _agent_keyword_map().get(agent, ())
    notes = _source_note_lines(source_text, limit=12)
    for note in notes:
        lowered = note.lower()
        if any(keyword in lowered for keyword in keywords):
            return note
    return notes[0] if notes else ""


def _profile_is_active(profile: dict[str, object], source_text: str) -> bool:
    """Return True when include_if_any keywords match source text."""
    include = profile.get("include_if_any", []) if isinstance(profile, dict) else []
    if not isinstance(include, list) or not include:
        return False
    lowered = source_text.lower()
    return any(str(token).strip().lower() in lowered for token in include if str(token).strip())


def _profile_role_lists(profile: dict[str, object]) -> tuple[list[str], list[str]]:
    """Return include/exclude role lists for one routing profile."""
    include = profile.get("include_roles", []) if isinstance(profile, dict) else []
    exclude = profile.get("exclude_roles", []) if isinstance(profile, dict) else []
    include_roles = [str(item).strip() for item in include if str(item).strip()] if isinstance(include, list) else []
    exclude_roles = [str(item).strip() for item in exclude if str(item).strip()] if isinstance(exclude, list) else []
    return include_roles, exclude_roles


def _agent_questions(agent: str, score: int, applicability: str, source_text: str) -> list[str]:
    """Build role-specific clarification questions from source evidence."""
    evidence = _agent_evidence_line(agent, source_text)
    evidence_suffix = f' Evidence seen: "{evidence}".' if evidence else ""
    role_bank = _review_bank_role(agent)
    if applicability == "not-relevant":
        not_relevant_templates = role_bank.get("not_relevant_questions", [])
        if isinstance(not_relevant_templates, list) and not_relevant_templates:
            return _unique_preserve_order(
                _render_review_templates(
                    [str(item) for item in not_relevant_templates],
                    {"role": agent, "evidence_suffix": evidence_suffix},
                )
            )
        return [
            f"Which explicit requirement should bring {agent} into scope for this stage?{evidence_suffix}",
            f"Which missing artifact or stakeholder signal would justify keeping {agent} in the review set?",
        ]

    relevant_templates = role_bank.get("relevant_questions", [])
    if isinstance(relevant_templates, list) and relevant_templates:
        questions = _render_review_templates(
            [str(item) for item in relevant_templates],
            {"role": agent, "evidence_suffix": evidence_suffix},
        )
    else:
        role_questions = {
            "ux-designer": [
                f"Which primary persona and end-to-end flow should UX optimize first?{evidence_suffix}",
                "Which accessibility acceptance criterion must be proven before planning handoff?",
            ],
            "security-expert": [
                f"Which threat scenario, trust boundary, or sensitive asset is most exposed here?{evidence_suffix}",
                "Which mandatory control must exist before delivery can start?",
            ],
            "quality-expert": [
                f"Which executable test or measurement will prove the requirement is done?{evidence_suffix}",
                "Which quality gate is currently weakest: correctness, coverage, or reproducibility?",
            ],
            "platform-architect": [
                f"Which service boundary or integration contract owns this capability?{evidence_suffix}",
                "Which dependency must be fixed first so stories can be split cleanly?",
            ],
            "quantum-expert": [
                f"Which classical baseline and comparison metric justify quantum exploration?{evidence_suffix}",
                "Which problem slice is genuinely quantum-relevant versus classical optimization?",
            ],
        }
        questions = role_questions.get(
            agent,
            [
                f"Which domain-specific acceptance criterion should this expert own first?{evidence_suffix}",
                "Which unresolved dependency still blocks delivery-ready planning?",
            ],
        )
    if score <= 3:
        low_score_template = role_bank.get("low_score_question")
        if isinstance(low_score_template, str) and low_score_template.strip():
            questions.append(
                low_score_template
                .replace("{role}", agent)
                .replace("{evidence_suffix}", evidence_suffix)
            )
        else:
            questions.append(
                f"Which missing detail would lift the {agent} assessment from proceed-with-conditions to proceed?"
            )
    return _unique_preserve_order(questions)


def _agent_missing_information(agent: str, score: int, applicability: str, source_text: str) -> list[str]:
    """Describe role-specific gaps that still block sharper downstream planning."""
    evidence = _agent_evidence_line(agent, source_text)
    evidence_hint = f' Current evidence: "{evidence}".' if evidence else ""
    role_bank = _review_bank_role(agent)
    if applicability == "not-relevant":
        not_relevant_gaps = role_bank.get("not_relevant_missing_information", [])
        if isinstance(not_relevant_gaps, list) and not_relevant_gaps:
            return _unique_preserve_order(
                _render_review_templates(
                    [str(item) for item in not_relevant_gaps],
                    {"role": agent, "evidence_hint": evidence_hint},
                )
            )
        return [
            f"No explicit {agent} trigger was strong enough in the normalized source bundle.{evidence_hint}",
            "Cross-role dependency evidence is missing for this expert domain.",
        ]

    relevant_gaps_templates = role_bank.get("relevant_missing_information", [])
    if isinstance(relevant_gaps_templates, list) and relevant_gaps_templates:
        role_gaps = {
            agent: _render_review_templates(
                [str(item) for item in relevant_gaps_templates],
                {"role": agent, "evidence_hint": evidence_hint},
            )
        }
    else:
        role_gaps = {
            "ux-designer": [
                f"Primary user segment, journey step, or interaction pain is underspecified.{evidence_hint}",
                "Accessibility and feedback-loop expectations are not yet crisp enough for implementation tasks.",
            ],
            "security-expert": [
                f"Threat actor, sensitive asset, or trust boundary is not explicitly documented.{evidence_hint}",
                "Required preventative and detective controls are still implicit.",
            ],
            "quality-expert": [
                f"Verification evidence and pass/fail thresholds are still too implicit.{evidence_hint}",
                "The path from acceptance criteria to executable tests is not fully mapped.",
            ],
            "platform-architect": [
                f"System boundaries and integration ownership need sharper decomposition.{evidence_hint}",
                "Operational dependencies are not yet translated into delivery-safe sequencing.",
            ],
            "quantum-expert": [
                f"Quantum applicability lacks a fully explicit baseline and evaluation envelope.{evidence_hint}",
                "The handoff between classical and quantum-inspired methods is not yet bounded tightly enough.",
            ],
        }
    if score >= 4:
        return [
            role_gaps.get(agent, [f"Residual {agent} assumptions should still be tracked for planning." + evidence_hint])[0],
            "No blocking information gaps remain, but assumptions should stay visible in planning artifacts.",
        ]
    return role_gaps.get(
        agent,
        [
            f"Task-level implementation detail is too thin for reliable execution.{evidence_hint}",
            "Owner handoff criteria require sharper boundaries.",
        ],
    )


def _agent_finding(agent: str, applicability: str, source_text: str) -> str:
    """Return a concise, evidence-based key finding for review summaries."""
    evidence = _agent_evidence_line(agent, source_text)
    role_bank = _review_bank_role(agent)
    finding_template = role_bank.get("finding_template")
    if isinstance(finding_template, str) and finding_template.strip():
        return (
            finding_template.replace("{role}", agent)
            .replace("{applicability}", applicability)
            .replace("{evidence}", evidence)
        )
    if applicability == "not-relevant":
        return f"{agent} found no strong domain signal in the current normalized bundle."
    if evidence:
        return f"{agent} anchored its assessment on: {evidence}"
    return f"{agent} assessed the source block as relevant but still needs sharper evidence."


def _score_agent_review(agent: str, source_text: str) -> tuple[int, str, str]:
    """Return (score, recommendation, applicability)."""
    lower = source_text.lower()
    keywords = _agent_keyword_map().get(agent, ())
    hits = sum(1 for key in keywords if key in lower)
    applicability = "relevant" if hits > 0 else "not-relevant"

    role_cfg = _routing_role_config(agent)
    score_bias = int(role_cfg.get("score_bias", 0)) if isinstance(role_cfg, dict) else 0
    min_score = int(role_cfg.get("min_score", 2)) if isinstance(role_cfg, dict) else 2
    max_score = int(role_cfg.get("max_score", 5)) if isinstance(role_cfg, dict) else 5

    specificity_tokens = _scoring_specificity_tokens()
    specificity_hits = sum(1 for token in specificity_tokens if token in lower)

    role_bonus_tokens = _scoring_role_bonus_tokens(agent)
    role_bonus_hits = sum(1 for token in role_bonus_tokens if token in lower)
    role_bonus = 2 if role_bonus_hits >= 3 else 1 if role_bonus_hits >= 1 else 0

    if applicability == "not-relevant":
        score = 2 + score_bias
    else:
        score = 2 + min(2, hits) + (1 if specificity_hits >= 2 else 0) + role_bonus + score_bias

    score = max(min_score, min(max_score, score))

    if score >= 4:
        recommendation = "proceed"
    elif score == 3:
        recommendation = "proceed-with-conditions"
    else:
        recommendation = "stop-and-clarify"
    return score, recommendation, applicability


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

    forced_include: list[str] = []
    forced_exclude: list[str] = []
    for profile in _routing_profiles().values():
        if _profile_is_active(profile, source_text):
            include_roles, exclude_roles = _profile_role_lists(profile)
            forced_include.extend(include_roles)
            forced_exclude.extend(exclude_roles)

    forced_include = _unique_preserve_order(forced_include)
    forced_exclude = _unique_preserve_order(forced_exclude)

    for agent in candidates:
        if agent in forced_exclude:
            skipped.append(agent)
            continue
        if agent in forced_include:
            selected.append(agent)
            continue

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


def _replace_markdown_section(markdown_text: str, heading: str, body_lines: list[str]) -> str:
    """Replace one level-2 markdown section body while preserving heading order."""
    body = "\n".join(body_lines).rstrip()
    section = f"## {heading}\n\n{body}\n"
    pattern = re.compile(rf"## {re.escape(heading)}\n.*?(?=\n## |\Z)", flags=re.DOTALL)
    if pattern.search(markdown_text):
        return pattern.sub(section, markdown_text)
    return markdown_text.rstrip() + "\n\n" + section


def _quantum_algorithm_topics(source_text: str) -> list[str]:
    """Extract up to three quantum algorithm topics from source text."""
    catalog, defaults = _quantum_topic_catalog()
    lowered = source_text.lower()
    topics = [label for token, label in catalog if token in lowered]
    for fallback in defaults:
        if len(topics) >= 3:
            break
        if fallback not in topics:
            topics.append(fallback)
    return topics[:3]


def _yaml_safe(value: str) -> str:
    """Return a YAML-safe double-quoted scalar."""
    return '"' + value.replace("\\", "\\\\").replace('"', "'") + '"'


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


def _agent_mapping_contract(
    agent: str,
    score: int,
    applicability: str,
    source_text: str,
) -> dict[str, object]:
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
            "missing_information": _agent_missing_information(role, score, applicability, source_text),
            "questions": _agent_questions(role, score, applicability, source_text),
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
        "missing_information": _agent_missing_information(role, score, applicability, source_text),
        "questions": _agent_questions(role, score, applicability, source_text),
    }


def _agent_review_markdown(
    template_text: str,
    *,
    stage: str,
    agent: str,
    bundle,
    source_text: str = "",
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
    mapping = _agent_mapping_contract(agent, score, applicability, source_text)
    missing_information = [str(item) for item in mapping.get("missing_information", [])]
    clarification_questions = [str(item) for item in mapping.get("questions", [])]

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
    rendered = _replace_markdown_section(
        rendered,
        "Missing Information",
        [f"- {item}" for item in missing_information] or ["- No blocking information gaps were identified."],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Questions for Clarification",
        [f"- {item}" for item in clarification_questions] or ["- No blocking clarification questions remain."],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Scenario Classification",
        [
            f"- scenario: {scenario}",
            f"- scenario_rationale: {scenario_rationale}",
        ],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Story/Task Mapping (Expert -> Agile Coach)",
        [
            f"- can_formulate_story: {mapping['can_story']}",
            f"- can_formulate_task: {mapping['can_task']}",
            "- required_fields:",
            *[f"  - {item}" for item in mapping["required_fields"]],
            "- coach_feedback_missing_information:",
            *[f"  - {item}" for item in missing_information],
            "- coach_feedback_questions:",
            *[f"  - {item}" for item in clarification_questions],
        ],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Dynamic Output (Scenario-specific)",
        [
            f"### {scenario}",
            "",
            *scenario_output[scenario],
            *(
                ["", "- not_relevant_reason: Domain trigger evidence is currently too weak for mandatory scope inclusion."]
                if applicability == "not-relevant"
                else []
            ),
        ],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Readiness Assessment",
        [
            f"- decision: {recommendation}",
            "- blocking_items:",
            "  - none" if recommendation == "proceed" else "  - Clarify open questions before planning freeze",
            f"- rationale: {scenario_rationale}",
        ],
    )
    rendered += "\n\n## Handoff Trace\n"
    rendered += f"- expert_request: {request_rel}\n"
    rendered += f"- expert_response: {response_rel}\n"
    rendered += f"- applicability: {applicability}\n"
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
    questions = _agent_questions(to_role, 3, "relevant", source_markdown)

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
            f"request_id: {_yaml_safe(request_id)}",
            f"from_role: {_yaml_safe('agile-coach')}",
            f"to_role: {_yaml_safe(to_role)}",
            f"goal: {_yaml_safe(f'Assess {bundle_id(bundle)} for stage {stage} and provide recommendation with confidence score.')}",
            "current_state:",
            f"  stage: {_yaml_safe(stage)}",
            f"  bundle: {_yaml_safe(bundle_id(bundle))}",
            "  artifacts:",
            *[f"    - {_yaml_safe(path)}" for path in artifact_lines],
            "context:",
            *[f"  - {_yaml_safe(entry)}" for entry in context_lines],
            "assumptions:",
            *[f"  - {_yaml_safe(entry)}" for entry in assumptions],
            "open_questions:",
            *[f"  - {_yaml_safe(entry)}" for entry in questions],
            "artifacts:",
            f"  - {_yaml_safe(f'stage_instruction: {stage_instruction}')}",
            *[f"  - {_yaml_safe(f'source_note: {line}')}" for line in notes],
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
    source_markdown: str = "",
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
    questions = _agent_questions(from_role, score, "relevant", source_markdown)

    return "\n".join(
        [
            "schema: expert_response_v1",
            f"request_id: {_yaml_safe(request_id)}",
            f"from_role: {_yaml_safe(from_role)}",
            f"to_role: {_yaml_safe('agile-coach')}",
            f"summary: {_yaml_safe(summary)}",
            f"confidence: {confidence}",
            "recommendations:",
            *[f"  - {_yaml_safe(entry)}" for entry in recs],
            "assumptions:",
            *[f"  - {_yaml_safe(entry)}" for entry in assumptions],
            "open_questions:",
            *[f"  - {_yaml_safe(entry)}" for entry in questions],
            "artifacts:",
            f"  - {_yaml_safe(f'review: {review_path.as_posix()}')}",
            f"  - {_yaml_safe(f'spec: {spec_path.as_posix()}')}",
            f"  - {_yaml_safe(f'score: {score}')}",
            f"  - {_yaml_safe(f'recommendation: {recommendation}')}",
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
    rendered = _replace_markdown_section(
        rendered,
        "Consensus",
        [
            "- Expert reviews agree that planning can proceed when scope and acceptance evidence stay explicit.",
            "- Confidence and recommendations are consolidated and must be preserved in planning artifacts.",
        ],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Open Questions",
        [f"- {q}" for q in open_questions],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Gap Analysis",
        [f"- {item}" for item in gap_analysis],
    )

    scope_filter_lines: list[str] = []
    if skipped:
        scope_filter_lines.append("Skipped expert roles for this source block:")
        scope_filter_lines.extend(f"- {agent}" for agent in skipped)
    else:
        scope_filter_lines.append("- All configured expert roles were relevant for this source block.")

    rendered = _replace_markdown_section(
        rendered,
        "Agent Review Summary",
        [
            "| Agent | Recommendation | Confidence | Key Finding |",
            "|-------|------------------|------------|-------------|",
            *summary_rows.splitlines(),
        ],
    )
    rendered = _replace_markdown_section(
        rendered,
        "Scenario Classification",
        [
            f"- scenario: {scenario}",
            f"- scenario_rationale: {scenario_rationale}",
        ],
    )

    dynamic_lines: list[str]
    if scenario == "cannot-start":
        dynamic_lines = [
            "### cannot-start",
            "",
            "- Checklist, scoring, and targeted clarification questions are required before planning.",
        ]
    elif scenario == "completed":
        dynamic_lines = [
            "### completed",
            "",
            "- Focus on optimization questions and additional feature opportunities.",
        ]
    else:
        dynamic_lines = [
            "### startable",
            "",
            "- Provide checklist, scoring, and feature suggestions for immediate project launch.",
        ]

    rendered = _replace_markdown_section(
        rendered,
        "Dynamic Output (Scenario-specific)",
        dynamic_lines,
    )
    rendered += "\n\n## Expert Scope Filter\n"
    rendered += "\n".join(scope_filter_lines) + "\n"
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
        mapping = _agent_mapping_contract(agent, score, applicability, combined_source)
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
                source_markdown=combined_source,
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
                source_text=combined_source,
                score=score,
                recommendation=recommendation,
                applicability=applicability,
                request_path=request_path,
                response_path=response_path,
                agent_spec_path=agent_spec_path,
            ),
        )

        if agent == "quantum-expert" and _enable_topic_handoffs():
            for topic in _quantum_algorithm_topics(combined_source):
                topic_slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
                topic_request_id = f"{request_id}-{topic_slug}"
                topic_request_path = handoff_dir / f"{topic_request_id}.expert_request.yaml"
                topic_response_path = handoff_dir / f"{topic_request_id}.expert_response.yaml"

                topic_request_exists = topic_request_path.exists()
                topic_response_exists = topic_response_path.exists()

                topic_source = (
                    f"Topic focus: {topic}\n"
                    "Assess algorithm applicability, baseline comparison expectations, and evaluation criteria.\n\n"
                    f"{combined_source}"
                )

                ensure_text(
                    topic_request_path,
                    _expert_request_yaml(
                        request_id=topic_request_id,
                        to_role=agent,
                        stage=stage,
                        bundle=block_bundle,
                        source_markdown=topic_source,
                        stage_instruction=stage_instruction_ref,
                        source_artifacts=source_artifacts,
                    ),
                )
                ensure_text(
                    topic_response_path,
                    _expert_response_yaml(
                        request_id=topic_request_id,
                        from_role=agent,
                        stage=stage,
                        bundle=block_bundle,
                        score=score,
                        recommendation=recommendation,
                        review_path=agent_review_path,
                        spec_path=agent_spec_path,
                        source_markdown=topic_source,
                    ),
                )

                touched_count += 2
                created_count += (0 if topic_request_exists else 1)
                created_count += (0 if topic_response_exists else 1)

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
                "finding": _agent_finding(agent, applicability, combined_source),
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
