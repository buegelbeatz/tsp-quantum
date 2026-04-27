#!/usr/bin/env python3
"""
Delivery Evidence Tracker

Manages delivery evidence artifacts, tracks handoff status, generates review artifacts,
and records approval evidence for delivered tasks.

This module is responsible for:
- Creating and updating delivery evidence records
- Tracking handoff status from dispatch through completion
- Generating review artifacts with verification evidence
- Recording human approval evidence
- Providing artifact recovery status queries
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field


@dataclass
class HandoffEvidence:
    """Evidence record for a single handoff."""

    task_id: str
    stage: str
    receiver: str
    status: str  # dispatched, in-progress, review, done
    created_at: str
    started_at: Optional[str] = None
    pr_url: Optional[str] = None
    pr_merged_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    tests_passed: bool = False
    quality_passed: bool = False
    coverage_percent: Optional[float] = None
    artifacts: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert to dict, excluding None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


class DeliveryEvidenceTracker:
    """Tracks and manages delivery evidence artifacts."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize tracker with repo root."""
        if repo_root is None:
            repo_root = Path.cwd()
        self.repo_root: Path = Path(repo_root)
        self.artifacts_root: Path = self.repo_root / ".digital-artifacts"
        self.review_root: Path = self.artifacts_root / "60-review"
        self.evidence_dir: Optional[Path] = None

    def initialize_stage_review(self, stage: str, timestamp: Optional[str] = None) -> Path:
        """Initialize review directory for a stage."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")

        stage_review_dir = self.review_root / timestamp / stage
        stage_review_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir = stage_review_dir
        return stage_review_dir

    def load_handoff(self, handoff_path: Path) -> Optional[Dict]:
        """Load handoff YAML file."""
        if not handoff_path.exists():
            return None
        with open(handoff_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def update_handoff_status(
        self, handoff_path: Path, status: str, updates: Optional[Dict] = None
    ) -> bool:
        """Update handoff status in YAML file."""
        try:
            handoff = self.load_handoff(handoff_path)
            if not handoff:
                return False
            handoff["status"] = status
            if updates:
                handoff.update(updates)
            with open(handoff_path, "w", encoding="utf-8") as f:
                yaml.dump(handoff, f)
            return True
        except (IOError, yaml.YAMLError) as e:
            print(f"Error updating handoff: {e}", file=sys.stderr)
            return False

    def create_delivery_evidence_artifact(
        self,
        evidence: HandoffEvidence,
        stage: str,
        timestamp: Optional[str] = None,
    ) -> Path:
        """Create a delivery evidence artifact from handoff evidence."""
        if self.evidence_dir is None:
            self.initialize_stage_review(stage, timestamp)

        artifact_path = (
            self.evidence_dir / f"delivery-evidence-{evidence.task_id}.md"
        )

        content = self._generate_evidence_markdown(evidence)
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(content)

        return artifact_path

    def _generate_evidence_markdown(self, evidence: HandoffEvidence) -> str:
        """Generate markdown evidence document."""
        content = f"""# Delivery Evidence — {evidence.task_id}

## Handoff Summary
- Task ID: {evidence.task_id}
- Stage: {evidence.stage}
- Receiver: {evidence.receiver}
- Created: {evidence.created_at}
- Started: {evidence.started_at or 'pending'}

## Status
- Current: {evidence.status}
- PR URL: {evidence.pr_url or 'not created'}
- Merged: {evidence.pr_merged_at or 'not merged'}

## Approval
- Approved By: {evidence.approved_by or 'pending'}
- Approved At: {evidence.approved_at or 'pending'}

## Quality Gates
- Tests Passed: {'✓' if evidence.tests_passed else '✗'}
- Quality Passed: {'✓' if evidence.quality_passed else '✗'}
- Coverage: {evidence.coverage_percent}% if evidence.coverage_percent else 'not measured'

## Related Artifacts
"""
        for artifact in evidence.artifacts:
            content += f"- {artifact}\n"

        return content

    def create_review_checkpoint(
        self,
        stage: str,
        tasks: List[Dict],
        timestamp: Optional[str] = None,
    ) -> Path:
        """Create a review checkpoint artifact tracking all delivery tasks."""
        if self.evidence_dir is None:
            self.initialize_stage_review(stage, timestamp)

        checkpoint_path = self.evidence_dir / "delivery-checkpoint.md"

        status_summary = self._summarize_task_statuses(tasks)

        content = f"""# Delivery Review Checkpoint

- Generated: {datetime.now().isoformat()}
- Stage: {stage}
- Total Tasks: {len(tasks)}

## Status Summary
{status_summary}

## Detailed Task Status

"""
        for task in tasks:
            content += self._format_task_entry(task)

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write(content)

        return checkpoint_path

    def _summarize_task_statuses(self, tasks: List[Dict]) -> str:
        """Summarize task statuses."""
        statuses: Dict[str, int] = {}
        for task in tasks:
            status = task.get("status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1

        lines = []
        for status, count in sorted(statuses.items()):
            lines.append(f"- {status}: {count}")
        return "\n".join(lines)

    def _format_task_entry(self, task: Dict) -> str:
        """Format a task entry."""
        task_id = task.get("task_id", "unknown")
        status = task.get("status", "unknown")
        assignee = task.get("receiver", "unknown")
        pr_url = task.get("pr_url")

        entry = f"### {task_id}\n"
        entry += f"- Status: {status}\n"
        entry += f"- Assignee: {assignee}\n"
        if pr_url:
            entry += f"- PR: {pr_url}\n"
        entry += "\n"
        return entry

    def record_approval_evidence(
        self,
        task_id: str,
        approver: str,
        pr_url: str,
        timestamp: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict:
        """Record human approval evidence for a task."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        approval_record = {
            "task_id": task_id,
            "approver": approver,
            "pr_url": pr_url,
            "approved_at": timestamp,
            "notes": notes,
        }

        return approval_record

    def verify_artifact_recovery(
        self, stage: str, task_ids: List[str]
    ) -> Dict[str, str]:
        """Verify artifact recovery status for tasks."""
        recovery_status = {}

        planning_dir = self.artifacts_root / "50-planning" / stage
        for task_id in task_ids:
            task_file = planning_dir / f"{task_id}.md"
            if task_file.exists():
                recovery_status[task_id] = "found"
            else:
                recovery_status[task_id] = "not_found"

        return recovery_status

    def generate_recovery_report(
        self, stage: str, timestamp: Optional[str] = None
    ) -> Path:
        """Generate artifact recovery report."""
        if self.evidence_dir is None:
            self.initialize_stage_review(stage, timestamp)

        report_path = self.evidence_dir / "artifact-recovery-report.md"

        planning_dir = self.artifacts_root / "50-planning" / stage
        handoff_dir = self.repo_root / ".digital-runtime" / "handoffs" / stage

        planning_artifacts = list(planning_dir.glob("*.md")) if planning_dir.exists() else []
        handoff_artifacts = list(handoff_dir.glob("*.yaml")) if handoff_dir.exists() else []

        content = f"""# Artifact Recovery Report

- Generated: {datetime.now().isoformat()}
- Stage: {stage}

## Planning Artifacts
- Found: {len(planning_artifacts)}
- Location: {planning_dir}

"""
        for artifact in planning_artifacts:
            content += f"- {artifact.name}\n"

        content += f"""
## Delivery Handoffs
- Found: {len(handoff_artifacts)}
- Location: {handoff_dir}

"""
        for artifact in handoff_artifacts:
            content += f"- {artifact.name}\n"

        artifacts_ok = len(planning_artifacts) > 0
        handoffs_ok = len(handoff_artifacts) > 0
        status_msg = (
            "Ready for rerun" if artifacts_ok and handoffs_ok else "Partial"
        )
        content += f"""
## Recovery Status

- Planning artifacts recoverable: {'✓' if artifacts_ok else '✗'}
- Handoff artifacts preserved: {'✓' if handoffs_ok else '✗'}
- Status: {status_msg}

"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path


def main():
    """CLI interface for delivery evidence tracker."""
    if len(sys.argv) < 2:
        print(
            "Usage: delivery_evidence_tracker.py <command> [args]",
            file=sys.stderr,
        )
        print(
            "Commands: init-review, load-handoff, update-status, "
            "create-evidence, verify-recovery",
            file=sys.stderr,
        )
        sys.exit(1)

    tracker = DeliveryEvidenceTracker()
    command = sys.argv[1]

    if command == "init-review":
        stage = sys.argv[2] if len(sys.argv) > 2 else "project"
        evidence_dir = tracker.initialize_stage_review(stage)
        print(f"Initialized review directory: {evidence_dir}")

    elif command == "verify-recovery":
        stage = sys.argv[2] if len(sys.argv) > 2 else "project"
        task_ids = sys.argv[3:] if len(sys.argv) > 3 else []
        status = tracker.verify_artifact_recovery(stage, task_ids)
        print(json.dumps(status, indent=2))

    elif command == "recovery-report":
        stage = sys.argv[2] if len(sys.argv) > 2 else "project"
        report_path = tracker.generate_recovery_report(stage)
        print(f"Recovery report: {report_path}")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
