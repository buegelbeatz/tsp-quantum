#!/usr/bin/env python3
"""
Unit tests for Delivery Quality Gates & Security Controls

Tests for approval gates, human review requirements, and security audit trail.
"""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from delivery_quality_gates import (
    DeliveryQualityGates,
    ApprovalGate,
    SecurityAuditEntry,
)


@pytest.fixture
def temp_repo():
    """Create temporary repository structure."""
    with TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".digital-artifacts" / "60-review" / "2026-04-27" / "project").mkdir(
            parents=True
        )
        (repo_root / ".digital-runtime" / "handoffs" / "project").mkdir(parents=True)
        yield repo_root


@pytest.fixture
def quality_gates(temp_repo):
    """Create quality gates instance."""
    return DeliveryQualityGates(temp_repo)


class TestApprovalGate:
    """Test ApprovalGate dataclass."""

    def test_approval_gate_creation(self):
        """Test creating an approval gate."""
        gate = ApprovalGate(
            gate_name="pr_approval",
            description="PR must be approved",
            required=True,
            status="pending",
        )
        assert gate.gate_name == "pr_approval"
        assert gate.required is True
        assert gate.status == "pending"

    def test_approval_gate_passed(self):
        """Test marking gate as passed."""
        gate = ApprovalGate(
            gate_name="test_coverage",
            description="Coverage >= 80%",
            required=True,
            status="passed",
            checked_by="system",
        )
        assert gate.status == "passed"
        assert gate.checked_by == "system"


class TestSecurityAuditEntry:
    """Test SecurityAuditEntry dataclass."""

    def test_audit_entry_creation(self):
        """Test creating an audit entry."""
        entry = SecurityAuditEntry(
            event_id="TASK-001_pr_opened_1234567890",
            event_type="pr_opened",
            task_id="TASK-001",
            actor="engineer",
            timestamp=datetime.now().isoformat(),
            details="PR opened for review",
            security_level="internal",
        )
        assert entry.task_id == "TASK-001"
        assert entry.actor == "engineer"
        assert entry.security_level == "internal"

    def test_audit_entry_hash_computation(self):
        """Test tamper-evident hash computation."""
        entry1 = SecurityAuditEntry(
            event_id="e1",
            event_type="handoff_created",
            task_id="T1",
            actor="user1",
            timestamp="2026-04-27T10:00:00Z",
            details="Handoff created",
            security_level="internal",
        )
        entry1_hash = entry1.compute_hash()
        assert entry1_hash is not None
        assert len(entry1_hash) == 64  # SHA256 hex digest length

        # Same entry produces same hash
        entry1_copy = SecurityAuditEntry(
            event_id="e1",
            event_type="handoff_created",
            task_id="T1",
            actor="user1",
            timestamp="2026-04-27T10:00:00Z",
            details="Handoff created",
            security_level="internal",
        )
        assert entry1_copy.compute_hash() == entry1_hash

        # Different details produce different hash
        entry2 = SecurityAuditEntry(
            event_id="e1",
            event_type="handoff_created",
            task_id="T1",
            actor="user1",
            timestamp="2026-04-27T10:00:00Z",
            details="Handoff modified",
            security_level="internal",
        )
        assert entry2.compute_hash() != entry1_hash


class TestDeliveryQualityGates:
    """Test DeliveryQualityGates functionality."""

    def test_initialization(self, quality_gates, temp_repo):
        """Test quality gates initialization."""
        assert quality_gates.repo_root == temp_repo
        assert quality_gates.handoff_dir == temp_repo / ".digital-runtime" / "handoffs"

    def test_pr_approval_gate_no_pr(self, quality_gates):
        """Test PR approval check when no PR exists."""
        ok, msg = quality_gates.require_pr_approval("TASK-001")
        assert ok is False
        assert "No PR found" in msg

    def test_pr_approval_gate_with_approval(self, quality_gates, temp_repo):
        """Test PR approval check with approved PR."""
        # Create handoff file with approved PR
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-001
pr_url: https://github.com/org/repo/pull/1
pr_approved: true
approved_by: reviewer@example.com
"""
        )

        ok, msg = quality_gates.require_pr_approval("TASK-001")
        assert ok is True
        assert "approved" in msg.lower()
        assert "reviewer@example.com" in msg

    def test_pr_approval_gate_without_approval(self, quality_gates, temp_repo):
        """Test PR approval check with unapproved PR."""
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-001
pr_url: https://github.com/org/repo/pull/2
pr_approved: false
"""
        )

        ok, msg = quality_gates.require_pr_approval("TASK-001")
        assert ok is False
        assert "not approved" in msg.lower()

    def test_test_coverage_gate_adequate(self, quality_gates, temp_repo):
        """Test coverage gate with adequate coverage."""
        # Create evidence file with coverage info
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_file = (
            temp_repo / ".digital-artifacts" / "60-review" / today / "project" / "evidence-task-001.md"
        )
        evidence_file.write_text(
            """# Test Evidence for TASK-001
Coverage: 85%
All tests passing.
"""
        )

        ok, msg = quality_gates.require_test_coverage("TASK-001", min_coverage=80)
        assert ok is True
        assert "85%" in msg
        assert "meets requirement" in msg.lower()

    def test_test_coverage_gate_inadequate(self, quality_gates, temp_repo):
        """Test coverage gate with inadequate coverage."""
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_file = (
            temp_repo / ".digital-artifacts" / "60-review" / today / "project" / "evidence-task-002.md"
        )
        evidence_file.write_text(
            """# Test Evidence for TASK-002
Coverage: 70%
Some tests missing.
"""
        )

        ok, msg = quality_gates.require_test_coverage("TASK-002", min_coverage=80)
        assert ok is False
        assert "70%" in msg
        assert "below minimum" in msg.lower()

    def test_test_coverage_gate_no_evidence(self, quality_gates):
        """Test coverage gate when no evidence exists."""
        ok, msg = quality_gates.require_test_coverage("TASK-999")
        assert ok is False
        assert "No test coverage evidence" in msg

    def test_human_review_gate_with_reviewer(self, quality_gates, temp_repo):
        """Test human review gate with recorded reviewer."""
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-001
human_review: true
approved_by: jane.doe@company.com
"""
        )

        ok, msg = quality_gates.require_human_review_gate("TASK-001")
        assert ok is True
        assert "jane.doe@company.com" in msg
        assert "approved" in msg.lower()

    def test_human_review_gate_automation_not_allowed(self, quality_gates, temp_repo):
        """Test that automation cannot approve (must be human)."""
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-001
approved_by: system
"""
        )

        ok, msg = quality_gates.require_human_review_gate("TASK-001")
        assert ok is False
        assert "No human review" in msg

    def test_security_checklist_gate_passed(self, quality_gates, temp_repo):
        """Test security checklist when passed."""
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_file = (
            temp_repo / ".digital-artifacts" / "60-review" / today / "project" / "security-task-001.md"
        )
        evidence_file.write_text(
            """# Security Review for TASK-001
- ✓ No hardcoded secrets
- ✓ Input validation
- ✓ Auth checks
"""
        )

        ok, msg = quality_gates.require_security_checklist("TASK-001")
        assert ok is True
        assert "validated" in msg.lower()

    def test_security_checklist_gate_missing(self, quality_gates):
        """Test security checklist when missing."""
        ok, msg = quality_gates.require_security_checklist("TASK-999")
        assert ok is False
        assert "incomplete" in msg.lower()

    def test_record_audit_event(self, quality_gates):
        """Test recording security audit events."""
        entry = quality_gates.record_audit_event(
            task_id="TASK-001",
            event_type="handoff_created",
            details="Handoff created for delivery",
            actor="engineer",
            security_level="internal",
        )

        assert entry.task_id == "TASK-001"
        assert entry.event_type == "handoff_created"
        assert entry.actor == "engineer"
        assert entry.hash_digest is not None
        assert len(quality_gates.audit_trail) == 1

    def test_can_transition_to_done_success(self, quality_gates, temp_repo):
        """Test successful verification for done transition."""
        # Setup all required gates
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-001
pr_url: https://github.com/org/repo/pull/1
pr_approved: true
approved_by: reviewer@example.com
human_review: true
"""
        )

        today = datetime.now().strftime("%Y-%m-%d")
        evidence_file = (
            temp_repo / ".digital-artifacts" / "60-review" / today / "project" / "evidence-task-001.md"
        )
        evidence_file.write_text("Coverage: 85%")

        can_done, issues = quality_gates.can_transition_to_done("TASK-001", skip_optional=True)
        assert can_done is True
        assert any("✅" in issue for issue in issues)

    def test_can_transition_to_done_failure(self, quality_gates):
        """Test failed verification (no PR approval)."""
        can_done, issues = quality_gates.can_transition_to_done("TASK-999", skip_optional=True)
        assert can_done is False
        assert any("❌" in issue for issue in issues)

    def test_generate_gate_report(self, quality_gates, temp_repo):
        """Test generating quality gate report."""
        # Setup task with gates
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-001-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
pr_url: https://github.com/org/repo/pull/1
pr_approved: true
approved_by: reviewer
human_review: true
"""
        )

        quality_gates.require_pr_approval("TASK-001")
        quality_gates.require_human_review_gate("TASK-001")

        report = quality_gates.generate_gate_report("TASK-001")
        assert "Quality Gate Report" in report
        assert "Gate Checks" in report
        assert "Approval Gate Status" in report
        assert "Conclusion" in report

    def test_audit_trail_recording(self, quality_gates):
        """Test comprehensive audit trail recording."""
        # Record multiple events
        quality_gates.record_audit_event(
            task_id="TASK-001",
            event_type="handoff_created",
            details="Initial handoff",
            actor="planner",
        )
        quality_gates.record_audit_event(
            task_id="TASK-001",
            event_type="pr_opened",
            details="PR for implementation",
            actor="developer",
            pr_url="https://github.com/org/repo/pull/1",
        )
        quality_gates.record_audit_event(
            task_id="TASK-001",
            event_type="approval_recorded",
            details="Approved by reviewer",
            actor="reviewer",
        )

        assert len(quality_gates.audit_trail) == 3
        assert quality_gates.audit_trail[0].event_type == "handoff_created"
        assert quality_gates.audit_trail[1].event_type == "pr_opened"
        assert quality_gates.audit_trail[2].event_type == "approval_recorded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
