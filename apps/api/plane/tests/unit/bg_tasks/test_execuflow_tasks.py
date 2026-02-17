# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for ExecuFlow async Celery tasks.

Tests the decompose_issue_task and process_brain_dump_task
background tasks that handle AI provider calls asynchronously.
"""

import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry

from plane.db.models import Project, Issue, MicroTask, User, Workspace
from plane.bgtasks.execuflow_tasks import (
    decompose_issue_task,
    process_brain_dump_task,
)


@pytest.mark.unit
class TestDecomposeIssueTask:
    """Test the async decompose_issue_task Celery task."""

    @pytest.fixture
    def workspace(self, create_user):
        """Create a workspace for testing."""
        return Workspace.objects.create(
            name="Test Workspace",
            owner=create_user,
            slug="test-workspace",
        )

    @pytest.fixture
    def project(self, create_user, workspace):
        """Create a project for testing."""
        return Project.objects.create(
            name="Test Project",
            identifier="test-project",
            workspace=workspace,
            created_by=create_user,
        )

    @pytest.fixture
    def issue(self, workspace, project, create_user):
        """Create an issue for testing."""
        return Issue.objects.create(
            name="Complex Feature Implementation",
            description_stripped="Implement user authentication with OAuth2",
            workspace=workspace,
            project=project,
            created_by=create_user,
        )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.decompose_issue_with_ai")
    def test_decompose_issue_task_success(
        self, mock_decompose_ai, mock_broadcast, create_user, workspace, project, issue
    ):
        """Test successful decomposition of an issue into micro-tasks."""
        # Arrange
        mock_decompose_ai.return_value = [
            {
                "title": "Setup OAuth2 client configuration",
                "description": "Configure OAuth2 client ID and secret",
                "energy_level": "low",
                "estimated_minutes": 10,
            },
            {
                "title": "Implement authorization flow",
                "description": "Create redirect and callback handlers",
                "energy_level": "medium",
                "estimated_minutes": 15,
            },
        ]

        # Act - Call the task directly (not .delay())
        result = decompose_issue_task(
            issue_id=str(issue.id),
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["issue_id"] == str(issue.id)
        assert result["created_count"] == 2

        # Verify micro-tasks were created
        micro_tasks = MicroTask.objects.filter(issue=issue)
        assert micro_tasks.count() == 2
        assert micro_tasks[0].title == "Setup OAuth2 client configuration"
        assert micro_tasks[0].energy_level == "low"
        assert micro_tasks[0].estimated_minutes == 10
        assert micro_tasks[1].title == "Implement authorization flow"

        # Verify AI was called with correct params
        mock_decompose_ai.assert_called_once_with(
            issue_title="Complex Feature Implementation",
            issue_description="Implement user authentication with OAuth2",
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
        )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.decompose_issue_with_ai")
    def test_decompose_issue_task_empty_result(
        self, mock_decompose_ai, mock_broadcast, create_user, workspace, project, issue
    ):
        """Test handling when AI returns empty result."""
        # Arrange
        mock_decompose_ai.return_value = []

        # Act
        result = decompose_issue_task(
            issue_id=str(issue.id),
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["created_count"] == 0
        assert MicroTask.objects.filter(issue=issue).count() == 0

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    def test_decompose_issue_task_issue_not_found(self, mock_broadcast, create_user, workspace):
        """Test error handling when issue doesn't exist."""
        # Arrange
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # Act
        result = decompose_issue_task(
            issue_id=non_existent_id,
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.decompose_issue_with_ai")
    def test_decompose_issue_task_ai_failure_retries(
        self, mock_decompose_ai, mock_broadcast, create_user, workspace, project, issue
    ):
        """Test that task retries on AI provider failure."""
        # Arrange
        mock_decompose_ai.side_effect = RuntimeError("API rate limit exceeded")

        # Act & Assert - Should raise Retry exception
        with pytest.raises(Retry):
            decompose_issue_task.apply(
                args=[
                    str(issue.id),
                    5,
                    "low",
                    15,
                    str(workspace.id),
                    str(create_user.id),
                ]
            )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.decompose_issue_with_ai")
    def test_decompose_issue_task_preserves_sort_order(
        self, mock_decompose_ai, mock_broadcast, create_user, workspace, project, issue
    ):
        """Test that micro-tasks maintain correct sort order."""
        # Arrange
        mock_decompose_ai.return_value = [
            {"title": "Step 1", "description": "First", "energy_level": "low", "estimated_minutes": 5},
            {"title": "Step 2", "description": "Second", "energy_level": "low", "estimated_minutes": 5},
            {"title": "Step 3", "description": "Third", "energy_level": "low", "estimated_minutes": 5},
        ]

        # Act
        decompose_issue_task(
            issue_id=str(issue.id),
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Assert
        tasks = MicroTask.objects.filter(issue=issue).order_by("sort_order")
        assert [t.sort_order for t in tasks] == [0, 1, 2]
        assert [t.title for t in tasks] == ["Step 1", "Step 2", "Step 3"]


@pytest.mark.unit
class TestProcessBrainDumpTask:
    """Test the async process_brain_dump_task Celery task."""

    @pytest.fixture
    def workspace(self, create_user):
        """Create a workspace for testing."""
        return Workspace.objects.create(
            name="Test Workspace",
            owner=create_user,
            slug="test-workspace",
        )

    @pytest.fixture
    def project(self, create_user, workspace):
        """Create a project for testing."""
        return Project.objects.create(
            name="Test Project",
            identifier="test-project",
            workspace=workspace,
            created_by=create_user,
        )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_process_brain_dump_task_success_with_auto_create(
        self, mock_extract_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test successful brain dump processing with auto-create enabled."""
        # Arrange
        raw_text = "Need to fix login bug. Also update documentation. Deploy to staging."
        mock_extract_ai.return_value = [
            {"title": "Fix login bug", "description": "Investigate and fix login issues"},
            {"title": "Update documentation", "description": "Update API documentation"},
            {"title": "Deploy to staging", "description": "Deploy latest changes to staging environment"},
        ]

        # Act
        result = process_brain_dump_task(
            raw_text=raw_text,
            source="voice",
            auto_create_issues=True,
            workspace_id=str(workspace.id),
            project_id=str(project.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["extracted_count"] == 3
        assert result["created_issues_count"] == 3

        # Verify issues were created
        issues = Issue.objects.filter(project=project)
        assert issues.count() == 3
        assert issues[0].name == "Fix login bug"
        assert issues[1].name == "Update documentation"
        assert issues[2].name == "Deploy to staging"

        # Verify AI was called
        mock_extract_ai.assert_called_once_with(raw_text)

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_process_brain_dump_task_success_without_auto_create(
        self, mock_extract_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test brain dump processing without auto-creating issues."""
        # Arrange
        raw_text = "Review PR 123. Test new feature. Schedule meeting."
        mock_extract_ai.return_value = [
            {"title": "Review PR 123", "description": "Review pull request 123"},
            {"title": "Test new feature", "description": "Test the new feature implementation"},
        ]

        # Act
        result = process_brain_dump_task(
            raw_text=raw_text,
            source="text",
            auto_create_issues=False,
            workspace_id=str(workspace.id),
            project_id=str(project.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["extracted_count"] == 2
        assert result["created_issues_count"] == 0

        # Verify no issues were created
        assert Issue.objects.filter(project=project).count() == 0

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_process_brain_dump_task_empty_text(
        self, mock_extract_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test handling of empty or whitespace-only text."""
        # Arrange
        mock_extract_ai.return_value = []

        # Act
        result = process_brain_dump_task(
            raw_text="   ",
            source="text",
            auto_create_issues=True,
            workspace_id=str(workspace.id),
            project_id=str(project.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["extracted_count"] == 0
        assert result["created_issues_count"] == 0

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_process_brain_dump_task_ai_failure_retries(
        self, mock_extract_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test that task retries on AI provider failure."""
        # Arrange
        mock_extract_ai.side_effect = RuntimeError("AI service unavailable")

        # Act & Assert - Should raise Retry exception
        with pytest.raises(Retry):
            process_brain_dump_task.apply(
                args=[
                    "Some text",
                    "text",
                    True,
                    str(workspace.id),
                    str(project.id),
                    str(create_user.id),
                ]
            )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    def test_process_brain_dump_task_project_not_found(self, mock_broadcast, create_user, workspace):
        """Test error handling when project doesn't exist."""
        # Arrange
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # Act
        result = process_brain_dump_task(
            raw_text="Some text",
            source="text",
            auto_create_issues=True,
            workspace_id=str(workspace.id),
            project_id=non_existent_id,
            user_id=str(create_user.id),
        )

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_process_brain_dump_task_max_items_limit(
        self, mock_extract_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test that only first 10 items are processed."""
        # Arrange - Return 15 items, should only create 10
        mock_extract_ai.return_value = [
            {"title": f"Task {i}", "description": f"Description {i}"}
            for i in range(15)
        ]

        # Act
        result = process_brain_dump_task(
            raw_text="Long brain dump with many items...",
            source="voice",
            auto_create_issues=True,
            workspace_id=str(workspace.id),
            project_id=str(project.id),
            user_id=str(create_user.id),
        )

        # Assert
        assert result["created_issues_count"] <= 10
        assert Issue.objects.filter(project=project).count() <= 10
