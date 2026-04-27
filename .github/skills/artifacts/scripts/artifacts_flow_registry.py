"""Registry helpers for artifacts flow expert-review tracking."""

from __future__ import annotations

from pathlib import Path

from artifact_inventory import InventoryEntry, append_inventory_entry
from artifacts_flow_common import BundleRef, ensure_text, timestamp


DEFAULT_EXPERT_REVIEW_AGENTS = [
    "platform-architect",
    "quality-expert",
    "security-expert",
    "ux-designer",
]


def _normalize_agent_list(agents: list[str]) -> list[str]:
    """Normalize and deduplicate agent names while preserving order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        normalized = agent.strip().lower()
        if not normalized or "-" not in normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _parse_role_agents(role_file: Path) -> list[str]:
    """Parse agents list from a generic role file frontmatter."""
    if not role_file.exists():
        return []

    agents: list[str] = []
    in_agents = False
    for raw_line in role_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "agents:":
            in_agents = True
            continue
        if in_agents and stripped.startswith("- "):
            agents.append(stripped[2:].strip())
            continue
        if in_agents and not line.startswith((" ", "\t")):
            break
    return _normalize_agent_list(agents)


def resolve_expert_review_agents(repo_root: Path) -> list[str]:
    """Resolve agents with both generic-expert and generic-review roles, plus ux-designer."""
    roles_root = repo_root / ".github" / "agents" / "roles"
    expert_agents = _parse_role_agents(roles_root / "generic-expert.agent.md")
    review_agents = _parse_role_agents(roles_root / "generic-review.agent.md")

    review_set = set(review_agents)
    overlap = [agent for agent in expert_agents if agent in review_set]

    if not overlap:
        overlap = [agent for agent in DEFAULT_EXPERT_REVIEW_AGENTS if agent != "ux-designer"]

    return _normalize_agent_list([*overlap, "ux-designer"])


def _request_file(bundle: BundleRef) -> Path:
    review_dir = bundle.item_root.parent.parent / "60-review" / bundle.date_key / bundle.item_code
    return review_dir / "00-expert-review-request.md"


def _response_files(bundle: BundleRef) -> list[Path]:
    review_dir = bundle.item_root.parent.parent / "60-review" / bundle.date_key / bundle.item_code
    if not review_dir.exists():
        return []
    return sorted(
        [
            path
            for path in review_dir.iterdir()
            if path.is_file()
            and path.name.startswith("expert-response-")
            and path.suffix.lower() in {".md", ".yaml", ".yml"}
        ]
    )


def _agent_from_response_file(path: Path) -> str | None:
    stem = path.stem
    if stem.startswith("expert-response-"):
        candidate = stem[len("expert-response-") :].strip().lower()
        if candidate:
            return candidate
    return None


def _requested_agents_from_request_file(request_path: Path) -> list[str]:
    if not request_path.exists():
        return []

    requested: list[str] = []
    in_list = False
    for raw_line in request_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Requested Expert Reviewers":
            in_list = True
            continue
        if in_list and line.startswith("## "):
            break
        if in_list and line.startswith("- "):
            requested.append(line[2:].strip())
    return _normalize_agent_list(requested)


def append_review_marker(
    bundle: BundleRef, prompt_name: str, agents: list[str]
) -> Path:
    """Ensure expert review request exists and stays normalized in bundle review folder."""
    request_file = _request_file(bundle)
    requested = _normalize_agent_list([*agents, *_requested_agents_from_request_file(request_file)])

    lines = [
        f"# Expert Review Request {bundle.item_code}",
        "",
        f"- prompt: /{prompt_name}",
        f"- item: {bundle.date_key}/{bundle.item_code}",
        f"- created_at: {timestamp()}",
        "",
        "## Requested Expert Reviewers",
    ]
    lines.extend(f"- {agent}" for agent in requested)
    lines.extend(
        [
            "",
            "## Response Contract",
            "- Use `expert_request_v1` for requests and `expert_response_v1` for responses.",
            "- Persist responses in this folder as `expert-response-<agent>.md` or `.yaml`.",
            "- Each response must include explicit 1-5 scoring and one recommendation: `proceed`, `proceed-with-conditions`, or `stop-and-clarify`.",
            "",
        ]
    )
    ensure_text(request_file, "\n".join(lines) + "\n")
    return request_file


def planning_reviews_status(
    bundle: BundleRef,
) -> tuple[list[str], list[str], list[str]]:
    """Return (requested_agents, received_agents, pending_agents) for one bundle."""
    request_file = _request_file(bundle)
    requested = _requested_agents_from_request_file(request_file)
    if not requested:
        requested = list(DEFAULT_EXPERT_REVIEW_AGENTS)

    received = _normalize_agent_list(
        [
            agent
            for response in _response_files(bundle)
            for agent in [_agent_from_response_file(response)]
            if agent
        ]
    )
    requested_set = set(requested)
    received_set = {agent for agent in received if agent in requested_set}
    pending = [agent for agent in requested if agent not in received_set]
    return requested, sorted(received_set), pending


def planning_reviews_ready(
    bundle: BundleRef,
) -> tuple[bool, list[str], list[str], list[str]]:
    """Return readiness and per-agent status for expert review confirmations."""
    requested, received, pending = planning_reviews_status(bundle)
    return len(pending) == 0, requested, received, pending


def inventory_upsert(
    inventory_path: Path,
    template_path: Path,
    item_id: str,
    fields: dict[str, str | list[str]],
) -> None:
    """Upsert one inventory entry with deterministic timestamp."""
    append_inventory_entry(
        inventory_path,
        InventoryEntry(item_id=item_id, created_at=timestamp(), fields=fields),
        template_path if template_path.exists() else None,
    )
