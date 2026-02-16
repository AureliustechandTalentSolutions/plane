# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Throttle classes for API rate limiting.

This module provides custom throttle classes for different
API endpoint categories, particularly AI-powered endpoints
that have higher cost and abuse potential.
"""

# Python imports
import os

# Third party imports
from rest_framework.throttling import UserRateThrottle


class AIEndpointThrottle(UserRateThrottle):
    """
    Rate limit for AI-powered endpoints - 10 requests per minute per user.

    This throttle is applied to endpoints that use LLM services (OpenAI, Anthropic)
    to prevent cost abuse and ensure fair resource allocation.

    Examples:
        - MicroTask decomposition endpoint
        - Brain dump processing endpoint
    """

    scope = "ai_endpoint"
    rate = os.environ.get("AI_ENDPOINT_RATE_LIMIT", "10/minute")

    def allow_request(self, request, view):
        """
        Override to add rate limit headers to response.

        Adds:
        - X-RateLimit-Remaining: Number of requests left
        - X-RateLimit-Reset: Unix timestamp when limit resets
        """
        allowed = super().allow_request(request, view)

        if allowed:
            now = self.timer()
            history = self.cache.get(self.key, [])

            # Remove expired entries
            while history and history[-1] <= now - self.duration:
                history.pop()

            num_requests = len(history)
            available = self.num_requests - num_requests
            reset_time = int(now + self.duration)

            # Add rate limit headers for client awareness
            request.META["X-RateLimit-Remaining"] = max(0, available)
            request.META["X-RateLimit-Reset"] = reset_time

        return allowed


class AIBurstThrottle(UserRateThrottle):
    """
    Burst limit for AI endpoints - 3 requests per second.

    This prevents rapid-fire requests that could overwhelm AI services
    or indicate malicious automation. Works in conjunction with
    AIEndpointThrottle for layered protection.
    """

    scope = "ai_burst"
    rate = os.environ.get("AI_BURST_RATE_LIMIT", "3/second")

    def allow_request(self, request, view):
        """
        Override to add burst limit headers to response.

        Adds:
        - X-RateLimit-Burst-Remaining: Number of burst requests left
        - X-RateLimit-Burst-Reset: Unix timestamp when burst limit resets
        """
        allowed = super().allow_request(request, view)

        if allowed:
            now = self.timer()
            history = self.cache.get(self.key, [])

            # Remove expired entries
            while history and history[-1] <= now - self.duration:
                history.pop()

            num_requests = len(history)
            available = self.num_requests - num_requests
            reset_time = int(now + self.duration)

            # Add burst-specific headers
            request.META["X-RateLimit-Burst-Remaining"] = max(0, available)
            request.META["X-RateLimit-Burst-Reset"] = reset_time

        return allowed


class TaskStatusThrottle(UserRateThrottle):
    """
    Rate limit for task status polling - 30 requests per minute per user.

    Prevents abuse of the status endpoint via rapid polling or
    task ID enumeration attacks.
    """

    scope = "task_status"
    rate = os.environ.get("TASK_STATUS_RATE_LIMIT", "30/minute")
