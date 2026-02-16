# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow AI Models — NEXUS Phase 2 Smart Scaffold

These models power the neurodivergent-first executive function support
system. They extend Plane's existing Issue infrastructure with energy-aware
micro-task decomposition, focus session management, context time-machine
snapshots, dopamine-driven reward menus, and gamification streaks.

Design Axioms (from nexus_design_philosophy.md):
  1. Externalize Everything — compensate for working-memory deficits
  2. Reduce to Binary — eliminate choice paralysis
  3. No-Shame Protocol — never punish, always encourage
  4. Body-Double Always — AI companion is always present
  5. Dopamine by Design — reward early and often
  6. Time is Felt, Not Counted — make time concrete and visual
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .project import ProjectBaseModel


# ---------------------------------------------------------------------------
# MicroTask — energy-aware atomic work unit
# ---------------------------------------------------------------------------

class MicroTaskManager(models.Manager):
    """Filters micro-tasks by energy level for 'Just Start' matching."""

    def for_energy(self, level):
        """Return tasks matching or below the given energy level."""
        ENERGY_ORDER = {"low": 1, "medium": 2, "high": 3}
        threshold = ENERGY_ORDER.get(level, 2)
        eligible = [k for k, v in ENERGY_ORDER.items() if v <= threshold]
        return self.filter(energy_level__in=eligible, is_completed=False)

    def appetizers(self):
        """Sub-5-minute tasks for momentum building."""
        return self.filter(
            energy_level="low",
            estimated_minutes__lte=5,
            is_completed=False,
        )


class MicroTask(ProjectBaseModel):
    """
    Atomic work unit decomposed from a parent Issue.

    MicroTasks are the fundamental atom of ExecuFlow — small enough to
    start without triggering the Wall of Awful, tagged with required
    energy so the system can match tasks to the user's current state.

    Fields:
        issue: FK to the parent Issue this micro-task was decomposed from.
        title: Short, action-oriented label (verb-first).
        description_json: Rich text description in Plane's JSON format.
        energy_level: Required energy — low/medium/high.
        estimated_minutes: Time estimate (1-120 min, default 5).
        is_completed: Completion flag.
        completed_at: Timestamp of completion.
        sort_order: Manual ordering within the parent issue.
        just_start_eligible: Whether this shows in "Just Start" prompts.
    """

    ENERGY_CHOICES = (
        ("low", "Low Energy"),
        ("medium", "Medium Energy"),
        ("high", "High Energy"),
    )

    issue = models.ForeignKey(
        "db.Issue",
        on_delete=models.CASCADE,
        related_name="micro_tasks",
    )
    title = models.CharField(max_length=512)
    description_json = models.JSONField(default=dict, blank=True)
    energy_level = models.CharField(
        max_length=10,
        choices=ENERGY_CHOICES,
        default="medium",
    )
    estimated_minutes = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.FloatField(default=65535)
    just_start_eligible = models.BooleanField(default=True)

    objects = MicroTaskManager()

    class Meta:
        verbose_name = "Micro Task"
        verbose_name_plural = "Micro Tasks"
        db_table = "execuflow_micro_tasks"
        ordering = ("sort_order", "created_at")

    def __str__(self):
        return f"[{self.energy_level}] {self.title}"

    def mark_complete(self):
        """Mark this micro-task as done with timestamp."""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=["is_completed", "completed_at", "updated_at"])


# ---------------------------------------------------------------------------
# FocusSession — body-double pomodoro with interrupt queue
# ---------------------------------------------------------------------------

class FocusSession(ProjectBaseModel):
    """
    A timed focus block with AI body-double and interrupt queue.

    When a user starts a FocusSession, notifications are queued rather
    than delivered, the AI companion announces its own parallel task,
    and a countdown timer makes elapsed time viscerally visible.

    Fields:
        user: The user running this session.
        issue: Optional Issue being worked on.
        micro_task: Optional MicroTask being focused on.
        started_at: Session start time.
        ended_at: Session end time (null if active).
        planned_duration_minutes: Target length (default 25 — Pomodoro).
        actual_duration_minutes: Computed on completion.
        session_type: pomodoro / deep_work / body_double / free_flow.
        interrupt_queue: JSONField holding queued notifications.
        mood_before: Self-reported mood at session start (1-5).
        mood_after: Self-reported mood at session end (1-5).
        notes_json: Freeform notes captured during the session.
        is_active: Whether the session is currently running.
    """

    SESSION_TYPE_CHOICES = (
        ("pomodoro", "Pomodoro (25 min)"),
        ("deep_work", "Deep Work (90 min)"),
        ("body_double", "Body Double"),
        ("free_flow", "Free Flow"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="focus_sessions",
    )
    issue = models.ForeignKey(
        "db.Issue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="focus_sessions",
    )
    micro_task = models.ForeignKey(
        MicroTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="focus_sessions",
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    planned_duration_minutes = models.PositiveSmallIntegerField(default=25)
    actual_duration_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        default="pomodoro",
    )
    interrupt_queue = models.JSONField(default=list, blank=True)
    mood_before = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    mood_after = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    notes_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Focus Session"
        verbose_name_plural = "Focus Sessions"
        db_table = "execuflow_focus_sessions"
        ordering = ("-started_at",)
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="idx_focus_user_active",
            ),
            models.Index(
                fields=["user", "started_at"],
                name="idx_focus_user_started",
            ),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Done"
        return f"FocusSession({self.session_type}, {status})"

    def end_session(self):
        """End the session and compute actual duration."""
        self.ended_at = timezone.now()
        self.is_active = False
        delta = self.ended_at - self.started_at
        self.actual_duration_minutes = int(delta.total_seconds() / 60)
        self.save(
            update_fields=[
                "ended_at",
                "is_active",
                "actual_duration_minutes",
                "updated_at",
            ]
        )


# ---------------------------------------------------------------------------
# ContextSnapshot — workspace state time-machine
# ---------------------------------------------------------------------------

class ContextSnapshot(ProjectBaseModel):
    """
    Saves a complete snapshot of the user's working context.

    When a user is interrupted or switches tasks, ContextSnapshot
    captures open tabs, active files, cursor positions, and mental
    notes — allowing perfect context restoration later.

    This compensates for the ADHD working-memory deficit that makes
    task-switching catastrophically expensive.

    Fields:
        user: The user whose context is captured.
        title: Human-readable label (auto-generated or user-named).
        snapshot_data: Full workspace state as JSON.
        trigger: How the snapshot was created.
        restored_at: When/if this snapshot was restored.
        is_pinned: Whether the user wants to keep this snapshot.
    """

    TRIGGER_CHOICES = (
        ("manual", "Manual Save"),
        ("auto_interrupt", "Auto (Interrupt Detected)"),
        ("auto_switch", "Auto (Task Switch)"),
        ("auto_timer", "Auto (Periodic)"),
        ("session_end", "Session End"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="context_snapshots",
    )
    title = models.CharField(max_length=255, default="Untitled Snapshot")
    snapshot_data = models.JSONField(
        default=dict,
        help_text="Full workspace state: open issues, scroll positions, "
        "active filters, draft text, mental notes.",
    )
    trigger = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        default="manual",
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Context Snapshot"
        verbose_name_plural = "Context Snapshots"
        db_table = "execuflow_context_snapshots"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="idx_ctx_user_created",
            ),
        ]

    def __str__(self):
        return f"Context: {self.title} ({self.trigger})"


# ---------------------------------------------------------------------------
# DopamineMenu — reward system for momentum
# ---------------------------------------------------------------------------

class DopamineMenu(ProjectBaseModel):
    """
    A categorized menu of rewards the user has pre-selected.

    Dopamine by Design: after completing micro-tasks, users pick from
    their own reward menu. Categories follow a meal metaphor:
      - Appetizer (< 5 min): quick dopamine hits
      - Side (5-15 min): moderate breaks
      - Entrée (15-30 min): substantial rewards
      - Dessert (30+ min): major treats for big wins

    Fields:
        user: The user who owns this menu item.
        title: Name of the reward.
        category: appetizer / side / entree / dessert.
        description: Optional details.
        cooldown_minutes: Min time between uses (prevents over-rewarding).
        last_used_at: When this reward was last claimed.
        use_count: How many times this reward has been used.
        is_active: Whether this item appears in the menu.
    """

    CATEGORY_CHOICES = (
        ("appetizer", "Appetizer (< 5 min)"),
        ("side", "Side (5-15 min)"),
        ("entree", "Entrée (15-30 min)"),
        ("dessert", "Dessert (30+ min)"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dopamine_menu_items",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default="appetizer",
    )
    description = models.TextField(blank=True, default="")
    cooldown_minutes = models.PositiveSmallIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Dopamine Menu Item"
        verbose_name_plural = "Dopamine Menu Items"
        db_table = "execuflow_dopamine_menu"
        ordering = ("category", "title")

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def claim(self):
        """Record usage of this reward."""
        self.last_used_at = timezone.now()
        self.use_count += 1
        self.save(update_fields=["last_used_at", "use_count", "updated_at"])

    @property
    def is_on_cooldown(self):
        """Check if reward is still in cooldown period."""
        if not self.last_used_at or self.cooldown_minutes == 0:
            return False
        elapsed = (timezone.now() - self.last_used_at).total_seconds() / 60
        return elapsed < self.cooldown_minutes

    @property
    def is_available(self):
        """Check if reward is currently available (not on cooldown)."""
        return not self.is_on_cooldown


# ---------------------------------------------------------------------------
# Achievement — milestone celebration
# ---------------------------------------------------------------------------

class Achievement(ProjectBaseModel):
    """
    Unlockable achievements for celebrating progress.

    Achievements are workspace-scoped and can be earned by any user.
    They are designed to be encouraging, never competitive — celebrating
    personal milestones, not ranking users against each other.

    Fields:
        name: Achievement title (e.g., "First Focus Session").
        description: What the user did to earn this.
        icon: Emoji or icon identifier.
        category: Category grouping.
        criteria_json: Machine-readable unlock criteria.
        xp_value: Experience points awarded.
        is_secret: Hidden until earned (surprise dopamine).
    """

    CATEGORY_CHOICES = (
        ("momentum", "Momentum"),
        ("consistency", "Consistency"),
        ("mastery", "Mastery"),
        ("exploration", "Exploration"),
        ("collaboration", "Collaboration"),
    )

    name = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=50, default="🏆")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="momentum",
    )
    criteria_json = models.JSONField(
        default=dict,
        help_text="Machine-readable criteria for auto-unlocking.",
    )
    xp_value = models.PositiveIntegerField(default=10)
    is_secret = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"
        db_table = "execuflow_achievements"
        ordering = ("category", "name")

    def __str__(self):
        return f"{self.icon} {self.name}"


class UserAchievement(ProjectBaseModel):
    """
    Junction model tracking which users have earned which achievements.

    Fields:
        user: The user who earned the achievement.
        achievement: The achievement that was earned.
        earned_at: When the achievement was unlocked.
        celebration_shown: Whether the celebration UI was displayed.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="user_achievements",
    )
    earned_at = models.DateTimeField(default=timezone.now)
    celebration_shown = models.BooleanField(default=False)

    class Meta:
        verbose_name = "User Achievement"
        verbose_name_plural = "User Achievements"
        db_table = "execuflow_user_achievements"
        ordering = ("-earned_at",)
        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user} earned {self.achievement}"


# ---------------------------------------------------------------------------
# Streak — consistency tracking (No-Shame: streaks never "break")
# ---------------------------------------------------------------------------

class Streak(ProjectBaseModel):
    """
    Tracks consistency patterns with a No-Shame philosophy.

    Key design: streaks never "break" in a punitive way. Instead:
      - Active streaks show encouragement
      - Paused streaks show "welcome back" messaging
      - Grace periods prevent accidental loss

    This follows the No-Shame Protocol — the system never makes the
    user feel bad about gaps in productivity.

    Fields:
        user: The streak owner.
        streak_type: What's being tracked.
        current_count: Current consecutive days/sessions.
        longest_count: Personal best (never resets).
        last_activity_at: Most recent qualifying activity.
        grace_period_hours: Hours of inactivity before pause (default 48).
        status: active / paused / archived.
        metadata: Flexible JSON for type-specific data.
    """

    STREAK_TYPE_CHOICES = (
        ("daily_login", "Daily Login"),
        ("focus_session", "Focus Sessions"),
        ("task_completion", "Task Completions"),
        ("brain_dump", "Brain Dumps"),
        ("review", "Daily Reviews"),
    )

    STATUS_CHOICES = (
        ("active", "Active"),
        ("paused", "Paused (Welcome Back!)"),
        ("archived", "Archived"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streaks",
    )
    streak_type = models.CharField(
        max_length=20,
        choices=STREAK_TYPE_CHOICES,
    )
    current_count = models.PositiveIntegerField(default=0)
    longest_count = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    grace_period_hours = models.PositiveSmallIntegerField(default=48)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Streak"
        verbose_name_plural = "Streaks"
        db_table = "execuflow_streaks"
        ordering = ("-current_count",)
        unique_together = ("user", "streak_type", "workspace")

    def __str__(self):
        return f"{self.get_streak_type_display()}: {self.current_count} ({self.status})"

    def record_activity(self):
        """Record a qualifying activity and update the streak."""
        now = timezone.now()

        if self.status == "paused":
            # Welcome back — don't punish, just resume
            self.status = "active"
            self.current_count = 1
        else:
            self.current_count += 1

        self.last_activity_at = now

        if self.current_count > self.longest_count:
            self.longest_count = self.current_count

        self.save(
            update_fields=[
                "current_count",
                "longest_count",
                "last_activity_at",
                "status",
                "updated_at",
            ]
        )

    def check_grace_period(self):
        """
        Check if the streak should be paused (not broken!).

        Called periodically — if the grace period has elapsed since
        last activity, the streak is paused, not destroyed.
        """
        if (
            self.status == "active"
            and self.last_activity_at
            and self.grace_period_hours > 0
        ):
            hours_elapsed = (
                timezone.now() - self.last_activity_at
            ).total_seconds() / 3600
            if hours_elapsed > self.grace_period_hours:
                self.status = "paused"
                self.save(update_fields=["status", "updated_at"])
