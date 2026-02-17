# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow Background Tasks for Asynchronous AI Processing

This module contains Celery tasks that handle AI provider calls
asynchronously for ExecuFlow features:
  - Issue decomposition into micro-tasks
  - Brain dump text extraction into action items

Uses the dual-provider architecture (Claude Opus 4.6 + Gemini 3 Pro)
defined in plane.services.ai.providers.
"""

import logging
from typing import Any, Dict

from celery import shared_task
from django.db import transaction

from plane.services.ai import (
    decompose_issue_with_ai,
    extract_actions_with_ai,
)
from plane.consumers.utils import broadcast_task_update
from plane.db.models import Issue, MicroTask, Project, User

logger = logging.getLogger(__name__)

# Task configuration constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60
MAX_BRAIN_DUMP_ITEMS = 10


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_DELAY_SECONDS)
def decompose_issue_task(
    self,
    issue_id: str,
    max_steps: int,
    target_energy: str,
    max_minutes_per_step: int,
    workspace_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Async task to decompose an issue into micro-tasks using AI.

    Args:
        issue_id: UUID of the parent issue
        max_steps: Maximum number of micro-tasks to generate
        target_energy: Target energy level (low/medium/high)
        max_minutes_per_step: Max estimated minutes per step
        workspace_id: UUID of the workspace
        user_id: UUID of the user who triggered this

    Returns:
        dict: Task result with status, issue_id, created_count

    Raises:
        Retry: On transient failures (rate limits, network errors)
    """
    try:
        # Fetch the parent issue
        try:
            issue = Issue.objects.get(pk=issue_id, workspace_id=workspace_id)
        except Issue.DoesNotExist:
            logger.error("decompose_issue_task: Issue %s not found", issue_id)
            result = {
                "status": "error",
                "issue_id": issue_id,
                "error": "Issue not found",
            }
            broadcast_task_update(self.request.id, result)
            return result

        # Get user for created_by/updated_by
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error("decompose_issue_task: User %s not found", user_id)
            result = {
                "status": "error",
                "issue_id": issue_id,
                "error": "User not found",
            }
            broadcast_task_update(self.request.id, result)
            return result

        # Call AI provider to decompose issue
        issue_title = issue.name or "Untitled Issue"
        issue_description = issue.description_stripped or issue_title

        try:
            decomposed_steps = decompose_issue_with_ai(
                issue_title=issue_title,
                issue_description=issue_description,
                max_steps=max_steps,
                target_energy=target_energy,
                max_minutes_per_step=max_minutes_per_step,
            )
        except Exception as exc:
            # Retry on AI provider failures (rate limits, network, etc)
            logger.warning(
                "decompose_issue_task: AI call failed for issue %s: %s",
                issue_id,
                exc,
            )
            raise self.retry(exc=exc)

        # Create MicroTask records in a transaction
        created_tasks = []
        with transaction.atomic():
            for idx, step in enumerate(decomposed_steps):
                task = MicroTask.objects.create(
                    title=step.get("title", f"Step {idx + 1}"),
                    description_json={"text": step.get("description", "")},
                    issue=issue,
                    energy_level=step.get("energy_level", target_energy or "low"),
                    estimated_minutes=step.get("estimated_minutes", 5),
                    sort_order=idx,
                    project_id=issue.project_id,
                    workspace_id=workspace_id,
                    created_by=user,
                    updated_by=user,
                )
                created_tasks.append(task)

        logger.info(
            "decompose_issue_task: Created %d micro-tasks for issue %s",
            len(created_tasks),
            issue_id,
        )

        result = {
            "status": "SUCCESS",
            "issue_id": issue_id,
            "created_count": len(created_tasks),
            "task_ids": [str(t.id) for t in created_tasks],
        }
        broadcast_task_update(self.request.id, result)
        return result

    except Exception as exc:
        # Log unexpected errors
        logger.exception(
            "decompose_issue_task: Unexpected error for issue %s",
            issue_id,
        )
        result = {
            "status": "error",
            "issue_id": issue_id,
            "error": str(exc),
        }
        broadcast_task_update(self.request.id, result)
        return result


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_DELAY_SECONDS)
def process_brain_dump_task(
    self,
    raw_text: str,
    source: str,
    auto_create_issues: bool,
    workspace_id: str,
    project_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Async task to process brain dump text using AI.

    Extracts action items from raw text (voice-to-text or manual input)
    and optionally creates issues for each item.

    Args:
        raw_text: Raw unstructured text input
        source: Source of text ("voice", "text", etc)
        auto_create_issues: Whether to auto-create Issue records
        workspace_id: UUID of the workspace
        project_id: UUID of the project
        user_id: UUID of the user who triggered this

    Returns:
        dict: Task result with status, extracted_count, created_issues_count

    Raises:
        Retry: On transient failures (rate limits, network errors)
    """
    try:
        # Validate project exists
        try:
            project = Project.objects.get(pk=project_id, workspace_id=workspace_id)
        except Project.DoesNotExist:
            logger.error("process_brain_dump_task: Project %s not found", project_id)
            result = {
                "status": "error",
                "error": "Project not found",
            }
            broadcast_task_update(self.request.id, result)
            return result

        # Get user
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error("process_brain_dump_task: User %s not found", user_id)
            result = {
                "status": "error",
                "error": "User not found",
            }
            broadcast_task_update(self.request.id, result)
            return result

        # Call AI provider to extract action items
        try:
            extracted_items = extract_actions_with_ai(raw_text)
        except Exception as exc:
            # Retry on AI provider failures
            logger.warning(
                "process_brain_dump_task: AI call failed: %s",
                exc,
            )
            raise self.retry(exc=exc)

        created_issues = []

        # Create issues if auto_create is enabled
        if auto_create_issues and extracted_items:
            # Limit to prevent spam
            items_to_create = extracted_items[:MAX_BRAIN_DUMP_ITEMS]

            with transaction.atomic():
                for item in items_to_create:
                    issue = Issue.objects.create(
                        name=item.get("title", "Untitled")[:200],
                        description_stripped=item.get("description", ""),
                        project=project,
                        workspace_id=workspace_id,
                        created_by=user,
                        updated_by=user,
                    )
                    created_issues.append(issue)

        logger.info(
            "process_brain_dump_task: Extracted %d items, created %d issues",
            len(extracted_items),
            len(created_issues),
        )

        result = {
            "status": "SUCCESS",
            "extracted_count": len(extracted_items),
            "created_issues_count": len(created_issues),
            "issue_ids": [str(i.id) for i in created_issues],
            "extracted_items": extracted_items,
        }
        broadcast_task_update(self.request.id, result)
        return result

    except Exception as exc:
        # Log unexpected errors
        logger.exception("process_brain_dump_task: Unexpected error")
        result = {
            "status": "error",
            "error": str(exc),
        }
        broadcast_task_update(self.request.id, result)
        return result
