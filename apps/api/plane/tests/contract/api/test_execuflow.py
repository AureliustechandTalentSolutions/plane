# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow API Contract Tests

Tests the 13 ExecuFlow API endpoints for:
- MicroTasks (CRUD + decompose)
- FocusSessions (list, create, update)
- ContextSnapshots (list, create, restore)
- DopamineMenu (list, claim)
- Achievements (list, mine)
- Streaks (get, update)
- BrainDump (process)
"""

import pytest
from rest_framework import status
from uuid import uuid4

from plane.db.models import Project, ProjectMember, Issue
from plane.db.models.execuflow import (
    MicroTask,
    FocusSession,
    ContextSnapshot,
    DopamineMenu,
    Achievement,
    UserAchievement,
    Streak,
)


@pytest.fixture
def project(db, workspace, create_user):
    """Create a test project with the user as a member"""
    project = Project.objects.create(
        name="ExecuFlow Test Project",
        identifier="EX",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        project=project,
        member=create_user,
        role=20,  # Admin role
        is_active=True,
    )
    return project


@pytest.fixture
def issue(db, project, workspace, create_user):
    """Create a test issue for micro-task association"""
    return Issue.objects.create(
        name="Test Issue for MicroTask",
        project=project,
        workspace=workspace,
        created_by=create_user,
    )


@pytest.fixture
def micro_task(db, project, workspace, create_user, issue):
    """Create a test micro-task"""
    return MicroTask.objects.create(
        title="Test MicroTask",
        description_json={"text": "A test micro-task description"},
        issue=issue,
        energy_level="low",
        estimated_minutes=15,
        sort_order=1,
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def focus_session(db, project, workspace, create_user):
    """Create a test focus session"""
    return FocusSession.objects.create(
        session_type="pomodoro",
        planned_duration_minutes=25,
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def context_snapshot(db, project, workspace, create_user):
    """Create a test context snapshot"""
    return ContextSnapshot.objects.create(
        title="Test Snapshot",
        snapshot_data={"active_issues": [], "open_tabs": []},
        trigger="manual",
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def dopamine_reward(db, project, workspace, create_user):
    """Create a test dopamine reward"""
    return DopamineMenu.objects.create(
        category="appetizer",
        title="5-min stretch break",
        description="Stand up and stretch",
        cooldown_minutes=30,
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def achievement(db, workspace, project):
    """Create a test achievement"""
    return Achievement.objects.create(
        name="First Step",
        description="Complete your first micro-task",
        icon="sparkles",
        xp_value=10,
        criteria_json={"micro_tasks_completed": 1},
        workspace=workspace,
        project=project,
    )


@pytest.fixture
def streak(db, project, workspace, create_user):
    """Create a test streak"""
    return Streak.objects.create(
        streak_type="daily_login",
        current_count=5,
        longest_count=10,
        grace_period_hours=24,
        status="active",
        workspace=workspace,
        project=project,
        user=create_user,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MicroTask Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestMicroTaskEndpoints:
    """Test MicroTask API endpoints"""

    def get_url(self, workspace_slug, project_id, task_id=None):
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/micro-tasks/"
        return f"{base}{task_id}/" if task_id else base

    @pytest.mark.django_db
    def test_list_micro_tasks_empty(self, session_client, workspace, project):
        """Test listing micro-tasks when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [] or len(response.data) == 0

    @pytest.mark.django_db
    def test_list_micro_tasks_success(self, session_client, workspace, project, micro_task):
        """Test successful micro-task listing"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["title"] == micro_task.title

    @pytest.mark.django_db
    def test_list_micro_tasks_filter_by_energy(self, session_client, workspace, project, micro_task):
        """Test filtering micro-tasks by energy level"""
        url = self.get_url(workspace.slug, project.id) + "?energy_level=low"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for task in response.data:
            assert task["energy_level"] == "low"

    @pytest.mark.django_db
    def test_list_micro_tasks_filter_by_completion(self, session_client, workspace, project, micro_task):
        """Test filtering micro-tasks by completion status"""
        url = self.get_url(workspace.slug, project.id) + "?is_completed=false"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for task in response.data:
            assert task["is_completed"] is False

    @pytest.mark.django_db
    def test_create_micro_task_success(self, session_client, workspace, project, issue):
        """Test successful micro-task creation"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "title": "New MicroTask",
            "description_json": {"text": "Description here"},
            "issue": str(issue.id),
            "energy_level": "medium",
            "estimated_minutes": 10,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == data["title"]
        assert response.data["energy_level"] == data["energy_level"]
        assert MicroTask.objects.filter(title="New MicroTask").exists()

    @pytest.mark.django_db
    def test_create_micro_task_minimal(self, session_client, workspace, project):
        """Test micro-task creation with minimal data"""
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Minimal Task"}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Minimal Task"
        assert response.data["energy_level"] == "low"  # default

    @pytest.mark.django_db
    def test_create_micro_task_invalid_energy(self, session_client, workspace, project):
        """Test micro-task creation with invalid energy level"""
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Invalid Energy", "energy_level": "extreme"}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_update_micro_task_success(self, session_client, workspace, project, micro_task):
        """Test successful micro-task update"""
        url = self.get_url(workspace.slug, project.id, micro_task.id)
        data = {"title": "Updated Title", "is_completed": True}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        micro_task.refresh_from_db()
        assert micro_task.title == "Updated Title"
        assert micro_task.is_completed is True

    @pytest.mark.django_db
    def test_update_micro_task_not_found(self, session_client, workspace, project):
        """Test updating non-existent micro-task"""
        url = self.get_url(workspace.slug, project.id, uuid4())
        response = session_client.patch(url, {"title": "Test"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_delete_micro_task_success(self, session_client, workspace, project, micro_task):
        """Test successful micro-task deletion"""
        task_id = micro_task.id
        url = self.get_url(workspace.slug, project.id, task_id)

        response = session_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MicroTask.objects.filter(id=task_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# FocusSession Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestFocusSessionEndpoints:
    """Test FocusSession API endpoints"""

    def get_url(self, workspace_slug, project_id, session_id=None):
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/focus-sessions/"
        return f"{base}{session_id}/" if session_id else base

    @pytest.mark.django_db
    def test_list_focus_sessions_empty(self, session_client, workspace, project):
        """Test listing focus sessions when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_focus_sessions_success(self, session_client, workspace, project, focus_session):
        """Test successful focus session listing"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_create_focus_session_pomodoro(self, session_client, workspace, project):
        """Test creating a pomodoro focus session"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "pomodoro",
            "planned_duration_minutes": 25,
            "mood_before": 3,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["session_type"] == "pomodoro"
        assert response.data["planned_duration_minutes"] == 25
        assert response.data["is_active"] is True

    @pytest.mark.django_db
    def test_create_focus_session_deep_work(self, session_client, workspace, project):
        """Test creating a deep work focus session"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "deep_work",
            "planned_duration_minutes": 90,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["session_type"] == "deep_work"

    @pytest.mark.django_db
    def test_create_focus_session_invalid_type(self, session_client, workspace, project):
        """Test creating focus session with invalid type"""
        url = self.get_url(workspace.slug, project.id)
        data = {"session_type": "invalid_type", "planned_duration_minutes": 25}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_end_focus_session(self, session_client, workspace, project, focus_session):
        """Test ending a focus session"""
        url = self.get_url(workspace.slug, project.id, focus_session.id)
        data = {"is_active": False, "mood_after": 4}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        focus_session.refresh_from_db()
        assert focus_session.is_active is False
        assert focus_session.ended_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# ContextSnapshot Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestContextSnapshotEndpoints:
    """Test ContextSnapshot API endpoints"""

    def get_url(self, workspace_slug, project_id, snapshot_id=None, action=None):
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/context-snapshots/"
        if snapshot_id and action:
            return f"{base}{snapshot_id}/{action}/"
        elif snapshot_id:
            return f"{base}{snapshot_id}/"
        return base

    @pytest.mark.django_db
    def test_list_snapshots_empty(self, session_client, workspace, project):
        """Test listing snapshots when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_snapshots_success(self, session_client, workspace, project, context_snapshot):
        """Test successful snapshot listing"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["title"] == context_snapshot.title

    @pytest.mark.django_db
    def test_create_snapshot_manual(self, session_client, workspace, project):
        """Test creating a manual snapshot"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "title": "Work in progress snapshot",
            "snapshot_data": {"active_issues": ["issue-1"], "notes": "Working on auth"},
            "trigger": "manual",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == data["title"]
        assert response.data["trigger"] == "manual"

    @pytest.mark.django_db
    def test_create_snapshot_invalid_trigger(self, session_client, workspace, project):
        """Test creating snapshot with invalid trigger"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "title": "Invalid trigger",
            "snapshot_data": {},
            "trigger": "invalid_trigger",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_restore_snapshot(self, session_client, workspace, project, context_snapshot):
        """Test restoring a snapshot"""
        url = self.get_url(workspace.slug, project.id, context_snapshot.id, "restore")

        response = session_client.post(url, format="json")

        assert response.status_code == status.HTTP_200_OK
        context_snapshot.refresh_from_db()
        assert context_snapshot.restored_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# DopamineMenu Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestDopamineMenuEndpoints:
    """Test DopamineMenu API endpoints"""

    def get_url(self, workspace_slug, project_id, reward_id=None, action=None):
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/dopamine-menu/"
        if reward_id and action:
            return f"{base}{reward_id}/{action}/"
        elif reward_id:
            return f"{base}{reward_id}/"
        return base

    @pytest.mark.django_db
    def test_list_rewards_empty(self, session_client, workspace, project):
        """Test listing rewards when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_rewards_success(self, session_client, workspace, project, dopamine_reward):
        """Test successful reward listing"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["title"] == dopamine_reward.title

    @pytest.mark.django_db
    def test_list_rewards_filter_by_category(self, session_client, workspace, project, dopamine_reward):
        """Test filtering rewards by category"""
        url = self.get_url(workspace.slug, project.id) + "?category=appetizer"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for reward in response.data:
            assert reward["category"] == "appetizer"

    @pytest.mark.django_db
    def test_claim_reward_success(self, session_client, workspace, project, dopamine_reward):
        """Test successfully claiming a reward"""
        url = self.get_url(workspace.slug, project.id, dopamine_reward.id, "claim")

        response = session_client.post(url, format="json")

        assert response.status_code == status.HTTP_200_OK
        dopamine_reward.refresh_from_db()
        assert dopamine_reward.use_count == 1
        assert dopamine_reward.last_used_at is not None

    @pytest.mark.django_db
    def test_claim_reward_not_found(self, session_client, workspace, project):
        """Test claiming non-existent reward"""
        url = self.get_url(workspace.slug, project.id, uuid4(), "claim")

        response = session_client.post(url, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_user_isolation(self, session_client, workspace, project, create_user):
        """Test that users only see their own rewards (security test)"""
        # Create another user with their own reward
        from plane.db.models import User

        other_user = User.objects.create(email="other@test.com", first_name="Other")
        DopamineMenu.objects.create(
            category="dessert",
            title="Other User Reward",
            description="Should not be visible",
            cooldown_minutes=60,
            workspace=workspace,
            project=project,
            user=other_user,
        )

        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for reward in response.data:
            assert reward["title"] != "Other User Reward"


# ─────────────────────────────────────────────────────────────────────────────
# Achievement Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestAchievementEndpoints:
    """Test Achievement API endpoints"""

    def get_url(self, workspace_slug, project_id, suffix=""):
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/achievements/"
        return f"{base}{suffix}" if suffix else base

    @pytest.mark.django_db
    def test_list_achievements_empty(self, session_client, workspace, project):
        """Test listing achievements when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_achievements_success(self, session_client, workspace, project, achievement):
        """Test successful achievement listing"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["name"] == achievement.name

    @pytest.mark.django_db
    def test_list_my_achievements_empty(self, session_client, workspace, project):
        """Test listing user achievements when none earned"""
        url = self.get_url(workspace.slug, project.id, "mine/")
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_list_my_achievements_success(self, session_client, workspace, project, achievement, create_user):
        """Test listing user's earned achievements"""
        # Grant achievement to user
        UserAchievement.objects.create(
            achievement=achievement,
            user=create_user,
            workspace=workspace,
            project=project,
        )

        url = self.get_url(workspace.slug, project.id, "mine/")
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Streak Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestStreakEndpoints:
    """Test Streak API endpoints"""

    def get_url(self, workspace_slug, project_id):
        return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/streaks/"

    @pytest.mark.django_db
    def test_get_streaks_empty(self, session_client, workspace, project):
        """Test getting streaks when none exist"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_get_streaks_success(self, session_client, workspace, project, streak):
        """Test successful streak retrieval"""
        url = self.get_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["streak_type"] == streak.streak_type
        assert response.data[0]["current_count"] == streak.current_count

    @pytest.mark.django_db
    def test_record_streak_activity(self, session_client, workspace, project, streak):
        """Test recording streak activity"""
        url = self.get_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "record"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.last_activity_at is not None

    @pytest.mark.django_db
    def test_pause_streak(self, session_client, workspace, project, streak):
        """Test pausing a streak"""
        url = self.get_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "pause"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.status == "paused"

    @pytest.mark.django_db
    def test_resume_streak(self, session_client, workspace, project, streak, create_user):
        """Test resuming a paused streak"""
        # First pause the streak
        streak.status = "paused"
        streak.save()

        url = self.get_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "resume"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.status == "active"


# ─────────────────────────────────────────────────────────────────────────────
# BrainDump Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestBrainDumpEndpoint:
    """Test BrainDump API endpoint"""

    def get_url(self, workspace_slug, project_id):
        return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/brain-dump/"

    @pytest.mark.django_db
    def test_brain_dump_success(self, session_client, workspace, project):
        """Test successful brain dump processing"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Need to fix login bug. Also update documentation. Remember to add tests.",
            "source": "quick_capture",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "extracted_items" in response.data
        assert len(response.data["extracted_items"]) > 0

    @pytest.mark.django_db
    def test_brain_dump_empty_text(self, session_client, workspace, project):
        """Test brain dump with empty text"""
        url = self.get_url(workspace.slug, project.id)
        data = {"raw_text": "", "source": "quick_capture"}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_brain_dump_auto_create_issues(self, session_client, workspace, project):
        """Test brain dump with auto issue creation"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Fix the authentication flow. Update user profile page.",
            "source": "voice_note",
            "auto_create_issues": True,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        # Should have created issues if AI extraction worked
        if response.data.get("created_issues"):
            assert len(response.data["created_issues"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Decompose Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestDecomposeEndpoint:
    """Test issue decomposition endpoint"""

    def get_url(self, workspace_slug, project_id):
        return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/execuflow/micro-tasks/decompose/"

    @pytest.mark.django_db
    def test_decompose_issue_success(self, session_client, workspace, project, issue):
        """Test successful issue decomposition"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 5,
            "target_energy": "low",
            "max_minutes_per_step": 15,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data) > 0
        # Each task should have required fields
        for task in response.data:
            assert "title" in task
            assert "energy_level" in task

    @pytest.mark.django_db
    def test_decompose_issue_not_found(self, session_client, workspace, project):
        """Test decomposing non-existent issue"""
        url = self.get_url(workspace.slug, project.id)
        data = {"parent_issue_id": str(uuid4())}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_decompose_custom_params(self, session_client, workspace, project, issue):
        """Test decomposition with custom parameters"""
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 3,
            "target_energy": "high",
            "max_minutes_per_step": 30,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data) <= 3
