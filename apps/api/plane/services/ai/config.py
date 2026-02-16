# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow AI Provider Configuration

Centralises model identifiers, environment variable names,
and prompt templates used by the AI provider layer.
"""

# ── Model identifiers ────────────────────────────────────────

ANTHROPIC_MODEL = "claude-opus-4-6"
GEMINI_MODEL = "gemini-3-pro-preview"

# ── Prompt templates ─────────────────────────────────────────

DECOMPOSE_PROMPT = """You are an ADHD-friendly task decomposition assistant.

Break the following issue into {max_steps} small, concrete micro-steps.

Issue title: {title}
Issue description: {description}

Requirements for each step:
- Energy level should be "{energy}" (low/medium/high)
- Each step should take at most {minutes} minutes
- Titles must be short action verbs (< 60 chars)
- Descriptions should be 1-2 sentences

Return ONLY a JSON array, no markdown fences. Each element:
{{
  "title": "...",
  "description": "...",
  "energy_level": "...",
  "estimated_minutes": N
}}
"""

EXTRACT_PROMPT = """You are an ADHD-friendly brain dump processor.

Extract concrete action items from this raw text:

---
{raw_text}
---

Rules:
- Each item needs a short title (< 200 chars) and a description
- Ignore filler words, focus on actionable tasks
- Return at most 10 items
- Return ONLY a JSON array, no markdown fences. Each element:
{{"title": "...", "description": "..."}}
"""
