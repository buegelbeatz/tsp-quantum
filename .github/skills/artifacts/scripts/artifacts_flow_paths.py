"""Path helpers for artifacts flow outputs."""

from __future__ import annotations

from pathlib import Path

from artifacts_flow_common import BundleRef


def specification_path(spec_root: Path, bundle: BundleRef) -> Path:
    """Resolve canonical specification path for one bundle."""
    return spec_root / bundle.date_key / "agile-coach" / f"{bundle.item_code}-specification.md"


def normalized_stage_name(stage: str) -> str:
    """Return the normalized stage command used in artifact paths."""
    return stage.strip().lower()


def canonical_stage_doc_name(stage: str) -> str:
    """Return the stage-specific canonical document name.

    Examples:
    - project -> PROJECT.md
    - exploration -> EXPLORATION.md
    """
    return f"{normalized_stage_name(stage).upper()}.md"


def stage_dir_path(stage_root: Path, _stage: str) -> Path:
    """Resolve the canonical directory for a stage."""
    return stage_root


def stage_doc_path(stage_root: Path, stage: str) -> Path:
    """Resolve the canonical stage document path for one stage."""
    return stage_root / canonical_stage_doc_name(stage)


def stage_readiness_path(stage_root: Path, stage: str) -> Path:
    """Resolve the readiness report path for one stage."""
    return stage_root / f"READINESS_{canonical_stage_doc_name(stage)}"


def planning_stage_dir(planning_root: Path, stage: str) -> Path:
    """Resolve the planning directory for one stage."""
    return planning_root / normalized_stage_name(stage)


def planning_item_path(
    planning_root: Path, stage: str, kind: str, item_code: str
) -> Path:
    """Resolve the canonical planning item path for one stage artifact."""
    safe_kind = kind.strip().upper()
    return planning_stage_dir(planning_root, stage) / f"{safe_kind}_{item_code}.md"


def planning_dispatch_path(planning_root: Path, stage: str, item_code: str) -> Path:
    """Resolve the dispatch trace path for one planning item."""
    return planning_stage_dir(planning_root, stage) / f"DISPATCH_{item_code}.md"
