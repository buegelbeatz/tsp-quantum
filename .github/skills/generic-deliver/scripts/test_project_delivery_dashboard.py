#!/usr/bin/env python3
"""
Unit tests for Project Delivery Dashboard

Tests for task visibility, handoff tracking, approval status, and dashboard generation.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from project_delivery_dashboard import (
    ProjectDeliveryDashboard,
    TaskStatus,
)


@pytest.fixture
def temp_repo():
    """Create temporary repository structure."""
    with TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".digital-artifacts" / "50-planning" / "project").mkdir(parents=True)
        (repo_root / ".digital-artifacts" / "60-review" / "2026-04-27" / "project").mkdir(
            parents=True
        )
        (repo_root / ".digital-runtime" / "handoffs" / "project").mkdir(parents=True)
        yield repo_root


@pytest.fixture
def dashboard(temp_repo):
    """Create dashboard instance with temporary repo."""
    return ProjectDeliveryDashboard(temp_repo)


class TestTaskStatus:
    """Test TaskStatus dataclass."""

    def test_task_status_creation(self):
        """Test creating a task status."""
        task = TaskStatus(
            task_id="TASK-001",
            title="Test Task",
            status="in-progress",
            assignee="engineer",
            created_at="2026-04-27T09:00:00Z",
            updated_at="2026-04-27T10:00:00Z",
        )
        assert task.task_id == "TASK-001"
        assert task.status == "in-progress"
        assert task.pr_approved is False

    def test_task_status_to_dict(self):
        """Test converting task status to dictionary."""
        task = TaskStatus(
            task_id="TASK-002",
            title="Another Task",
            status="done",
            assignee="lead",
            created_at="2026-04-27T09:00:00Z",
            updated_at="2026-04-27T11:00:00Z",
        )
        task_dict = task.to_dict()
        assert task_dict["task_id"] == "TASK-002"
        assert task_dict["status"] == "done"
        assert "evidence_artifacts" in task_dict


class TestProjectDeliveryDashboard:
    """Test ProjectDeliveryDashboard functionality."""

    def test_dashboard_initialization(self, dashboard, temp_repo):
        """Test dashboard initialization."""
        assert dashboard.repo_root == temp_repo
        assert dashboard.handoff_dir == temp_repo / ".digital-runtime" / "handoffs"

    def test_extract_yaml_field(self, dashboard):
        """Test YAML field extraction."""
        yaml_text = """
        task_id: TASK-003
        title: "Test Task"
        status: in-progress
        """
        assert dashboard._extract_yaml_field(yaml_text, "task_id") == "TASK-003"
        assert dashboard._extract_yaml_field(yaml_text, "status") == "in-progress"
        assert dashboard._extract_yaml_field(yaml_text, "missing", "default") == "default"

    def test_parse_task_file(self, dashboard, temp_repo):
        """Test parsing task file."""
        task_file = temp_repo / ".digital-artifacts" / "50-planning" / "project" / "TASK_001.md"
        task_file.write_text(
            """---
task_id: TASK-001
title: Delivery Task
status: in-progress
assignee_hint: fullstack-engineer
created: 2026-04-27T09:00:00Z
---

# Task: Delivery Task

Test content."""
        )

        task = dashboard._parse_task_file(task_file)
        assert task is not None
        assert task.task_id == "TASK-001"
        assert task.title == "Task: Delivery Task"
        assert task.status == "in-progress"
        assert task.assignee == "fullstack-engineer"

    def test_parse_invalid_task_file(self, dashboard, temp_repo):
        """Test parsing invalid task file returns None."""
        task_file = temp_repo / ".digital-artifacts" / "50-planning" / "project" / "INVALID.md"
        task_file.write_text("No frontmatter here")

        task = dashboard._parse_task_file(task_file)
        assert task is None

    def test_enrich_with_handoff_status(self, dashboard, temp_repo):
        """Test enriching task with handoff status."""
        task = TaskStatus(
            task_id="TASK-004",
            title="Test",
            status="backlog",
            assignee="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-004-handoff.yaml"
        )
        handoff_file.write_text(
            """
schema: work_handoff_v1
status: in-progress
task_id: TASK-004
"""
        )

        dashboard._enrich_with_handoff_status(task, "project")
        assert task.handoff_path is not None
        assert "task-004-handoff.yaml" in task.handoff_path
        assert task.status == "in-progress"

    def test_generate_markdown_dashboard(self, dashboard):
        """Test markdown dashboard generation."""
        tasks = [
            TaskStatus(
                task_id="TASK-A",
                title="Design Review",
                status="done",
                assignee="ux-designer",
                created_at="2026-04-27T09:00:00Z",
                updated_at="2026-04-27T12:00:00Z",
                pr_url="https://github.com/user/repo/pull/1",
                pr_approved=True,
                approved_by="reviewer1",
            ),
            TaskStatus(
                task_id="TASK-B",
                title="Quality Assurance",
                status="in-progress",
                assignee="quality-expert",
                created_at="2026-04-27T09:30:00Z",
                updated_at="2026-04-27T11:30:00Z",
                test_coverage="85%",
            ),
        ]

        markdown = dashboard.generate_markdown_dashboard(tasks)
        assert "Project Delivery Dashboard" in markdown
        assert "TASK-A" in markdown
        assert "TASK-B" in markdown
        assert "Design Review" in markdown
        assert "Quality Assurance" in markdown
        assert "ux-designer" in markdown
        assert "85%" in markdown
        assert "✅ Approved" in markdown

    def test_generate_markdown_dashboard_status_icons(self, dashboard):
        """Test that dashboard uses correct status icons."""
        tasks = [
            TaskStatus(
                task_id="TASK-DONE",
                title="Complete",
                status="done",
                assignee="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            TaskStatus(
                task_id="TASK-REVIEW",
                title="Pending Review",
                status="review",
                assignee="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            TaskStatus(
                task_id="TASK-ACTIVE",
                title="In Progress",
                status="in-progress",
                assignee="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            TaskStatus(
                task_id="TASK-BACKLOG",
                title="Future Work",
                status="backlog",
                assignee="test",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
        ]

        markdown = dashboard.generate_markdown_dashboard(tasks)
        assert "✅ Done" in markdown
        assert "🔍 Review" in markdown
        assert "⏳ Active" in markdown
        assert "📋 Backlog" in markdown

    def test_generate_json_status(self, dashboard):
        """Test JSON status export."""
        tasks = [
            TaskStatus(
                task_id="TASK-1",
                title="Task One",
                status="done",
                assignee="dev1",
                created_at="2026-04-27T09:00:00Z",
                updated_at="2026-04-27T12:00:00Z",
            ),
            TaskStatus(
                task_id="TASK-2",
                title="Task Two",
                status="in-progress",
                assignee="dev2",
                created_at="2026-04-27T09:30:00Z",
                updated_at="2026-04-27T11:30:00Z",
            ),
        ]

        json_str = dashboard.generate_json_status(tasks)
        data = json.loads(json_str)

        assert "timestamp" in data
        assert data["summary"]["total"] == 2
        assert data["summary"]["done"] == 1
        assert data["summary"]["in_progress"] == 1
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "TASK-1"

    def test_scan_tasks_empty_repo(self, dashboard):
        """Test scanning tasks in empty repository."""
        tasks = dashboard.scan_tasks("project")
        assert tasks == []

    def test_scan_tasks_with_files(self, dashboard, temp_repo):
        """Test scanning tasks with actual task files."""
        # Create multiple task files
        for i in range(1, 4):
            task_file = (
                temp_repo / ".digital-artifacts" / "50-planning" / "project" / f"TASK_{i:03d}.md"
            )
            task_file.write_text(
                f"""---
task_id: TASK-{i:03d}
title: Task {i}
status: in-progress
assignee_hint: engineer
created: 2026-04-27T{9+i}:00:00Z
---

# Task: Task {i}
"""
            )

        tasks = dashboard.scan_tasks("project")
        assert len(tasks) == 3
        assert all(hasattr(t, "task_id") for t in tasks)

    def test_export_dashboard_with_output_dir(self, dashboard, temp_repo):
        """Test exporting dashboard with output directory."""
        output_dir = temp_repo / "output"
        output_dir.mkdir()

        tasks = [
            TaskStatus(
                task_id="TASK-001",
                title="Export Test",
                status="done",
                assignee="tester",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
        ]

        # Mock scan_tasks to return our test tasks
        dashboard.scan_tasks = lambda stage: tasks
        markdown, json_status = dashboard.export_dashboard("project", output_dir)

        assert (output_dir / "project-delivery-dashboard-project.md").exists()
        assert (output_dir / "project-delivery-status-project.json").exists()

        # Verify file contents
        md_content = (output_dir / "project-delivery-dashboard-project.md").read_text()
        assert "Export Test" in md_content

        json_content = (output_dir / "project-delivery-status-project.json").read_text()
        json_data = json.loads(json_content)
        assert json_data["summary"]["done"] == 1

    def test_security_audit_trail_in_dashboard(self, dashboard):
        """Test that dashboard includes security audit trail."""
        tasks = [
            TaskStatus(
                task_id="TASK-SEC",
                title="Security Task",
                status="review",
                assignee="security-expert",
                created_at="2026-04-27T09:00:00Z",
                updated_at="2026-04-27T11:00:00Z",
                pr_url="https://github.com/org/repo/pull/100",
                pr_approved=False,
            )
        ]

        markdown = dashboard.generate_markdown_dashboard(tasks)
        assert "Security & Audit Trail" in markdown
        assert "No tasks transition to `done`" in markdown
        assert "human approval" in markdown

    def test_recovery_status_in_dashboard(self, dashboard):
        """Test that dashboard mentions artifact recovery status."""
        markdown = dashboard.generate_markdown_dashboard([])
        assert "Recovery & Artifact Status" in markdown
        assert ".digital-runtime/handoffs/" in markdown
        assert ".digital-artifacts/" in markdown
        assert "✅" in markdown


class TestDashboardIntegration:
    """Integration tests for dashboard."""

    def test_full_workflow_visibility(self, dashboard, temp_repo):
        """Test full workflow visibility from planning to done."""
        # Create planning artifact
        task_file = temp_repo / ".digital-artifacts" / "50-planning" / "project" / "TASK_100.md"
        task_file.write_text(
            """---
task_id: TASK-THM-02
title: Implement approved scope
status: in-progress
assignee_hint: fullstack-engineer
created: 2026-04-27T09:00:00Z
---

# Task: Implement approved scope
"""
        )

        # Create handoff file
        handoff_file = (
            temp_repo / ".digital-runtime" / "handoffs" / "project" / "task-thm-02-handoff.yaml"
        )
        handoff_file.write_text(
            """schema: work_handoff_v1
task_id: TASK-THM-02
status: in-progress
pr_url: https://github.com/org/repo/pull/200
"""
        )

        # Scan and verify
        tasks = dashboard.scan_tasks("project")
        assert len(tasks) == 1
        task = tasks[0]
        assert task.task_id == "TASK-THM-02"
        assert task.status == "in-progress"
        assert task.pr_url == "https://github.com/org/repo/pull/200"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
