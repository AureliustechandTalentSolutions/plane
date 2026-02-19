# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
White Box Security Tests for ExecuFlowTaskStatusEndpoint

Tests cover:
- UUID format validation on task_id parameter
- Task ownership verification via cache-based tracking
- Rate limiting on the status polling endpoint (30/minute)
- Ownership storage by decompose and brain_dump endpoints
- Cross-user isolation (user cannot see another user's tasks)
"""

from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIRequestFactory

from plane.api.views.execuflow import (
    ExecuFlowTaskStatusEndpoint,
    MicroStepDecomposeEndpoint,
    BrainDumpEndpoint,
    _is_valid_uuid,
    _store_task_ownership,
    _verify_task_ownership,
    TASK_OWNER_CACHE_TIMEOUT,
)
from plane.tests.factories import ProjectFactory, UserFactory


# ---------------------------------------------------------------
# Helper Utility Tests
# ---------------------------------------------------------------


class TestIsValidUUID:
    """Tests for the _is_valid_uuid helper."""

    def test_valid_uuid4(self):
        assert _is_valid_uuid(str(uuid4())) is True

    def test_valid_uuid_with_hyphens(self):
        assert _is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_uuid_without_hyphens(self):
        assert _is_valid_uuid("550e8400e29b41d4a716446655440000") is True

    def test_invalid_short_string(self):
        assert _is_valid_uuid("abc123") is False

    def test_invalid_empty_string(self):
        assert _is_valid_uuid("") is False

    def test_invalid_none(self):
        assert _is_valid_uuid(None) is False

    def test_invalid_sql_injection_attempt(self):
        assert _is_valid_uuid("'; DROP TABLE--") is False

    def test_invalid_path_traversal(self):
        assert _is_valid_uuid("../../etc/passwd") is False

    def test_invalid_celery_task_id_format(self):
        """Non-UUID Celery task IDs should be rejected."""
        assert _is_valid_uuid("celery-task-id-12345") is False


# ---------------------------------------------------------------
# Task Ownership Cache Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestTaskOwnership:
    """Tests for _store_task_ownership and _verify_task_ownership."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    def test_store_and_verify_ownership(self):
        """Stored ownership can be verified by the same user."""
        task_id = str(uuid4())
        user_id = str(uuid4())

        _store_task_ownership(task_id, user_id)
        assert _verify_task_ownership(task_id, user_id) is True

    def test_verify_wrong_user_denied(self):
        """A different user cannot verify ownership of another user's task."""
        task_id = str(uuid4())
        owner_id = str(uuid4())
        other_id = str(uuid4())

        _store_task_ownership(task_id, owner_id)
        assert _verify_task_ownership(task_id, other_id) is False

    def test_verify_no_record_denied(self):
        """Tasks with no ownership record are denied by default."""
        task_id = str(uuid4())
        user_id = str(uuid4())

        assert _verify_task_ownership(task_id, user_id) is False

    def test_ownership_cache_key_format(self):
        """Ownership is stored under the correct cache key."""
        task_id = str(uuid4())
        user_id = str(uuid4())

        _store_task_ownership(task_id, user_id)

        raw = cache.get(f"execuflow_task_owner:{task_id}")
        assert raw == user_id

    def test_ownership_timeout_matches_constant(self):
        """Ownership cache entry should use the configured timeout."""
        task_id = str(uuid4())
        user_id = str(uuid4())

        with patch.object(cache, "set") as mock_set:
            _store_task_ownership(task_id, user_id)
            mock_set.assert_called_once_with(
                f"execuflow_task_owner:{task_id}",
                user_id,
                timeout=TASK_OWNER_CACHE_TIMEOUT,
            )


# ---------------------------------------------------------------
# Task Status Endpoint Security Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestTaskStatusEndpointSecurity:
    """Security tests for ExecuFlowTaskStatusEndpoint."""

    def setup_method(self):
        cache.clear()
        self.factory = APIRequestFactory()

    def teardown_method(self):
        cache.clear()

    def _make_request(self, user, slug, project_id, task_id=None):
        """Helper to create an authenticated GET request."""
        url = f"/api/v1/workspaces/{slug}/projects/{project_id}/execuflow/task-status/"
        if task_id:
            url += f"?task_id={task_id}"
        request = self.factory.get(url)
        request.user = user
        return request

    def test_missing_task_id_returns_400(self):
        """Request without task_id query param returns 400."""
        project = ProjectFactory()
        user = project.created_by

        request = self._make_request(user, project.workspace.slug, project.id)
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "task_id parameter is required"

    def test_invalid_uuid_returns_404(self):
        """Non-UUID task_id returns 404 (not 400, to prevent enumeration info leak)."""
        project = ProjectFactory()
        user = project.created_by

        request = self._make_request(
            user, project.workspace.slug, project.id, task_id="not-a-uuid"
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Not found"

    def test_sql_injection_task_id_returns_404(self):
        """SQL injection attempt in task_id returns 404."""
        project = ProjectFactory()
        user = project.created_by

        request = self._make_request(
            user, project.workspace.slug, project.id, task_id="'; DROP TABLE--"
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unowned_task_returns_404(self):
        """Valid UUID for a task the user doesn't own returns 404."""
        project = ProjectFactory()
        user = project.created_by

        fake_task_id = str(uuid4())
        # No ownership stored for this task
        request = self._make_request(
            user, project.workspace.slug, project.id, task_id=fake_task_id
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Not found"

    def test_other_users_task_returns_404(self):
        """User cannot access another user's task -- cross-user isolation."""
        project = ProjectFactory()
        owner = project.created_by
        attacker = UserFactory()

        task_id = str(uuid4())
        _store_task_ownership(task_id, owner.id)

        # Attacker tries to check owner's task
        request = self._make_request(
            attacker, project.workspace.slug, project.id, task_id=task_id
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("plane.api.views.execuflow.AsyncResult")
    def test_owned_task_returns_200(self, mock_async_result_cls):
        """User who owns the task can successfully check its status."""
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"status": "success", "created_count": 3}
        mock_async_result_cls.return_value = mock_result

        project = ProjectFactory()
        user = project.created_by

        task_id = str(uuid4())
        _store_task_ownership(task_id, user.id)

        request = self._make_request(
            user, project.workspace.slug, project.id, task_id=task_id
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == task_id
        assert response.data["status"] == "SUCCESS"
        assert response.data["result"]["created_count"] == 3

    @patch("plane.api.views.execuflow.AsyncResult")
    def test_pending_task_returns_processing_message(self, mock_async_result_cls):
        """A pending task returns status with processing message."""
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_result.ready.return_value = False
        mock_async_result_cls.return_value = mock_result

        project = ProjectFactory()
        user = project.created_by

        task_id = str(uuid4())
        _store_task_ownership(task_id, user.id)

        request = self._make_request(
            user, project.workspace.slug, project.id, task_id=task_id
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "PENDING"
        assert response.data["message"] == "Task is still processing"

    @patch("plane.api.views.execuflow.AsyncResult")
    def test_failed_task_returns_error(self, mock_async_result_cls):
        """A failed task returns status with error details."""
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.info = Exception("AI provider timeout")
        mock_async_result_cls.return_value = mock_result

        project = ProjectFactory()
        user = project.created_by

        task_id = str(uuid4())
        _store_task_ownership(task_id, user.id)

        request = self._make_request(
            user, project.workspace.slug, project.id, task_id=task_id
        )
        view = ExecuFlowTaskStatusEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "FAILURE"
        assert "AI provider timeout" in response.data["error"]


# ---------------------------------------------------------------
# Task Ownership Integration: Decompose & BrainDump
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestDecomposeStoresOwnership:
    """Verify MicroStepDecomposeEndpoint stores task ownership."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    @patch("plane.api.views.execuflow.decompose_issue_task")
    def test_decompose_stores_task_ownership(self, mock_task):
        """After queuing decompose, task ownership should be in cache."""
        mock_result = MagicMock()
        mock_result.id = str(uuid4())
        mock_task.delay.return_value = mock_result

        project = ProjectFactory()
        user = project.created_by
        user.last_workspace_id = project.workspace_id
        user.save()

        # Create an issue to decompose
        from plane.db.models import Issue
        issue = Issue.objects.create(
            name="Test Issue",
            project=project,
            workspace=project.workspace,
            created_by=user,
        )

        factory_req = APIRequestFactory()
        request = factory_req.post(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/micro-tasks/decompose/",
            {"parent_issue_id": str(issue.id)},
            format="json",
        )
        request.user = user

        view = MicroStepDecomposeEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify ownership was stored
        assert _verify_task_ownership(mock_result.id, user.id) is True


@pytest.mark.django_db
class TestBrainDumpStoresOwnership:
    """Verify BrainDumpEndpoint stores task ownership."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    @patch("plane.api.views.execuflow.process_brain_dump_task")
    def test_brain_dump_stores_task_ownership(self, mock_task):
        """After queuing brain dump, task ownership should be in cache."""
        mock_result = MagicMock()
        mock_result.id = str(uuid4())
        mock_task.delay.return_value = mock_result

        project = ProjectFactory()
        user = project.created_by
        user.last_workspace_id = project.workspace_id
        user.save()

        factory_req = APIRequestFactory()
        request = factory_req.post(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/brain-dump/",
            {"raw_text": "Fix the login page and add tests.", "source": "text"},
            format="json",
        )
        request.user = user

        view = BrainDumpEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify ownership was stored
        assert _verify_task_ownership(mock_result.id, user.id) is True


# ---------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestTaskStatusRateLimiting:
    """Tests for TaskStatusThrottle on the status endpoint."""

    def test_throttle_class_is_applied(self):
        """Verify TaskStatusThrottle is in the endpoint's throttle_classes."""
        from plane.api.throttles import TaskStatusThrottle
        assert TaskStatusThrottle in ExecuFlowTaskStatusEndpoint.throttle_classes

    def test_throttle_rate_is_30_per_minute(self):
        """Verify the default rate is 30 requests per minute."""
        from plane.api.throttles import TaskStatusThrottle
        throttle = TaskStatusThrottle()
        assert throttle.rate == "30/minute"
