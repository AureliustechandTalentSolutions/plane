/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

"use client";

import { useEffect, useCallback } from "react";
import { observer } from "mobx-react";
import { Play, Pause, RotateCcw, Zap } from "lucide-react";
// plane imports
import type { THomeWidgetProps } from "@plane/types";
import { useExecuFlow  } from "./use-execuflow";
import type {TSessionType} from "./use-execuflow";

const FOCUS_DURATIONS: Record<TSessionType, number> = {
  micro: 5 * 60, // 5 min
  short: 15 * 60, // 15 min
  flow: 25 * 60, // 25 min
  deep: 50 * 60, // 50 min
};

type TFocusState = "idle" | "working" | "break" | "paused";

export const ExecuFlowFocusWidget = observer(function ExecuFlowFocusWidget(props: THomeWidgetProps) {
  const { workspaceSlug } = props;

  const { activeSession, completedToday, startSession, pauseSession, resumeSession, endSession, updateSecondsLeft } =
    useExecuFlow({ workspaceSlug });

  // Derive state from activeSession
  const focusState: TFocusState = activeSession
    ? activeSession.isPaused
      ? "paused"
      : activeSession.secondsLeft <= 0
        ? "break"
        : "working"
    : "idle";

  const secondsLeft = activeSession?.secondsLeft ?? FOCUS_DURATIONS.flow;
  const selectedDuration: TSessionType = activeSession?.sessionType ?? "flow";

  // Timer logic
  useEffect(() => {
    if (focusState !== "working" || !activeSession) return;

    if (activeSession.secondsLeft <= 0) {
      endSession();
      return;
    }

    const timer = setInterval(() => {
      updateSecondsLeft(activeSession.secondsLeft - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [focusState, activeSession, endSession, updateSecondsLeft]);

  const formatTime = useCallback((secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }, []);

  const handleStart = (duration: TSessionType) => startSession(duration);
  const handlePause = () => pauseSession();
  const handleResume = () => resumeSession();
  const handleReset = () => endSession();

  const progress = activeSession ? 1 - activeSession.secondsLeft / (activeSession.plannedMinutes * 60) : 0;

  return (
    <div className="rounded-lg border border-subtle bg-surface-1 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" />
          <h3 className="text-14 font-medium text-primary">Focus Timer</h3>
        </div>
        <span className="text-12 text-tertiary">
          {completedToday} session{completedToday !== 1 ? "s" : ""} today
        </span>
      </div>

      {/* Timer display */}
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-32 h-32">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="currentColor"
              className="text-surface-3"
              strokeWidth="6"
            />
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="currentColor"
              className="text-amber-500 transition-all duration-1000"
              strokeWidth="6"
              strokeDasharray={`${progress * 283} 283`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-24 font-mono font-semibold text-primary">{formatTime(secondsLeft)}</span>
          </div>
        </div>

        {/* Duration selector (only when idle) */}
        {focusState === "idle" && (
          <div className="flex gap-2">
            {(Object.keys(FOCUS_DURATIONS) as TSessionType[]).map((key) => (
              <button
                key={key}
                onClick={() => handleStart(key)}
                className="px-3 py-1 rounded-full text-12 font-medium transition-colors bg-surface-3 text-secondary hover:text-primary hover:bg-amber-500/15 hover:text-amber-500"
              >
                {key === "micro" ? "5m" : key === "short" ? "15m" : key === "flow" ? "25m" : "50m"}
              </button>
            ))}
          </div>
        )}

        {/* Active session indicator */}
        {focusState !== "idle" && (
          <div className="text-12 text-tertiary">
            {selectedDuration === "micro"
              ? "Micro focus"
              : selectedDuration === "short"
                ? "Short session"
                : selectedDuration === "flow"
                  ? "Flow session"
                  : "Deep work"}
          </div>
        )}

        {/* Controls */}
        <div className="flex gap-2">
          {focusState === "working" && (
            <button
              onClick={handlePause}
              className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-surface-3 text-secondary text-13 font-medium hover:text-primary transition-colors"
            >
              <Pause className="h-3.5 w-3.5" /> Pause
            </button>
          )}
          {focusState === "paused" && (
            <>
              <button
                onClick={handleResume}
                className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-amber-500 text-white text-13 font-medium hover:bg-amber-600 transition-colors"
              >
                <Play className="h-3.5 w-3.5" /> Resume
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-surface-3 text-secondary text-13 font-medium hover:text-primary transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Reset
              </button>
            </>
          )}
          {focusState === "break" && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-green-500 text-white text-13 font-medium hover:bg-green-600 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" /> New Session
            </button>
          )}
        </div>

        {focusState === "break" && (
          <p className="text-13 text-green-500 font-medium animate-pulse">Focus session complete! Take a break.</p>
        )}
      </div>
    </div>
  );
});
