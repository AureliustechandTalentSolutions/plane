# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Test Settings"""

from .common import *  # noqa

DEBUG = True

# Send it in a dummy outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

INSTALLED_APPS.append(  # noqa
    "plane.tests"
)

# Use in-memory channel layer for WebSocket tests (no Redis required)
# SOURCE: feature/nexus-phase2-smart-scaffold — adapted for local V&V
CHANNEL_LAYERS = {  # noqa: F811
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
