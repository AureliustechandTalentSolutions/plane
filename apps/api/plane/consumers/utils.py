# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Utility functions for broadcasting task updates via Django Channels.

Used by Celery tasks to send real-time updates to WebSocket clients.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("plane.consumers")


def broadcast_task_update(task_id: str, data: dict) -> None:
    """
    Broadcast a task update to all WebSocket clients listening for this task.

    Args:
        task_id: The Celery task ID to broadcast to.
        data: The update payload (status, result, progress, error, etc).
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("broadcast_task_update: No channel layer configured, skipping broadcast")
        return

    async_to_sync(channel_layer.group_send)(
        f"task_{task_id}",
        {
            "type": "task_update",
            "data": data,
        },
    )
