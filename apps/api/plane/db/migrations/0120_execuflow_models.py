# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow AI Models — Phase 2 Smart Scaffold
Creates: MicroTask, FocusSession, ContextSnapshot, DopamineMenu,
         Achievement, UserAchievement, Streak
"""

import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0119_alter_estimatepoint_key"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -----------------------------------------------------------
        # MicroTask
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="MicroTask",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=512)),
                (
                    "description_json",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "energy_level",
                    models.CharField(
                        choices=[
                            ("low", "Low Energy"),
                            ("medium", "Medium Energy"),
                            ("high", "High Energy"),
                        ],
                        default="medium",
                        max_length=10,
                    ),
                ),
                (
                    "estimated_minutes",
                    models.PositiveSmallIntegerField(
                        default=5,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(120),
                        ],
                    ),
                ),
                ("is_completed", models.BooleanField(default=False)),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("sort_order", models.FloatField(default=65535)),
                (
                    "just_start_eligible",
                    models.BooleanField(default=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="micro_tasks",
                        to="db.issue",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Micro Task",
                "verbose_name_plural": "Micro Tasks",
                "db_table": "execuflow_micro_tasks",
                "ordering": ("sort_order", "created_at"),
            },
        ),
        # -----------------------------------------------------------
        # FocusSession
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="FocusSession",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "planned_duration_minutes",
                    models.PositiveSmallIntegerField(default=25),
                ),
                (
                    "actual_duration_minutes",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True
                    ),
                ),
                (
                    "session_type",
                    models.CharField(
                        choices=[
                            ("pomodoro", "Pomodoro (25 min)"),
                            ("deep_work", "Deep Work (90 min)"),
                            ("body_double", "Body Double"),
                            ("free_flow", "Free Flow"),
                        ],
                        default="pomodoro",
                        max_length=20,
                    ),
                ),
                (
                    "interrupt_queue",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "mood_before",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "mood_after",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "notes_json",
                    models.JSONField(blank=True, default=dict),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="focus_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="focus_sessions",
                        to="db.issue",
                    ),
                ),
                (
                    "micro_task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="focus_sessions",
                        to="db.microtask",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Focus Session",
                "verbose_name_plural": "Focus Sessions",
                "db_table": "execuflow_focus_sessions",
                "ordering": ("-started_at",),
            },
        ),
        migrations.AddIndex(
            model_name="focussession",
            index=models.Index(
                fields=["user", "is_active"],
                name="idx_focus_user_active",
            ),
        ),
        migrations.AddIndex(
            model_name="focussession",
            index=models.Index(
                fields=["user", "started_at"],
                name="idx_focus_user_started",
            ),
        ),
        # -----------------------------------------------------------
        # ContextSnapshot
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="ContextSnapshot",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        default="Untitled Snapshot", max_length=255
                    ),
                ),
                (
                    "snapshot_data",
                    models.JSONField(
                        default=dict,
                        help_text=(
                            "Full workspace state: open issues, "
                            "scroll positions, active filters, "
                            "draft text, mental notes."
                        ),
                    ),
                ),
                (
                    "trigger",
                    models.CharField(
                        choices=[
                            ("manual", "Manual Save"),
                            ("auto_interrupt", "Auto (Interrupt Detected)"),
                            ("auto_switch", "Auto (Task Switch)"),
                            ("auto_timer", "Auto (Periodic)"),
                            ("session_end", "Session End"),
                        ],
                        default="manual",
                        max_length=20,
                    ),
                ),
                (
                    "restored_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("is_pinned", models.BooleanField(default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="context_snapshots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Context Snapshot",
                "verbose_name_plural": "Context Snapshots",
                "db_table": "execuflow_context_snapshots",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="contextsnapshot",
            index=models.Index(
                fields=["user", "-created_at"],
                name="idx_ctx_user_created",
            ),
        ),
        # -----------------------------------------------------------
        # DopamineMenu
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="DopamineMenu",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("appetizer", "Appetizer (< 5 min)"),
                            ("side", "Side (5-15 min)"),
                            ("entree", "Entrée (15-30 min)"),
                            ("dessert", "Dessert (30+ min)"),
                        ],
                        default="appetizer",
                        max_length=10,
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "cooldown_minutes",
                    models.PositiveSmallIntegerField(default=0),
                ),
                (
                    "last_used_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "use_count",
                    models.PositiveIntegerField(default=0),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dopamine_menu_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dopamine Menu Item",
                "verbose_name_plural": "Dopamine Menu Items",
                "db_table": "execuflow_dopamine_menu",
                "ordering": ("category", "title"),
            },
        ),
        # -----------------------------------------------------------
        # Achievement
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="Achievement",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField()),
                (
                    "icon",
                    models.CharField(default="🏆", max_length=50),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("momentum", "Momentum"),
                            ("consistency", "Consistency"),
                            ("mastery", "Mastery"),
                            ("exploration", "Exploration"),
                            ("collaboration", "Collaboration"),
                        ],
                        default="momentum",
                        max_length=20,
                    ),
                ),
                (
                    "criteria_json",
                    models.JSONField(
                        default=dict,
                        help_text=(
                            "Machine-readable criteria for auto-unlocking."
                        ),
                    ),
                ),
                (
                    "xp_value",
                    models.PositiveIntegerField(default=10),
                ),
                ("is_secret", models.BooleanField(default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Achievement",
                "verbose_name_plural": "Achievements",
                "db_table": "execuflow_achievements",
                "ordering": ("category", "name"),
            },
        ),
        # -----------------------------------------------------------
        # UserAchievement
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="UserAchievement",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "earned_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "celebration_shown",
                    models.BooleanField(default=False),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="achievements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "achievement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_achievements",
                        to="db.achievement",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Achievement",
                "verbose_name_plural": "User Achievements",
                "db_table": "execuflow_user_achievements",
                "ordering": ("-earned_at",),
                "unique_together": {("user", "achievement")},
            },
        ),
        # -----------------------------------------------------------
        # Streak
        # -----------------------------------------------------------
        migrations.CreateModel(
            name="Streak",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last Modified At"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "streak_type",
                    models.CharField(
                        choices=[
                            ("daily_login", "Daily Login"),
                            ("focus_session", "Focus Sessions"),
                            ("task_completion", "Task Completions"),
                            ("brain_dump", "Brain Dumps"),
                            ("review", "Daily Reviews"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "current_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "longest_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "last_activity_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "grace_period_hours",
                    models.PositiveSmallIntegerField(default=48),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("paused", "Paused (Welcome Back!)"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=10,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="streaks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Streak",
                "verbose_name_plural": "Streaks",
                "db_table": "execuflow_streaks",
                "ordering": ("-current_count",),
                "unique_together": {
                    ("user", "streak_type", "workspace")
                },
            },
        ),
    ]
