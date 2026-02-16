# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Caching utilities for ExecuFlow read-heavy endpoints.

Provides per-user cache key generation and invalidation helpers
for achievement and dopamine-menu list endpoints.
"""

from django.conf import settings
from django.core.cache import cache


def get_cache_key(endpoint: str, user_id: str) -> str:
    """Build a per-user cache key for an ExecuFlow endpoint."""
    return f"execuflow:{endpoint}:{user_id}"


def get_cache_timeout() -> int:
    """Return the cache timeout in seconds, configurable via settings."""
    return getattr(settings, "EXECUFLOW_CACHE_TIMEOUT", 300)


def invalidate_user_cache(endpoint: str, user_id: str) -> None:
    """Delete the cached response for a specific user and endpoint."""
    cache.delete(get_cache_key(endpoint, user_id))
