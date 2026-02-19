# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

from plane.db.models import Achievement, ContextSnapshot, DopamineMenu, FocusSession, MicroTask, Streak, UserAchievement

# Module imports
from .base import BaseSerializer

# ──────────────────────────────────────────────────────────────
# MicroTask
# ──────────────────────────────────────────────────────────────


class MicroTaskSerializer(BaseSerializer):
    """Read serializer for MicroTask."""

    class Meta:
        model = MicroTask
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class MicroTaskCreateSerializer(BaseSerializer):
    """Create/update serializer with validation for MicroTask."""

    class Meta:
        model = MicroTask
        fields = [
            "title",
            "description",
            "description_json",
            "issue",
            "energy_level",
            "estimated_minutes",
            "sort_order",
            "is_completed",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate_estimated_minutes(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("estimated_minutes must be a positive number.")
        return value


class MicroStepDecomposeSerializer(serializers.Serializer):
    """
    Input serializer for the LLM-powered decomposition endpoint.
    Accepts the parent issue and optional configuration — no hardcoded values.
    """

    parent_issue_id = serializers.UUIDField(help_text="UUID of the issue to decompose into micro-tasks.")
    max_steps = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
        help_text="Maximum number of micro-tasks to generate.",
    )
    target_energy = serializers.ChoiceField(
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        required=False,
        help_text="Filter generated tasks to this energy level.",
    )
    max_minutes_per_step = serializers.IntegerField(
        required=False,
        default=15,
        min_value=1,
        max_value=120,
        help_text="Maximum minutes per individual micro-task.",
    )


# ──────────────────────────────────────────────────────────────
# Brain Dump
# ──────────────────────────────────────────────────────────────


class BrainDumpSerializer(serializers.Serializer):
    """
    Input serializer for capturing raw thoughts.
    Accepts text or audio transcription — zero hardcoded defaults.
    """

    raw_text = serializers.CharField(
        required=True,
        max_length=10000,
        help_text="Raw text dump from user (voice-to-text or typed).",
    )
    source = serializers.ChoiceField(
        choices=[("text", "Text"), ("voice", "Voice"), ("paste", "Paste")],
        default="text",
        help_text="How the input was captured.",
    )
    auto_create_issues = serializers.BooleanField(
        default=False,
        help_text="Whether to auto-create issues from extracted action items.",
    )


# ──────────────────────────────────────────────────────────────
# FocusSession
# ──────────────────────────────────────────────────────────────


class FocusSessionSerializer(BaseSerializer):
    """Full serializer for FocusSession with computed duration."""

    actual_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = FocusSession
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "ended_at",
        ]

    def get_actual_duration_minutes(self, obj):
        """Return the actual duration in minutes, computed on session end."""
        return obj.actual_duration_minutes


class FocusSessionCreateSerializer(BaseSerializer):
    """Create serializer for starting a focus session."""

    class Meta:
        model = FocusSession
        fields = [
            "session_type",
            "planned_duration_minutes",
            "issue",
            "mood_before",
            "notes_json",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────────
# ContextSnapshot
# ──────────────────────────────────────────────────────────────


class ContextSnapshotSerializer(BaseSerializer):
    """Full serializer for ContextSnapshot."""

    class Meta:
        model = ContextSnapshot
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ContextSnapshotCreateSerializer(BaseSerializer):
    """Create serializer — snapshot_data comes from the client."""

    class Meta:
        model = ContextSnapshot
        fields = [
            "title",
            "snapshot_data",
            "trigger",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────────
# DopamineMenu
# ──────────────────────────────────────────────────────────────


class DopamineMenuSerializer(BaseSerializer):
    """Full serializer for DopamineMenu rewards."""

    is_available = serializers.SerializerMethodField()

    class Meta:
        model = DopamineMenu
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_is_available(self, obj):
        """Check if the reward is currently available (past cooldown)."""
        return obj.is_available


# ──────────────────────────────────────────────────────────────
# Achievement + UserAchievement
# ──────────────────────────────────────────────────────────────


class AchievementSerializer(BaseSerializer):
    """Read serializer for Achievement definitions."""

    class Meta:
        model = Achievement
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class UserAchievementSerializer(BaseSerializer):
    """Serializer for earned achievements with nested Achievement data."""

    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "earned_at",
        ]


# ──────────────────────────────────────────────────────────────
# Streak
# ──────────────────────────────────────────────────────────────


class StreakSerializer(BaseSerializer):
    """
    Full serializer for Streak — No-Shame Protocol enforced.
    Streaks pause, they never break.
    """

    class Meta:
        model = Streak
        fields = "__all__"
        read_only_fields = [
            "id",
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "current_count",
            "longest_count",
            "last_activity_at",
        ]
