# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
ExecuFlow AI Provider Integration

Dual-provider architecture:
  Primary  ->  Claude Opus 4.6  (claude-opus-4-6)
  Fallback ->  Gemini 3 Pro     (gemini-3-pro-preview)

All functions return plain list[dict] matching the existing
_decompose_issue / _extract_action_items contracts.
If both providers fail the original stub logic is used.
"""

import json
import logging
import os

from .config import (
    ANTHROPIC_MODEL,
    DECOMPOSE_PROMPT,
    EXTRACT_PROMPT,
    GEMINI_MODEL,
)

logger = logging.getLogger(__name__)

# ── Provider clients (lazy-initialised) ──────────────────────

_anthropic_client = None
_gemini_model = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        import anthropic

        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _get_gemini():
    global _gemini_model
    if _gemini_model is None:
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        import google.generativeai as genai

        genai.configure(api_key=key)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    return _gemini_model


# ── JSON parser ──────────────────────────────────────────────


def _parse_json_array(text):
    """Extract a JSON array from LLM output."""
    text = text.strip()
    # Strip markdown fences if the model added them
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    # Try to find array in the text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ── Anthropic caller ─────────────────────────────────────────


def _call_anthropic(prompt):
    """Call Claude Opus 4.6 and return parsed JSON array."""
    client = _get_anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return _parse_json_array(text)


# ── Gemini caller ────────────────────────────────────────────


def _call_gemini(prompt):
    """Call Gemini 3 Pro and return parsed JSON array."""
    model = _get_gemini()
    response = model.generate_content(prompt)
    text = response.text
    return _parse_json_array(text)


# ── Provider dispatch with fallback ──────────────────────────


def _call_with_fallback(prompt, label="ai_call"):
    """
    Try the configured primary provider; on failure try the
    secondary. Returns parsed list or None.
    """
    provider = os.environ.get("EXECUFLOW_AI_PROVIDER", "anthropic")

    if provider == "fallback":
        order = [
            ("Anthropic", _call_anthropic),
            ("Gemini", _call_gemini),
        ]
    elif provider == "google":
        order = [
            ("Gemini", _call_gemini),
            ("Anthropic", _call_anthropic),
        ]
    else:  # default: anthropic
        order = [
            ("Anthropic", _call_anthropic),
            ("Gemini", _call_gemini),
        ]

    for name, caller in order:
        try:
            result = caller(prompt)
            if result:
                logger.info(
                    "%s: %s returned %d items",
                    label,
                    name,
                    len(result),
                )
                return result
            logger.warning(
                "%s: %s returned unparseable output",
                label,
                name,
            )
        except Exception as exc:
            logger.warning(
                "%s: %s failed -- %s",
                label,
                name,
                exc,
            )

    return None


# ── Public API ───────────────────────────────────────────────


def decompose_issue_with_ai(
    issue_title,
    issue_description,
    max_steps=5,
    target_energy="low",
    max_minutes_per_step=15,
):
    """
    Break an issue into micro-steps using AI.

    Returns list[dict] with keys:
      title, description, energy_level, estimated_minutes

    Falls back to simple stub if both providers fail.
    """
    prompt = DECOMPOSE_PROMPT.format(
        max_steps=max_steps,
        title=issue_title,
        description=issue_description,
        energy=target_energy or "low",
        minutes=max_minutes_per_step,
    )

    result = _call_with_fallback(prompt, "decompose")
    if result:
        # Normalise keys
        steps = []
        for item in result[:max_steps]:
            steps.append(
                {
                    "title": str(item.get("title", ""))[:200],
                    "description": str(item.get("description", "")),
                    "energy_level": str(
                        item.get(
                            "energy_level",
                            target_energy or "low",
                        )
                    ),
                    "estimated_minutes": min(
                        int(
                            item.get(
                                "estimated_minutes",
                                max_minutes_per_step,
                            )
                        ),
                        max_minutes_per_step,
                    ),
                }
            )
        return steps

    # ── Last-resort stub ──
    logger.warning("decompose: all providers failed, using stub")
    steps = []
    for i in range(min(max_steps, 5)):
        steps.append(
            {
                "title": f"Step {i + 1} for: {issue_title[:50]}",
                "description": (f"Work on part {i + 1} -- {issue_description[:50]}"),
                "energy_level": target_energy or "low",
                "estimated_minutes": min(max_minutes_per_step, 15),
            }
        )
    return steps


def extract_actions_with_ai(raw_text):
    """
    Extract action items from raw brain-dump text using AI.

    Returns list[dict] with keys: title, description

    Falls back to sentence splitting if both providers fail.
    """
    if not raw_text or not raw_text.strip():
        return []

    prompt = EXTRACT_PROMPT.format(raw_text=raw_text)

    result = _call_with_fallback(prompt, "extract")
    if result:
        items = []
        for item in result[:10]:
            items.append(
                {
                    "title": str(item.get("title", ""))[:200],
                    "description": str(item.get("description", "")),
                }
            )
        return items

    # ── Last-resort stub ──
    logger.warning("extract: all providers failed, using stub")
    raw = raw_text.replace("\n", ". ")
    sentences = [s.strip() for s in raw.split(".") if s.strip() and len(s.strip()) > 3]
    items = []
    for sentence in sentences[:10]:
        items.append(
            {
                "title": sentence[:200],
                "description": sentence,
            }
        )
    return items
