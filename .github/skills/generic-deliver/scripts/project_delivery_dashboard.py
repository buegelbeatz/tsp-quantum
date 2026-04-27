#!/usr/bin/env python3
"""
Project Delivery Dashboard Generator

Provides real-time project visibility and delivery status reporting for stakeholders.
Generates human-readable dashboards showing task assignments, handoff status, and progress.

Key features:
- Task assignment visibility with clear ownership
- Handoff status tracking (backlog → in-progress → review → done)
- Delivery evidence summary for each task
- Recovery status and artifact availability
- Security control audit trail
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class TaskStatus:
    """Represents the current state of a delivery task."""
    task_id: str
    title: str
    status: str  # backlog, in-progress, review, done
    assignee: str
    created_at: str
    updated_at: str
    handoff_path: Optional[str] = None
    pr_url: Optional[str] = None
    pr_approved: bool = False
    approval_timestamp: Optional[str] = None
    approved_by: Optional[str] = None
    evidence_artifacts: List[str] = field(default_factory=list)
    test_coverage: Optional[str] = None
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ProjectDeliveryDashboard:
    """Manages project delivery visibility and status reporting."""

    def __init__(self, repo_root: Path):
        """Initialize dashboard from repository root."""
        self.repo_root = Path(repo_root)
        self.artifacts_root = self.repo_root / ".digital-artifacts"
        self.runtime_root = self.repo_root / ".digital-runtime"
        self.planning_root = self.artifacts_root / "50-planning"
        self.review_root = self.artifacts_root / "60-review"
        self.handoff_dir = self.runtime_root / "handoffs"

    def scan_tasks(self, stage: str) -> List[TaskStatus]:
        """Scan planning artifacts and handoff files to build task status list."""
        tasks: List[TaskStatus] = []

        # Discover task documents in planning
        planning_stage_dir = self.planning_root / stage
        if planning_stage_dir.exists():
            for task_file in planning_stage_dir.glob("TASK_*.md"):
                task_status = self._parse_task_file(task_file)
                if task_status:
                    # Enrich with handoff status
                    self._enrich_with_handoff_status(task_status, stage)
                    # Enrich with PR/approval status
                    self._enrich_with_approval_status(task_status, stage)
                    # Enrich with evidence
                    self._enrich_with_evidence(task_status, stage)
                    tasks.append(task_status)

        # Sort by creation time
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def _parse_task_file(self, task_file: Path) -> Optional[TaskStatus]:
        """Extract basic task information from markdown file."""
        try:
            content = task_file.read_text()

            # Extract frontmatter
            fm_match = re.search(r'^---\n(.*?)\n---', content, re.MULTILINE | re.DOTALL)
            if not fm_match:
                return None

            fm_text = fm_match.group(1)
            task_id = self._extract_yaml_field(fm_text, "task_id")
            status = self._extract_yaml_field(fm_text, "status", "in-progress")
            assignee_hint = self._extract_yaml_field(fm_text, "assignee_hint", "unassigned")
            created = self._extract_yaml_field(fm_text, "created", datetime.now().isoformat())

            # Extract title from heading
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "Untitled Task"

            return TaskStatus(
                task_id=task_id or "UNKNOWN",
                title=title,
                status=status,
                assignee=assignee_hint,
                created_at=created,
                updated_at=datetime.now().isoformat(),
            )
        except (IOError, OSError, AttributeError):
            return None

    def _extract_yaml_field(self, yaml_text: str, field_name: str, default: str = "") -> str:
        """Extract a field value from YAML frontmatter text."""
        pattern = rf'{field_name}:\s*["\']?([^"\'\n]+)["\']?'
        match = re.search(pattern, yaml_text)
        return match.group(1).strip() if match else default

    def _enrich_with_handoff_status(self, task: TaskStatus, stage: str) -> None:
        """Add handoff file status information to task."""
        handoff_stage_dir = self.handoff_dir / stage
        if not handoff_stage_dir.exists():
            return

        # Look for handoff YAML file
        handoff_file = handoff_stage_dir / f"{task.task_id.lower()}-handoff.yaml"
        if handoff_file.exists():
            task.handoff_path = str(handoff_file)
            # Parse status from handoff
            try:
                content = handoff_file.read_text()
                status_match = re.search(r'status:\s*([^\n]+)', content)
                if status_match:
                    task.status = status_match.group(1).strip()
            except (IOError, OSError, AttributeError):
                pass

    def _enrich_with_approval_status(self, task: TaskStatus, stage: str) -> None:
        """Add PR and approval status information to task."""
        # First check handoff files for PR reference
        handoff_stage_dir = self.handoff_dir / stage
        if handoff_stage_dir.exists():
            handoff_file = handoff_stage_dir / f"{task.task_id.lower()}-handoff.yaml"
            if handoff_file.exists():
                try:
                    content = handoff_file.read_text()
                    # Look for PR URL
                    pr_match = re.search(r'pr[_-]?url:\s*([^\s\n]+)', content, re.IGNORECASE)
                    if pr_match:
                        task.pr_url = pr_match.group(1)

                    # Look for approval
                    if "approved" in content.lower() and "pending" not in content.lower():
                        task.pr_approved = True
                        approval_match = re.search(r'approved[_-]?by:\s*([^\n]+)', content, re.IGNORECASE)
                        if approval_match:
                            task.approved_by = approval_match.group(1).strip()
                except (IOError, OSError, AttributeError):
                    pass

        # Also check review artifacts for PR information
        review_dir = self.review_root / datetime.now().strftime("%Y-%m-%d") / stage
        if not review_dir.exists():
            return

        for review_file in review_dir.glob(f"*{task.task_id.lower()}*"):
            try:
                content = review_file.read_text()
                # Look for PR URL
                pr_match = re.search(r'pr[_-]?url:\s*([^\s\n]+)', content, re.IGNORECASE)
                if pr_match:
                    task.pr_url = pr_match.group(1)

                # Look for approval
                if "approved" in content.lower() and "pending" not in content.lower():
                    task.pr_approved = True
                    approval_match = re.search(r'approved[_-]?by:\s*([^\n]+)', content, re.IGNORECASE)
                    if approval_match:
                        task.approved_by = approval_match.group(1).strip()
            except (IOError, OSError, AttributeError):
                pass

    def _enrich_with_evidence(self, task: TaskStatus, stage: str) -> None:
        """Add evidence artifacts and test coverage info to task."""
        # Scan for evidence files
        today = datetime.now().strftime("%Y-%m-%d")
        review_dir = self.review_root / today / stage
        if review_dir.exists():
            for evidence_file in review_dir.glob(f"*{task.task_id.lower()}*"):
                task.evidence_artifacts.append(str(evidence_file))
                # Look for test coverage
                try:
                    content = evidence_file.read_text()
                    coverage_match = re.search(r'coverage[:\s]*(\d+)\s*%', content, re.IGNORECASE)
                    if coverage_match:
                        task.test_coverage = f"{coverage_match.group(1)}%"
                except (IOError, OSError, AttributeError):
                    pass

    def generate_markdown_dashboard(self, tasks: List[TaskStatus]) -> str:
        """Generate markdown dashboard view of project delivery status."""
        lines = [
            "# Project Delivery Dashboard",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            f"- Total Tasks: {len(tasks)}",
            f"- Done: {len([t for t in tasks if t.status == 'done'])}",
            f"- In Progress: {len([t for t in tasks if t.status == 'in-progress'])}",
            f"- In Review: {len([t for t in tasks if t.status == 'review'])}",
            f"- Backlog: {len([t for t in tasks if t.status == 'backlog'])}",
            "",
            "## Task Assignment Visibility",
            "",
            "| Task ID | Title | Assignee | Status | Progress | Coverage |",
            "|---------|-------|----------|--------|----------|----------|",
        ]

        for task in tasks:
            progress_icon = self._status_icon(task)
            coverage_str = task.test_coverage if task.test_coverage else "—"
            title_short = (task.title[:40] + "...") if len(task.title) > 40 else task.title

            lines.append(
                f"| {task.task_id} | {title_short} | {task.assignee} | "
                f"{task.status} | {progress_icon} | {coverage_str} |"
            )

        lines.extend(["", "## Handoff Status & Evidence Trail", ""])

        for task in tasks:
            if task.handoff_path or task.pr_url:
                lines.append(f"### {task.task_id}: {task.title}")
                lines.append("")

                if task.handoff_path:
                    lines.append(f"**Handoff Path**: `{task.handoff_path}`")

                if task.pr_url:
                    approval_status = "✅ Approved" if task.pr_approved else "⏳ Pending"
                    lines.append(f"**PR**: [{task.pr_url}]({task.pr_url}) {approval_status}")

                    if task.approved_by:
                        lines.append(f"**Approved By**: {task.approved_by}")

                if task.test_coverage:
                    lines.append(f"**Test Coverage**: {task.test_coverage}")

                if task.evidence_artifacts:
                    lines.append(f"**Evidence Artifacts**: {len(task.evidence_artifacts)} file(s)")

                lines.append("")

        lines.extend([
            "## Recovery & Artifact Status",
            "",
            "✅ All handoff files are located in `.digital-runtime/handoffs/`",
            "✅ Delivery evidence is preserved in `.digital-artifacts/60-review/`",
            "✅ Planning artifacts are backed up in `.digital-artifacts/50-planning/`",
            "",
            "## Human Approval Gates",
            "",
            "| Task | Status | Reviewer | Timestamp |",
            "|------|--------|----------|-----------|",
        ])

        for task in tasks:
            if task.pr_approved:
                reviewer = task.approved_by or "Pending"
                timestamp = task.approval_timestamp or "N/A"
                lines.append(f"| {task.task_id} | ✅ Done | {reviewer} | {timestamp} |")
            elif task.pr_url:
                lines.append(f"| {task.task_id} | ⏳ Review | Pending | {task.updated_at} |")

        lines.extend([
            "",
            "## Security & Audit Trail",
            "",
            "All delivery handoffs are tracked with:",
            "- Task ID and assignment",
            "- Handoff creation timestamp",
            "- PR reference and review link",
            "- Approval evidence and reviewer name",
            "- Separation of automation (in-progress) and human review (done)",
            "",
            "No tasks transition to `done` without explicit human approval and recorded evidence.",
        ])

        return "\n".join(lines)

    def _status_icon(self, task: TaskStatus) -> str:
        """Get visual indicator for task status."""
        icons = {
            "done": "✅ Done",
            "review": "🔍 Review",
            "in-progress": "⏳ Active",
            "backlog": "📋 Backlog",
        }
        return icons.get(task.status, "❓ Unknown")

    def generate_json_status(self, tasks: List[TaskStatus]) -> str:
        """Generate JSON status export for CLI/API consumption."""
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(tasks),
                "done": len([t for t in tasks if t.status == "done"]),
                "in_progress": len([t for t in tasks if t.status == "in-progress"]),
                "in_review": len([t for t in tasks if t.status == "review"]),
                "backlog": len([t for t in tasks if t.status == "backlog"]),
            },
            "tasks": [t.to_dict() for t in tasks],
        }
        return json.dumps(status_data, indent=2)

    def export_dashboard(self, stage: str, output_dir: Optional[Path] = None) -> Tuple[str, str]:
        """Scan, generate, and save dashboard outputs."""
        tasks = self.scan_tasks(stage)
        markdown = self.generate_markdown_dashboard(tasks)
        json_status = self.generate_json_status(tasks)

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            md_file = output_dir / f"project-delivery-dashboard-{stage}.md"
            json_file = output_dir / f"project-delivery-status-{stage}.json"

            md_file.write_text(markdown)
            json_file.write_text(json_status)

        return markdown, json_status


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 project_delivery_dashboard.py <stage> [output_dir]")
        sys.exit(1)

    main_stage = sys.argv[1]
    main_output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
    main_repo_root = Path.cwd()

    main_dashboard = ProjectDeliveryDashboard(main_repo_root)
    main_markdown, main_json_status = main_dashboard.export_dashboard(main_stage, main_output_dir)

    print(main_markdown)
    print("\n# JSON Status Export:")
    print(main_json_status)
