"""Central registry for generated markdown artifact names and legacy aliases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artifacts_flow_paths import normalized_stage_name


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "markdown-artifacts.env"


@dataclass(frozen=True)
class MarkdownArtifact:
    """Canonical markdown filename plus legacy aliases for migration cleanup."""

    canonical_filename: str
    legacy_filenames: tuple[str, ...] = ()


def _load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    for raw_line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        config[key.strip()] = value.strip()
    return config


def _legacy_names(config: dict[str, str], key: str) -> tuple[str, ...]:
    raw = config.get(key, "")
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


_CONFIG = _load_config()

STAGE_HANDOFF_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["STAGE_HANDOFF_FILENAME"],
)
DELIVERY_STATUS_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["DELIVERY_STATUS_FILENAME"],
    legacy_filenames=_legacy_names(_CONFIG, "DELIVERY_STATUS_LEGACY_FILENAMES"),
)
DELIVERY_REVIEW_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["DELIVERY_REVIEW_FILENAME"],
    legacy_filenames=_legacy_names(_CONFIG, "DELIVERY_REVIEW_LEGACY_FILENAMES"),
)
STAGE_COMPLETION_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["STAGE_COMPLETION_FILENAME"],
    legacy_filenames=_legacy_names(_CONFIG, "STAGE_COMPLETION_LEGACY_FILENAMES"),
)
WHY_NOT_PROGRESSING_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["WHY_NOT_PROGRESSING_FILENAME"],
    legacy_filenames=_legacy_names(_CONFIG, "WHY_NOT_PROGRESSING_LEGACY_FILENAMES"),
)
PROJECT_ASSESSMENT_ARTIFACT = MarkdownArtifact(
    canonical_filename=_CONFIG["PROJECT_ASSESSMENT_FILENAME"],
    legacy_filenames=_legacy_names(_CONFIG, "PROJECT_ASSESSMENT_LEGACY_FILENAMES"),
)


def review_artifact_path(review_dir: Path, artifact: MarkdownArtifact) -> Path:
    """Return the canonical review artifact path for one stage/day directory."""
    return review_dir / artifact.canonical_filename


def planning_assessment_path(planning_root: Path, stage: str) -> Path:
    """Return the canonical planning assessment path for one stage."""
    return (
        planning_root
        / normalized_stage_name(stage)
        / PROJECT_ASSESSMENT_ARTIFACT.canonical_filename
    )


def stage_handoff_path(review_dir: Path) -> Path:
    """Return the canonical stage handoff path for one review directory."""
    return review_dir / STAGE_HANDOFF_ARTIFACT.canonical_filename


def resolve_existing_path(directory: Path, artifact: MarkdownArtifact) -> Path:
    """Resolve the existing canonical or legacy artifact path, preferring canonical."""
    canonical_path = directory / artifact.canonical_filename
    if canonical_path.exists():
        return canonical_path
    for legacy_name in artifact.legacy_filenames:
        legacy_path = directory / legacy_name
        if legacy_path.exists():
            return legacy_path
    return canonical_path


def cleanup_legacy_aliases(canonical_path: Path, artifact: MarkdownArtifact) -> None:
    """Remove migrated legacy alias files once the canonical path exists."""
    if not canonical_path.exists():
        return
    for legacy_name in artifact.legacy_filenames:
        legacy_path = canonical_path.parent / legacy_name
        if legacy_path != canonical_path and legacy_path.exists():
            legacy_path.unlink()


__all__ = [
    "DELIVERY_REVIEW_ARTIFACT",
    "DELIVERY_STATUS_ARTIFACT",
    "PROJECT_ASSESSMENT_ARTIFACT",
    "STAGE_COMPLETION_ARTIFACT",
    "STAGE_HANDOFF_ARTIFACT",
    "WHY_NOT_PROGRESSING_ARTIFACT",
    "MarkdownArtifact",
    "cleanup_legacy_aliases",
    "planning_assessment_path",
    "resolve_existing_path",
    "review_artifact_path",
    "stage_handoff_path",
]