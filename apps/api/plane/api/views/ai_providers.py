# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
DEPRECATED -- This module has moved to plane.services.ai

Kept for backward compatibility. Import from plane.services.ai instead.
"""

import warnings

warnings.warn(
    "plane.api.views.ai_providers is deprecated. "
    "Import from plane.services.ai instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the new location
from plane.services.ai.providers import (  # noqa: F401, E402
    _call_with_fallback,
    _get_anthropic,
    _get_gemini,
    decompose_issue_with_ai,
    extract_actions_with_ai,
)
