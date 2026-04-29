#!/usr/bin/env python3
"""
Unit tests for delivery_evidence_tracker module.

Tests cover:
- Handoff loading and status updates
- Delivery evidence artifact generation
- Review checkpoint creation
- Artifact recovery verification
- Approval evidence recording
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from delivery_evidence_tracker import (
    DeliveryEvidenceTracker,
    HandoffEvidence,
)


@pytest.fixture
def temp_repo():
    """Create temporary repo structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        artifacts_root = repo_root / ".digital-artifacts"
        artifacts_root.mkdir()

        # Create subdirectories
        (artifacts_root / "50-planning" / "project").mkdir(parents=True)
        (artifacts_root / "60-review").mkdir(parents=True)
        (repo_root / ".digital-runtime" / "handoffs" / "project").mkdir(
            parents=True
        )

        yield repo_root


@pytest.fixture
def tracker(temp_repo):
    """Create tracker instance with temporary repo."""
    return DeliveryEvidenceTracker(temp_repo)


class TestHandoffEvidence:
    """Tests for HandoffEvidence dataclass."""

    def test_handoff_evidence_creation(self):
        """Test creating handoff evidence record."""
        evidence = HandoffEvidence(
            task_id="TASK-001",
            stage="project",
            receiver="fullstack-engineer",
            status="in-progress",
            created_at="2026-04-27T09:00:00Z",
        )

        assert evidence.task_id == "TASK-001"
        assert evidence.stage == "project"
        assert evidence.receiver == "fullstack-engineer"
        assert evidence.status == "in-progress"

    def test_handoff_evidence_to_dict(self):
        """Test converting evidence to dict."""
        evidence = HandoffEvidence(
            task_id="TASK-001",
            stage="project",
            receiver="fullstack-engineer",
            status="in-progress",
            created_at="2026-04-27T09:00:00Z",
            tests_passed=True,
        )

        d = evidence.to_dict()
        assert d["task_id"] == "TASK-001"
        assert d["tests_passed"] is True
        assert "pr_url" not in d  # None values excluded


class TestDeliveryEvidenceTracker:
    """Tests for DeliveryEvidenceTracker."""

    def test_tracker_initialization(self, temp_repo):
        """Test tracker initialization."""
        tracker = DeliveryEvidenceTracker(temp_repo)
        assert tracker.repo_root == temp_repo
        assert tracker.artifacts_root == temp_repo / ".digital-artifacts"

    def test_initialize_stage_review(self, tracker):
        """Test initializing stage review directory."""
        review_dir = tracker.initialize_stage_review("project", "2026-04-27")
        assert review_dir.exists()
        assert "project" in str(review_dir)
        assert "2026-04-27" in str(review_dir)

    def test_load_handoff_not_found(self, tracker):
        """Test loading nonexistent handoff."""
        result = tracker.load_handoff(Path("/nonexistent/handoff.yaml"))
        assert result is None

    def test_load_handoff_success(self, tracker, temp_repo):
        """Test successfully loading handoff."""
        handoff_path = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task.yaml"
        )
        handoff_path.parent.mkdir(parents=True, exist_ok=True)

        handoff_data = {
            "schema": "work_handoff_v1",
            "status": "dispatched",
            "task_id": "TASK-001",
        }

        with open(handoff_path, "w", encoding="utf-8") as f:
            yaml.dump(handoff_data, f)

        result = tracker.load_handoff(handoff_path)
        assert result is not None
        assert result["task_id"] == "TASK-001"

    def test_update_handoff_status(self, tracker, temp_repo):
        """Test updating handoff status."""
        handoff_path = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task.yaml"
        )
        handoff_path.parent.mkdir(parents=True, exist_ok=True)

        handoff_data = {"schema": "work_handoff_v1", "status": "dispatched"}
        with open(handoff_path, "w", encoding="utf-8") as f:
            yaml.dump(handoff_data, f)

        success = tracker.update_handoff_status(
            handoff_path, "in-progress", {"pr_url": "https://github.com/..."}
        )

        assert success is True

        # Verify update
        updated = tracker.load_handoff(handoff_path)
        assert updated["status"] == "in-progress"
        assert updated["pr_url"] == "https://github.com/..."

    def test_create_delivery_evidence_artifact(self, tracker):
        """Test creating delivery evidence artifact."""
        evidence = HandoffEvidence(
            task_id="TASK-001",
            stage="project",
            receiver="fullstack-engineer",
            status="review",
            created_at="2026-04-27T09:00:00Z",
            pr_url="https://github.com/...",
            tests_passed=True,
            quality_passed=True,
            coverage_percent=85.5,
        )

        artifact_path = tracker.create_delivery_evidence_artifact(evidence, "project")
        assert artifact_path.exists()

        # Verify content
        with open(artifact_path, encoding="utf-8") as f:
            content = f.read()
        assert "TASK-001" in content
        assert "85.5%" in content

    def test_create_review_checkpoint(self, tracker):
        """Test creating review checkpoint."""
        tasks = [
            {
                "task_id": "TASK-001",
                "status": "in-progress",
                "receiver": "fullstack-engineer",
            },
            {
                "task_id": "TASK-002",
                "status": "done",
                "receiver": "fullstack-engineer",
            },
        ]

        checkpoint_path = tracker.create_review_checkpoint("project", tasks)
        assert checkpoint_path.exists()

        with open(checkpoint_path, encoding="utf-8") as f:
            content = f.read()
        assert "Delivery Review Checkpoint" in content
        assert "TASK-001" in content
        assert "TASK-002" in content

    def test_verify_artifact_recovery(self, tracker, temp_repo):
        """Test artifact recovery verification."""
        planning_dir = temp_repo / ".digital-artifacts" / "50-planning" / "project"

        # Create a planning artifact
        (planning_dir / "TASK-001.md").write_text("# Task")

        recovery_status = tracker.verify_artifact_recovery(
            "project", ["TASK-001", "TASK-002"]
        )

        assert recovery_status["TASK-001"] == "found"
        assert recovery_status["TASK-002"] == "not_found"

    def test_record_approval_evidence(self, tracker):
        """Test recording approval evidence."""
        approval = tracker.record_approval_evidence(
            task_id="TASK-001",
            approver="reviewer@example.com",
            pr_url="https://github.com/.../pull/123",
            notes="Approved after verification",
        )

        assert approval["task_id"] == "TASK-001"
        assert approval["approver"] == "reviewer@example.com"
        assert approval["notes"] == "Approved after verification"

    def test_generate_recovery_report(self, tracker, temp_repo):
        """Test generating recovery report."""
        planning_dir = temp_repo / ".digital-artifacts" / "50-planning" / "project"
        handoff_dir = temp_repo / ".digital-runtime" / "handoffs" / "project"

        # Create artifacts and handoffs
        (planning_dir / "TASK-001.md").write_text("# Task")
        (handoff_dir / "task-001-handoff.yaml").write_text("schema: work_handoff_v1")

        report_path = tracker.generate_recovery_report("project")
        assert report_path.exists()

        with open(report_path, encoding="utf-8") as f:
            content = f.read()
        assert "Artifact Recovery Report" in content
        assert "Ready for rerun" in content


class TestDeliveryEvidenceIntegration:
    """Integration tests for full delivery evidence workflow."""

    def test_full_delivery_workflow(self, tracker, temp_repo):
        """Test complete delivery evidence workflow."""
        # 1. Initialize review
        review_dir = tracker.initialize_stage_review("project")
        assert review_dir.exists()

        # 2. Create evidence artifact
        evidence = HandoffEvidence(
            task_id="TASK-THM-01",
            stage="project",
            receiver="fullstack-engineer",
            status="review",
            created_at="2026-04-27T09:00:00Z",
            pr_url="https://github.com/user/repo/pull/1",
            tests_passed=True,
            quality_passed=True,
            coverage_percent=82.0,
            artifacts=[
                ".digital-artifacts/50-planning/project/TASK_THM-01.md",
                ".digital-artifacts/60-review/2026-04-27/project/delivery-evidence-TASK-THM-01.md",
            ],
        )

        artifact_path = tracker.create_delivery_evidence_artifact(evidence, "project")
        assert artifact_path.exists()

        # 3. Record approval
        approval = tracker.record_approval_evidence(
            task_id="TASK-THM-01",
            approver="reviewer@example.com",
            pr_url="https://github.com/user/repo/pull/1",
            notes="Quality and tests verified",
        )

        assert approval["approver"] == "reviewer@example.com"

        # 4. Generate recovery report
        report_path = tracker.generate_recovery_report("project")
        assert report_path.exists()
