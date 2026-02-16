# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

from plane.api.serializers.execuflow import (
    AchievementSerializer,
    BrainDumpSerializer,
    ContextSnapshotCreateSerializer,
    ContextSnapshotSerializer,
    DopamineMenuSerializer,
    FocusSessionCreateSerializer,
    FocusSessionSerializer,
    MicroStepDecomposeSerializer,
    MicroTaskCreateSerializer,
    MicroTaskSerializer,
    StreakSerializer,
    UserAchievementSerializer,
)

# ExecuFlow AI providers
from plane.api.views.ai_providers import decompose_issue_with_ai, extract_actions_with_ai
from plane.app.permissions import ProjectEntityPermission
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
from plane.utils.exception_logger import log_exception

# Module imports
from .base import BaseAPIView

logger = logging.getLogger("plane.api")


# ──────────────────────────────────────────────────────────────
# MicroTask Endpoints
# ──────────────────────────────────────────────────────────────


class MicroTaskListCreateEndpoint(BaseAPIView):
    """List and create micro-tasks within a project."""

    model = MicroTask
    permission_classes = [ProjectEntityPermission]
    serializer_class = MicroTaskSerializer

    def get_queryset(self):
        return MicroTask.objects.filter(
            workspace__slug=self.workspace_slug,
            project_id=self.project_id,
        ).order_by("sort_order", "created_at")

    def get(self, request, slug, project_id):
        try:
            queryset = self.get_queryset()

            # Dynamic filtering — no hardcoded defaults
            energy = request.query_params.get("energy_level")
            if energy:
                queryset = queryset.filter(energy_level=energy)

            max_minutes = request.query_params.get("max_minutes")
            if max_minutes:
                queryset = queryset.filter(estimated_minutes__lte=int(max_minutes))

            is_completed = request.query_params.get("is_completed")
            if is_completed is not None:
                queryset = queryset.filter(is_completed=(is_completed.lower() == "true"))

            issue = request.query_params.get("issue")
            if issue:
                queryset = queryset.filter(issue_id=issue)

            serializer = MicroTaskSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, slug, project_id):
        try:
            serializer = MicroTaskCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    project_id=project_id,
                    workspace_id=request.user.last_workspace_id,
                    created_by=request.user,
                    updated_by=request.user,
                )
                return Response(
                    MicroTaskSerializer(serializer.instance).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MicroTaskDetailEndpoint(BaseAPIView):
    """Retrieve, update, or delete a single micro-task."""

    model = MicroTask
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id, pk):
        try:
            task = MicroTask.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
            )
            serializer = MicroTaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MicroTask.DoesNotExist:
            return Response(
                {"error": "Micro-task not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def patch(self, request, slug, project_id, pk):
        try:
            task = MicroTask.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
            )
            serializer = MicroTaskCreateSerializer(task, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    MicroTaskSerializer(task).data,
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except MicroTask.DoesNotExist:
            return Response(
                {"error": "Micro-task not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, slug, project_id, pk):
        try:
            task = MicroTask.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
            )
            task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MicroTask.DoesNotExist:
            return Response(
                {"error": "Micro-task not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ──────────────────────────────────────────────────────────────
# Micro-Step Decomposition (LLM-powered)
# ──────────────────────────────────────────────────────────────


class MicroStepDecomposeEndpoint(BaseAPIView):
    """
    LLM-powered decomposition of issues into micro-tasks.

    This endpoint accepts an issue ID and optional params, then generates
    a set of bite-sized micro-tasks. The LLM integration point is stubbed
    with a clean interface for future provider injection — no hardcoded prompts.
    """

    permission_classes = [ProjectEntityPermission]

    def post(self, request, slug, project_id):
        try:
            serializer = MicroStepDecomposeSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            parent_issue_id = data["parent_issue_id"]

            # Validate parent issue exists
            try:
                parent_issue = Issue.objects.get(
                    pk=parent_issue_id,
                    workspace__slug=slug,
                    project_id=project_id,
                )
            except Issue.DoesNotExist:
                return Response(
                    {"error": "Parent issue not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # ─── LLM Integration Point ───
            # This is the provider-agnostic decomposition interface.
            # Replace this block with your LLM call (OpenAI, Anthropic, etc).
            # The contract: given issue context, return a list of step dicts.
            decomposed_steps = self._decompose_issue(
                issue=parent_issue,
                max_steps=data.get("max_steps", 5),
                target_energy=data.get("target_energy"),
                max_minutes_per_step=data.get("max_minutes_per_step", 15),
            )

            # Create MicroTask records from decomposed steps
            created_tasks = []
            for idx, step in enumerate(decomposed_steps):
                task = MicroTask.objects.create(
                    title=step.get("title", f"Step {idx + 1}"),
                    description_json={"text": step.get("description", "")},
                    issue=parent_issue,
                    energy_level=step.get("energy_level", "low"),
                    estimated_minutes=step.get("estimated_minutes", 5),
                    sort_order=idx,
                    project_id=project_id,
                    workspace_id=request.user.last_workspace_id,
                    created_by=request.user,
                    updated_by=request.user,
                )
                created_tasks.append(task)

            serializer = MicroTaskSerializer(created_tasks, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _decompose_issue(
        self,
        issue,
        max_steps,
        target_energy,
        max_minutes_per_step,
    ):
        """
        Decompose an issue into micro-steps using AI.

        Uses Claude Opus 4.6 (primary) with Gemini 3 Pro
        fallback.  Returns list[dict] with title, description,
        energy_level, estimated_minutes.
        """
        issue_title = issue.name or "Untitled Issue"
        issue_desc = issue.description_stripped or issue_title
        return decompose_issue_with_ai(
            issue_title=issue_title,
            issue_description=issue_desc,
            max_steps=max_steps,
            target_energy=target_energy,
            max_minutes_per_step=max_minutes_per_step,
        )


# ──────────────────────────────────────────────────────────────
# Brain Dump (Voice Capture)
# ──────────────────────────────────────────────────────────────


class BrainDumpEndpoint(BaseAPIView):
    """
    Capture raw thoughts and optionally convert to issues.

    Accepts text (from voice-to-text or direct input). The processing
    pipeline is provider-agnostic — no hardcoded parsing logic.
    """

    permission_classes = [ProjectEntityPermission]

    def post(self, request, slug, project_id):
        try:
            serializer = BrainDumpSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            raw_text = data["raw_text"]
            source = data.get("source", "text")
            auto_create = data.get("auto_create_issues", False)

            # ─── NLP Processing Point ───
            # Replace with actual NLP/LLM extraction.
            extracted_items = self._extract_action_items(raw_text)

            created_issues = []
            if auto_create and extracted_items:
                for item in extracted_items:
                    issue = Issue.objects.create(
                        name=item["title"],
                        description_stripped=item.get("description", ""),
                        project_id=project_id,
                        workspace_id=request.user.last_workspace_id,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    created_issues.append({"id": str(issue.id), "name": issue.name})

            return Response(
                {
                    "raw_text": raw_text,
                    "source": source,
                    "extracted_items": extracted_items,
                    "created_issues": created_issues,
                    "items_count": len(extracted_items),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _extract_action_items(self, raw_text):
        """
        Extract action items from raw text using AI.

        Uses Claude Opus 4.6 (primary) with Gemini 3 Pro
        fallback.  Returns list[dict] with title, description.
        """
        return extract_actions_with_ai(raw_text)


# ──────────────────────────────────────────────────────────────
# FocusSession Endpoints
# ──────────────────────────────────────────────────────────────


class FocusSessionListCreateEndpoint(BaseAPIView):
    """List and create focus sessions."""

    model = FocusSession
    permission_classes = [ProjectEntityPermission]

    def get_queryset(self):
        return FocusSession.objects.filter(
            workspace__slug=self.workspace_slug,
            project_id=self.project_id,
            created_by=self.request.user,
        ).order_by("-created_at")

    def get(self, request, slug, project_id):
        try:
            queryset = self.get_queryset()

            session_type = request.query_params.get("session_type")
            if session_type:
                queryset = queryset.filter(session_type=session_type)

            is_active = request.query_params.get("active")
            if is_active is not None:
                if is_active.lower() == "true":
                    queryset = queryset.filter(ended_at__isnull=True)
                else:
                    queryset = queryset.filter(ended_at__isnull=False)

            serializer = FocusSessionSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, slug, project_id):
        try:
            serializer = FocusSessionCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    project_id=project_id,
                    workspace_id=request.user.last_workspace_id,
                    created_by=request.user,
                    updated_by=request.user,
                )
                return Response(
                    FocusSessionSerializer(serializer.instance).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FocusSessionDetailEndpoint(BaseAPIView):
    """Retrieve or update a focus session (end session, set mood)."""

    model = FocusSession
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id, pk):
        try:
            session = FocusSession.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
            )
            serializer = FocusSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FocusSession.DoesNotExist:
            return Response(
                {"error": "Focus session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def patch(self, request, slug, project_id, pk):
        try:
            session = FocusSession.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
            )

            # Handle ending the session
            if request.data.get("end_session"):
                session.end_session()
                session.save()

            # Update mood_after and other allowed fields
            allowed_updates = ["mood_after", "notes_json", "interrupt_queue"]
            for field in allowed_updates:
                if field in request.data:
                    setattr(session, field, request.data[field])

            session.updated_by = request.user
            session.save()

            serializer = FocusSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FocusSession.DoesNotExist:
            return Response(
                {"error": "Focus session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ──────────────────────────────────────────────────────────────
# ContextSnapshot Endpoints
# ──────────────────────────────────────────────────────────────


class ContextSnapshotListCreateEndpoint(BaseAPIView):
    """List and save workspace context snapshots."""

    model = ContextSnapshot
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        try:
            snapshots = ContextSnapshot.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
            ).order_by("-created_at")[:20]

            serializer = ContextSnapshotSerializer(snapshots, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, slug, project_id):
        try:
            serializer = ContextSnapshotCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    project_id=project_id,
                    workspace_id=request.user.last_workspace_id,
                    created_by=request.user,
                    updated_by=request.user,
                )
                return Response(
                    ContextSnapshotSerializer(serializer.instance).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ContextSnapshotRestoreEndpoint(BaseAPIView):
    """Restore workspace state from a saved snapshot."""

    permission_classes = [ProjectEntityPermission]

    def post(self, request, slug, project_id, pk):
        try:
            snapshot = ContextSnapshot.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
            )
            # Return snapshot data for the client to restore locally
            return Response(
                {
                    "snapshot_id": str(snapshot.id),
                    "title": snapshot.title,
                    "snapshot_data": snapshot.snapshot_data,
                    "trigger": snapshot.trigger,
                    "created_at": snapshot.created_at,
                },
                status=status.HTTP_200_OK,
            )
        except ContextSnapshot.DoesNotExist:
            return Response(
                {"error": "Snapshot not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ──────────────────────────────────────────────────────────────
# DopamineMenu Endpoints
# ──────────────────────────────────────────────────────────────


class DopamineMenuListEndpoint(BaseAPIView):
    """List available rewards."""

    model = DopamineMenu
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        try:
            rewards = DopamineMenu.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                user=request.user,
            ).order_by("category", "title")

            category = request.query_params.get("category")
            if category:
                rewards = rewards.filter(category=category)

            serializer = DopamineMenuSerializer(rewards, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DopamineMenuClaimEndpoint(BaseAPIView):
    """Claim a reward from the dopamine menu (with cooldown enforcement)."""

    permission_classes = [ProjectEntityPermission]

    def post(self, request, slug, project_id, pk):
        try:
            reward = DopamineMenu.objects.get(
                pk=pk,
                workspace__slug=slug,
                project_id=project_id,
                user=request.user,
            )

            if not reward.is_available:
                return Response(
                    {
                        "error": "Reward is on cooldown.",
                        "last_used": reward.last_used_at,
                        "cooldown_minutes": reward.cooldown_minutes,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            # Claim the reward
            reward.last_used_at = timezone.now()
            reward.use_count = (reward.use_count or 0) + 1
            reward.save()

            serializer = DopamineMenuSerializer(reward)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DopamineMenu.DoesNotExist:
            return Response(
                {"error": "Reward not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ──────────────────────────────────────────────────────────────
# Achievement Endpoints
# ──────────────────────────────────────────────────────────────


class AchievementListEndpoint(BaseAPIView):
    """List all available achievements for a project."""

    model = Achievement
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        try:
            achievements = Achievement.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
            ).order_by("name")

            serializer = AchievementSerializer(achievements, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserAchievementListEndpoint(BaseAPIView):
    """List achievements earned by the current user."""

    model = UserAchievement
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        try:
            earned = (
                UserAchievement.objects.filter(
                    workspace__slug=slug,
                    project_id=project_id,
                    user=request.user,
                )
                .select_related("achievement")
                .order_by("-earned_at")
            )

            serializer = UserAchievementSerializer(earned, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ──────────────────────────────────────────────────────────────
# Streak Endpoints (No-Shame Protocol)
# ──────────────────────────────────────────────────────────────


class StreakEndpoint(BaseAPIView):
    """
    Manage user streaks with the No-Shame Protocol.
    Streaks pause — they never break.
    """

    model = Streak
    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        try:
            streaks = Streak.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
            ).order_by("streak_type")

            serializer = StreakSerializer(streaks, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, slug, project_id):
        """
        Record streak activity or pause/resume.
        No-Shame Protocol: is_paused can be set to True, but
        current_count is never reset to zero.
        """
        try:
            streak_type = request.data.get("streak_type")
            if not streak_type:
                return Response(
                    {"error": "streak_type is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            streak, created = Streak.objects.get_or_create(
                workspace__slug=slug,
                project_id=project_id,
                created_by=request.user,
                streak_type=streak_type,
                defaults={
                    "workspace_id": request.user.last_workspace_id,
                    "updated_by": request.user,
                    "current_count": 0,
                    "longest_count": 0,
                },
            )

            action = request.data.get("action")

            if action == "record":
                # Record activity — increment streak
                streak.current_count += 1
                if streak.current_count > streak.longest_count:
                    streak.longest_count = streak.current_count
                streak.last_activity_at = timezone.now()
                streak.status = "active"

            elif action == "pause":
                # No-Shame: pause, don't break
                streak.status = "paused"

            elif action == "resume":
                streak.status = "active"

            streak.updated_by = request.user
            streak.save()

            serializer = StreakSerializer(streak)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
