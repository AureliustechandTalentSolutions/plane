/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TSessionType as TWidgetSessionType } from "./use-execuflow";
import type { TSessionType as TApiSessionType } from "@/store/execuflow.store";

/**
 * Maps widget-level session types (used by the timer UI) to the API session
 * types accepted by the ExecuFlow backend.
 *
 * Widget types describe user-facing durations:
 *   micro  = 5 min
 *   short  = 15 min
 *   flow   = 25 min
 *   deep   = 50 min
 *
 * API types describe work patterns:
 *   pomodoro  — classic 25-min sprint (used for micro/short)
 *   deep_work — extended focus block (used for flow/deep)
 */
export const WIDGET_TO_API_SESSION_MAP: Record<TWidgetSessionType, TApiSessionType> = {
  micro: "pomodoro",
  short: "pomodoro",
  flow: "deep_work",
  deep: "deep_work",
};

/**
 * Convert a widget session type to its corresponding API session type.
 */
export function toApiSessionType(widgetType: TWidgetSessionType): TApiSessionType {
  return WIDGET_TO_API_SESSION_MAP[widgetType];
}

/**
 * Planned duration in minutes per widget session type, mirroring the
 * duration expected by the API for each session category.
 */
export const WIDGET_PLANNED_DURATION_MAP: Record<TWidgetSessionType, number> = {
  micro: 5,
  short: 15,
  flow: 25,
  deep: 50,
};
