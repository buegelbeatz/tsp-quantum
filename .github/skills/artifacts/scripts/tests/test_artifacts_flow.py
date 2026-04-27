"""Unit tests for artifacts workflow transition orchestration."""

from __future__ import annotations

import subprocess
import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "artifacts").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_DIR = ROOT / ".github" / "skills" / "artifacts" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

artifacts_flow = import_module("artifacts_flow")
artifacts_flow_stage = import_module("artifacts_flow_stage")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_expert_responses(
    repo_root: Path,
    *,
    complete: bool,
    date_key: str = "2026-03-31",
    item_code: str = "00000",
) -> Path:
    reviews_dir = (
        repo_root
        / ".digital-artifacts"
        / "10-data"
        / date_key
        / item_code
        / "reviews"
    )
    responses = [
        "platform-architect",
        "quality-expert",
        "security-expert",
        "ux-designer",
    ]
    if not complete:
        responses = responses[:-1]

    for agent in responses:
        _write(
            reviews_dir / f"expert-response-{agent}.md",
            "\n".join(
                [
                    f"# Expert Response {agent}",
                    "",
                    "- kind: expert_response_v1",
                    f"- from: {agent}",
                    "- recommendation: proceed",
                    "- confidence: 4",
                    "",
                ]
            ),
        )

    _write(
        reviews_dir / "00-expert-review-request.md",
        "\n".join(
            [
                "# Expert Review Request 00000",
                "",
                "## Requested Expert Reviewers",
                "- platform-architect",
                "- quality-expert",
                "- security-expert",
                "- ux-designer",
                "",
            ]
        ),
    )
    return reviews_dir


def _seed_bundle(
    repo_root: Path, date_key: str = "2026-03-31", item_code: str = "00000"
) -> Path:
    bundle_root = repo_root / ".digital-artifacts" / "10-data" / date_key / item_code
    _write(bundle_root / f"{item_code}.md", "# Extracted\n\nSample content\n")
    _write(bundle_root / f"{item_code}.yaml", "classification: document\n")
    return bundle_root


def _seed_ready_specification(
    repo_root: Path,
    stage: str = "mvp",
    date_key: str = "2026-03-31",
    item_code: str = "00000",
) -> Path:
    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / date_key
        / "agile-coach"
        / f"{item_code}-specification.md"
    )
    review_path = (
        repo_root
        / ".digital-artifacts"
        / "60-review"
        / date_key
        / "agile-coach"
        / f"{item_code}.REVIEW.md"
    )
    _write(
        spec_path,
        "\n".join(
            [
                f"# Spec {item_code}",
                "",
                "## Problem",
                "The current workflow produces inconsistent stage artifacts.",
                "",
                "## Scope",
                "Create a canonical stage document and template-based planning artifacts.",
                "",
                "## Acceptance Criteria",
                "- Canonical stage document exists.",
                "- Planning artifacts are generated from templates.",
                "",
            ]
        ),
    )
    _write(
        review_path,
        "\n".join(
            [
                "---",
                f'stage: "{stage}"',
                'updated: "2026-03-31T00:00:00Z"',
                "agent_reviews: []",
                "readiness: ready",
                "status: complete",
                "layer: digital-generic-team",
                "---",
                "",
                f"# Cumulated Stage Review: {stage}",
                "",
                "## Readiness Assessment",
                "",
                "- recommendation: proceed",
                "- confidence_score: 4",
                "- rationale: Sufficient to proceed.",
                "",
            ]
        ),
    )
    return spec_path


def test_data_to_specification_creates_spec_and_review_markers(tmp_path: Path) -> None:
    """TODO: add docstring for test_data_to_specification_creates_spec_and_review_markers."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_expert_responses(repo_root, complete=True)

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(
        template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n"
    )
    _write(template_root / "60-review" / "LATEST.template.md", "# LATEST\n")
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    result = artifacts_flow.run_data_to_specification(repo_root)

    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "agile-coach"
        / "00000-specification.md"
    )
    reviews_dir = (
        repo_root
        / ".digital-artifacts"
        / "10-data"
        / "2026-03-31"
        / "00000"
        / "reviews"
    )
    assert result["touched"] >= 1
    assert result["created"] >= 1
    assert spec_path.exists()
    assert reviews_dir.exists()


def test_data_to_specification_surfaces_language_gate_status(tmp_path: Path) -> None:
    """Primary specifications should expose the ingest language gate status from bundle metadata."""
    repo_root = tmp_path
    bundle_root = _seed_bundle(repo_root)
    _seed_expert_responses(repo_root, complete=True)
    _write(
        bundle_root / "00000.yaml",
        "\n".join(
            [
                "classification: document",
                "language_gate_status: failed",
                'language_gate_note: "Canonical downstream content still contains localized fragments; translate or normalize before planning promotion."',
            ]
        )
        + "\n",
    )

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n")
    _write(template_root / "60-review" / "LATEST.template.md", "# LATEST\n")
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    artifacts_flow.run_data_to_specification(repo_root)

    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "agile-coach"
        / "00000-specification.md"
    )
    content = spec_path.read_text(encoding="utf-8")
    assert "## Language Gate" in content
    assert "- status: failed" in content
    assert "localized fragments" in content
    assert "Repair or regenerate canonical English bundle content" in content


def test_data_to_specification_blocks_until_all_requested_expert_responses_exist(
    tmp_path: Path,
) -> None:
    """Specification synthesis is always created even when expert responses are incomplete."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_expert_responses(repo_root, complete=False)

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(
        template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n"
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    result = artifacts_flow.run_data_to_specification(repo_root)

    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "agile-coach"
        / "00000-specification.md"
    )
    assert result["created"] >= 1
    assert result["touched"] >= 1
    assert spec_path.exists()


def test_data_to_specification_keeps_existing_cumulative_review(tmp_path: Path) -> None:
    """Legacy 10-data reviews folder is not required for specification reruns."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_expert_responses(repo_root, complete=True)

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(
        template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n"
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    artifacts_flow.run_data_to_specification(repo_root)
    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "agile-coach"
        / "00000-specification.md"
    )
    assert spec_path.exists()


def test_data_to_specification_uses_block_level_expert_reviews_and_filters_roles(
    tmp_path: Path,
) -> None:
    """Expert reviews should be generated once per date block with role relevance filtering."""
    repo_root = tmp_path
    _seed_bundle(repo_root, date_key="2026-03-31", item_code="00000")
    _seed_bundle(repo_root, date_key="2026-03-31", item_code="00001")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n")
    _write(template_root / "60-review" / "LATEST.template.md", "# LATEST\n")
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    artifacts_flow.run_data_to_specification(repo_root)

    block_quality_review = (
        repo_root
        / ".digital-artifacts"
        / "60-review"
        / "2026-03-31"
        / "quality-expert"
        / "BLOCK.quality-expert.review.md"
    )
    block_quantum_review = (
        repo_root
        / ".digital-artifacts"
        / "60-review"
        / "2026-03-31"
        / "quantum-expert"
        / "BLOCK.quantum-expert.review.md"
    )
    bundle_review = (
        repo_root
        / ".digital-artifacts"
        / "60-review"
        / "2026-03-31"
        / "agile-coach"
        / "00000.REVIEW.md"
    )

    assert block_quality_review.exists()
    assert not block_quantum_review.exists()
    assert bundle_review.exists()
    review_text = bundle_review.read_text(encoding="utf-8")
    assert "## Expert Scope Filter" in review_text
    assert "quantum-expert" in review_text


def test_data_to_specification_surfaces_expert_questions_and_gap_analysis(
    tmp_path: Path,
) -> None:
    """Cumulated review should include explicit expert questions and missing-information feedback."""
    repo_root = tmp_path
    _seed_bundle(repo_root, date_key="2026-03-31", item_code="00000")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "30-specification" / "INVENTORY.template.md", "# INVENTORY\n")
    _write(template_root / "60-review" / "LATEST.template.md", "# LATEST\n")
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "agent-review.md",
        "status: pending\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n- one_line_rationale: \"\"\nbundle_ids: []\n| Problem clarity | | |\n| Scope clarity | | |\n| Constraint clarity | | |\n| Stakeholder clarity | | |\n| Delivery readiness | | |\n| Risk clarity | | |\n| Problem statement | [ ] | |\n| Stakeholders | [ ] | |\n| Constraints | [ ] | |\n| Success criteria | [ ] | |\n- Spec file: (path or \"none\")\n- Coverage assessment: incomplete / partial / sufficient\n",
    )
    _write(
        repo_root / ".github" / "skills" / "stages-action" / "templates" / "cumulated-review.md",
        "readiness: pending\nagent_reviews: []\n| Problem clarity | | | |\n| Scope clarity | | | |\n| Constraint clarity | | | |\n| Stakeholder clarity | | | |\n| Delivery readiness | | | |\n| Risk clarity | | | |\n- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n- confidence_score: 1-5\n",
    )

    artifacts_flow.run_data_to_specification(repo_root)

    review_path = (
        repo_root
        / ".digital-artifacts"
        / "60-review"
        / "2026-03-31"
        / "agile-coach"
        / "00000.REVIEW.md"
    )
    review_text = review_path.read_text(encoding="utf-8")
    assert "## Open Questions" in review_text
    assert "Which explicit requirement should be owned by" in review_text
    assert "## Gap Analysis" in review_text


def test_data_to_specification_does_not_restore_inputs_from_done(
    tmp_path: Path, monkeypatch
) -> None:
    """Data->specification must not trigger 20-done re-ingest restores."""
    called_restore = False

    monkeypatch.setattr(
        artifacts_flow,
        "run_data_to_specification_impl",
        lambda repo_root: {"created": 2, "touched": 3},
    )

    def _unexpected_restore(_repo_root):
        nonlocal called_restore
        called_restore = True
        return {"restored": 0, "skipped_existing": 0, "skipped_inventory": 0}

    monkeypatch.setattr(artifacts_flow, "restore_inputs_from_done", _unexpected_restore)

    result = artifacts_flow.run_data_to_specification(tmp_path)

    assert called_restore is False
    assert result["created"] == 2
    assert result["touched"] == 3


def test_specification_to_stage_skips_when_sections_missing(tmp_path: Path) -> None:
    """TODO: add docstring for test_specification_to_stage_skips_when_sections_missing."""
    repo_root = tmp_path
    _seed_bundle(repo_root)

    spec_path = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "00000"
        / "00000-specification.md"
    )
    _write(spec_path, "# Specification\n\nMissing mandatory sections\n")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "40-stage" / "INVENTORY.template.md", "# INVENTORY\n")

    result = artifacts_flow.run_specification_to_stage(repo_root, "mvp")

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "MVP.md"
    assert result["ready"] == 0
    assert result["skipped"] == 1
    assert stage_path.exists()
    assert "status: in-progress" in stage_path.read_text(encoding="utf-8")


def test_specification_to_stage_creates_stage_named_from_stage_command(
    tmp_path: Path,
) -> None:
    """Stage output uses the canonical stage-specific filename."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_ready_specification(repo_root, stage="pilot")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "40-stage" / "INVENTORY.template.md", "# INVENTORY\n")

    result = artifacts_flow.run_specification_to_stage(repo_root, "pilot")

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PILOT.md"
    assert result["ready"] == 1
    assert result["skipped"] == 0
    assert stage_path.exists()


def test_specification_to_stage_quarantines_blocked_bundles_but_stays_ready(
    tmp_path: Path,
) -> None:
    """Stage should remain planning-ready when at least one selected bundle is ready."""
    repo_root = tmp_path
    _seed_bundle(repo_root, item_code="00000")
    _seed_bundle(repo_root, item_code="00001")
    _seed_ready_specification(repo_root, stage="project", item_code="00000")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "40-stage" / "INVENTORY.template.md", "# INVENTORY\n")

    artifacts_flow.run_specification_to_stage(repo_root, "project")

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_text = stage_path.read_text(encoding="utf-8")
    assert "status: active" in stage_text
    assert "ready_for_planning: true" in stage_text
    assert 'gate_reason: "stage is ready for planning with quarantined blocked bundles"' in stage_text
    assert "selected_bundle_count: 1" in stage_text
    assert "blocked_bundle_count: 1" in stage_text
    assert '- "2026-03-31/00001"' in stage_text


def test_specification_to_stage_blocks_failed_language_gate(tmp_path: Path) -> None:
    """A failed language gate in the canonical specification must block stage readiness."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    spec_path = _seed_ready_specification(repo_root, stage="project")
    _write(
        spec_path,
        spec_path.read_text(encoding="utf-8")
        + "\n## Language Gate\n- status: failed\n- note: Localized canonical text remains in the specification.\n",
    )

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "40-stage" / "INVENTORY.template.md", "# INVENTORY\n")

    result = artifacts_flow.run_specification_to_stage(repo_root, "project")

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_text = stage_path.read_text(encoding="utf-8")
    assert result["ready"] == 0
    assert result["skipped"] == 1
    assert "ready_for_planning: false" in stage_text
    assert "language gate failed for canonical specification content" in stage_text


def test_specification_to_planning_requires_existing_stage_doc(
    tmp_path: Path, monkeypatch
) -> None:
    """TODO: add docstring for test_specification_to_planning_requires_existing_stage_doc."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_ready_specification(repo_root, stage="mvp")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "50-planning" / "INVENTORY.template.md", "# INVENTORY\n")
    stages_action_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    _write(
        stages_action_template_root / "epic.md",
        "epic {{epic_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "story.md",
        "story {{story_id}} {{title}}\n{{criterion_1}}\n",
    )
    _write(
        stages_action_template_root / "task.md",
        "task {{task_id}} {{title}}\n{{description}}\n{{hints}}\n",
    )
    _write(
        stages_action_template_root / "bug.md",
        "bug {{bug_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "wiki-stage-page.md",
        "# {{stage_title}}\n## Vision\n{{vision}}\n",
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )

    monkeypatch.setattr(
        artifacts_flow, "_github_project_sync", lambda _stage: ("found", "ok")
    )

    result_without_stage = artifacts_flow.run_specification_to_planning(
        repo_root, "mvp"
    )
    assert result_without_stage["created"] == 0
    assert result_without_stage["skipped"] == 1
    assert result_without_stage["scenario"] == 0
    assessment_missing_stage = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / "mvp"
        / "project-assessment.md"
    )
    assert assessment_missing_stage.exists()
    assert "scenario: cannot-start" in assessment_missing_stage.read_text(encoding="utf-8")

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "MVP.md"
    _write(
        stage_path,
        "---\nready_for_planning: true\nsource_bundles:\n  - \"2026-03-31/00000\"\n---\n# Stage\n",
    )

    result_with_stage = artifacts_flow.run_specification_to_planning(repo_root, "mvp")
    epic_path = (
        repo_root / ".digital-artifacts" / "50-planning" / "mvp" / "EPIC_THM-01.md"
    )
    story_path = (
        repo_root / ".digital-artifacts" / "50-planning" / "mvp" / "STORY_THM-01.md"
    )
    task_path = (
        repo_root / ".digital-artifacts" / "50-planning" / "mvp" / "TASK_THM-01.md"
    )
    assert result_with_stage["created"] == 1
    assert result_with_stage["scenario"] == 1
    assessment_with_stage = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / "mvp"
        / "project-assessment.md"
    )
    assert assessment_with_stage.exists()
    assessment_text = assessment_with_stage.read_text(encoding="utf-8")
    assert "scenario: startable" in assessment_text
    assert "## Stage Requirement Checklist" in assessment_text
    assert "## Input Helpfulness Score (1-5)" in assessment_text
    assert epic_path.exists()
    assert story_path.exists()
    assert task_path.exists()


def test_specification_to_planning_surfaces_stage_gate_context(
    tmp_path: Path, monkeypatch
) -> None:
    """Planning assessment should include stage gate reason and blocked bundle ids."""
    repo_root = tmp_path
    _seed_bundle(repo_root, item_code="00000")
    _seed_bundle(repo_root, item_code="00001")
    _seed_ready_specification(repo_root, stage="project", item_code="00000")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "50-planning" / "INVENTORY.template.md", "# INVENTORY\n")
    stages_action_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    _write(
        stages_action_template_root / "epic.md",
        "epic {{epic_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "story.md",
        "story {{story_id}} {{title}}\n{{criterion_1}}\n",
    )
    _write(
        stages_action_template_root / "task.md",
        "task {{task_id}} {{title}}\n{{description}}\n{{hints}}\n",
    )
    _write(
        stages_action_template_root / "bug.md",
        "bug {{bug_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "wiki-stage-page.md",
        "# {{stage_title}}\n## Vision\n{{vision}}\n",
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )
    _write(
        repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md",
        "---\n"
        "ready_for_planning: true\n"
        'gate_reason: "stage is ready for planning with quarantined blocked bundles"\n'
        "blocked_bundle_ids:\n"
        '  - "2026-03-31/00001"\n'
        "source_bundles:\n"
        '  - "2026-03-31/00000"\n'
        "---\n"
        "# Project\n",
    )

    monkeypatch.setattr(
        artifacts_flow, "_github_project_sync", lambda _stage: ("found", "ok")
    )

    result = artifacts_flow.run_specification_to_planning(repo_root, "project")

    assessment_path = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "project-assessment.md"
    )
    assessment_text = assessment_path.read_text(encoding="utf-8")
    assert result["created"] == 1
    assert "## Stage Gate Context" in assessment_text
    assert "stage is ready for planning with quarantined blocked bundles" in assessment_text
    assert "2026-03-31/00001" in assessment_text


artifacts_flow_planning = import_module("artifacts_flow_planning")
artifacts_flow_data_to_spec = import_module("artifacts_flow_data_to_spec")


def test_ensure_board_ticket_defaults_to_remote_push(tmp_path: Path, monkeypatch) -> None:
    """Board ticket creation should push refs by default to keep remote state aligned."""
    repo_root = tmp_path
    script_path = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    _write(script_path, "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(artifacts_flow_planning, "_board_ticket_exists", lambda *_a, **_k: False)

    captured_env: dict[str, str] = {}

    def _fake_run(args, cwd, *, env=None):
        del args, cwd
        if env:
            captured_env.update(env)
        return True, "created"

    monkeypatch.setattr(artifacts_flow_planning, "_run_command", _fake_run)

    ensure_board_ticket = getattr(artifacts_flow_planning, "_ensure_board_ticket")
    created, _message = ensure_board_ticket(
        repo_root,
        "project",
        "PRO-THM-01-TASK",
        "[project] Task THM-01",
        "desc",
        assigned_to="fullstack-engineer",
        sprint_id="SPRINT-PROJECT-ACTIVE",
    )

    assert created is True
    assert captured_env.get("BOARD_PUSH") == "1"
    assert captured_env.get("BOARD_NAME") == "project"
    assert captured_env.get("BOARD_STRICT_CREATE") == "1"
    assert captured_env.get("BOARD_ASSIGNED") == "fullstack-engineer"
    assert captured_env.get("BOARD_SPRINT") == "SPRINT-PROJECT-ACTIVE"
    assert captured_env.get("BOARD_ENSURE_SPRINT") == "1"


def test_ensure_board_ticket_respects_explicit_board_push_override(
    tmp_path: Path, monkeypatch
) -> None:
    """Explicit BOARD_PUSH values in the environment should remain unchanged."""
    repo_root = tmp_path
    script_path = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    _write(script_path, "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(artifacts_flow_planning, "_board_ticket_exists", lambda *_a, **_k: False)
    monkeypatch.setenv("BOARD_PUSH", "0")

    captured_env: dict[str, str] = {}

    def _fake_run(args, cwd, *, env=None):
        del args, cwd
        if env:
            captured_env.update(env)
        return True, "created"

    monkeypatch.setattr(artifacts_flow_planning, "_run_command", _fake_run)

    ensure_board_ticket = getattr(artifacts_flow_planning, "_ensure_board_ticket")
    created, _message = ensure_board_ticket(
        repo_root,
        "project",
        "PRO-THM-01-TASK",
        "[project] Task THM-01",
        "desc",
        assigned_to="fullstack-engineer",
        sprint_id="SPRINT-PROJECT-ACTIVE",
    )

    assert created is True
    assert captured_env.get("BOARD_PUSH") == "0"


def test_ensure_board_ticket_hydrates_existing_sparse_ticket(tmp_path: Path) -> None:
    """Existing sparse tickets should be enriched with planning description/AC/DoD."""
    repo_root = tmp_path
    board_yaml = repo_root / ".digital-team" / "board.yaml"
    _write(
        board_yaml,
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )

    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    board_script = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    _write(board_script, "#!/usr/bin/env bash\nexit 0\n")

    sparse_ticket = "\n".join(
        [
            "id: PRO-THM-01-TASK",
            'title: "[project] Task THM-01"',
            "description: |",
            "  Auto-seeded from /project planning flow. planning=...",
            "layer: digital-generic-team",
            "created: 2026-04-20T08:00:00Z",
            "assigned: null",
            "locked_by: null",
            "locked_at: null",
            "labels: []",
            "sprint: null",
            "",
        ]
    )
    blob_sha = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo_root,
        input=sparse_ticket,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/board/project/backlog/PRO-THM-01-TASK", blob_sha],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    ensure_board_ticket = getattr(artifacts_flow_planning, "_ensure_board_ticket")
    changed, message = ensure_board_ticket(
        repo_root,
        "project",
        "PRO-THM-01-TASK",
        "[project] Task THM-01",
        "Planning-backed description",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        definition_of_done=["PR merged", "Tests pass"],
        assigned_to="fullstack-engineer",
        sprint_id="SPRINT-PROJECT-ACTIVE",
    )

    assert changed is True
    assert message == "updated:PRO-THM-01-TASK"

    hydrated = subprocess.run(
        ["git", "cat-file", "-p", "refs/board/project/backlog/PRO-THM-01-TASK"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Planning-backed description" in hydrated
    assert "acceptance_criteria:" in hydrated
    assert "Criterion 1" in hydrated
    assert "definition_of_done:" in hydrated
    assert "PR merged" in hydrated
    assert "assigned: fullstack-engineer" in hydrated
    assert "sprint: SPRINT-PROJECT-ACTIVE" in hydrated


def test_ensure_local_board_seed_uses_autark_fallback_without_local_paths(
    tmp_path: Path, monkeypatch
) -> None:
    """Fallback payloads must be autonomous and free of absolute local paths."""
    captured: dict[str, object] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        _ticket_id,
        _title,
        description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        captured["description"] = description
        captured["acceptance_criteria"] = acceptance_criteria or []
        captured["definition_of_done"] = definition_of_done or []
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-77"),
        {},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-77-TASK" in created_ids
    description = str(captured.get("description", ""))
    assert "Auto-seeded delivery ticket." in description
    assert "/Users/" not in description
    acceptance = captured.get("acceptance_criteria", [])
    assert isinstance(acceptance, list)
    assert len(acceptance) > 0


def test_ensure_local_board_seed_derives_acceptance_from_execution_plan(
    tmp_path: Path, monkeypatch
) -> None:
    """Task payload should derive AC from Execution plan when AC section is absent."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-88.md"
    _write(
        task_path,
        "\n".join(
            [
                "# Task",
                "",
                "## Description",
                "Sample task.",
                "",
                "## Execution plan",
                "- [ ] Execute step A",
                "- [ ] Execute step B",
                "",
                "## Definition of Done",
                "- [ ] PR merged",
            ]
        ),
    )

    captured: dict[str, dict[str, list[str]]] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        _title,
        _description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        captured[ticket_id] = {
            "acceptance_criteria": list(acceptance_criteria or []),
            "definition_of_done": list(definition_of_done or []),
        }
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-88"),
        {"task": task_path},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-88-TASK" in created_ids
    acceptance = captured.get("PRO-THM-88-TASK", {}).get("acceptance_criteria", [])
    assert isinstance(acceptance, list)
    assert "Execute step A" in acceptance
    assert "Execute step B" in acceptance


def test_ensure_local_board_seed_uses_planning_frontmatter_title(
    tmp_path: Path, monkeypatch
) -> None:
    """Board ticket title should use planning frontmatter title when available."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-99.md"
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'title: "Implement contextual help command overview"',
                "---",
                "",
                "## Description",
                "Provide contextual command guidance in /help output.",
            ]
        ),
    )

    captured: dict[str, dict[str, str]] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        title,
        _description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        del acceptance_criteria, definition_of_done
        captured[ticket_id] = {"title": str(title)}
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-99"),
        {"task": task_path},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-99-TASK" in created_ids
    assert (
        captured.get("PRO-THM-99-TASK", {}).get("title")
        == "Implement contextual help command overview"
    )


def test_ensure_local_board_seed_derives_bug_title_from_related_planning_title(
    tmp_path: Path, monkeypatch
) -> None:
    """When BUG markdown is absent, bug ticket title should still be human-readable."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-42.md"
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'title: "Implement unified handoff rendering"',
                "---",
                "",
                "## Description",
                "Improve rendering of handoff payloads.",
            ]
        ),
    )

    captured: dict[str, dict[str, str]] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        title,
        _description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        del acceptance_criteria, definition_of_done
        captured[ticket_id] = {"title": str(title)}
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-42"),
        {"task": task_path},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-42-BUG" in created_ids
    assert (
        captured.get("PRO-THM-42-BUG", {}).get("title")
        == "Fix defects in Implement unified handoff rendering"
    )


def test_ensure_local_board_seed_normalizes_localized_ticket_payload(
    tmp_path: Path, monkeypatch
) -> None:
    """Localized fragments should be normalized before board ticket hydration."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-02.md"
    _write(
        task_path,
        "\n".join(
            [
                "# Task",
                "",
                "## Description",
                "Heute passiert die Bewertung oft:.",
                "",
                "## Acceptance Criteria",
                "- Heute passiert die Bewertung oft:.",
                "- zu spaet (Wartezeit auf geeignete Experten),.",
                "- zu uneinheitlich (kein durchgaengiges Gate-Format),.",
            ]
        ),
    )

    captured: dict[str, dict[str, object]] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        _title,
        description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        captured[ticket_id] = {
            "description": str(description),
            "acceptance_criteria": list(acceptance_criteria or []),
            "definition_of_done": list(definition_of_done or []),
        }
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-02"),
        {"task": task_path},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-02-TASK" in created_ids
    payload = captured["PRO-THM-02-TASK"]
    description = str(payload["description"]).lower()
    acceptance = [str(item).lower() for item in payload["acceptance_criteria"]]

    assert "heute passiert" not in description
    assert all("zu spaet" not in item for item in acceptance)
    assert all("zu uneinheitlich" not in item for item in acceptance)
    assert any("today, assessment often happens" in item for item in acceptance)
    assert any("too late" in item for item in acceptance)
    assert any("too inconsistent" in item for item in acceptance)


def test_ensure_local_board_seed_preserves_bullet_structure_after_localized_normalization(
    tmp_path: Path, monkeypatch
) -> None:
    """Localized heading/bullet sections should keep structure after normalization."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-77.md"
    _write(
        task_path,
        "\n".join(
            [
                "# Task",
                "",
                "## Description",
                "Ausgangslage:",
                "- Heute passiert die Bewertung oft:.",
                "- zu spaet (Wartezeit auf geeignete Experten),.",
                "",
                "## Acceptance Criteria",
                "- zu uneinheitlich (kein durchgaengiges Gate-Format),.",
            ]
        ),
    )

    captured: dict[str, dict[str, object]] = {}

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        _title,
        description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        captured[ticket_id] = {
            "description": str(description),
            "acceptance_criteria": list(acceptance_criteria or []),
            "definition_of_done": list(definition_of_done or []),
        }
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    status, created_ids, _details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-77"),
        {"task": task_path},
        "feature",
    )

    assert status == "seeded"
    assert "PRO-THM-77-TASK" in created_ids

    payload = captured["PRO-THM-77-TASK"]
    description = str(payload["description"])
    assert "Ausgangslage" not in description
    assert "Translated source statement (fallback normalization applied)." in description
    assert "- Today, assessment often happens:" in description
    assert "- too late (waiting time for suitable experts)." in description


def test_ensure_local_board_seed_skips_new_bug_ticket_without_bug_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    """Feature-only planning should not create a generic fallback BUG ticket."""
    task_path = tmp_path / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-55.md"
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'title: "Implement command discovery improvements"',
                "---",
                "",
                "## Description",
                "Improve command visibility and guidance.",
            ]
        ),
    )

    captured_ids: list[str] = []

    def _fake_ensure_board_ticket(
        _repo_root,
        _board_name,
        ticket_id,
        _title,
        _description,
        acceptance_criteria=None,
        definition_of_done=None,
        **_kwargs,
    ):
        del acceptance_criteria, definition_of_done
        captured_ids.append(str(ticket_id))
        return True, "created"

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_board_ticket",
        _fake_ensure_board_ticket,
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "_block_unspecified_bug_ticket",
        lambda *_args, **_kwargs: "bug-ticket-skip:not-present:PRO-THM-55-BUG",
    )

    ensure_local_board_seed = getattr(artifacts_flow_planning, "_ensure_local_board_seed")
    _status, _created_ids, details = ensure_local_board_seed(
        tmp_path,
        "project",
        "project",
        SimpleNamespace(item_code="THM-55"),
        {"task": task_path},
        "feature",
    )

    assert "PRO-THM-55-TASK" in captured_ids
    assert "PRO-THM-55-BUG" not in captured_ids
    assert any("bug-ticket-skip:not-present:PRO-THM-55-BUG" in item for item in details)


def test_block_unspecified_bug_ticket_moves_backlog_bug_and_sets_reason(
    tmp_path: Path,
) -> None:
    """Legacy generic bug tickets should be blocked with an explicit reason."""
    repo_root = tmp_path
    board_yaml = repo_root / ".digital-team" / "board.yaml"
    _write(
        board_yaml,
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )

    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    board_script = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    _write(board_script, (Path(__file__).resolve().parents[3] / "board" / "scripts" / "board-ticket.sh").read_text(encoding="utf-8"))

    sparse_bug = "\n".join(
        [
            "id: PRO-THM-66-BUG",
            'title: "[project] THM-66 Bug"',
            "description: |",
            "  Auto-seeded delivery ticket.",
            "layer: digital-generic-team",
            "created: 2026-04-21T00:00:00Z",
            "assigned: null",
            "locked_by: null",
            "locked_at: null",
            "labels: []",
            "acceptance_criteria: []",
            "definition_of_done: []",
            "sprint: null",
            "",
        ]
    )
    bug_sha = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo_root,
        input=sparse_bug,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/board/project/backlog/PRO-THM-66-BUG", bug_sha],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    block_helper = getattr(artifacts_flow_planning, "_block_unspecified_bug_ticket")
    result = block_helper(repo_root, "project", "project", "THM-66")

    assert "bug-ticket-blocked:unspecified:PRO-THM-66-BUG" == result
    ticket_ref_path = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname)",
            "refs/board/project/*/PRO-THM-66-BUG",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert ticket_ref_path
    ticket_ref = subprocess.run(
        ["git", "rev-parse", ticket_ref_path],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    updated = subprocess.run(
        ["git", "cat-file", "-p", ticket_ref],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "blocked_by:" in updated
    assert "no dedicated BUG planning artifact exists" in updated


def test_build_core_planning_artifacts_routes_meta_scope_to_fullstack() -> None:
    """Governance-heavy bundles still emit implementation-ready fullstack tasks."""
    templates = {
        "epic": "{{epic_id}} {{agent_role}}",
        "story": "{{story_id}} {{agent_role}}",
        "task": "{{task_id}}|{{title}}|{{agent_role}}\n{{description}}",
    }
    bundle = SimpleNamespace(item_code="THM-01")

    build_core = getattr(artifacts_flow_planning, "_build_core_planning_artifacts")
    rendered = build_core(
        stage="project",
        bundle=bundle,
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="Stage Governance Alignment",
        problem="The governance workflow lacks readiness checks and owner coordination.",
        scope="Standardize planning workflow and decision gates.",
        acceptance=["Readiness checks are explicit."],
        hints=["Use canonical artifacts."],
        milestone_id="MS-PROJECT-THM-01",
        sprint_hint="next",
    )

    task_text = rendered["task"]
    assert "fullstack-engineer" in task_text
    assert "Implement approved scope" in task_text
    assert "Functional requirements" in task_text
    assert "Run `make test` and `make quality`" in task_text


def test_build_core_planning_artifacts_keeps_fullstack_for_delivery_scope() -> None:
    """Implementation-heavy tasks should remain assigned to fullstack-engineer."""
    templates = {
        "epic": "{{epic_id}} {{agent_role}}",
        "story": "{{story_id}} {{agent_role}}",
        "task": "{{task_id}}|{{title}}|{{agent_role}}\n{{description}}",
    }
    bundle = SimpleNamespace(item_code="THM-02")

    build_core = getattr(artifacts_flow_planning, "_build_core_planning_artifacts")
    rendered = build_core(
        stage="mvp",
        bundle=bundle,
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="API endpoint rollout",
        problem="Add secure endpoint and integrate backend handler.",
        scope="Implement endpoint, tests, and deployment wiring.",
        acceptance=["Endpoint returns validated payload."],
        hints=["Keep existing contracts stable."],
        milestone_id="MS-MVP-THM-02",
        sprint_hint="next",
    )

    task_text = rendered["task"]
    assert "fullstack-engineer" in task_text
    assert "Implement approved scope" in task_text
    assert "Run `make test` and `make quality`" in task_text


def test_build_core_planning_artifacts_routes_ux_scope_to_ux_designer() -> None:
    """UX-heavy scope should create a ux-designer task with UX requirement contract."""
    templates = {
        "epic": "{{epic_id}} {{agent_role}}",
        "story": "{{story_id}} {{agent_role}}",
        "task": "{{task_id}}|{{title}}|{{agent_role}}\n{{description}}",
    }
    bundle = SimpleNamespace(item_code="THM-03")
    build_core = getattr(artifacts_flow_planning, "_build_core_planning_artifacts")

    rendered = build_core(
        stage="project",
        bundle=bundle,
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="UX journey redesign",
        problem="Current user experience has usability issues and inconsistent interaction design.",
        scope="Create wireframes and prototype for onboarding flow with accessibility checks.",
        acceptance=["Prototype is validated with usability walkthrough."],
        hints=["Reference current analytics baseline."],
        milestone_id="MS-PROJECT-THM-03",
        sprint_hint="next",
    )

    task_text = rendered["task"]
    assert "ux-designer" in task_text
    assert "Design validated user experience scope" in task_text
    assert "WCAG 2.2 AA" in task_text


def test_build_core_planning_artifacts_routes_user_scribble_scope_to_ux_designer() -> None:
    """User-centric discovery scope should route to ux-designer even without explicit UX acronym."""
    templates = {
        "epic": "{{epic_id}} {{agent_role}}",
        "story": "{{story_id}} {{agent_role}}",
        "task": "{{task_id}}|{{title}}|{{agent_role}}\n{{description}}",
    }
    bundle = SimpleNamespace(item_code="THM-04")
    build_core = getattr(artifacts_flow_planning, "_build_core_planning_artifacts")

    rendered = build_core(
        stage="project",
        bundle=bundle,
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="Virtual user discovery",
        problem="Input statements describe users, feedback, and open interaction questions.",
        scope="Interview a virtual user and produce scribble sketches for the journey.",
        acceptance=["Scribbles capture validated user flow assumptions."],
        hints=["Use existing user statements as input evidence."],
        milestone_id="MS-PROJECT-THM-04",
        sprint_hint="next",
    )

    task_text = rendered["task"]
    assert "ux-designer" in task_text
    assert "Design validated user experience scope" in task_text


def test_build_core_planning_artifacts_routes_help_command_scope_to_fullstack() -> None:
    """Help/command delivery scopes should generate implementable fullstack tasks."""
    templates = {
        "epic": "{{epic_id}} {{agent_role}}",
        "story": "{{story_id}} {{agent_role}}",
        "task": "{{task_id}}|{{title}}|{{agent_role}}\n{{description}}",
    }
    bundle = SimpleNamespace(item_code="THM-05")
    build_core = getattr(artifacts_flow_planning, "_build_core_planning_artifacts")

    rendered = build_core(
        stage="project",
        bundle=bundle,
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="Project User Guidance Experience",
        problem="The /help output lists commands but does not recommend the next sensible step.",
        scope="Provide context-sensitive command guidance based on stage status.",
        acceptance=[
            "Provide a complete command overview with one-line explanations.",
            "Group commands by workflow phase.",
            "Provide context-sensitive next-step guidance.",
        ],
        hints=["Reference current prompt inventory."],
        milestone_id="MS-PROJECT-THM-05",
        sprint_hint="next",
        preferred_role="ux-designer",
    )

    task_text = rendered["task"]
    assert "fullstack-engineer" in task_text
    assert "Implement approved scope" in task_text


def test_mark_handoff_done_with_evidence_updates_required_fields(tmp_path: Path) -> None:
    """Handoff completion helper should persist done status and required review evidence fields."""
    handoff = tmp_path / "task-thm-99-handoff.yaml"
    _write(
        handoff,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "status: pending",
                "task_id: TASK-THM-99",
                "receiver: fullstack-engineer",
                "",
            ]
        ),
    )

    mark_done = getattr(artifacts_flow, "_mark_handoff_done_with_evidence")
    updated = mark_done(
        handoff,
        "https://github.com/example/repo/pull/99",
        "2026-04-24T10:00:00Z",
    )

    content = handoff.read_text(encoding="utf-8")
    assert updated is True
    assert "status: done" in content
    assert "pr_url: https://github.com/example/repo/pull/99" in content
    assert "approved_by: github-review" in content
    assert "approved_at: 2026-04-24T10:00:00Z" in content


def test_find_merged_pr_for_task_accepts_approved_review_history(
    tmp_path: Path, monkeypatch
) -> None:
    """Merged PR evidence should accept explicit APPROVED review states even if reviewDecision is empty."""

    def fake_run_gh_json(_repo_root: Path, args: list[str]):
        if args[:2] == ["pr", "list"]:
            return [
                {
                    "number": 149,
                    "url": "https://github.com/example/repo/pull/149",
                    "title": "feat(project): improve delivery review visibility",
                    "mergedAt": "2026-04-24T12:59:33Z",
                    "reviewDecision": "",
                    "body": "Includes tests and coverage notes plus security checks.",
                }
            ]
        if args[:3] == ["pr", "view", "149"]:
            return {
                "reviewDecision": "",
                "reviews": [
                    {"state": "COMMENTED", "submittedAt": "2026-04-24T12:30:00Z"},
                    {"state": "APPROVED", "submittedAt": "2026-04-24T12:40:00Z"},
                ],
            }
        return None

    monkeypatch.setattr(artifacts_flow, "_run_gh_json", fake_run_gh_json)

    find_pr = getattr(artifacts_flow, "_find_merged_pr_for_task")
    evidence = find_pr(tmp_path, "TASK-THM-02")

    assert evidence is not None
    assert evidence["pr_number"] == "149"
    assert evidence["pr_url"] == "https://github.com/example/repo/pull/149"
    assert evidence["approved_at"] == "2026-04-24T12:40:00Z"


def test_find_merged_pr_for_task_searches_board_ticket_alias(
    tmp_path: Path, monkeypatch
) -> None:
    """Merged PR lookup must also match board ticket aliases like PRO-THM-01-TASK."""

    captured_search = {"value": ""}

    def fake_run_gh_json(_repo_root: Path, args: list[str]):
        if args[:2] == ["pr", "list"]:
            captured_search["value"] = args[3]
            return [
                {
                    "number": 201,
                    "url": "https://github.com/example/repo/pull/201",
                    "title": "feat(project): close PRO-THM-01-TASK",
                    "mergedAt": "2026-04-25T10:00:00Z",
                    "reviewDecision": "APPROVED",
                    "body": "Includes tests and coverage notes plus security checks.",
                }
            ]
        return None

    monkeypatch.setattr(artifacts_flow, "_run_gh_json", fake_run_gh_json)

    find_pr = getattr(artifacts_flow, "_find_merged_pr_for_task")
    evidence = find_pr(tmp_path, "TASK-THM-01")

    assert evidence is not None
    assert evidence["pr_number"] == "201"
    assert '"TASK-THM-01"' in captured_search["value"]
    assert '"PRO-THM-01-TASK"' in captured_search["value"]


def test_run_delivery_to_review_reports_auto_completion_metrics(
    tmp_path: Path, monkeypatch
) -> None:
    """Delivery review status should expose auto-completion and pending scan metrics."""
    repo_root = tmp_path
    handoff_path = (
        repo_root
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-01-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "status: pending",
                "task_id: TASK-THM-01",
                "receiver: fullstack-engineer",
                "",
            ]
        ),
    )

    monkeypatch.setattr(
        artifacts_flow,
        "_find_merged_pr_for_task",
        lambda *_args, **_kwargs: {
            "task_id": "TASK-THM-01",
            "pr_number": "149",
            "pr_url": "https://github.com/example/repo/pull/149",
            "merged_at": "2026-04-24T11:00:00Z",
            "review_decision": "APPROVED",
            "tests_evidence": "yes",
            "coverage_evidence": "yes",
            "security_evidence": "missing",
            "non_technical_summary": "missing",
        },
    )
    monkeypatch.setattr(
        artifacts_flow,
        "_move_board_ticket_to_done",
        lambda *_args, **_kwargs: (True, ""),
    )
    monkeypatch.setattr(
        artifacts_flow,
        "_move_board_ticket_to_blocked",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        artifacts_flow,
        "_sync_feedback_handoffs_to_checklists",
        lambda *_args, **_kwargs: {"handoffs_processed": 0, "artifacts_updated": 0},
    )

    result = artifacts_flow.run_delivery_to_review(repo_root, "project")

    assert result["status"] == "ready_for_done"
    assert result["auto_completed_from_merged_pr"] == 1
    assert result["blocked_after_done_gate"] == 0
    assert result["pending_after_scan"] == 0


def test_sync_handoff_artifacts_replaces_empty_list_and_deduplicates(tmp_path: Path) -> None:
    """Artifact sync should replace empty arrays and keep unique artifact references."""
    handoff = tmp_path / "task-thm-02-handoff.yaml"
    _write(
        handoff,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "status: in-progress",
                "task_id: TASK-THM-02",
                "artifacts: []",
                "",
            ]
        ),
    )

    sync_artifacts = getattr(artifacts_flow, "_sync_handoff_artifacts")
    changed = sync_artifacts(
        handoff,
        [
            ".digital-artifacts/60-review/2026-04-27/project/delivery-review-status.md",
            ".digital-artifacts/60-review/2026-04-27/project/delivery-review-status.md",
            ".digital-artifacts/50-planning/project/TASK_THM-02.md",
        ],
    )

    text = handoff.read_text(encoding="utf-8")
    assert changed is True
    assert "status: in-progress" in text
    assert "artifacts: []" not in text
    assert (
        text.count(".digital-artifacts/60-review/2026-04-27/project/delivery-review-status.md")
        == 1
    )
    assert ".digital-artifacts/50-planning/project/TASK_THM-02.md" in text


def test_run_delivery_to_review_updates_handoff_artifacts_without_done_transition(
    tmp_path: Path, monkeypatch
) -> None:
    """Delivery review should append evidence artifacts even when no merged PR exists."""
    repo_root = tmp_path
    source_doc = repo_root / ".digital-artifacts" / "50-planning" / "project" / "TASK_THM-02.md"
    _write(source_doc, "# task\n")

    handoff_path = (
        repo_root
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-02-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "status: in-progress",
                "task_id: TASK-THM-02",
                f"source_document: {source_doc.as_posix()}",
                "artifacts: []",
                "",
            ]
        ),
    )

    monkeypatch.setattr(artifacts_flow, "_find_merged_pr_for_task", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        artifacts_flow,
        "_sync_feedback_handoffs_to_checklists",
        lambda *_args, **_kwargs: {"handoffs_processed": 0, "artifacts_updated": 0},
    )

    result = artifacts_flow.run_delivery_to_review(repo_root, "project")

    handoff_text = handoff_path.read_text(encoding="utf-8")
    assert result["status"] == "awaiting_human_review"
    assert "status: in-progress" in handoff_text
    assert "delivery-review-status.md" in handoff_text
    assert source_doc.as_posix() in handoff_text


def test_build_planning_inputs_aggregates_expert_specs_and_role_hints(
    tmp_path: Path,
) -> None:
    """Planning inputs should use expert source notes and delivery-role hints when available."""
    repo_root = tmp_path
    bundle_root = _seed_bundle(repo_root, item_code="00003")
    agile_spec = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "agile-coach"
        / "00003-specification.md"
    )
    ux_spec = (
        repo_root
        / ".digital-artifacts"
        / "30-specification"
        / "2026-03-31"
        / "ux-designer"
        / "00003.ux-designer.specification.md"
    )
    _write(
        agile_spec,
        "\n".join(
            [
                "# Specification 00003",
                "",
                "## Synthesized Problem Statement",
                "- Core problem: The /help output is the primary discovery interface for available commands.",
                "",
                "## Scope",
                "- Focus on: Provide context-sensitive guidance based on the current stage status.",
                "",
                "## Acceptance Criteria",
                "- At least one thematic epic can be derived from aggregated context.",
                "- Recommendations and confidence from expert reviews are consolidated.",
                "",
            ]
        ),
    )
    _write(
        ux_spec,
        "\n".join(
            [
                "# Expert Specification 00003 — ux-designer",
                "",
                "## Expert Recommendation",
                "- assignee_hint: ux-designer",
                "",
                "## Source Notes",
                "- The /help output is the primary discovery interface for available commands.",
                "- Provide context-sensitive guidance based on the current stage status.",
                "- There is no onboarding path for first-time users.",
                "",
            ]
        ),
    )

    build_inputs = getattr(artifacts_flow_planning, "_build_planning_inputs")
    bundle = SimpleNamespace(
        item_code="00003",
        date_key="2026-03-31",
        metadata_path=bundle_root / "00003.yaml",
    )

    inputs = build_inputs(bundle, agile_spec)

    assert inputs["preferred_role"] == "ux-designer"
    assert inputs["acceptance"] == [
        "Provide context-sensitive guidance based on the current stage status.",
        "There is no onboarding path for first-time users.",
        "The /help output is the primary discovery interface for available commands.",
    ]


def test_build_bug_planning_artifact_dedupes_repeated_issue_text() -> None:
    """Bug planning output should avoid repeating the same long issue sentence."""
    build_bug = getattr(artifacts_flow_planning, "_build_bug_planning_artifact")
    bundle = SimpleNamespace(item_code="THM-03")

    repeated = (
        "The board should show in-progress state for active tasks and this is currently not reflected "
        "even though dispatch happened"
    )

    rendered = build_bug(
        stage="project",
        bundle=bundle,
        templates={
            "bug": "## Description\n\n{{description}}\n\n## Acceptance Criteria\n\n{{acceptance_criteria}}\n",
        },
        title="Project Delivery Execution",
        problem=f"- {repeated}",
        scope=f"- {repeated}",
        acceptance=[repeated, repeated],
        hints=["Keep acceptance criteria concrete."],
        milestone_id="MS-PROJECT-THM-03",
        sprint_hint="next",
    )

    assert "## Description" in rendered
    assert "- Symptom: The board should show in-progress state" in rendered
    assert "- Impact scope:" not in rendered
    assert rendered.count("Expected fix outcome") == 1
    assert rendered.count("- [ ] The board should show in-progress state") == 0
    assert "Root cause is identified and verified with regression coverage" in rendered


def test_is_ux_scope_treats_help_command_work_as_delivery_scope() -> None:
    """Help/command implementation work should not be forced into UX-only task ownership."""
    is_ux_scope = getattr(artifacts_flow_planning, "_is_ux_scope")

    result = is_ux_scope(
        "User Guidance Experience",
        "The /help output lists commands but does not recommend the next sensible step.",
        "Provide context-sensitive command guidance based on stage status.",
    )

    assert result is False


def test_enforce_implementable_scope_gate_defaults_to_project(monkeypatch) -> None:
    """Project stage enforces implementable scope by default unless explicitly disabled."""
    monkeypatch.delenv("DIGITAL_ARTIFACTS_ENFORCE_IMPLEMENTABLE_SCOPE", raising=False)
    enforce_gate = getattr(artifacts_flow_planning, "_enforce_implementable_scope_gate")

    assert enforce_gate("project") is True
    assert enforce_gate("mvp") is False


def test_enforce_implementable_scope_gate_honors_override(monkeypatch) -> None:
    """Environment flag must force gate behavior regardless of stage."""
    enforce_gate = getattr(artifacts_flow_planning, "_enforce_implementable_scope_gate")

    monkeypatch.setenv("DIGITAL_ARTIFACTS_ENFORCE_IMPLEMENTABLE_SCOPE", "0")
    assert enforce_gate("project") is False

    monkeypatch.setenv("DIGITAL_ARTIFACTS_ENFORCE_IMPLEMENTABLE_SCOPE", "1")
    assert enforce_gate("mvp") is True


def test_task_is_actionable_delivery_contract() -> None:
    """Actionable delivery detection should accept delivery roles and reject meta roles."""
    is_actionable = getattr(artifacts_flow_planning, "_task_is_actionable_delivery")

    actionable_text = """---
status: open
assignee_hint: \"fullstack-engineer\"
---
Requirement contract:
- Functional requirements: explicit behavior.
- Non-functional requirements: constraints.
- Verification requirements: tests.
Verification plan:
"""
    assert is_actionable(actionable_text) is True

    blocked_text = actionable_text.replace("status: open", "status: blocked")
    assert is_actionable(blocked_text) is False

    wrong_role_text = actionable_text.replace("fullstack-engineer", "agile-coach")
    assert is_actionable(wrong_role_text) is False

    ux_text = """---
status: open
assignee_hint: \"ux-designer\"
---
Requirement contract:
- UX outcome requirements: explicit journey.
- Accessibility requirements: WCAG 2.2 AA.
- Validation requirements: interview and scribble review.
Verification plan:
"""
    assert is_actionable(ux_text) is True


def test_specification_to_planning_records_configured_default_board(
    tmp_path: Path, monkeypatch
) -> None:
    """Planning fallback records the configured default lifecycle board in dispatch output."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_ready_specification(repo_root, stage="mvp")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "50-planning" / "INVENTORY.template.md", "# INVENTORY\n")
    stages_action_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    _write(
        stages_action_template_root / "epic.md",
        "epic {{epic_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "story.md",
        "story {{story_id}} {{title}}\n{{criterion_1}}\n",
    )
    _write(
        stages_action_template_root / "task.md",
        "task {{task_id}} {{title}}\n{{description}}\n{{hints}}\n",
    )
    _write(
        stages_action_template_root / "bug.md",
        "bug {{bug_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "wiki-stage-page.md",
        "# {{stage_title}}\n## Vision\n{{vision}}\n",
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: pilot",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    mvp:",
                "      ref_prefix: refs/board/mvp",
                "    pilot:",
                "      ref_prefix: refs/board/pilot",
            ]
        ),
    )

    monkeypatch.setattr(
        artifacts_flow,
        "_github_project_sync",
        lambda _stage: ("manual-required", "fallback to git board"),
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_local_board_seed",
        lambda *_args, **_kwargs: (
            "seeded",
            ["MVP-THM-01-EPIC", "MVP-THM-01-STORY", "MVP-THM-01-TASK"],
            ["created:project"],
        ),
    )

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "MVP.md"
    _write(
        stage_path,
        "---\nready_for_planning: true\nsource_bundles:\n  - \"2026-03-31/00000\"\n---\n# Stage\n",
    )

    result = artifacts_flow.run_specification_to_planning(repo_root, "mvp")

    assert result["board_tickets_seeded"] == 3

    dispatch_path = (
        repo_root / ".digital-artifacts" / "50-planning" / "mvp" / "DISPATCH_THM-01.md"
    )
    assert dispatch_path.exists()
    assert "- board_name: mvp" in dispatch_path.read_text(encoding="utf-8")


def test_ensure_board_seeding_skips_when_stage_board_not_configured(
    tmp_path: Path, monkeypatch
) -> None:
    """Planning should skip board seeding instead of falling back to another board namespace."""

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_is_configured_stage_board",
        lambda *_args, **_kwargs: False,
    )

    def _unexpected_seed(*_args, **_kwargs):
        raise AssertionError("_ensure_local_board_seed should not be called")

    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_local_board_seed",
        _unexpected_seed,
    )

    ensure_board_seeding = getattr(artifacts_flow_planning, "_ensure_board_seeding")
    status, tickets, details, trigger_state, seeded_count = ensure_board_seeding(
        "found",
        tmp_path,
        "project",
        "project",
        object(),
        {},
        "feature",
    )

    assert status == "skipped-stage-board-not-configured"
    assert tickets == []
    assert trigger_state == "skipped"
    assert seeded_count == 0
    assert any(entry.startswith("board-config-missing:project") for entry in details)


def test_specification_to_planning_seeds_board_even_when_primary_sync_found(
    tmp_path: Path, monkeypatch
) -> None:
    """Board refs are seeded even when GitHub project already exists."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_ready_specification(repo_root, stage="project")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "50-planning" / "INVENTORY.template.md", "# INVENTORY\n")
    stages_action_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    _write(
        stages_action_template_root / "epic.md",
        "epic {{epic_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "story.md",
        "story {{story_id}} {{title}}\n{{criterion_1}}\n",
    )
    _write(
        stages_action_template_root / "task.md",
        "task {{task_id}} {{title}}\n{{description}}\n{{hints}}\n",
    )
    _write(
        stages_action_template_root / "bug.md",
        "bug {{bug_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "wiki-stage-page.md",
        "# {{stage_title}}\n## Vision\n{{vision}}\n",
    )
    _write(
        repo_root / ".digital-team" / "board.yaml",
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
            ]
        ),
    )

    monkeypatch.setattr(
        artifacts_flow, "_github_project_sync", lambda _stage: ("found", "ok")
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_local_board_seed",
        lambda *_args, **_kwargs: (
            "seeded",
            ["PRO-THM-01-TASK"],
            ["created:project"],
        ),
    )

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    _write(
        stage_path,
        "---\nready_for_planning: true\nsource_bundles:\n  - \"2026-03-31/00000\"\n---\n# Stage\n",
    )

    result = artifacts_flow.run_specification_to_planning(repo_root, "project")
    assert result["board_tickets_seeded"] == 1

    dispatch_path = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "DISPATCH_THM-01.md"
    )
    dispatch_text = dispatch_path.read_text(encoding="utf-8")
    assert "- board_seed_status: seeded" in dispatch_text
    assert "- trigger_state: deliveries-triggered" in dispatch_text


def test_specification_to_planning_records_primary_sync_details(
    tmp_path: Path, monkeypatch
) -> None:
    """Dispatch trace should record primary-system wiki and issue sync details."""
    repo_root = tmp_path
    _seed_bundle(repo_root)
    _seed_ready_specification(repo_root, stage="project")

    template_root = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
    )
    _write(template_root / "50-planning" / "INVENTORY.template.md", "# INVENTORY\n")
    stages_action_template_root = (
        repo_root / ".github" / "skills" / "stages-action" / "templates"
    )
    _write(
        stages_action_template_root / "epic.md",
        "epic {{epic_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "story.md",
        "story {{story_id}} {{title}}\n{{criterion_1}}\n",
    )
    _write(
        stages_action_template_root / "task.md",
        "task {{task_id}} {{title}}\n{{description}}\n{{hints}}\n",
    )
    _write(
        stages_action_template_root / "bug.md",
        "bug {{bug_id}} {{title}}\n{{description}}\n{{acceptance_criteria}}\n",
    )
    _write(
        stages_action_template_root / "wiki-stage-page.md",
        "# {{stage_title}}\n## Vision\n{{vision}}\n",
    )

    monkeypatch.setattr(
        artifacts_flow,
        "_github_project_sync",
        lambda _stage: ("found", "existing project"),
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "_ensure_local_board_seed",
        lambda *_args, **_kwargs: (
            "existing",
            [],
            [
                "exists:PRO-THM-01-TASK",
            ],
        ),
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "ensure_stage_primary_assets",
        lambda repo_root, stage, stage_path: {
            "project": {
                "status": "found",
                "message": "existing project",
                "owner": "acme",
                "repo_slug": "acme/demo",
                "number": "7",
                "url": "https://github.com/orgs/acme/projects/7",
            },
            "wiki": {
                "status": "updated",
                "message": "wiki updated",
                "url": "https://github.com/acme/demo/wiki/Project",
            },
            "repo_slug": "acme/demo",
            "owner": "acme",
        },
    )
    monkeypatch.setattr(
        artifacts_flow_planning,
        "ensure_planning_issue_assets",
        lambda repo_root, stage, bundle_key, planning_paths, board_ticket_ids, primary_assets: {
            "status": "synced",
            "issues": {
                "task": {
                    "status": "updated",
                    "url": "https://github.com/acme/demo/issues/13",
                    "project_item_status": "added",
                },
            },
            "message": "issue-sync:synced",
        },
    )

    stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    _write(
        stage_path,
        "---\nready_for_planning: true\nsource_bundles:\n  - \"2026-03-31/00000\"\n---\n# Stage\n",
    )

    result = artifacts_flow.run_specification_to_planning(repo_root, "project")

    assert result["created"] == 1
    dispatch_path = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "DISPATCH_THM-01.md"
    )
    dispatch_text = dispatch_path.read_text(encoding="utf-8")
    assert "- primary-wiki-status:updated" in dispatch_text
    assert (
        "- primary-wiki-url:https://github.com/acme/demo/wiki/Project" in dispatch_text
    )
    assert "- primary-issue-task:updated:https://github.com/acme/demo/issues/13" in dispatch_text
    assert "- primary-project-item-task:added" in dispatch_text


def test_data_to_spec_filters_extraction_noise_and_keeps_meaningful_lines() -> None:
    """Synthesis should ignore extraction metadata placeholders and keep real problem content."""
    source_text = "\n".join(
        [
            "# Data Bundle 00000",
            "## Source",
            "- source_done_file: /tmp/a.md",
            "## Extraction",
            "- extraction_engine: markitdown",
            "## Content",
            "User Profile & UX",
            "Die /help-Ausgabe ist damit das einzige Discovery-Interface für verfügbare Funktionen.",
            "Kontext-sensitiver Einstieg — idealerweise Hinweis auf den aktuellen Stage-Status.",
            "It defines the exit gates that must be met.",
            "Small teams lack architecture, security, and UX expertise for structured decisions.",
            "How can virtual experts enable faster stage decisions with quality gates?",
        ]
    )

    source_note_lines = getattr(artifacts_flow_data_to_spec, "_source_note_lines")
    bundle_synthesis_lines = getattr(
        artifacts_flow_data_to_spec, "_bundle_synthesis_lines"
    )

    notes = source_note_lines(source_text, limit=6)
    assert all(line.lower() not in {"source", "extraction", "content"} for line in notes)
    assert all("User Profile & UX" not in line for line in notes)
    assert all("/help-Ausgabe" not in line for line in notes)
    assert all("Kontext-sensitiver" not in line for line in notes)
    assert all("exit gates" not in line for line in notes)
    assert any("primary discovery interface" in line for line in notes)
    assert any("Small teams" in line for line in notes)

    problem_lines, scope_items = bundle_synthesis_lines(source_text)
    assert any("Core problem" in line for line in problem_lines)
    assert all("Extraction" not in line for line in problem_lines)
    assert all("Focus on: Extraction" not in item for item in scope_items)


def test_stage_clean_markdown_lines_strips_findings_and_localized_noise() -> None:
    """Stage synthesis should remove raw finding prefixes and localized/noisy lines."""
    clean_lines = getattr(artifacts_flow_stage, "_clean_markdown_lines")

    cleaned = clean_lines(
        "\n".join(
            [
                "- Primary finding: How can the team replace missing expertise with virtual expert roles?**",
                "Secondary finding: Stakeholder Map - digital-generic-team as a self-managed virtual team.",
                "- Der primäre Zugang erfolgt über den GitHub Copilot Chat.",
                "- Focus on: Establish explicit stage governance and delivery ownership.",
            ]
        )
    )

    assert cleaned == [
        "How can the team replace missing expertise with virtual expert roles?",
        "Establish explicit stage governance and delivery ownership.",
    ]


def test_stage_document_content_builds_reader_friendly_summary_and_scope() -> None:
    """Canonical stage docs should synthesize a readable summary instead of copying raw intake phrasing."""
    stage_document_content = getattr(artifacts_flow_stage, "_stage_document_content")

    content = stage_document_content(
        "project",
        {
            "stage_id": "05",
            "description": "Enterprise Specification: Project Stage",
            "purpose": "\n".join(
                [
                    "Defines the formal state machine governing the Project layer.",
                    "",
                    "- Transform a validated exploration candidate into a registered project",
                    "- Establish project infrastructure (board, team, wiki)",
                    "- Define initial scope, ownership, and constraints",
                ]
            ),
            "requirements": "",
            "readiness": "- PROJECT.md exists\n- Board is operational",
        },
        [
            {
                "bundle": SimpleNamespace(date_key="2026-04-16", item_code="00000"),
                "spec_path": Path("spec.md"),
                "spec_text": "\n".join(
                    [
                        "# Spec",
                        "",
                        "## Synthesized Problem Statement",
                        "These questions are currently either delayed (due to lack of available expertise) or answered in an unstructured manner (because no consistent evaluation framework is used).",
                        "Ideas linger too long in raw idea status because no one is asking the right questions.",
                        "",
                        "## Acceptance Criteria",
                        "- At least one thematic epic can be derived from aggregated context.",
                        "- Blocking contradictions are either resolved or tracked with owners.",
                        "",
                        "## Scope",
                        "### In Scope",
                        "- Define the first planning-ready theme.",
                        "### Out of Scope",
                        "- Assume evidence that does not exist.",
                        "",
                        "## Constraints",
                        "- Keep downstream artifacts in English.",
                    ]
                ),
                "review_text": "## Open Questions\n- None",
            }
        ],
        [],
    )

    assert "The Project stage exists to transform a validated exploration candidate into a registered project" in content
    assert "These questions are currently either delayed" not in content
    assert "Ideas linger too long in raw idea status" not in content
    assert "## Current Context" in content
    assert "## Scope Boundaries" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content


def test_planning_theme_focus_and_milestone_fields_are_deterministic() -> None:
    """Theme focus and milestone metadata should be deterministic and non-generic."""
    entries = [
        (
            object(),
            Path("spec.md"),
            {
                "problem": "Team needs virtual expert roles for security and architecture decisions.",
                "scope": "Define stakeholder responsibilities and stage governance criteria.",
            },
        )
    ]

    derive_theme_focus = getattr(artifacts_flow_planning, "_derive_theme_focus")
    milestone_fields = getattr(artifacts_flow_planning, "_milestone_fields")

    label, summary = derive_theme_focus(entries)
    assert label in {
        "User Guidance Experience",
        "Team Operating Model",
        "Stage Governance",
        "Delivery Execution",
        "Strategic Theme",
    }
    assert summary

    milestone_id, sprint_hint = milestone_fields("project", "THM-01")
    assert milestone_id == "MS-PROJECT-THM-01"
    assert "Sprint candidate" in sprint_hint


def test_planning_theme_focus_identifies_user_guidance_experience() -> None:
    """User-help and onboarding bundles should map to a user-guidance theme."""
    derive_theme_focus = getattr(artifacts_flow_planning, "_derive_theme_focus")

    label, summary = derive_theme_focus(
        [
            (
                object(),
                Path("spec.md"),
                {
                    "title": "User Profile & UX",
                    "problem": "The /help output is the primary discovery interface for available commands.",
                    "scope": "Provide onboarding, prompt discovery, and next-step guidance for chat-first users.",
                },
            )
        ]
    )

    assert label == "User Guidance Experience"
    assert "onboarding" in summary.lower()


def test_project_scenario_classifier_distinguishes_completed_state() -> None:
    """Scenario classifier should detect cannot-start, startable, and completed states."""
    classify = getattr(artifacts_flow_planning, "_scenario_from_counts")

    assert classify(epics=0, tasks=0, tasks_done=0) == "cannot-start"
    assert classify(epics=1, tasks=1, tasks_done=0) == "startable"
    assert classify(epics=1, tasks=2, tasks_done=2) == "completed"


def test_assessment_questions_and_suggestions_are_english() -> None:
    """Assessment helper text should stay English-only for deterministic downstream consumption."""
    questions_fn = getattr(artifacts_flow_planning, "_improvement_questions_for_gaps")
    suggestions_fn = getattr(artifacts_flow_planning, "_feature_suggestions")

    questions = questions_fn(
        [
            "required_inputs",
            "problem_clarity",
            "scope_clarity",
            "task_formulability",
            "constraints_clarity",
            "owner_clarity",
        ],
        1,
    )
    suggestions = suggestions_fn(["User Guidance Experience"])

    joined_questions = "\n".join(questions)
    joined_suggestions = "\n".join(suggestions)

    assert "Frage:" not in joined_questions
    assert "Beispiel:" not in joined_questions
    assert "Kontextsensitiver" not in joined_suggestions
    assert "Question:" in joined_questions
    assert "Example:" in joined_questions


def test_assessment_filename_contract_is_stable() -> None:
    """Assessment artifact filename contract should remain explicit and stable."""
    assert getattr(artifacts_flow_planning, "PROJECT_ASSESSMENT_FILENAME") == "project-assessment.md"


def test_agent_review_markdown_contains_dynamic_scenario_and_mapping_sections(
    tmp_path: Path,
) -> None:
    """Agent review output should include scenario classification and mapping contract."""
    render = getattr(artifacts_flow_data_to_spec, "_agent_review_markdown")
    bundle = SimpleNamespace(item_code="00077", date_key="2026-04-16")
    template = (
        "status: pending\n"
        "- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n"
        "- confidence_score: 1-5\n"
        "- one_line_rationale: \"\"\n"
        "bundle_ids: []\n"
        "| Problem clarity | | |\n"
        "| Scope clarity | | |\n"
        "| Constraint clarity | | |\n"
        "| Stakeholder clarity | | |\n"
        "| Delivery readiness | | |\n"
        "| Risk clarity | | |\n"
        "| Problem statement | [ ] | |\n"
        "| Stakeholders | [ ] | |\n"
        "| Constraints | [ ] | |\n"
        "| Success criteria | [ ] | |\n"
        "- Spec file: (path or \"none\")\n"
        "- Coverage assessment: incomplete / partial / sufficient\n"
    )

    output = render(
        template,
        stage="project",
        agent="ux-designer",
        bundle=bundle,
        score=4,
        recommendation="proceed",
        applicability="relevant",
        request_path=tmp_path / "req.yaml",
        response_path=tmp_path / "resp.yaml",
        agent_spec_path=tmp_path / "spec.md",
    )

    assert "## Scenario Classification" in output
    assert "- scenario: startable" in output
    assert "## Story/Task Mapping (Expert -> Agile Coach)" in output
    assert "- can_formulate_story: yes" in output
    assert "## Dynamic Output (Scenario-specific)" in output


def test_cumulated_review_markdown_contains_dynamic_scenario_section() -> None:
    """Cumulated review output should include scenario classification and dynamic output block."""
    render = getattr(artifacts_flow_data_to_spec, "_cumulated_review_markdown")
    template = (
        "{{stage}}\n"
        "{{date}}\n"
        "agent_reviews: []\n"
        "readiness: pending\n"
        "| Problem clarity | | | |\n"
        "| Scope clarity | | | |\n"
        "| Constraint clarity | | | |\n"
        "| Stakeholder clarity | | | |\n"
        "| Delivery readiness | | | |\n"
        "| Risk clarity | | | |\n"
        "- recommendation: proceed / proceed-with-conditions / stop-and-clarify\n"
        "- confidence_score: 1-5\n"
    )

    output = render(
        template,
        stage="project",
        agent_rows=[
            {
                "agent": "ux-designer",
                "score": 4,
                "recommendation": "proceed",
                "finding": "ux-designer assessed relevant",
            }
        ],
    )

    assert "## Scenario Classification" in output
    assert "- scenario: startable" in output
    assert "## Dynamic Output (Scenario-specific)" in output


def test_run_planning_to_delivery_emits_status_report(tmp_path: Path) -> None:
    """Planning->delivery emits handoff artifacts and a status report for ready tasks."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-99.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-99"',
                'title: "Implement help guidance"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["status"] == "ok"
    assert result["ready"] == 1
    assert result["triggered"] == 1
    report_path = Path(result["status_report_path"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Delivery Automation Status (project)" in report_text
    assert "TASK-THM-99" in report_text
    # Handoff artifact must exist under runtime dispatch artifacts
    handoff_dir = tmp_path / ".digital-runtime" / "handoffs" / "project"
    assert handoff_dir.exists()
    handoff_files = list(handoff_dir.glob("*-handoff.yaml"))
    assert len(handoff_files) == 1
    handoff_text = handoff_files[0].read_text(encoding="utf-8")
    assert "work_handoff_v1" in handoff_text
    assert "fullstack-engineer" in handoff_text


def test_run_planning_to_delivery_moves_board_ticket_with_stage_board_env(
    tmp_path: Path, monkeypatch
) -> None:
    """Dispatch should move board tickets on the stage board and push refs."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-01.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-01"',
                'title: "Implement project flow"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    board_script = (
        tmp_path / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    )
    _write(board_script, "#!/usr/bin/env bash\nexit 0\n")

    captured: dict[str, object] = {}

    seen_args: list[list[str]] = []

    def _fake_run(args, cwd=None, env=None, capture_output=None, check=None, timeout=None, text=None):
        del cwd, capture_output, check, timeout, text
        captured["args"] = args
        captured["env"] = env or {}
        seen_args.append(args)
        if len(args) >= 3 and args[2] == "move":
            captured["last_move_args"] = args
            captured["last_move_env"] = env or {}

        class _Completed:
            returncode = 1

        # First attempt with TASK-* should fail; second mapped PRO-* should pass.
        if args[3] == "PRO-THM-01-TASK":
            _Completed.returncode = 0

        return _Completed()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["status"] == "ok"
    assert seen_args[0] == [
        "bash",
        str(board_script),
        "move",
        "TASK-THM-01",
        "backlog",
        "in-progress",
    ]
    assert captured["last_move_args"] == [
        "bash",
        str(board_script),
        "move",
        "PRO-THM-01-TASK",
        "backlog",
        "in-progress",
    ]
    env = captured["last_move_env"]
    assert isinstance(env, dict)
    assert env.get("BOARD_NAME") == "project"
    assert env.get("BOARD_PUSH") == "1"


def test_run_planning_to_delivery_skips_already_done_handoff(tmp_path: Path) -> None:
    """Existing handoff files marked done should not be re-dispatched."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-01.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-01"',
                'title: "Implement project flow"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-01-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "receiver: fullstack-engineer",
                "status: done",
                "pr_url: https://github.com/example/repo/pull/123",
                "approved_by: reviewer-login",
                "approved_at: 2026-04-22T10:00:00Z",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["ready"] == 1
    assert result["triggered"] == 0
    assert result["already_done_handoffs"] == 1
    assert result["status"] == "already_dispatched"
    assert "status: done" in handoff_path.read_text(encoding="utf-8")


def test_run_planning_to_delivery_reopens_unverified_done_handoff(
    tmp_path: Path,
) -> None:
    """Done handoffs without PR/reviewer evidence must be reopened and re-dispatched."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-01.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-01"',
                'title: "Implement project flow"',
                "status: done",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-01-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "receiver: fullstack-engineer",
                "status: done",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 1
    assert result["already_done_handoffs"] == 0
    assert result["status_updates"] >= 1
    task_text = task_path.read_text(encoding="utf-8")
    assert "status: in-progress" in task_text


def test_run_planning_to_delivery_keeps_existing_handoff_active_without_redispatch(
    tmp_path: Path,
) -> None:
    """Existing unfinished handoffs must stay active and must not be re-dispatched."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-03.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-03"',
                'title: "Implement active delivery flow"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-03-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "receiver: fullstack-engineer",
                "intent: deliver task",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 0
    assert result["already_dispatched_handoffs"] == 1
    assert result["status"] == "already_dispatched"
    assert "status: in-progress" in handoff_path.read_text(encoding="utf-8")
    assert "status: in-progress" in task_path.read_text(encoding="utf-8")


def test_run_delivery_to_review_emits_status_report(tmp_path: Path) -> None:
    """Delivery->review should report awaiting_human_review without feedback evidence."""
    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-01-handoff.yaml"
    )
    _write(handoff_path, "schema: work_handoff_v1\n")

    result = artifacts_flow.run_delivery_to_review(tmp_path, "project")

    assert result["status"] == "awaiting_human_review"
    assert result["detected_handoffs"] == 1
    report_path = Path(result["status_report_path"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Delivery Review Aggregation Status (project)" in report_text
    assert "status: awaiting_human_review" in report_text
    assert "## Human Review Gate" in report_text
    assert "| PR created | yes | no |" in report_text
    assert "Create PRs for the active delivery handoffs before review can proceed." in report_text
    assert "task-thm-01-handoff.yaml" in report_text


def test_run_delivery_to_review_reports_recovery_and_gate_evidence(tmp_path: Path) -> None:
    """Delivery->review should expose PR evidence and recovery guidance for missing sources."""
    recoverable_source = (
        tmp_path
        / ".digital-artifacts"
        / "20-done"
        / "feature"
        / "2026-04-24"
        / "00000__TASK_THM-02.md"
    )
    _write(recoverable_source, "# recovered source\n")

    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-02-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-02",
                f"source_document: {tmp_path / '.digital-artifacts' / '50-planning' / 'project' / 'TASK_THM-02.md'}",
                "pr_url: https://github.com/example/repo/pull/124",
                "approved_by: reviewer1",
                "approved_at: 2026-04-24T13:00:00Z",
                "quality_gate_passed: true",
            ]
        )
        + "\n",
    )

    result = artifacts_flow.run_delivery_to_review(tmp_path, "project")

    assert result["status"] == "awaiting_human_review"
    report_path = Path(result["status_report_path"])
    report_text = report_path.read_text(encoding="utf-8")
    assert "| PR created | yes | yes |" in report_text
    assert "| PR approved by human | yes | yes |" in report_text
    assert "| PR merged to main | yes | no |" in report_text
    assert "| Quality gate passed | yes | yes |" in report_text
    assert "| Approval evidence recorded | yes | yes |" in report_text
    assert "TASK_THM-02.md | partially recoverable | .digital-artifacts/20-done/feature/2026-04-24/00000__TASK_THM-02.md" in report_text
    assert "TASK-THM-02 delivery PR" in report_text
    assert "Merge approved PRs to main before reconciling board tickets." in report_text


def test_run_delivery_to_review_blocks_review_request_when_quality_fails(tmp_path: Path) -> None:
    """Quality-gate failures should keep PRs blocked and avoid review-request guidance."""
    handoff_path = (
        tmp_path
        / ".digital-runtime"
        / "handoffs"
        / "project"
        / "task-thm-05-handoff.yaml"
    )
    _write(
        handoff_path,
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-05",
                "source_document: .digital-artifacts/50-planning/project/TASK_THM-05.md",
                "pr_url: https://github.com/example/repo/pull/205",
                "quality_gate_passed: false",
            ]
        )
        + "\n",
    )

    result = artifacts_flow.run_delivery_to_review(tmp_path, "project")

    assert result["status"] == "awaiting_human_review"
    report_path = Path(result["status_report_path"])
    report_text = report_path.read_text(encoding="utf-8")
    assert "## Open PRs Ready For Human Review" in report_text
    assert "## Open PRs Blocked By Quality Gate" in report_text
    assert "TASK-THM-05 delivery PR — https://github.com/example/repo/pull/205" in report_text
    assert "Keep PRs in draft and apply blocked:quality-gate until make test and make quality pass; do not request human review yet." in report_text
    assert "Request human review approval and record reviewer identity plus approval timestamp in the handoff or review artifact." not in report_text


# ---------------------------------------------------------------------------
# New tests: BUG dispatch, blocked drain, quality-expert, unassigned handling
# ---------------------------------------------------------------------------


def _make_board_script(tmp_path: Path, returncode: int = 0) -> Path:
    """Create a stub board-ticket.sh that returns the given exit code."""
    board_script = (
        tmp_path / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    )
    _write(board_script, f"#!/usr/bin/env bash\nexit {returncode}\n")
    return board_script


def test_run_planning_to_delivery_bug_creates_bug_prefixed_handoff(
    tmp_path: Path,
) -> None:
    """BUG planning artifacts must produce a 'bug-*-handoff.yaml' file."""
    bug_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "BUG_THM-01.md"
    )
    _write(
        bug_path,
        "\n".join(
            [
                "---",
                'bug_id: "BUG-THM-01"',
                'title: "Fix null pointer in flow"',
                "status: open",
                'assignee_hint: "quality-expert"',
                "---",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["ready"] == 1
    assert result["triggered"] == 1
    handoff_dir = tmp_path / ".digital-runtime" / "handoffs" / "project"
    handoff_files = list(handoff_dir.glob("bug-*-handoff.yaml"))
    assert len(handoff_files) == 1, f"Expected 1 bug handoff, found: {list(handoff_dir.iterdir())}"
    handoff_text = handoff_files[0].read_text(encoding="utf-8")
    assert "work_handoff_v1" in handoff_text
    assert "quality-expert" in handoff_text


def test_run_planning_to_delivery_quality_expert_is_dispatched(
    tmp_path: Path,
) -> None:
    """quality-expert assignee_hint must be included in the ready set and dispatched."""
    bug_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "BUG_THM-02.md"
    )
    _write(
        bug_path,
        "\n".join(
            [
                "---",
                'bug_id: "BUG-THM-02"',
                'title: "Coverage gap in module X"',
                "status: open",
                'assignee_hint: "quality-expert"',
                "---",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["ready"] >= 1
    assert result["triggered"] >= 1


def test_run_planning_to_delivery_blocked_item_moves_board_and_prints(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """An artifact with status: blocked must move its ticket to the blocked lane
    and print a [BLOCKED] message to stdout."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-07.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-07"',
                'title: "Blocked delivery task"',
                "status: blocked",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    seen_args: list[list[str]] = []

    def _fake_run(args, **kwargs):
        del kwargs
        seen_args.append(args)

        class _Completed:
            returncode = 0

        return _Completed()

    _make_board_script(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 0
    assert result["blocked"] >= 1

    # Board call must target the blocked lane
    blocked_calls = [a for a in seen_args if "blocked" in a]
    assert blocked_calls, f"No 'blocked' board call found in {seen_args}"

    # Console output must contain [BLOCKED] marker
    captured = capsys.readouterr()
    assert "[BLOCKED]" in captured.out
    assert "TASK-THM-07" in captured.out or "PRO-THM-07" in captured.out


def test_run_planning_to_delivery_unassigned_item_is_blocked_with_explanation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """An open artifact with an unknown assignee_hint must be moved to blocked
    and print a [BLOCKED] explanation naming the unrecognized assignee."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-08.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-08"',
                'title: "Task with unknown assignee"',
                "status: open",
                'assignee_hint: "some-unknown-role"',
                "---",
            ]
        ),
    )

    seen_args: list[list[str]] = []

    def _fake_run(args, **kwargs):
        del kwargs
        seen_args.append(args)

        class _Completed:
            returncode = 0

        return _Completed()

    _make_board_script(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 0
    assert result["blocked"] >= 1

    captured = capsys.readouterr()
    assert "[BLOCKED]" in captured.out
    assert "some-unknown-role" in captured.out


def test_run_planning_to_delivery_blocks_invalid_for_delivery_generic_title(
    tmp_path: Path,
) -> None:
    """Generic planning titles are marked invalid-for-delivery and blocked."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-10.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-10"',
                'title: "Task THM-10"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 0
    assert result["invalid_for_delivery"] == 1
    assert result["blocked"] >= 1
    report_text = Path(result["status_report_path"]).read_text(encoding="utf-8")
    assert "invalid-for-delivery" in report_text
    assert "generic-title" in report_text


def test_run_planning_to_delivery_reports_board_sync_conflict_when_move_fails(
    tmp_path: Path, monkeypatch
) -> None:
    """Failed in-progress transition must be visible in result counters and report."""
    task_path = (
        tmp_path
        / ".digital-artifacts"
        / "50-planning"
        / "project"
        / "TASK_THM-11.md"
    )
    _write(
        task_path,
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-11"',
                'title: "Implement targeted fix"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    _make_board_script(tmp_path)

    def _always_fail(args, **kwargs):
        del args, kwargs

        class _Completed:
            returncode = 1

        return _Completed()

    monkeypatch.setattr(subprocess, "run", _always_fail)

    result = artifacts_flow.run_planning_to_delivery(tmp_path, "project")

    assert result["triggered"] == 1
    assert result["board_sync_conflicts"] == 1
    assert result["board_refresh_ok"] == 0
    report_text = Path(result["status_report_path"]).read_text(encoding="utf-8")
    assert "board_sync_conflicts: 1" in report_text
    assert "board-refresh: fetch --all failed" in report_text


def test_task_metadata_reads_bug_id_fallback(tmp_path: Path) -> None:
    """_task_metadata must extract the id from bug_id: when task_id: is absent."""
    bug_file = tmp_path / "BUG_THM-03.md"
    _write(
        bug_file,
        "\n".join(
            [
                "---",
                'bug_id: "BUG-THM-03"',
                'title: "Regression in parser"',
                "status: open",
                'assignee_hint: "quality-expert"',
                "---",
            ]
        ),
    )

    meta = artifacts_flow._task_metadata(bug_file)  # type: ignore[attr-defined]

    assert meta["task_id"] == "BUG-THM-03"
    assert meta["title"] == "Regression in parser"
    assert meta["assignee"] == "quality-expert"


def test_planning_bug_metadata_returns_entries_for_bug_files(tmp_path: Path) -> None:
    """_planning_bug_metadata must glob BUG_*.md and return one entry per file."""
    planning_dir = tmp_path / ".digital-artifacts" / "50-planning" / "project"
    planning_dir.mkdir(parents=True)
    for i in range(3):
        _write(
            planning_dir / f"BUG_THM-{i}.md",
            "\n".join(
                [
                    "---",
                    f'bug_id: "BUG-THM-{i}"',
                    f'title: "Bug {i}"',
                    "status: open",
                    'assignee_hint: "quality-expert"',
                    "---",
                ]
            ),
        )
    # A TASK file must not be returned
    _write(
        planning_dir / "TASK_THM-99.md",
        "\n".join(
            [
                "---",
                'task_id: "TASK-THM-99"',
                "status: open",
                'assignee_hint: "fullstack-engineer"',
                "---",
            ]
        ),
    )

    result = artifacts_flow._planning_bug_metadata(tmp_path, "project")  # type: ignore[attr-defined]

    assert len(result) == 3
    ids = {entry["task_id"] for entry in result}
    assert "TASK-THM-99" not in ids


def test_planning_bug_metadata_empty_for_missing_directory(tmp_path: Path) -> None:
    """_planning_bug_metadata must return [] when the planning directory is absent."""
    result = artifacts_flow._planning_bug_metadata(tmp_path, "nonexistent-stage")  # type: ignore[attr-defined]
    assert result == []


def test_move_board_ticket_to_blocked_calls_correct_args(
    tmp_path: Path, monkeypatch
) -> None:
    """_move_board_ticket_to_blocked must call board-ticket.sh move <id> backlog blocked."""
    _make_board_script(tmp_path)

    seen_args: list[list[str]] = []

    def _fake_run(args, **kwargs):
        del kwargs
        seen_args.append(list(args))

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    ok = artifacts_flow._move_board_ticket_to_blocked(tmp_path, "project", "TASK-THM-05")  # type: ignore[attr-defined]

    assert ok is True
    # At least one call must use the blocked lane
    assert any("blocked" in a for a in seen_args), f"No blocked-lane call in {seen_args}"
    # The move sub-command must be present
    assert any("move" in a for a in seen_args)


# ---------------------------------------------------------------------------
# restore_inputs_from_done
# ---------------------------------------------------------------------------


def test_restore_inputs_from_done_restores_document(tmp_path: Path) -> None:
    """Files from 20-done/ are copied to 00-input/documents/."""
    done_file = tmp_path / ".digital-artifacts" / "20-done" / "document" / "2026-04-24" / "00000__01-problem-statement.md"
    done_file.parent.mkdir(parents=True, exist_ok=True)
    done_file.write_text("# Problem Statement\n\nSome content.", encoding="utf-8")

    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    assert result["restored"] == 1
    assert result["skipped_existing"] == 0
    assert result["skipped_inventory"] == 0

    restored_file = tmp_path / ".digital-artifacts" / "00-input" / "documents" / "01-problem-statement.md"
    assert restored_file.exists()
    assert "Problem Statement" in restored_file.read_text(encoding="utf-8")


def test_restore_inputs_from_done_skips_existing(tmp_path: Path) -> None:
    """Files already present in 00-input/documents/ are not overwritten."""
    done_file = tmp_path / ".digital-artifacts" / "20-done" / "file.md"
    done_file.parent.mkdir(parents=True, exist_ok=True)
    done_file.write_text("# Done version", encoding="utf-8")

    existing_file = tmp_path / ".digital-artifacts" / "00-input" / "documents" / "file.md"
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text("# Existing version", encoding="utf-8")

    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    assert result["skipped_existing"] == 1
    assert result["restored"] == 0
    assert existing_file.read_text(encoding="utf-8") == "# Existing version"


def test_restore_inputs_from_done_skips_inventory(tmp_path: Path) -> None:
    """INVENTORY.md files in 20-done/ are excluded."""
    inventory = tmp_path / ".digital-artifacts" / "20-done" / "INVENTORY.md"
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text("# Inventory", encoding="utf-8")

    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    assert result["skipped_inventory"] == 1
    assert result["restored"] == 0
    assert not (tmp_path / ".digital-artifacts" / "00-input" / "documents" / "INVENTORY.md").exists()


def test_restore_inputs_from_done_empty_done_dir(tmp_path: Path) -> None:
    """When 20-done/ does not exist, zero counts are returned and no error raised."""
    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    assert result == {"restored": 0, "skipped_existing": 0, "skipped_inventory": 0}


def test_restore_inputs_from_done_strips_numeric_prefix_levels(tmp_path: Path) -> None:
    """Repeated numeric prefixes are stripped from filename."""
    done_file = tmp_path / ".digital-artifacts" / "20-done" / "00001__00002__context.md"
    done_file.parent.mkdir(parents=True, exist_ok=True)
    done_file.write_text("# Context", encoding="utf-8")

    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    assert result["restored"] == 1
    clean = tmp_path / ".digital-artifacts" / "00-input" / "documents" / "context.md"
    assert clean.exists()


def test_restore_inputs_from_done_creates_input_dir_when_missing(tmp_path: Path) -> None:
    """00-input/documents/ is created if it does not exist."""
    done_file = tmp_path / ".digital-artifacts" / "20-done" / "note.md"
    done_file.parent.mkdir(parents=True, exist_ok=True)
    done_file.write_text("# Note", encoding="utf-8")

    result = artifacts_flow.restore_inputs_from_done(tmp_path)  # type: ignore[attr-defined]

    input_dir = tmp_path / ".digital-artifacts" / "00-input" / "documents"
    assert input_dir.is_dir()
    assert result["restored"] == 1
