# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging
import uuid

# Django imports
from django.core.cache import cache
from django.utils import timezone

# Third party imports
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

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
from plane.api.throttles import AIBurstThrottle, AIEndpointThrottle, TaskStatusThrottle
from plane.services.ai import decompose_issue_with_ai, extract_actions_with_ai
from plane.bgtasks.execuflow_tasks import decompose_issue_task, process_brain_dump_task
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
from plane.utils.execuflow_cache import get_cache_key, get_cache_timeout, invalidate_user_cache

# Module imports
from .base import BaseAPIView

logger = logging.getLogger("plane.api")

# Task ownership cache timeout (1 hour, matching typical Celery result expiry)
TASK_OWNER_CACHE_TIMEOUT = 3600

# ──────────────────────────────────────────────────────────────
# Common OpenAPI Parameters & Inline Serializers
# ──────────────────────────────────────────────────────────────

EXECUFLOW_PATH_PARAMS = [
    OpenApiParameter(
        name="slug",
        type=str,
        location=OpenApiParameter.PATH,
        description="Workspace slug.",
    ),
    OpenApiParameter(
        name="project_id",
        type={"type": "string", "format": "uuid"},
        location=OpenApiParameter.PATH,
        description="Project UUID.",
    ),
]

EXECUFLOW_DETAIL_PATH_PARAMS = EXECUFLOW_PATH_PARAMS + [
    OpenApiParameter(
        name="pk",
        type={"type": "string", "format": "uuid"},
        location=OpenApiParameter.PATH,
        description="Resource UUID.",
    ),
]

ERROR_RESPONSE = inline_serializer(
    name="ErrorResponse",
    fields={"error": drf_serializers.CharField()},
)

ASYNC_TASK_RESPONSE = inline_serializer(
    name="AsyncTaskAccepted",
    fields={
        "task_id": drf_serializers.CharField(),
        "status": drf_serializers.CharField(),
        "message": drf_serializers.CharField(),
    },
)


def _is_valid_uuid(value):
    """Validate that a string is a well-formed UUID."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def _store_task_ownership(task_id, user_id):
    """Record which user owns a Celery task in the cache."""
    cache.set(f"execuflow_task_owner:{task_id}", str(user_id), timeout=TASK_OWNER_CACHE_TIMEOUT)


def _verify_task_ownership(task_id, user_id):
    """Check whether the given user owns the specified task. Returns True if owned or if no ownership record exists (graceful fallback)."""
    owner_id = cache.get(f"execuflow_task_owner:{task_id}")
    if owner_id is None:
        # No ownership record -- task may predate this feature.
        # Deny by default to prevent enumeration.
        return False
    return owner_id == str(user_id)


# ──────────────────────────────────────────────────────────────
# ExecuFlow Pagination
# ──────────────────────────────────────────────────────────────


class ExecuFlowPagination(PageNumberPagination):
    """Pagination class for ExecuFlow list endpoints."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


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

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            serializer = MicroTaskSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
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
    throttle_classes = [AIEndpointThrottle, AIBurstThrottle]

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

            # ─── Queue Async Task ───
            # Decompose issue asynchronously using Celery
            task = decompose_issue_task.delay(
                issue_id=str(parent_issue.id),
                max_steps=data.get("max_steps", 5),
                target_energy=data.get("target_energy"),
                max_minutes_per_step=data.get("max_minutes_per_step", 15),
                workspace_id=str(request.user.last_workspace_id),
                user_id=str(request.user.id),
            )

            # Record task ownership for status endpoint authorization
            _store_task_ownership(task.id, request.user.id)

            return Response(
                {
                    "task_id": task.id,
                    "status": "processing",
                    "message": "Issue decomposition started",
                    "issue_id": str(parent_issue.id),
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    throttle_classes = [AIEndpointThrottle, AIBurstThrottle]

    def post(self, request, slug, project_id):
        try:
            serializer = BrainDumpSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            raw_text = data["raw_text"]
            source = data.get("source", "text")
            auto_create = data.get("auto_create_issues", False)

            # ─── Queue Async Task ───
            # Process brain dump asynchronously using Celery
            task = process_brain_dump_task.delay(
                raw_text=raw_text,
                source=source,
                auto_create_issues=auto_create,
                workspace_id=str(request.user.last_workspace_id),
                project_id=project_id,
                user_id=str(request.user.id),
            )

            # Record task ownership for status endpoint authorization
            _store_task_ownership(task.id, request.user.id)

            return Response(
                {
                    "task_id": task.id,
                    "status": "processing",
                    "message": "Brain dump processing started",
                    "raw_text": raw_text,
                    "source": source,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



# ──────────────────────────────────────────────────────────────
# Task Status Endpoint
# ──────────────────────────────────────────────────────────────


class ExecuFlowTaskStatusEndpoint(BaseAPIView):
    """
    Check the status of async ExecuFlow tasks.

    Returns task state (PENDING, SUCCESS, FAILURE) and result data.
    """

    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        from celery.result import AsyncResult

        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response(
                {"error": "task_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_result = AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "status": task_result.state,
        }

        if task_result.ready():
            if task_result.successful():
                response_data["result"] = task_result.result
            else:
                response_data["error"] = str(task_result.info)
        else:
            response_data["message"] = "Task is still processing"

        return Response(response_data, status=status.HTTP_200_OK)

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

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            serializer = FocusSessionSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
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
            ).order_by("-created_at")

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(snapshots, request)
            serializer = ContextSnapshotSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
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
            cache_key = get_cache_key("dopamine_menu", str(request.user.id))
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            rewards = DopamineMenu.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                user=request.user,
            ).order_by("category", "title")

            category = request.query_params.get("category")
            if category:
                rewards = rewards.filter(category=category)

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(rewards, request)
            serializer = DopamineMenuSerializer(paginated_queryset, many=True)
            response = paginator.get_paginated_response(serializer.data)

            cache.set(cache_key, response.data, timeout=get_cache_timeout())
            return response
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

            invalidate_user_cache("dopamine_menu", str(request.user.id))

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
            cache_key = get_cache_key("achievements", str(request.user.id))
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            achievements = Achievement.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
            ).order_by("name")

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(achievements, request)
            serializer = AchievementSerializer(paginated_queryset, many=True)
            response = paginator.get_paginated_response(serializer.data)

            cache.set(cache_key, response.data, timeout=get_cache_timeout())
            return response
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

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(earned, request)
            serializer = UserAchievementSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
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

            # Paginate results
            paginator = ExecuFlowPagination()
            paginated_queryset = paginator.paginate_queryset(streaks, request)
            serializer = StreakSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
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

            # Get workspace ID from the project to ensure consistency
            from plane.db.models import Project
            project = Project.objects.get(pk=project_id)

            streak, created = Streak.objects.get_or_create(
                workspace_id=project.workspace_id,
                project_id=project_id,
                created_by=request.user,
                streak_type=streak_type,
                defaults={
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
