# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
WebSocket URL routing for ExecuFlow real-time updates.
"""

from django.urls import re_path

from plane.consumers.execuflow import ExecuFlowTaskConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/execuflow/tasks/(?P<task_id>[^/]+)/$",
        ExecuFlowTaskConsumer.as_asgi(),
    ),
]
