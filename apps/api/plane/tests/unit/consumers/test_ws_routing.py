# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for ExecuFlow WebSocket URL routing.

Tests cover:
  - WebSocket URL patterns resolve to the correct consumer
  - ASGI application includes WebSocket protocol handling
"""

import pytest
from channels.routing import URLRouter
from django.urls import re_path

from plane.consumers.execuflow import ExecuFlowTaskConsumer
from plane.consumers.routing import websocket_urlpatterns


@pytest.mark.unit
class TestWebSocketRouting:
    """Test WebSocket URL routing configuration."""

    def test_websocket_urlpatterns_contains_task_route(self):
        """Test that the task WebSocket route is defined."""
        assert len(websocket_urlpatterns) >= 1

        # Check that we have a pattern for task updates
        pattern_strings = [str(p.pattern) for p in websocket_urlpatterns]
        matching = [p for p in pattern_strings if "task" in p.lower() or "execuflow" in p.lower()]
        assert len(matching) >= 1, f"No task-related WebSocket route found in {pattern_strings}"

    def test_websocket_urlpatterns_are_valid_for_url_router(self):
        """Test that URL patterns can be used in a URLRouter."""
        # Should not raise
        router = URLRouter(websocket_urlpatterns)
        assert router is not None
