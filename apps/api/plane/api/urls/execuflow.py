# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views.execuflow import (
    AchievementListEndpoint,
    BrainDumpEndpoint,
    ContextSnapshotListCreateEndpoint,
    ContextSnapshotRestoreEndpoint,
    DopamineMenuClaimEndpoint,
    DopamineMenuListEndpoint,
    FocusSessionDetailEndpoint,
    FocusSessionListCreateEndpoint,
    MicroStepDecomposeEndpoint,
    MicroTaskDetailEndpoint,
    MicroTaskListCreateEndpoint,
    StreakEndpoint,
    UserAchievementListEndpoint,
)

urlpatterns = [
    # ── MicroTask ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/micro-tasks/",
        MicroTaskListCreateEndpoint.as_view(http_method_names=["get", "post"]),
        name="execuflow-micro-task-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/micro-tasks/<uuid:pk>/",
        MicroTaskDetailEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="execuflow-micro-task-detail",
    ),
    # ── Micro-Step Decomposition (LLM) ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/micro-tasks/decompose/",
        MicroStepDecomposeEndpoint.as_view(http_method_names=["post"]),
        name="execuflow-micro-step-decompose",
    ),
    # ── Brain Dump ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/brain-dump/",
        BrainDumpEndpoint.as_view(http_method_names=["post"]),
        name="execuflow-brain-dump",
    ),
    # ── Focus Session ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/focus-sessions/",
        FocusSessionListCreateEndpoint.as_view(http_method_names=["get", "post"]),
        name="execuflow-focus-session-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/focus-sessions/<uuid:pk>/",
        FocusSessionDetailEndpoint.as_view(http_method_names=["get", "patch"]),
        name="execuflow-focus-session-detail",
    ),
    # ── Context Snapshot ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/context-snapshots/",
        ContextSnapshotListCreateEndpoint.as_view(http_method_names=["get", "post"]),
        name="execuflow-context-snapshot-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/context-snapshots/<uuid:pk>/restore/",
        ContextSnapshotRestoreEndpoint.as_view(http_method_names=["post"]),
        name="execuflow-context-snapshot-restore",
    ),
    # ── Dopamine Menu ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/dopamine-menu/",
        DopamineMenuListEndpoint.as_view(http_method_names=["get"]),
        name="execuflow-dopamine-menu-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/dopamine-menu/<uuid:pk>/claim/",
        DopamineMenuClaimEndpoint.as_view(http_method_names=["post"]),
        name="execuflow-dopamine-menu-claim",
    ),
    # ── Achievements ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/achievements/",
        AchievementListEndpoint.as_view(http_method_names=["get"]),
        name="execuflow-achievement-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/achievements/mine/",
        UserAchievementListEndpoint.as_view(http_method_names=["get"]),
        name="execuflow-user-achievement-list",
    ),
    # ── Streaks (No-Shame Protocol) ──
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/execuflow/streaks/",
        StreakEndpoint.as_view(http_method_names=["get", "patch"]),
        name="execuflow-streak",
    ),
]
