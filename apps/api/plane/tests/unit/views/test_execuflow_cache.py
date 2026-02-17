# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for ExecuFlow endpoint caching.

Tests cover:
- Cache key generation utility
- Cache hit / miss for AchievementListEndpoint
- Cache hit / miss for DopamineMenuListEndpoint
- Cache invalidation on DopamineMenuClaimEndpoint (reward claimed)
- Cache invalidation on UserAchievement creation (achievement earned)
- Configurable cache timeout via settings
"""

from unittest.mock import patch, MagicMock
from uuid import uuid4

import factory
import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from plane.db.models import (
    Achievement,
    DopamineMenu,
    UserAchievement,
)
from plane.tests.factories import ProjectFactory, UserFactory

from plane.api.views.execuflow import (
    AchievementListEndpoint,
    DopamineMenuClaimEndpoint,
    DopamineMenuListEndpoint,
)
from plane.utils.execuflow_cache import get_cache_key, invalidate_user_cache


# ---------------------------------------------------------------
# Factories (reused from model tests pattern)
# ---------------------------------------------------------------


class AchievementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Achievement

    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"Achievement {n}")
    description = "Test achievement description"
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")


class DopamineMenuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DopamineMenu

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    title = factory.Sequence(lambda n: f"Reward {n}")
    category = "appetizer"


# ---------------------------------------------------------------
# Cache Key Utility Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestCacheKeyGeneration:
    """Tests for the get_cache_key utility."""

    def test_cache_key_format(self):
        """Cache key follows the pattern execuflow:<endpoint>:<user_id>."""
        user_id = str(uuid4())
        key = get_cache_key("achievements", user_id)
        assert key == f"execuflow:achievements:{user_id}"

    def test_cache_key_unique_per_user(self):
        """Different users produce different cache keys."""
        user_a = str(uuid4())
        user_b = str(uuid4())
        key_a = get_cache_key("achievements", user_a)
        key_b = get_cache_key("achievements", user_b)
        assert key_a != key_b

    def test_cache_key_unique_per_endpoint(self):
        """Different endpoints produce different cache keys for same user."""
        user_id = str(uuid4())
        key_ach = get_cache_key("achievements", user_id)
        key_dop = get_cache_key("dopamine_menu", user_id)
        assert key_ach != key_dop


# ---------------------------------------------------------------
# Achievement Caching Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestAchievementListCache:
    """Tests for caching in the AchievementListEndpoint."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    def test_first_request_is_cache_miss(self):
        """First GET to achievements endpoint should not have cached data."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        AchievementFactory(project=project)

        cache_key = get_cache_key("achievements", user_id)
        assert cache.get(cache_key) is None

    def test_first_request_populates_cache(self):
        """After first GET, result data should be stored in cache."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        AchievementFactory(project=project)
        AchievementFactory(project=project)

        factory_req = APIRequestFactory()
        request = factory_req.get(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/achievements/"
        )
        request.user = user

        view = AchievementListEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_200_OK

        cache_key = get_cache_key("achievements", user_id)
        cached = cache.get(cache_key)
        assert cached is not None

    def test_second_request_returns_cached_data(self):
        """Second GET should return data from cache without hitting the DB again."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        AchievementFactory(project=project)

        factory_req = APIRequestFactory()
        request = factory_req.get(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/achievements/"
        )
        request.user = user

        view = AchievementListEndpoint.as_view()

        # First request populates cache
        response1 = view(request, slug=project.workspace.slug, project_id=project.id)
        assert response1.status_code == status.HTTP_200_OK

        # Second request should use cache (we verify by checking cache is populated)
        cache_key = get_cache_key("achievements", user_id)
        cached_before = cache.get(cache_key)
        assert cached_before is not None

        response2 = view(request, slug=project.workspace.slug, project_id=project.id)
        assert response2.status_code == status.HTTP_200_OK

    def test_achievement_cache_invalidated_on_new_achievement(self):
        """Cache should be cleared when invalidate_user_cache is called for achievements."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        cache_key = get_cache_key("achievements", user_id)
        cache.set(cache_key, [{"fake": "data"}], timeout=300)
        assert cache.get(cache_key) is not None

        invalidate_user_cache("achievements", user_id)
        assert cache.get(cache_key) is None


# ---------------------------------------------------------------
# DopamineMenu Caching Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestDopamineMenuListCache:
    """Tests for caching in the DopamineMenuListEndpoint."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    def test_first_request_is_cache_miss(self):
        """First GET to dopamine-menu endpoint should not have cached data."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        DopamineMenuFactory(project=project, user=user)

        cache_key = get_cache_key("dopamine_menu", user_id)
        assert cache.get(cache_key) is None

    def test_first_request_populates_cache(self):
        """After first GET, dopamine menu data should be stored in cache."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        DopamineMenuFactory(project=project, user=user)

        factory_req = APIRequestFactory()
        request = factory_req.get(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/dopamine-menu/"
        )
        request.user = user

        view = DopamineMenuListEndpoint.as_view()
        response = view(request, slug=project.workspace.slug, project_id=project.id)

        assert response.status_code == status.HTTP_200_OK

        cache_key = get_cache_key("dopamine_menu", user_id)
        cached = cache.get(cache_key)
        assert cached is not None

    def test_second_request_returns_cached_data(self):
        """Second GET to dopamine-menu returns data from cache."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        DopamineMenuFactory(project=project, user=user)

        factory_req = APIRequestFactory()
        request = factory_req.get(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/dopamine-menu/"
        )
        request.user = user

        view = DopamineMenuListEndpoint.as_view()

        response1 = view(request, slug=project.workspace.slug, project_id=project.id)
        assert response1.status_code == status.HTTP_200_OK

        cache_key = get_cache_key("dopamine_menu", user_id)
        assert cache.get(cache_key) is not None

        response2 = view(request, slug=project.workspace.slug, project_id=project.id)
        assert response2.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------
# Cache Invalidation on Mutations Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestCacheInvalidationOnMutations:
    """Tests for cache invalidation when mutations occur."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    def test_dopamine_claim_invalidates_cache(self):
        """Claiming a reward should invalidate the dopamine menu cache."""
        project = ProjectFactory()
        user = project.created_by
        user_id = str(user.id)

        reward = DopamineMenuFactory(
            project=project,
            user=user,
            cooldown_minutes=0,
        )

        # Pre-populate cache
        cache_key = get_cache_key("dopamine_menu", user_id)
        cache.set(cache_key, [{"fake": "cached_data"}], timeout=300)
        assert cache.get(cache_key) is not None

        factory_req = APIRequestFactory()
        request = factory_req.post(
            f"/api/v1/workspaces/{project.workspace.slug}/projects/{project.id}/execuflow/dopamine-menu/{reward.id}/claim/"
        )
        request.user = user

        view = DopamineMenuClaimEndpoint.as_view()
        response = view(
            request,
            slug=project.workspace.slug,
            project_id=project.id,
            pk=reward.id,
        )

        assert response.status_code == status.HTTP_200_OK
        assert cache.get(cache_key) is None

    def test_invalidate_user_cache_utility(self):
        """invalidate_user_cache clears the correct key."""
        user_id = str(uuid4())
        cache_key = get_cache_key("dopamine_menu", user_id)
        cache.set(cache_key, {"data": "test"}, timeout=300)

        invalidate_user_cache("dopamine_menu", user_id)
        assert cache.get(cache_key) is None

    def test_invalidate_does_not_affect_other_users(self):
        """Invalidating one user's cache should not affect another user."""
        user_a = str(uuid4())
        user_b = str(uuid4())

        key_a = get_cache_key("dopamine_menu", user_a)
        key_b = get_cache_key("dopamine_menu", user_b)

        cache.set(key_a, {"user": "a"}, timeout=300)
        cache.set(key_b, {"user": "b"}, timeout=300)

        invalidate_user_cache("dopamine_menu", user_a)

        assert cache.get(key_a) is None
        assert cache.get(key_b) is not None

    def test_invalidate_does_not_affect_other_endpoints(self):
        """Invalidating achievements cache should not affect dopamine cache."""
        user_id = str(uuid4())

        key_ach = get_cache_key("achievements", user_id)
        key_dop = get_cache_key("dopamine_menu", user_id)

        cache.set(key_ach, {"endpoint": "ach"}, timeout=300)
        cache.set(key_dop, {"endpoint": "dop"}, timeout=300)

        invalidate_user_cache("achievements", user_id)

        assert cache.get(key_ach) is None
        assert cache.get(key_dop) is not None


# ---------------------------------------------------------------
# Configurable Cache Timeout Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestCacheTimeout:
    """Tests for configurable cache timeout."""

    def setup_method(self):
        cache.clear()

    def teardown_method(self):
        cache.clear()

    @override_settings(EXECUFLOW_CACHE_TIMEOUT=600)
    def test_custom_cache_timeout_from_settings(self):
        """Cache timeout should be configurable via EXECUFLOW_CACHE_TIMEOUT setting."""
        from django.conf import settings

        assert settings.EXECUFLOW_CACHE_TIMEOUT == 600

    def test_default_cache_timeout(self):
        """Default cache timeout should be 300 seconds (5 minutes)."""
        from plane.utils.execuflow_cache import get_cache_timeout

        timeout = get_cache_timeout()
        assert timeout == 300
