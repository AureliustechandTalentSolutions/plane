# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for ExecuFlow AI models.

Tests cover model creation, business methods, managers, constraints,
and the No-Shame Protocol (streaks pause, never break).
"""

from datetime import timedelta
from uuid import uuid4

import factory
import pytest
from django.utils import timezone

from plane.db.models import (
    Achievement,
    ContextSnapshot,
    DopamineMenu,
    FocusSession,
    Issue,
    MicroTask,
    Streak,
    UserAchievement,
)
from plane.tests.factories import ProjectFactory, UserFactory

# ---------------------------------------------------------------
# Factories for ExecuFlow models
# ---------------------------------------------------------------


class IssueFactory(factory.django.DjangoModelFactory):
    """Minimal Issue factory for ExecuFlow tests."""

    class Meta:
        model = Issue

    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"Issue {n}")
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    created_by = factory.SelfAttribute("project.created_by")
    updated_by = factory.SelfAttribute("project.created_by")


class MicroTaskFactory(factory.django.DjangoModelFactory):
    """Factory for MicroTask instances."""

    class Meta:
        model = MicroTask

    id = factory.LazyFunction(uuid4)
    issue = factory.SubFactory(IssueFactory)
    project = factory.SelfAttribute("issue.project")
    workspace = factory.SelfAttribute("issue.workspace")
    title = factory.Sequence(lambda n: f"Micro Task {n}")
    energy_level = "medium"
    estimated_minutes = 5


class FocusSessionFactory(factory.django.DjangoModelFactory):
    """Factory for FocusSession instances."""

    class Meta:
        model = FocusSession

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    session_type = "pomodoro"
    planned_duration_minutes = 25


class ContextSnapshotFactory(factory.django.DjangoModelFactory):
    """Factory for ContextSnapshot instances."""

    class Meta:
        model = ContextSnapshot

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    title = factory.Sequence(lambda n: f"Snapshot {n}")
    trigger = "manual"


class DopamineMenuFactory(factory.django.DjangoModelFactory):
    """Factory for DopamineMenu instances."""

    class Meta:
        model = DopamineMenu

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    title = factory.Sequence(lambda n: f"Reward {n}")
    category = "appetizer"


class AchievementFactory(factory.django.DjangoModelFactory):
    """Factory for Achievement instances."""

    class Meta:
        model = Achievement

    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"Achievement {n}")
    description = "Test achievement description"
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")


class StreakFactory(factory.django.DjangoModelFactory):
    """Factory for Streak instances."""

    class Meta:
        model = Streak

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    workspace = factory.SelfAttribute("project.workspace")
    streak_type = "daily_login"


# ---------------------------------------------------------------
# MicroTask Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestMicroTask:
    """Tests for the MicroTask model."""

    def test_create_micro_task(self):
        """MicroTask can be created with default values."""
        task = MicroTaskFactory()
        assert task.id is not None
        assert task.energy_level == "medium"
        assert task.estimated_minutes == 5
        assert task.is_completed is False
        assert task.just_start_eligible is True

    def test_str_representation(self):
        """String representation includes energy level and title."""
        task = MicroTaskFactory(title="Write tests", energy_level="low")
        assert str(task) == "[low] Write tests"

    def test_mark_complete(self):
        """mark_complete() sets is_completed and completed_at."""
        task = MicroTaskFactory()
        assert task.completed_at is None

        task.mark_complete()
        task.refresh_from_db()

        assert task.is_completed is True
        assert task.completed_at is not None

    def test_energy_manager_filters(self):
        """MicroTaskManager.for_energy() returns correct subset."""
        issue = IssueFactory()
        MicroTaskFactory(issue=issue, energy_level="low")
        MicroTaskFactory(issue=issue, energy_level="medium")
        MicroTaskFactory(issue=issue, energy_level="high")

        low_tasks = MicroTask.objects.for_energy("low")
        assert low_tasks.count() == 1

        medium_tasks = MicroTask.objects.for_energy("medium")
        assert medium_tasks.count() == 2  # low + medium

        high_tasks = MicroTask.objects.for_energy("high")
        assert high_tasks.count() == 3  # all

    def test_appetizers_manager(self):
        """MicroTaskManager.appetizers() returns quick low-energy tasks."""
        issue = IssueFactory()
        MicroTaskFactory(issue=issue, energy_level="low", estimated_minutes=3)
        MicroTaskFactory(issue=issue, energy_level="low", estimated_minutes=10)
        MicroTaskFactory(issue=issue, energy_level="high", estimated_minutes=3)

        appetizers = MicroTask.objects.appetizers()
        assert appetizers.count() == 1

    def test_completed_tasks_excluded_from_managers(self):
        """Completed tasks are excluded from energy and appetizer queries."""
        issue = IssueFactory()
        task = MicroTaskFactory(issue=issue, energy_level="low", estimated_minutes=3)
        task.mark_complete()

        assert MicroTask.objects.for_energy("high").count() == 0
        assert MicroTask.objects.appetizers().count() == 0


# ---------------------------------------------------------------
# FocusSession Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestFocusSession:
    """Tests for the FocusSession model."""

    def test_create_session(self):
        """FocusSession created with sensible defaults."""
        session = FocusSessionFactory()
        assert session.is_active is True
        assert session.session_type == "pomodoro"
        assert session.planned_duration_minutes == 25
        assert session.ended_at is None

    def test_end_session(self):
        """end_session() sets ended_at, is_active, actual_duration."""
        session = FocusSessionFactory(started_at=timezone.now() - timedelta(minutes=30))
        session.end_session()
        session.refresh_from_db()

        assert session.is_active is False
        assert session.ended_at is not None
        assert session.actual_duration_minutes >= 29  # ~30 minutes

    def test_str_representation(self):
        """String includes session type and status."""
        session = FocusSessionFactory()
        assert "pomodoro" in str(session)
        assert "Active" in str(session)


# ---------------------------------------------------------------
# ContextSnapshot Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestContextSnapshot:
    """Tests for the ContextSnapshot model."""

    def test_create_snapshot(self):
        """ContextSnapshot stores workspace state."""
        snapshot = ContextSnapshotFactory(snapshot_data={"open_issues": ["abc"], "draft": "hello"})
        assert snapshot.trigger == "manual"
        assert snapshot.snapshot_data["open_issues"] == ["abc"]
        assert snapshot.is_pinned is False

    def test_str_representation(self):
        """String includes title and trigger."""
        snapshot = ContextSnapshotFactory(title="Before lunch")
        assert "Before lunch" in str(snapshot)
        assert "manual" in str(snapshot)


# ---------------------------------------------------------------
# DopamineMenu Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestDopamineMenu:
    """Tests for the DopamineMenu model."""

    def test_create_reward(self):
        """DopamineMenu item can be created."""
        reward = DopamineMenuFactory(title="Coffee break")
        assert reward.use_count == 0
        assert reward.is_active is True
        assert reward.category == "appetizer"

    def test_claim_reward(self):
        """claim() increments use_count and sets last_used_at."""
        reward = DopamineMenuFactory()
        reward.claim()
        reward.refresh_from_db()

        assert reward.use_count == 1
        assert reward.last_used_at is not None

    def test_cooldown_check(self):
        """is_on_cooldown returns True during cooldown period."""
        reward = DopamineMenuFactory(cooldown_minutes=60)
        assert reward.is_on_cooldown is False

        reward.claim()
        assert reward.is_on_cooldown is True

    def test_no_cooldown_when_zero(self):
        """Rewards with cooldown_minutes=0 are never on cooldown."""
        reward = DopamineMenuFactory(cooldown_minutes=0)
        reward.claim()
        assert reward.is_on_cooldown is False

    def test_str_representation(self):
        """String includes category display and title."""
        reward = DopamineMenuFactory(title="YouTube", category="side")
        assert "Side (5-15 min)" in str(reward)
        assert "YouTube" in str(reward)


# ---------------------------------------------------------------
# Achievement Tests
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestAchievement:
    """Tests for Achievement and UserAchievement models."""

    def test_create_achievement(self):
        """Achievement can be created with defaults."""
        achievement = AchievementFactory()
        assert achievement.icon == "🏆"
        assert achievement.xp_value == 10
        assert achievement.is_secret is False

    def test_user_achievement_junction(self):
        """UserAchievement links users to achievements."""
        user = UserFactory()
        achievement = AchievementFactory()
        ua = UserAchievement.objects.create(
            user=user,
            achievement=achievement,
            project=achievement.project,
            workspace=achievement.workspace,
        )
        assert ua.celebration_shown is False
        assert ua.earned_at is not None

    def test_user_achievement_unique_constraint(self):
        """Same user can't earn the same achievement twice."""
        user = UserFactory()
        achievement = AchievementFactory()
        UserAchievement.objects.create(
            user=user,
            achievement=achievement,
            project=achievement.project,
            workspace=achievement.workspace,
        )
        with pytest.raises(Exception):  # IntegrityError
            UserAchievement.objects.create(
                user=user,
                achievement=achievement,
                project=achievement.project,
                workspace=achievement.workspace,
            )


# ---------------------------------------------------------------
# Streak Tests — No-Shame Protocol
# ---------------------------------------------------------------


@pytest.mark.django_db
class TestStreak:
    """Tests for the Streak model's No-Shame behavior."""

    def test_create_streak(self):
        """Streak starts at zero with active status."""
        streak = StreakFactory()
        assert streak.current_count == 0
        assert streak.longest_count == 0
        assert streak.status == "active"

    def test_record_activity_increments(self):
        """record_activity() increments count and updates PB."""
        streak = StreakFactory()
        streak.record_activity()
        streak.refresh_from_db()

        assert streak.current_count == 1
        assert streak.longest_count == 1
        assert streak.last_activity_at is not None

    def test_personal_best_never_resets(self):
        """longest_count always tracks the all-time best."""
        streak = StreakFactory()
        for _ in range(5):
            streak.record_activity()

        streak.refresh_from_db()
        assert streak.longest_count == 5

        # Simulate pause and resume
        streak.status = "paused"
        streak.save()
        streak.record_activity()  # resets to 1
        streak.refresh_from_db()

        assert streak.current_count == 1
        assert streak.longest_count == 5  # PB preserved!

    def test_grace_period_pauses_not_breaks(self):
        """After grace period, streak pauses — never breaks."""
        streak = StreakFactory(grace_period_hours=24)
        streak.record_activity()

        # Simulate 25 hours passing
        streak.last_activity_at = timezone.now() - timedelta(hours=25)
        streak.save()

        streak.check_grace_period()
        streak.refresh_from_db()

        assert streak.status == "paused"  # Paused, not broken!
        assert streak.current_count == 1  # Count preserved

    def test_welcome_back_on_resume(self):
        """Paused streak resumes with count=1 on next activity."""
        streak = StreakFactory()
        for _ in range(10):
            streak.record_activity()

        streak.status = "paused"
        streak.save()

        streak.record_activity()
        streak.refresh_from_db()

        assert streak.status == "active"
        assert streak.current_count == 1  # Fresh start
        assert streak.longest_count == 10  # PB safe

    def test_str_representation(self):
        """String includes streak type, count, and status."""
        streak = StreakFactory(streak_type="focus_session")
        streak.record_activity()
        streak.record_activity()
        assert "Focus Sessions" in str(streak)
        assert "2" in str(streak)
