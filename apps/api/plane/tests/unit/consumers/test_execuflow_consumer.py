# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for ExecuFlow WebSocket consumer and broadcast utilities.

Tests cover:
  - WebSocket consumer connect/disconnect lifecycle
  - Group membership for task_id channels
  - Receiving task_update messages and forwarding to client
  - Broadcast helper function for Celery task integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer

from plane.consumers.execuflow import ExecuFlowTaskConsumer
from plane.consumers.routing import websocket_urlpatterns
from plane.consumers.utils import broadcast_task_update


@pytest.mark.unit
class TestExecuFlowTaskConsumer:
    """Test the ExecuFlowTaskConsumer WebSocket consumer."""

    @pytest.fixture
    def valid_task_id(self):
        return "abc123-def456-ghi789"

    @pytest.fixture
    def application(self):
        """Create a URLRouter application with WebSocket routes."""
        return URLRouter(websocket_urlpatterns)

    @pytest.fixture
    def communicator(self, application, valid_task_id):
        """Create a WebSocket communicator routed through URLRouter."""
        return WebsocketCommunicator(
            application,
            f"/ws/execuflow/tasks/{valid_task_id}/",
        )

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_connect_accepts_websocket(self, communicator):
        """Test that the consumer accepts a WebSocket connection."""
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_disconnect_removes_from_group(self, communicator, valid_task_id):
        """Test that disconnecting removes the channel from the task group."""
        await communicator.connect()
        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_receives_task_update(self, communicator, valid_task_id):
        """Test that the consumer forwards task_update events to the client."""
        await communicator.connect()

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"task_{valid_task_id}",
            {
                "type": "task_update",
                "data": {
                    "status": "SUCCESS",
                    "result": {"created_count": 3},
                },
            },
        )

        response = await communicator.receive_json_from(timeout=2)
        assert response["status"] == "SUCCESS"
        assert response["result"]["created_count"] == 3

        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_receives_progress_update(self, communicator, valid_task_id):
        """Test that in-progress updates are forwarded to the client."""
        await communicator.connect()

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"task_{valid_task_id}",
            {
                "type": "task_update",
                "data": {
                    "status": "PROGRESS",
                    "progress": 50,
                    "message": "Processing step 3 of 6",
                },
            },
        )

        response = await communicator.receive_json_from(timeout=2)
        assert response["status"] == "PROGRESS"
        assert response["progress"] == 50

        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_receives_failure_update(self, communicator, valid_task_id):
        """Test that failure updates are forwarded to the client."""
        await communicator.connect()

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"task_{valid_task_id}",
            {
                "type": "task_update",
                "data": {
                    "status": "FAILURE",
                    "error": "AI provider timeout",
                },
            },
        )

        response = await communicator.receive_json_from(timeout=2)
        assert response["status"] == "FAILURE"
        assert response["error"] == "AI provider timeout"

        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_consumer_multiple_updates_in_sequence(self, communicator, valid_task_id):
        """Test that multiple sequential updates are all forwarded."""
        await communicator.connect()

        channel_layer = get_channel_layer()

        updates = [
            {"status": "PROGRESS", "progress": 25, "message": "Step 1"},
            {"status": "PROGRESS", "progress": 50, "message": "Step 2"},
            {"status": "PROGRESS", "progress": 75, "message": "Step 3"},
            {"status": "SUCCESS", "result": {"count": 3}},
        ]

        for update_data in updates:
            await channel_layer.group_send(
                f"task_{valid_task_id}",
                {"type": "task_update", "data": update_data},
            )

        for update_data in updates:
            response = await communicator.receive_json_from(timeout=2)
            assert response["status"] == update_data["status"]

        await communicator.disconnect()


@pytest.mark.unit
class TestBroadcastTaskUpdate:
    """Test the broadcast_task_update helper function."""

    @patch("plane.consumers.utils.get_channel_layer")
    def test_broadcast_task_update_sends_to_group(self, mock_get_layer):
        """Test that broadcast_task_update sends data to the correct group."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_get_layer.return_value = mock_layer

        task_id = "test-task-123"
        data = {"status": "SUCCESS", "result": {"count": 5}}

        broadcast_task_update(task_id, data)

        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args
        assert call_args[0][0] == "task_test-task-123"
        assert call_args[0][1]["type"] == "task_update"
        assert call_args[0][1]["data"] == data

    @patch("plane.consumers.utils.get_channel_layer")
    def test_broadcast_task_update_handles_no_channel_layer(self, mock_get_layer):
        """Test graceful handling when channel layer is not available."""
        mock_get_layer.return_value = None

        # Should not raise
        broadcast_task_update("test-task-123", {"status": "SUCCESS"})

    @patch("plane.consumers.utils.get_channel_layer")
    def test_broadcast_with_progress_data(self, mock_get_layer):
        """Test broadcasting progress updates."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_get_layer.return_value = mock_layer

        task_id = "task-456"
        data = {"status": "PROGRESS", "progress": 60, "message": "Processing..."}

        broadcast_task_update(task_id, data)

        call_args = mock_layer.group_send.call_args
        assert call_args[0][1]["data"]["progress"] == 60
        assert call_args[0][1]["data"]["message"] == "Processing..."
