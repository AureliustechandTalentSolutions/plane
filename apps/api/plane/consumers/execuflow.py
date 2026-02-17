# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow WebSocket Consumer for Real-Time Task Updates.

Provides a WebSocket endpoint that clients can connect to for receiving
real-time updates on async AI task processing (decompose, brain_dump).
Celery tasks broadcast updates to the channel group, and this consumer
forwards them to connected WebSocket clients.
"""

import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger("plane.consumers")


class ExecuFlowTaskConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for ExecuFlow async task updates.

    Clients connect to ws/execuflow/tasks/<task_id>/ to receive
    real-time status updates for a specific Celery task.
    """

    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.group_name = f"task_{self.task_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def task_update(self, event):
        """Handle task_update messages from the channel layer."""
        await self.send_json(event["data"])
