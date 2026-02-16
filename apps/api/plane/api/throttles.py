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


class AIBurstThrottle(UserRateThrottle):
    """
    Burst limit for AI endpoints - 3 requests per second.

    This prevents rapid-fire requests that could overwhelm AI services
    or indicate malicious automation. Works in conjunction with
    AIEndpointThrottle for layered protection.
    """

    scope = "ai_burst"
    rate = os.environ.get("AI_BURST_RATE_LIMIT", "3/second")
