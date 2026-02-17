# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Integration tests for ExecuFlow Celery tasks with WebSocket broadcasting.

Tests that Celery tasks call broadcast_task_update to send real-time
updates through the WebSocket channel layer.
"""

import pytest
from unittest.mock import patch, MagicMock

from plane.db.models import Project, Issue, MicroTask, User, Workspace
from plane.bgtasks.execuflow_tasks import (
    decompose_issue_task,
    process_brain_dump_task,
)


@pytest.mark.unit
class TestDecomposeIssueTaskBroadcast:
    """Test that decompose_issue_task broadcasts updates via WebSocket."""

    @pytest.fixture
    def workspace(self, create_user):
        return Workspace.objects.create(
            name="Test Workspace",
            owner=create_user,
            slug="test-ws-broadcast",
        )

    @pytest.fixture
    def project(self, create_user, workspace):
        return Project.objects.create(
            name="Test Project",
            identifier="test-broadcast",
            workspace=workspace,
            created_by=create_user,
        )

    @pytest.fixture
    def issue(self, workspace, project, create_user):
        return Issue.objects.create(
            name="WebSocket Test Issue",
            description_stripped="Testing WebSocket broadcasting",
            workspace=workspace,
            project=project,
            created_by=create_user,
        )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.decompose_issue_with_ai")
    def test_decompose_broadcasts_success(
        self, mock_ai, mock_broadcast, create_user, workspace, project, issue
    ):
        """Test that successful decomposition broadcasts the result."""
        mock_ai.return_value = [
            {"title": "Step 1", "description": "First step", "energy_level": "low", "estimated_minutes": 5},
        ]

        result = decompose_issue_task(
            issue_id=str(issue.id),
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Verify broadcast was called with SUCCESS status
        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args
        broadcast_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("data")
        assert broadcast_data["status"] == "SUCCESS"

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    def test_decompose_broadcasts_error_on_missing_issue(
        self, mock_broadcast, create_user, workspace
    ):
        """Test that missing issue broadcasts an error."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        result = decompose_issue_task(
            issue_id=non_existent_id,
            max_steps=5,
            target_energy="low",
            max_minutes_per_step=15,
            workspace_id=str(workspace.id),
            user_id=str(create_user.id),
        )

        # Verify broadcast was called with error status
        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args
        broadcast_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("data")
        assert broadcast_data["status"] == "error"


@pytest.mark.unit
class TestProcessBrainDumpTaskBroadcast:
    """Test that process_brain_dump_task broadcasts updates via WebSocket."""

    @pytest.fixture
    def workspace(self, create_user):
        return Workspace.objects.create(
            name="Test Workspace",
            owner=create_user,
            slug="test-ws-braindump",
        )

    @pytest.fixture
    def project(self, create_user, workspace):
        return Project.objects.create(
            name="Test Project",
            identifier="test-braindump-bc",
            workspace=workspace,
            created_by=create_user,
        )

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    @patch("plane.bgtasks.execuflow_tasks.extract_actions_with_ai")
    def test_brain_dump_broadcasts_success(
        self, mock_ai, mock_broadcast, create_user, workspace, project
    ):
        """Test that successful brain dump processing broadcasts the result."""
        mock_ai.return_value = [
            {"title": "Task 1", "description": "First task"},
        ]

        result = process_brain_dump_task(
            raw_text="Do the thing",
            source="text",
            auto_create_issues=False,
            workspace_id=str(workspace.id),
            project_id=str(project.id),
            user_id=str(create_user.id),
        )

        # Verify broadcast was called with SUCCESS status
        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args
        broadcast_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("data")
        assert broadcast_data["status"] == "SUCCESS"

    @pytest.mark.django_db
    @patch("plane.bgtasks.execuflow_tasks.broadcast_task_update")
    def test_brain_dump_broadcasts_error_on_missing_project(
        self, mock_broadcast, create_user, workspace
    ):
        """Test that missing project broadcasts an error."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        result = process_brain_dump_task(
            raw_text="Some text",
            source="text",
            auto_create_issues=True,
            workspace_id=str(workspace.id),
            project_id=non_existent_id,
            user_id=str(create_user.id),
        )

        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args
        broadcast_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("data")
        assert broadcast_data["status"] == "error"
