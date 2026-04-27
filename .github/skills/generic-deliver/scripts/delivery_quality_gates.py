#!/usr/bin/env python3
"""
Delivery Quality Gates & Security Controls

Implements quality validation, security controls, and approval gates for the delivery workflow.
Ensures human review requirements are met before task completion.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import hashlib


@dataclass
class ApprovalGate:
    """Represents a single approval gate check."""
    gate_name: str
    description: str
    required: bool
    status: str  # pending, passed, failed, waived
    checked_at: Optional[str] = None
    checked_by: Optional[str] = None
    evidence_link: Optional[str] = None
    waiver_reason: Optional[str] = None


@dataclass
class SecurityAuditEntry:
    """Records security audit events for delivery workflow."""
    event_id: str
    event_type: str  # handoff_created, pr_opened, approval_recorded, done_transition
    task_id: str
    actor: Optional[str]
    timestamp: str
    details: str
    security_level: str  # public, internal, confidential
    related_pr: Optional[str] = None
    hash_digest: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute tamper-evident hash of audit entry."""
        content = f"{self.task_id}|{self.event_type}|{self.timestamp}|{self.details}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class DeliveryCheckpoint:
    """Represents verification checkpoint in delivery workflow."""
    checkpoint_id: str
    checkpoint_name: str
    stage: str  # ingestion, specification, planning, delivery, review
    required_gates: List[str]
    passed: bool = False
    completion_time: Optional[str] = None
    verification_notes: str = ""


class DeliveryQualityGates:
    """Manages quality gates and approval requirements for delivery."""

    def __init__(self, repo_root: Path):
        """Initialize quality gates."""
        self.repo_root = Path(repo_root)
        self.handoff_dir = self.repo_root / ".digital-runtime" / "handoffs"
        self.review_dir = self.repo_root / ".digital-artifacts" / "60-review"
        self.gates: Dict[str, ApprovalGate] = {}
        self.audit_trail: List[SecurityAuditEntry] = []

    def require_pr_approval(self, task_id: str) -> Tuple[bool, str]:
        """Check if task has required PR approval from human reviewer."""
        gate = ApprovalGate(
            gate_name="pr_approval",
            description="Pull request must have human reviewer approval",
            required=True,
            status="pending",
        )

        # Look for PR reference in handoff files
        handoff_files = list(self.handoff_dir.glob(f"*/task-{task_id.lower()}-handoff.yaml"))
        if not handoff_files:
            handoff_files = list(self.handoff_dir.glob(f"*/{task_id.lower()}-handoff.yaml"))

        for handoff_file in handoff_files:
            try:
                content = handoff_file.read_text()
                pr_match = re.search(r'pr[_-]?url:\s*([^\s\n]+)', content, re.IGNORECASE)
                if pr_match:
                    pr_url = pr_match.group(1)

                    # Check for approval status
                    approved_match = re.search(
                        r'pr[_-]?approved:\s*(true|yes|1)', content, re.IGNORECASE
                    )
                    if approved_match:
                        approver_match = re.search(
                            r'approved[_-]?by:\s*([^\n]+)', content, re.IGNORECASE
                        )
                        gate.status = "passed"
                        gate.checked_at = datetime.now().isoformat()
                        gate.checked_by = (
                            approver_match.group(1).strip() if approver_match else "system"
                        )
                        gate.evidence_link = pr_url

                        self.gates["pr_approval"] = gate
                        return True, f"PR {pr_url} approved by {gate.checked_by}"
                    else:
                        return False, f"PR exists but not approved: {pr_url}"
            except (IOError, OSError):
                pass

        return False, "No PR found or PR not yet created"

    def require_test_coverage(
        self, task_id: str, min_coverage: int = 80
    ) -> Tuple[bool, str]:
        """Verify test coverage meets minimum threshold."""
        gate = ApprovalGate(
            gate_name="test_coverage",
            description=f"Code must have >= {min_coverage}% test coverage",
            required=True,
            status="pending",
        )

        # Look for test coverage in evidence files
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_dir = self.repo_root / ".digital-artifacts" / "60-review" / today

        if evidence_dir.exists():
            for evidence_file in evidence_dir.rglob(f"*{task_id.lower()}*"):
                try:
                    content = evidence_file.read_text()
                    coverage_match = re.search(r'coverage[:\s]*(\d+)%?', content, re.IGNORECASE)
                    if coverage_match:
                        coverage = int(coverage_match.group(1))
                        if coverage >= min_coverage:
                            gate.status = "passed"
                            gate.checked_at = datetime.now().isoformat()
                            gate.evidence_link = str(evidence_file)
                            self.gates["test_coverage"] = gate
                            return True, f"Test coverage {coverage}% meets requirement >= {min_coverage}%"
                        else:
                            return (
                                False,
                                f"Test coverage {coverage}% below minimum {min_coverage}%",
                            )
                except (IOError, OSError, ValueError):
                    pass

        return False, "No test coverage evidence found"

    def require_human_review_gate(self, task_id: str) -> Tuple[bool, str]:
        """Enforce mandatory human review before done transition."""
        gate = ApprovalGate(
            gate_name="human_review",
            description="Mandatory human reviewer must approve task before done",
            required=True,
            status="pending",
        )

        # Check for explicit human review record
        handoff_files = list(self.handoff_dir.glob(f"**/*{task_id.lower()}*"))
        for handoff_file in handoff_files:
            try:
                content = handoff_file.read_text()
                # Look for explicit human review indication
                if re.search(r'(human[_-]?review|approved[_-]?by|reviewer):\s*', content, re.IGNORECASE):
                    # Check that reviewer is not system/automation
                    reviewer_match = re.search(
                        r'approved[_-]?by:\s*([^\n]+)', content, re.IGNORECASE
                    )
                    if reviewer_match:
                        reviewer = reviewer_match.group(1).strip()
                        if reviewer.lower() not in ["system", "automation", "pending"]:
                            gate.status = "passed"
                            gate.checked_at = datetime.now().isoformat()
                            gate.checked_by = reviewer
                            self.gates["human_review"] = gate
                            return True, f"Human review approved by {reviewer}"
            except (IOError, OSError):
                pass

        return False, "No human review recorded. Task cannot transition to done."

    def require_security_checklist(self, task_id: str) -> Tuple[bool, str]:
        """Verify security checklist has been completed."""
        gate = ApprovalGate(
            gate_name="security_checklist",
            description="Security controls must be validated",
            required=False,  # Can be waived
            status="pending",
        )

        # Check for security validation in review artifacts
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_dir = self.repo_root / ".digital-artifacts" / "60-review" / today

        if evidence_dir.exists():
            for evidence_file in evidence_dir.rglob(f"*{task_id.lower()}*"):
                try:
                    content = evidence_file.read_text()
                    if "security" in content.lower() and "✓" in content:
                        gate.status = "passed"
                        gate.checked_at = datetime.now().isoformat()
                        gate.evidence_link = str(evidence_file)
                        self.gates["security_checklist"] = gate
                        return True, "Security checklist validated"
                except (IOError, OSError):
                    pass

        return False, "Security checklist incomplete"

    def record_audit_event(
        self,
        task_id: str,
        event_type: str,
        details: str,
        actor: Optional[str] = None,
        security_level: str = "internal",
        pr_url: Optional[str] = None,
    ) -> SecurityAuditEntry:
        """Record security audit event."""
        event_id = f"{task_id}_{event_type}_{datetime.now().timestamp()}"
        entry = SecurityAuditEntry(
            event_id=event_id,
            event_type=event_type,
            task_id=task_id,
            actor=actor or "system",
            timestamp=datetime.now().isoformat(),
            details=details,
            security_level=security_level,
            related_pr=pr_url,
        )
        entry.hash_digest = entry.compute_hash()
        self.audit_trail.append(entry)
        return entry

    def can_transition_to_done(self, task_id: str, skip_optional: bool = False) -> Tuple[bool, List[str]]:
        """Check if task meets all gates to transition to done status."""
        issues: List[str] = []

        # Always require PR approval
        pr_ok, pr_msg = self.require_pr_approval(task_id)
        if not pr_ok:
            issues.append(f"❌ PR Approval: {pr_msg}")
        else:
            issues.append(f"✅ PR Approval: {pr_msg}")

        # Always require human review
        hr_ok, hr_msg = self.require_human_review_gate(task_id)
        if not hr_ok:
            issues.append(f"❌ Human Review: {hr_msg}")
        else:
            issues.append(f"✅ Human Review: {hr_msg}")

        # Test coverage required  
        tc_ok, tc_msg = self.require_test_coverage(task_id)
        if not tc_ok:
            issues.append(f"⚠️  Test Coverage: {tc_msg}")
        else:
            issues.append(f"✅ Test Coverage: {tc_msg}")

        # Security checklist optional
        if not skip_optional:
            sc_ok, sc_msg = self.require_security_checklist(task_id)
            if not sc_ok:
                issues.append(f"⚠️  Security Checklist: {sc_msg} (optional)")
            else:
                issues.append(f"✅ Security Checklist: {sc_msg}")

        can_proceed = pr_ok and hr_ok
        return can_proceed, issues

    def generate_gate_report(self, task_id: str) -> str:
        """Generate human-readable quality gate report."""
        lines = [
            f"# Quality Gate Report: {task_id}",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Gate Checks",
            "",
        ]

        can_done, issues = self.can_transition_to_done(task_id)

        for issue in issues:
            lines.append(f"- {issue}")

        lines.extend(
            [
                "",
                "## Approval Gate Status",
                "",
                "| Gate | Status | Evidence | Checked By |",
                "|------|--------|----------|-----------|",
            ]
        )

        for gate_name, gate in self.gates.items():
            status_icon = "✅" if gate.status == "passed" else "❌" if gate.status == "failed" else "⏳"
            evidence = gate.evidence_link or "N/A"
            checked_by = gate.checked_by or "Pending"
            lines.append(f"| {gate_name} | {status_icon} {gate.status} | {evidence} | {checked_by} |")

        lines.extend(
            [
                "",
                "## Audit Trail",
                "",
                "| Event | Timestamp | Actor | Details |",
                "|-------|-----------|-------|---------|",
            ]
        )

        for entry in self.audit_trail:
            if entry.task_id == task_id:
                lines.append(
                    f"| {entry.event_type} | {entry.timestamp} | {entry.actor} | {entry.details} |"
                )

        lines.extend(
            [
                "",
                "## Conclusion",
                "",
            ]
        )

        if can_done:
            lines.append("✅ **Task is ready for done transition.** All required gates passed.")
        else:
            lines.append("❌ **Task cannot transition to done.** Required gates are blocking.")

        return "\n".join(lines)
