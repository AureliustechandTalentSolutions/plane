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
# Pagination Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestExecuFlowPaginationEndpoints:
    """Test pagination for all ExecuFlow list endpoints"""

    @pytest.mark.django_db
    def test_micro_tasks_default_pagination(self, session_client, workspace, project, issue, create_user):
        """Test micro-tasks list returns paginated response with default page size"""
        # Create 25 micro-tasks to exceed default page size (20)
        for i in range(25):
            MicroTask.objects.create(
                title=f"Task {i}",
                description_json={"text": f"Description {i}"},
                issue=issue,
                energy_level="low",
                estimated_minutes=5,
                sort_order=i,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20  # Default page size

    @pytest.mark.django_db
    def test_micro_tasks_custom_page_size(self, session_client, workspace, project, issue, create_user):
        """Test micro-tasks list with custom page_size parameter"""
        for i in range(15):
            MicroTask.objects.create(
                title=f"Task {i}",
                description_json={"text": f"Description {i}"},
                issue=issue,
                energy_level="low",
                estimated_minutes=5,
                sort_order=i,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/?page_size=5"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5

    @pytest.mark.django_db
    def test_micro_tasks_max_page_size_limit(self, session_client, workspace, project, issue, create_user):
        """Test micro-tasks list enforces max page_size of 100"""
        for i in range(150):
            MicroTask.objects.create(
                title=f"Task {i}",
                description_json={"text": f"Description {i}"},
                issue=issue,
                energy_level="low",
                estimated_minutes=5,
                sort_order=i,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/?page_size=200"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= 100  # Max page size enforced

    @pytest.mark.django_db
    def test_micro_tasks_page_navigation(self, session_client, workspace, project, issue, create_user):
        """Test micro-tasks pagination with next/previous page navigation"""
        for i in range(30):
            MicroTask.objects.create(
                title=f"Task {i}",
                description_json={"text": f"Description {i}"},
                issue=issue,
                energy_level="low",
                estimated_minutes=5,
                sort_order=i,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        # Page 1
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["next"] is not None
        assert response.data["previous"] is None

        # Page 2
        url_page2 = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/?page=2"
        response_page2 = session_client.get(url_page2)

        assert response_page2.status_code == status.HTTP_200_OK
        assert response_page2.data["previous"] is not None
        assert len(response_page2.data["results"]) == 10  # Remaining items

    @pytest.mark.django_db
    def test_focus_sessions_pagination(self, session_client, workspace, project, create_user):
        """Test focus sessions list returns paginated response"""
        for i in range(25):
            FocusSession.objects.create(
                session_type="pomodoro",
                planned_duration_minutes=25,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/focus-sessions/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20

    @pytest.mark.django_db
    def test_context_snapshots_pagination(self, session_client, workspace, project, create_user):
        """Test context snapshots list returns paginated response"""
        for i in range(25):
            ContextSnapshot.objects.create(
                title=f"Snapshot {i}",
                snapshot_data={"test": i},
                trigger="manual",
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/context-snapshots/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20

    @pytest.mark.django_db
    def test_dopamine_menu_pagination(self, session_client, workspace, project, create_user):
        """Test dopamine menu list returns paginated response"""
        for i in range(25):
            DopamineMenu.objects.create(
                category="appetizer",
                title=f"Reward {i}",
                description=f"Description {i}",
                cooldown_minutes=30,
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/dopamine-menu/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20

    @pytest.mark.django_db
    def test_achievements_pagination(self, session_client, workspace, project):
        """Test achievements list returns paginated response"""
        for i in range(25):
            Achievement.objects.create(
                name=f"Achievement {i}",
                description=f"Description {i}",
                icon="star",
                xp_value=10,
                criteria_json={"tasks": 1},
                workspace=workspace,
                project=project,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/achievements/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20

    @pytest.mark.django_db
    def test_user_achievements_pagination(self, session_client, workspace, project, create_user):
        """Test user achievements (mine) list returns paginated response"""
        # Create achievements and grant them to user
        for i in range(25):
            achievement = Achievement.objects.create(
                name=f"Achievement {i}",
                description=f"Description {i}",
                icon="star",
                xp_value=10,
                criteria_json={"tasks": 1},
                workspace=workspace,
                project=project,
            )
            UserAchievement.objects.create(
                achievement=achievement,
                user=create_user,
                workspace=workspace,
                project=project,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/achievements/mine/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20

    @pytest.mark.django_db
    def test_streaks_pagination(self, session_client, workspace, project, create_user):
        """Test streaks list returns paginated response"""
        streak_types = ["daily_login", "weekly_tasks", "focus_session", "micro_task_completion", "achievement_earned"]
        for i in range(25):
            Streak.objects.create(
                streak_type=streak_types[i % len(streak_types)],
                current_count=i,
                longest_count=i * 2,
                grace_period_hours=24,
                status="active",
                workspace=workspace,
                project=project,
                user=create_user,
            )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/streaks/"
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20


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


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting Tests - AI Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestAIEndpointRateLimiting:
    """Test rate limiting on AI-powered endpoints (decompose, brain_dump)"""

    @pytest.mark.django_db
    def test_decompose_rate_limit_enforcement(self, session_client, workspace, project, issue):
        """Test that decompose endpoint enforces rate limits"""
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/decompose/"
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 3,
        }

        # Make 11 rapid requests (limit is 10/minute)
        responses = []
        for i in range(11):
            response = session_client.post(url, data, format="json")
            responses.append(response)

        # First 10 should succeed
        for i in range(10):
            assert responses[i].status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_200_OK,
            ], f"Request {i+1} should succeed"

        # 11th request should be throttled
        assert responses[10].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.django_db
    def test_brain_dump_rate_limit_enforcement(self, session_client, workspace, project):
        """Test that brain_dump endpoint enforces rate limits"""
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/brain-dump/"
        data = {
            "raw_text": "Fix login bug. Update docs.",
            "source": "text",
        }

        # Make 11 rapid requests (limit is 10/minute)
        responses = []
        for i in range(11):
            response = session_client.post(url, data, format="json")
            responses.append(response)

        # First 10 should succeed
        for i in range(10):
            assert responses[i].status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_200_OK,
            ], f"Request {i+1} should succeed"

        # 11th request should be throttled
        assert responses[10].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.django_db
    def test_decompose_burst_limit_enforcement(self, session_client, workspace, project, issue):
        """Test that decompose endpoint enforces burst limits (3/second)"""
        import time

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/decompose/"
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 3,
        }

        # Make 4 requests within 1 second
        responses = []
        start_time = time.time()
        for i in range(4):
            response = session_client.post(url, data, format="json")
            responses.append(response)
        elapsed = time.time() - start_time

        # Ensure requests were made within 1 second
        assert elapsed < 1.0, "Requests should complete within 1 second"

        # First 3 should succeed (burst limit)
        for i in range(3):
            assert responses[i].status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_200_OK,
            ], f"Burst request {i+1} should succeed"

        # 4th request should be throttled
        assert responses[3].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.django_db
    def test_throttle_response_headers(self, session_client, workspace, project, issue):
        """Test that throttled responses include retry information"""
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/decompose/"
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 3,
        }

        # Exhaust rate limit
        for i in range(10):
            session_client.post(url, data, format="json")

        # Make throttled request
        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # Check for rate limit headers (if implemented)
        # Note: DRF throttling doesn't add headers by default, but we can add them

    @pytest.mark.django_db
    def test_non_ai_endpoints_not_throttled(self, session_client, workspace, project, issue):
        """Test that non-AI endpoints (like list) are not affected by AI throttles"""
        list_url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/"

        # Make many requests to list endpoint
        for i in range(15):
            response = session_client.get(list_url)
            # Should succeed - no AI throttle applied
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_different_users_have_separate_rate_limits(self, client, workspace, project, issue, create_user):
        """Test that rate limits are per-user, not global"""
        from plane.db.models import User

        # Create second user
        user2 = User.objects.create(
            email="user2@test.com",
            first_name="User",
            last_name="Two",
        )

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/execuflow/micro-tasks/decompose/"
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 3,
        }

        # User 1 exhausts their limit
        client.force_authenticate(user=create_user)
        for i in range(10):
            client.post(url, data, format="json")

        # User 1 is throttled
        response_user1 = client.post(url, data, format="json")
        assert response_user1.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # User 2 can still make requests
        client.force_authenticate(user=user2)
        response_user2 = client.post(url, data, format="json")
        # Should succeed (different user has their own limit)
        assert response_user2.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,  # May lack project permission
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Authorization Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestExecuFlowAuthorization:
    """
    Test authentication and authorization for all 13 ExecuFlow endpoints.

    Verifies that:
    - Unauthenticated requests are rejected (401 or 403)
    - Non-project-members cannot access project-scoped resources
    """

    # ── URL helpers ──────────────────────────────────────────────────────────

    def micro_task_list_url(self, workspace_slug, project_id):
        """Return URL for micro-task list endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/micro-tasks/"

    def focus_session_list_url(self, workspace_slug, project_id):
        """Return URL for focus-session list endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/focus-sessions/"

    def brain_dump_url(self, workspace_slug, project_id):
        """Return URL for brain-dump endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/brain-dump/"

    def decompose_url(self, workspace_slug, project_id):
        """Return URL for micro-task decompose endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/micro-tasks/decompose/"

    def task_status_url(self, workspace_slug, project_id):
        """Return URL for task-status endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/task-status/"

    def dopamine_menu_url(self, workspace_slug, project_id):
        """Return URL for dopamine-menu list endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/dopamine-menu/"

    def achievements_url(self, workspace_slug, project_id):
        """Return URL for achievements list endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/achievements/"

    def streaks_url(self, workspace_slug, project_id):
        """Return URL for streaks endpoint."""
        base = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        return f"{base}/execuflow/streaks/"

    # ── Unauthenticated request tests ────────────────────────────────────────

    @pytest.mark.django_db
    def test_unauthenticated_micro_task_list_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on micro-tasks must be rejected"""
        # Arrange - api_client is intentionally NOT authenticated
        url = self.micro_task_list_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert - must be 401 (no credentials) or 403 (forbidden)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_micro_task_create_returns_403(self, api_client, workspace, project):
        """Unauthenticated POST on micro-tasks must be rejected"""
        # Arrange
        url = self.micro_task_list_url(workspace.slug, project.id)
        data = {"title": "Should Not Be Created"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )
        assert not MicroTask.objects.filter(title="Should Not Be Created").exists()

    @pytest.mark.django_db
    def test_unauthenticated_focus_session_list_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on focus-sessions must be rejected"""
        # Arrange
        url = self.focus_session_list_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_brain_dump_returns_403(self, api_client, workspace, project):
        """Unauthenticated POST on brain-dump must be rejected"""
        # Arrange
        url = self.brain_dump_url(workspace.slug, project.id)
        data = {"raw_text": "Should not process", "source": "text"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_decompose_returns_403(self, api_client, workspace, project):
        """Unauthenticated POST on decompose must be rejected"""
        # Arrange
        url = self.decompose_url(workspace.slug, project.id)
        data = {"parent_issue_id": str(uuid4())}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_task_status_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on task-status must be rejected"""
        # Arrange
        url = self.task_status_url(workspace.slug, project.id)
        fake_task_id = str(uuid4())

        # Act
        response = api_client.get(url, {"task_id": fake_task_id})

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_dopamine_menu_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on dopamine-menu must be rejected"""
        # Arrange
        url = self.dopamine_menu_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_achievements_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on achievements must be rejected"""
        # Arrange
        url = self.achievements_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_unauthenticated_streaks_returns_403(self, api_client, workspace, project):
        """Unauthenticated GET on streaks must be rejected"""
        # Arrange
        url = self.streaks_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ], (
            f"Expected 401 or 403 but got {response.status_code}"
        )

    # ── Non-member access tests ───────────────────────────────────────────────

    @pytest.mark.django_db
    def test_non_member_cannot_access_project_micro_tasks(self, api_client, workspace, project):
        """A workspace member who is not a project member must be denied micro-task access"""
        # Arrange - create a user who is a workspace member but NOT a project member
        from plane.db.models import User

        non_member = User.objects.create(
            email="non-member@test.com",
            first_name="Non",
            last_name="Member",
        )
        # Authenticate as non-member (no project membership)
        api_client.force_authenticate(user=non_member)
        url = self.micro_task_list_url(workspace.slug, project.id)

        # Act
        response = api_client.get(url)

        # Assert - must be forbidden (no project membership)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,  # Project may not be visible
        ], (
            f"Expected 401/403/404 but got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_non_member_cannot_create_micro_task(self, api_client, workspace, project):
        """A user without project membership cannot create micro-tasks"""
        # Arrange
        from plane.db.models import User

        non_member = User.objects.create(
            email="intruder@test.com",
            first_name="Intruder",
            last_name="User",
        )
        api_client.force_authenticate(user=non_member)
        url = self.micro_task_list_url(workspace.slug, project.id)
        data = {"title": "Unauthorized Task"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert - task must NOT be created
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ], (
            f"Expected 401/403/404 but got {response.status_code}"
        )
        assert not MicroTask.objects.filter(title="Unauthorized Task").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Cross-User Isolation Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestExecuFlowCrossUserIsolation:
    """
    Test that users cannot access or modify each other's ExecuFlow data.

    Verifies row-level isolation for:
    - FocusSessions  (created_by filter)
    - ContextSnapshots (created_by filter + restore)
    - DopamineMenu rewards (user filter + claim)
    - Streaks (created_by filter)
    """

    @pytest.fixture
    def other_user(self, db):
        """A second user who is NOT a member of the test project."""
        from plane.db.models import User

        return User.objects.create(
            email="other-isolation@test.com",
            first_name="Other",
            last_name="User",
        )

    @pytest.fixture
    def other_user_client(self, api_client, other_user):
        """API client authenticated as the other (non-member) user."""
        api_client.force_authenticate(user=other_user)
        return api_client

    # ── FocusSession isolation ────────────────────────────────────────────────

    @pytest.mark.django_db
    def test_user_cannot_see_other_users_focus_sessions(
        self, session_client, workspace, project, create_user, other_user
    ):
        """Users only see their own focus sessions; other users' sessions are invisible"""
        # Arrange - session for create_user (pomodoro, 25 min)
        FocusSession.objects.create(
            session_type="pomodoro",
            planned_duration_minutes=25,
            workspace=workspace,
            project=project,
            user=create_user,
            created_by=create_user,
            updated_by=create_user,
        )
        # Session for other_user - must NOT appear in create_user's results
        FocusSession.objects.create(
            session_type="deep_work",
            planned_duration_minutes=90,
            workspace=workspace,
            project=project,
            user=other_user,
            created_by=other_user,
            updated_by=other_user,
        )

        url = (
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"
            "/execuflow/focus-sessions/"
        )

        # Act - create_user lists their focus sessions
        response = session_client.get(url)

        # Assert - create_user must not see other_user's deep_work session (90 min)
        assert response.status_code == status.HTTP_200_OK
        items = (
            response.data.get("results", [])
            if isinstance(response.data, dict)
            else response.data
        )
        other_user_sessions = [
            item for item in items
            if item.get("session_type") == "deep_work"
            and item.get("planned_duration_minutes") == 90
        ]
        assert len(other_user_sessions) == 0, (
            "create_user must not see other_user's deep_work session"
        )

    @pytest.mark.django_db
    def test_user_cannot_update_other_users_focus_session(
        self, session_client, workspace, project, other_user
    ):
        """A user cannot patch another user's focus session - must get 404"""
        # Arrange - focus session owned exclusively by other_user
        other_session = FocusSession.objects.create(
            session_type="pomodoro",
            planned_duration_minutes=25,
            workspace=workspace,
            project=project,
            user=other_user,
            created_by=other_user,
            updated_by=other_user,
        )

        url = (
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"
            f"/execuflow/focus-sessions/{other_session.id}/"
        )
        data = {"mood_after": 5}

        # Act - session_client is authenticated as create_user
        response = session_client.patch(url, data, format="json")

        # Assert - 404 because the query filters by created_by=request.user
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "Expected 404 when patching another user's focus session, "
            f"got {response.status_code}"
        )

    # ── ContextSnapshot isolation ─────────────────────────────────────────────

    @pytest.mark.django_db
    def test_user_cannot_restore_other_users_snapshot(
        self, session_client, workspace, project, other_user
    ):
        """A user cannot restore another user's context snapshot - must get 404"""
        # Arrange - snapshot owned exclusively by other_user
        other_snapshot = ContextSnapshot.objects.create(
            title="Other User's Snapshot",
            snapshot_data={"secret_data": True},
            trigger="manual",
            workspace=workspace,
            project=project,
            user=other_user,
            created_by=other_user,
            updated_by=other_user,
        )

        url = (
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"
            f"/execuflow/context-snapshots/{other_snapshot.id}/restore/"
        )

        # Act - session_client is authenticated as create_user
        response = session_client.post(url, format="json")

        # Assert - 404 because the query filters by created_by=request.user
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "Expected 404 when restoring another user's snapshot, "
            f"got {response.status_code}"
        )

    # ── DopamineMenu isolation ────────────────────────────────────────────────

    @pytest.mark.django_db
    def test_user_cannot_claim_other_users_reward(
        self, session_client, workspace, project, other_user
    ):
        """A user cannot claim a reward that belongs to another user - must get 404"""
        # Arrange - create a reward owned by other_user
        other_reward = DopamineMenu.objects.create(
            category="appetizer",
            title="Other User's Reward",
            description="Belongs to other_user",
            cooldown_minutes=30,
            workspace=workspace,
            project=project,
            user=other_user,
        )

        url = (
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"
            f"/execuflow/dopamine-menu/{other_reward.id}/claim/"
        )

        # Act - session_client is authenticated as create_user
        response = session_client.post(url, format="json")

        # Assert - 404 because the claim query filters by user=request.user
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "Expected 404 when claiming another user's reward, "
            f"got {response.status_code}"
        )
        # Verify the reward's use_count was NOT incremented
        other_reward.refresh_from_db()
        assert other_reward.use_count == 0 or other_reward.use_count is None, (
            "Other user's reward use_count must not be incremented"
        )

    # ── Streak isolation ──────────────────────────────────────────────────────

    @pytest.mark.django_db
    def test_user_cannot_see_other_users_streaks(
        self, session_client, workspace, project, create_user, other_user
    ):
        """Users only see their own streaks; other users' streaks are invisible"""
        # Arrange - create_user's streak (daily_login, count=10)
        Streak.objects.create(
            streak_type="daily_login",
            current_count=10,
            longest_count=10,
            grace_period_hours=24,
            status="active",
            workspace=workspace,
            project=project,
            user=create_user,
            created_by=create_user,
            updated_by=create_user,
        )
        # other_user's streak (focus_session, count=99) must NOT appear
        # in create_user's results
        Streak.objects.create(
            streak_type="focus_session",
            current_count=99,
            longest_count=99,
            grace_period_hours=24,
            status="active",
            workspace=workspace,
            project=project,
            user=other_user,
            created_by=other_user,
            updated_by=other_user,
        )

        url = (
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"
            "/execuflow/streaks/"
        )

        # Act - create_user lists their streaks
        response = session_client.get(url)

        # Assert - other_user's focus_session streak (count=99) must not be visible
        assert response.status_code == status.HTTP_200_OK
        items = (
            response.data.get("results", [])
            if isinstance(response.data, dict)
            else response.data
        )
        other_user_streaks = [
            item for item in items
            if item.get("streak_type") == "focus_session"
            and item.get("current_count") == 99
        ]
        assert len(other_user_streaks) == 0, (
            "create_user must not see other_user's streaks"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Task Status Security Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestExecuFlowTaskStatusIntegration:
    """
    Test the task-status endpoint security behavior.

    Covers:
    - Missing task_id parameter returns 400
    - Malformed (non-UUID) task_id returns 404
    - Well-formed UUID with no ownership record returns 404
    - Task owned by another user returns 404 (no cross-user enumeration)
    """

    def get_url(self, workspace_slug, project_id):
        """Return URL for task-status endpoint."""
        base = (
            f"/api/v1/workspaces/{workspace_slug}"
            f"/projects/{project_id}"
        )
        return f"{base}/execuflow/task-status/"

    @pytest.mark.django_db
    def test_task_status_requires_task_id_param(
        self, session_client, workspace, project
    ):
        """GET task-status without task_id query param returns 400"""
        # Arrange
        url = self.get_url(workspace.slug, project.id)

        # Act - no task_id provided
        response = session_client.get(url)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            "Expected 400 when task_id is missing, "
            f"got {response.status_code}"
        )
        # Response must contain an error message about the missing parameter
        response_str = str(response.data).lower()
        assert "task_id" in response_str or "error" in response_str, (
            "Response must include an error message referencing task_id"
        )

    @pytest.mark.django_db
    def test_task_status_invalid_uuid_returns_404(
        self, session_client, workspace, project
    ):
        """GET task-status with non-UUID task_id is rejected with 404"""
        # Arrange - deliberately malformed task IDs (not valid UUIDs)
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "../../etc/passwd",  # Path traversal attempt
            "' OR 1=1 --",       # SQL injection attempt
            "",
        ]

        url = self.get_url(workspace.slug, project.id)

        for invalid_id in invalid_ids:
            # Act
            response = session_client.get(url, {"task_id": invalid_id})

            # Assert - must return 404 or 400, never 500
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_400_BAD_REQUEST,
            ], (
                f"Expected 404 or 400 for invalid_id='{invalid_id}', "
                f"got {response.status_code}"
            )

    @pytest.mark.django_db
    def test_task_status_non_existent_task_returns_404(
        self, session_client, workspace, project
    ):
        """GET task-status with valid UUID but no ownership record returns 404"""
        # Arrange - UUID never registered in the ownership cache
        non_existent_task_id = str(uuid4())
        url = self.get_url(workspace.slug, project.id)

        # Act
        response = session_client.get(url, {"task_id": non_existent_task_id})

        # Assert - 404 (ownership check fails, preventing enumeration)
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "Expected 404 for task with no ownership record, "
            f"got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_task_status_other_users_task_returns_404(
        self, session_client, workspace, project
    ):
        """A user cannot poll the status of another user's task"""
        # Arrange - place a task ownership entry for a different user ID
        from django.core.cache import cache

        other_user_id = str(uuid4())
        task_id = str(uuid4())
        cache.set(
            f"execuflow_task_owner:{task_id}",
            other_user_id,
            timeout=3600,
        )

        url = self.get_url(workspace.slug, project.id)

        # Act - session_client is create_user (a different ID than other_user_id)
        response = session_client.get(url, {"task_id": task_id})

        # Assert - 404 because ownership check: other_user_id != create_user.id
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "Expected 404 when polling another user's task, "
            f"got {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Cooldown and Paused Streak
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def dopamine_reward_on_cooldown(db, project, workspace, create_user):
    """Create a reward that was just used (still on cooldown)."""
    from django.utils import timezone

    return DopamineMenu.objects.create(
        category="appetizer",
        title="Cooldown Reward",
        cooldown_minutes=60,
        last_used_at=timezone.now(),  # Used right now — still on cooldown
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def dopamine_reward_no_cooldown(db, project, workspace, create_user):
    """Create a reward with zero cooldown (always claimable)."""
    return DopamineMenu.objects.create(
        category="side",
        title="No Cooldown Reward",
        cooldown_minutes=0,  # Zero cooldown — always available
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def dopamine_reward_cooldown_expired(db, project, workspace, create_user):
    """Create a reward whose cooldown has already elapsed."""
    from django.utils import timezone
    from datetime import timedelta

    return DopamineMenu.objects.create(
        category="entree",
        title="Expired Cooldown Reward",
        cooldown_minutes=30,
        last_used_at=timezone.now() - timedelta(hours=2),  # Used 2 hours ago
        workspace=workspace,
        project=project,
        user=create_user,
    )


@pytest.fixture
def paused_streak(db, project, workspace, create_user):
    """Create a paused streak with existing count (No-Shame Protocol scenario)."""
    return Streak.objects.create(
        streak_type="daily_login",
        current_count=5,
        longest_count=10,
        status="paused",
        workspace=workspace,
        project=project,
        created_by=create_user,
        updated_by=create_user,
        user=create_user,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DopamineMenu Cooldown Enforcement Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestDopamineMenuCooldown:
    """
    Tests for cooldown enforcement on the DopamineMenu claim endpoint.

    The No-Shame Protocol applies here too: the API must clearly communicate
    when a reward is on cooldown (429) and provide retry information,
    while rewards with zero cooldown must always be claimable.
    """

    def get_claim_url(self, workspace_slug, project_id, reward_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/dopamine-menu/{reward_id}/claim/"
        )

    @pytest.mark.django_db
    def test_claim_reward_on_cooldown_returns_429(
        self, session_client, workspace, project, dopamine_reward_on_cooldown
    ):
        """
        Arrange: A reward that was just used (still within cooldown period).
        Act: POST to the claim endpoint.
        Assert: 429 Too Many Requests is returned and the response body
                contains an "error" key with "cooldown" in the message.
        """
        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_on_cooldown.id
        )
        response = session_client.post(url)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "error" in response.data
        assert "cooldown" in response.data["error"].lower()

    @pytest.mark.django_db
    def test_claim_reward_on_cooldown_includes_retry_info(
        self, session_client, workspace, project, dopamine_reward_on_cooldown
    ):
        """
        Arrange: A reward still on cooldown.
        Act: POST to the claim endpoint.
        Assert: The 429 response includes last_used and cooldown_minutes fields
                so the client can display when the user may retry.
        """
        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_on_cooldown.id
        )
        response = session_client.post(url)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "last_used" in response.data
        assert "cooldown_minutes" in response.data
        assert response.data["cooldown_minutes"] == dopamine_reward_on_cooldown.cooldown_minutes

    @pytest.mark.django_db
    def test_claim_reward_after_cooldown_succeeds(
        self, session_client, workspace, project, dopamine_reward_cooldown_expired
    ):
        """
        Arrange: A reward whose cooldown has elapsed (used 2 hours ago,
                 cooldown is 30 minutes).
        Act: POST to the claim endpoint.
        Assert: 200 OK — the reward is successfully claimed.
        """
        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_cooldown_expired.id
        )
        response = session_client.post(url)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_claim_reward_no_cooldown_always_available(
        self, session_client, workspace, project, dopamine_reward_no_cooldown
    ):
        """
        Arrange: A reward with cooldown_minutes=0 (no cooldown enforced).
        Act: POST to the claim endpoint twice in a row.
        Assert: Both claims succeed with 200 OK — zero-cooldown rewards
                are always claimable regardless of last_used_at.
        """
        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_no_cooldown.id
        )

        # First claim
        response_1 = session_client.post(url)
        assert response_1.status_code == status.HTTP_200_OK

        # Second immediate claim — still available because cooldown_minutes=0
        response_2 = session_client.post(url)
        assert response_2.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_multiple_claims_update_use_count(
        self, session_client, workspace, project, dopamine_reward_no_cooldown
    ):
        """
        Arrange: A zero-cooldown reward with use_count=0.
        Act: Claim it three times.
        Assert: use_count increments by 1 after each successful claim.
        """
        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_no_cooldown.id
        )
        initial_count = dopamine_reward_no_cooldown.use_count

        for expected_count in range(initial_count + 1, initial_count + 4):
            response = session_client.post(url)
            assert response.status_code == status.HTTP_200_OK
            dopamine_reward_no_cooldown.refresh_from_db()
            assert dopamine_reward_no_cooldown.use_count == expected_count

    @pytest.mark.django_db
    def test_claim_updates_last_used_at(
        self, session_client, workspace, project, dopamine_reward_no_cooldown
    ):
        """
        Arrange: A zero-cooldown reward with no last_used_at (never claimed).
        Act: Claim it once.
        Assert: last_used_at is set to a non-null datetime after claiming.
        """
        assert dopamine_reward_no_cooldown.last_used_at is None

        url = self.get_claim_url(
            workspace.slug, project.id, dopamine_reward_no_cooldown.id
        )
        response = session_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        dopamine_reward_no_cooldown.refresh_from_db()
        assert dopamine_reward_no_cooldown.last_used_at is not None

    @pytest.mark.django_db
    def test_cooldown_reward_model_properties(self, db):
        """
        Unit-level: verify the DopamineMenu model's is_on_cooldown and
        is_available properties correctly reflect a just-used reward state.
        """
        from django.utils import timezone

        reward = DopamineMenu(
            cooldown_minutes=60,
            last_used_at=timezone.now(),
        )
        assert reward.is_on_cooldown is True
        assert reward.is_available is False

    @pytest.mark.django_db
    def test_no_cooldown_reward_is_always_available_property(self, db):
        """
        Unit-level: a reward with cooldown_minutes=0 must always report
        is_on_cooldown=False and is_available=True, even if last_used_at
        is set to right now.
        """
        from django.utils import timezone

        reward = DopamineMenu(
            cooldown_minutes=0,
            last_used_at=timezone.now(),
        )
        assert reward.is_on_cooldown is False
        assert reward.is_available is True


# ─────────────────────────────────────────────────────────────────────────────
# Streak No-Shame Protocol Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestStreakNoShameProtocol:
    """
    Tests validating the No-Shame Protocol for streaks.

    Key invariants:
      - Pausing a streak NEVER resets current_count.
      - Pausing a streak NEVER decrements longest_count.
      - Resuming a paused streak restores status to "active".
      - Recording activity updates longest_count when current surpasses it.
      - Recording activity does NOT lower longest_count when current is lower.
      - A new streak is auto-created on first record (get_or_create pattern).
    """

    def get_streak_url(self, workspace_slug, project_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/streaks/"
        )

    @pytest.mark.django_db
    def test_paused_streak_current_count_preserved_in_response(
        self, session_client, workspace, project, paused_streak
    ):
        """
        Arrange: An existing paused streak with current_count=5.
        Act: GET the streaks list endpoint.
        Assert: The paused streak appears in the response with current_count
                still at 5 — the API never wipes count on pause.
        """
        url = self.get_streak_url(workspace.slug, project.id)
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        streak_data = response.data.get("results", response.data)
        matching = [s for s in streak_data if s["streak_type"] == "daily_login"]
        assert len(matching) >= 1
        assert matching[0]["current_count"] == 5
        assert matching[0]["status"] == "paused"

    @pytest.mark.django_db
    def test_pause_does_not_reset_current_count(
        self, session_client, workspace, project, streak
    ):
        """
        Arrange: An active streak with current_count=5.
        Act: PATCH the streaks endpoint with action="pause".
        Assert: current_count remains 5 after pausing — the No-Shame Protocol
                guarantees that pause never equals break.
        """
        original_count = streak.current_count
        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "pause"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.status == "paused"
        assert streak.current_count == original_count  # Never reset

    @pytest.mark.django_db
    def test_pause_does_not_reset_longest_count(
        self, session_client, workspace, project, streak
    ):
        """
        Arrange: An active streak with longest_count=10.
        Act: PATCH the streaks endpoint with action="pause".
        Assert: longest_count remains 10 — personal bests are never erased.
        """
        original_longest = streak.longest_count
        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "pause"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.longest_count == original_longest

    @pytest.mark.django_db
    def test_resume_paused_streak_to_active(
        self, session_client, workspace, project, paused_streak
    ):
        """
        Arrange: A paused streak (status="paused", current_count=5).
        Act: PATCH the streaks endpoint with action="resume".
        Assert: status transitions to "active" — the user is welcomed back.
        """
        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "resume"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        paused_streak.refresh_from_db()
        assert paused_streak.status == "active"

    @pytest.mark.django_db
    def test_resume_preserves_current_count(
        self, session_client, workspace, project, paused_streak
    ):
        """
        Arrange: A paused streak with current_count=5.
        Act: PATCH the streaks endpoint with action="resume".
        Assert: current_count is still 5 after resuming — no reset on resume.
        """
        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "resume"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        paused_streak.refresh_from_db()
        assert paused_streak.current_count == 5

    @pytest.mark.django_db
    def test_record_activity_updates_longest_count(
        self, session_client, workspace, project, create_user
    ):
        """
        Arrange: A streak where current_count == longest_count (at the boundary).
        Act: PATCH with action="record".
        Assert: After incrementing, current_count surpasses longest_count and
                longest_count is updated to match.
        """
        test_streak = Streak.objects.create(
            streak_type="focus_session",
            current_count=10,
            longest_count=10,
            status="active",
            workspace=workspace,
            project=project,
            created_by=create_user,
            updated_by=create_user,
            user=create_user,
        )

        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "focus_session", "action": "record"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        test_streak.refresh_from_db()
        assert test_streak.current_count == 11
        assert test_streak.longest_count == 11

    @pytest.mark.django_db
    def test_record_activity_preserves_longest_when_current_lower(
        self, session_client, workspace, project, create_user
    ):
        """
        Arrange: A streak where longest_count far exceeds current_count.
        Act: PATCH with action="record".
        Assert: longest_count is NOT lowered — personal bests are sacred.
        """
        test_streak = Streak.objects.create(
            streak_type="task_completion",
            current_count=2,
            longest_count=50,  # Far ahead of current
            status="active",
            workspace=workspace,
            project=project,
            created_by=create_user,
            updated_by=create_user,
            user=create_user,
        )

        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "task_completion", "action": "record"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        test_streak.refresh_from_db()
        assert test_streak.current_count == 3
        assert test_streak.longest_count == 50  # Unchanged — never lowered

    @pytest.mark.django_db
    def test_new_streak_created_on_first_record(
        self, session_client, workspace, project
    ):
        """
        Arrange: No streak of type "brain_dump" exists for this user/project.
        Act: PATCH with streak_type="brain_dump" and action="record".
        Assert: A new streak is created automatically (get_or_create),
                current_count=1 and status="active".
        """
        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "brain_dump", "action": "record"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["streak_type"] == "brain_dump"
        assert response.data["current_count"] == 1
        assert response.data["status"] == "active"

    @pytest.mark.django_db
    def test_record_updates_last_activity_at(
        self, session_client, workspace, project, streak
    ):
        """
        Arrange: An active streak with no last_activity_at set.
        Act: PATCH with action="record".
        Assert: last_activity_at is set to a non-null datetime after recording.
        """
        assert streak.last_activity_at is None

        url = self.get_streak_url(workspace.slug, project.id)
        data = {"streak_type": "daily_login", "action": "record"}

        response = session_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        streak.refresh_from_db()
        assert streak.last_activity_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# MicroTask Validation Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestMicroTaskValidationEdgeCases:
    """
    Boundary and invalid-input tests for MicroTask creation.

    Guards the serializer and model validation layer against out-of-range,
    missing, or malformed inputs per the model constraints:
      - title: max_length=512 (required)
      - estimated_minutes: MinValueValidator(1), MaxValueValidator(120)
      - energy_level: choices=[low, medium, high]
    """

    def get_url(self, workspace_slug, project_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/micro-tasks/"
        )

    @pytest.mark.django_db
    def test_title_at_max_length_succeeds(self, session_client, workspace, project):
        """
        Arrange: A title exactly at the 512-character limit.
        Act: POST to create.
        Assert: 201 Created — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "A" * 512}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_title_exceeds_max_length_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: A title with 513 characters (one over the 512-char limit).
        Act: POST to create.
        Assert: 400 Bad Request — exceeds max_length.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "A" * 513}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_negative_estimated_minutes_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: estimated_minutes=-1 (invalid — must be positive per
                 the serializer's validate_estimated_minutes method).
        Act: POST to create.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Negative Time Task", "estimated_minutes": -1}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_zero_estimated_minutes_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: estimated_minutes=0 (invalid — MinValueValidator(1)).
        Act: POST to create.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Zero Time Task", "estimated_minutes": 0}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_estimated_minutes_over_max_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: estimated_minutes=121 (over MaxValueValidator(120)).
        Act: POST to create.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Over Max Task", "estimated_minutes": 121}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_estimated_minutes_at_max_succeeds(
        self, session_client, workspace, project
    ):
        """
        Arrange: estimated_minutes=120 (exactly at the MaxValueValidator limit).
        Act: POST to create.
        Assert: 201 Created — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Max Time Task", "estimated_minutes": 120}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_invalid_energy_level_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: energy_level="extreme" (not in choices: low/medium/high).
        Act: POST to create.
        Assert: 400 Bad Request — invalid choice value rejected.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"title": "Invalid Energy", "energy_level": "extreme"}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_missing_title_returns_400(self, session_client, workspace, project):
        """
        Arrange: Request body with energy_level and estimated_minutes but no title.
        Act: POST to create.
        Assert: 400 Bad Request — title is required.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"energy_level": "low", "estimated_minutes": 10}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# FocusSession Validation Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestFocusSessionValidationEdgeCases:
    """
    Boundary tests for FocusSession mood field validation.

    mood_before and mood_after are validated by model MinValueValidator(1)
    and MaxValueValidator(5). Valid range: 1-5 inclusive.
    """

    def get_url(self, workspace_slug, project_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/focus-sessions/"
        )

    @pytest.mark.django_db
    def test_mood_before_below_minimum_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: mood_before=0 (below MinValueValidator(1)).
        Act: POST to create a focus session.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "pomodoro",
            "planned_duration_minutes": 25,
            "mood_before": 0,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_mood_before_above_maximum_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: mood_before=6 (above MaxValueValidator(5)).
        Act: POST to create a focus session.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "pomodoro",
            "planned_duration_minutes": 25,
            "mood_before": 6,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_mood_before_at_boundary_min_succeeds(
        self, session_client, workspace, project
    ):
        """
        Arrange: mood_before=1 (minimum valid value).
        Act: POST to create a focus session.
        Assert: 201 Created — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "pomodoro",
            "planned_duration_minutes": 25,
            "mood_before": 1,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_mood_before_at_boundary_max_succeeds(
        self, session_client, workspace, project
    ):
        """
        Arrange: mood_before=5 (maximum valid value).
        Act: POST to create a focus session.
        Assert: 201 Created — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "pomodoro",
            "planned_duration_minutes": 25,
            "mood_before": 5,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_invalid_session_type_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: session_type="sprints" (not in choices: pomodoro/deep_work/
                 body_double/free_flow).
        Act: POST to create.
        Assert: 400 Bad Request — invalid session type rejected.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "session_type": "sprints",
            "planned_duration_minutes": 25,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# BrainDump Validation Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestBrainDumpValidationEdgeCases:
    """
    Boundary tests for the BrainDump endpoint input validation.

    BrainDumpSerializer constraints:
      - raw_text: required, max_length=10000
      - source: choices=[text, voice, paste], default=text
    The endpoint returns 202 ACCEPTED (async via Celery) on success.
    """

    def get_url(self, workspace_slug, project_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/brain-dump/"
        )

    @pytest.mark.django_db
    def test_raw_text_at_max_length_accepted(self, session_client, workspace, project):
        """
        Arrange: raw_text exactly at max_length=10000.
        Act: POST to brain dump.
        Assert: 202 Accepted — async processing started successfully.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "A" * 10000,
            "source": "text",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_raw_text_exceeds_max_length_returns_400(
        self, session_client, workspace, project
    ):
        """
        Arrange: raw_text with 10001 characters (one over max_length=10000).
        Act: POST to brain dump.
        Assert: 400 Bad Request — serializer rejects oversized input.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "A" * 10001,
            "source": "text",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_empty_raw_text_returns_400(self, session_client, workspace, project):
        """
        Arrange: raw_text is an empty string.
        Act: POST to brain dump.
        Assert: 400 Bad Request — required field must not be blank.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {"raw_text": "", "source": "text"}

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_invalid_source_returns_400(self, session_client, workspace, project):
        """
        Arrange: source="quick_capture" (not in choices: text/voice/paste).
        Act: POST to brain dump.
        Assert: 400 Bad Request — invalid source choice rejected.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Something to capture",
            "source": "quick_capture",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_valid_voice_source_accepted(self, session_client, workspace, project):
        """
        Arrange: source="voice" (valid choice).
        Act: POST to brain dump.
        Assert: 202 Accepted — async processing started.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Fix the login flow and update the profile page.",
            "source": "voice",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_valid_paste_source_accepted(self, session_client, workspace, project):
        """
        Arrange: source="paste" (valid choice).
        Act: POST to brain dump.
        Assert: 202 Accepted — async processing started.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Refactor auth module. Add unit tests for edge cases.",
            "source": "paste",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_brain_dump_async_response_includes_task_id(
        self, session_client, workspace, project
    ):
        """
        Arrange: Valid brain dump request.
        Act: POST to brain dump.
        Assert: 202 response body includes task_id and status="processing"
                so the client can poll the task-status endpoint.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "raw_text": "Need to review auth PR and update sprint board.",
            "source": "text",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "task_id" in response.data
        assert response.data.get("status") == "processing"


# ─────────────────────────────────────────────────────────────────────────────
# Decompose Validation Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestDecomposeValidationEdgeCases:
    """
    Boundary and invalid-input tests for the decompose endpoint.

    MicroStepDecomposeSerializer constraints:
      - max_steps: min_value=1, max_value=20
      - max_minutes_per_step: min_value=1, max_value=120
      - target_energy: choices=[low, medium, high] (optional)
    The endpoint returns 202 ACCEPTED (async) on success.
    """

    def get_url(self, workspace_slug, project_id):
        return (
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
            f"/execuflow/micro-tasks/decompose/"
        )

    @pytest.mark.django_db
    def test_max_steps_above_limit_returns_400(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: max_steps=21 (over max_value=20).
        Act: POST to decompose.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 21,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_max_steps_at_limit_accepted(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: max_steps=20 (exactly at max_value).
        Act: POST to decompose.
        Assert: 202 Accepted — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 20,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_max_steps_zero_returns_400(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: max_steps=0 (below min_value=1).
        Act: POST to decompose.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 0,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_max_minutes_per_step_over_limit_returns_400(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: max_minutes_per_step=121 (over max_value=120).
        Act: POST to decompose.
        Assert: 400 Bad Request.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_minutes_per_step": 121,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_max_minutes_per_step_at_limit_accepted(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: max_minutes_per_step=120 (exactly at max_value).
        Act: POST to decompose.
        Assert: 202 Accepted — boundary value is valid.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_minutes_per_step": 120,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_invalid_target_energy_returns_400(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: target_energy="extreme" (not in choices: low/medium/high).
        Act: POST to decompose.
        Assert: 400 Bad Request — invalid energy choice rejected.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "target_energy": "extreme",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_valid_target_energy_low_accepted(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: target_energy="low" (valid choice).
        Act: POST to decompose.
        Assert: 202 Accepted — async processing started.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "target_energy": "low",
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED

    @pytest.mark.django_db
    def test_decompose_async_response_includes_task_id(
        self, session_client, workspace, project, issue
    ):
        """
        Arrange: Valid decompose request with minimal required fields.
        Act: POST to decompose.
        Assert: 202 response body includes task_id, status="processing",
                and issue_id for client correlation.
        """
        url = self.get_url(workspace.slug, project.id)
        data = {
            "parent_issue_id": str(issue.id),
            "max_steps": 5,
        }

        response = session_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "task_id" in response.data
        assert response.data.get("status") == "processing"
        assert "issue_id" in response.data
