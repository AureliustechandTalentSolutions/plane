/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

"use client";

import { useEffect, useCallback, useRef } from "react";
import { observer } from "mobx-react";
import { Play, Pause, RotateCcw, Zap } from "lucide-react";
// plane imports
import type { THomeWidgetProps } from "@plane/types";
import { useTranslation } from "@plane/i18n";
import { useExecuFlow } from "./use-execuflow";
import type { TSessionType } from "./use-execuflow";

const FOCUS_DURATIONS: Record<TSessionType, number> = {
  micro: 5 * 60, // 5 min
  short: 15 * 60, // 15 min
  flow: 25 * 60, // 25 min
  deep: 50 * 60, // 50 min
};

const SESSION_LABELS: Record<TSessionType, string> = {
  micro: "5 minutes",
  short: "15 minutes",
  flow: "25 minutes",
  deep: "50 minutes",
};

type TFocusState = "idle" | "working" | "break" | "paused";

export const ExecuFlowFocusWidget = observer(function ExecuFlowFocusWidget(props: THomeWidgetProps) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const timerAnnouncerRef = useRef<HTMLDivElement>(null);
  const lastAnnouncedMinute = useRef<number>(-1);

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

  // Announce time remaining to screen readers at each minute boundary
  useEffect(() => {
    if (focusState !== "working") return;
    const currentMinute = Math.floor(secondsLeft / 60);
    if (currentMinute !== lastAnnouncedMinute.current && timerAnnouncerRef.current) {
      lastAnnouncedMinute.current = currentMinute;
      timerAnnouncerRef.current.textContent =
        currentMinute > 0
          ? `${currentMinute} minute${currentMinute !== 1 ? "s" : ""} remaining`
          : "Less than 1 minute remaining";
    }
  }, [secondsLeft, focusState]);

  const formatTime = useCallback((secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }, []);

  const handleStart = (duration: TSessionType) => startSession(duration);
  const handlePause = useCallback(() => pauseSession(), [pauseSession]);
  const handleResume = useCallback(() => resumeSession(), [resumeSession]);
  const handleReset = useCallback(() => endSession(), [endSession]);

  // Keyboard handler for play/pause with Space key on the timer region
  const handleTimerKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (focusState === "working") handlePause();
        else if (focusState === "paused") handleResume();
      }
    },
    [focusState, handlePause, handleResume]
  );

  const progress = activeSession ? 1 - activeSession.secondsLeft / (activeSession.plannedMinutes * 60) : 0;

  const sessionTypeLabel =
    selectedDuration === "micro"
      ? t("execuflow.focus_timer.micro_focus")
      : selectedDuration === "short"
        ? t("execuflow.focus_timer.short_session")
        : selectedDuration === "flow"
          ? t("execuflow.focus_timer.flow_session")
          : t("execuflow.focus_timer.deep_work");

  return (
    <section aria-label={t("execuflow.focus_timer.title")} className="rounded-lg border border-subtle bg-surface-1 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" aria-hidden="true" />
          <h3 className="text-14 font-medium text-primary">{t("execuflow.focus_timer.title")}</h3>
        </div>
        <span className="text-12 text-tertiary">
          {completedToday === 1
            ? t("execuflow.focus_timer.sessions_today", { count: completedToday })
            : t("execuflow.focus_timer.sessions_today_plural", { count: completedToday })}
        </span>
      </div>

      {/* Timer display */}
      <div className="flex flex-col items-center gap-4">
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- timer region supports keyboard pause/resume */}
        <div
          className="relative w-32 h-32 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500 rounded-full"
          role="timer"
          aria-label={
            focusState === "idle"
              ? `Focus timer: ${formatTime(secondsLeft)}`
              : focusState === "working"
                ? `${sessionTypeLabel}: ${formatTime(secondsLeft)} remaining`
                : focusState === "paused"
                  ? `${sessionTypeLabel}: ${formatTime(secondsLeft)} remaining, paused`
                  : "Session complete"
          }
          tabIndex={focusState === "working" || focusState === "paused" ? 0 : -1}
          onKeyDown={handleTimerKeyDown}
        >
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100" aria-hidden="true">
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
              className="text-amber-500 transition-all duration-1000 motion-reduce:transition-none"
              strokeWidth="6"
              strokeDasharray={`${progress * 283} 283`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
            <span className="text-24 font-mono font-semibold text-primary">{formatTime(secondsLeft)}</span>
          </div>
        </div>

        {/* Screen reader live announcements for timer */}
        <div ref={timerAnnouncerRef} role="status" aria-live="polite" aria-atomic="true" className="sr-only" />

        {/* Duration selector (only when idle) */}
        {focusState === "idle" && (
          <div className="flex gap-2" role="group" aria-label="Select focus duration">
            {(Object.keys(FOCUS_DURATIONS) as TSessionType[]).map((key) => (
              <button
                key={key}
                onClick={() => handleStart(key)}
                aria-label={`Start ${SESSION_LABELS[key]} ${key} focus session`}
                className="min-w-[44px] min-h-[44px] px-3 py-2 rounded-full text-12 font-medium transition-colors bg-surface-3 text-secondary hover:text-primary hover:bg-amber-500/15 hover:text-amber-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
              >
                {key === "micro" ? "5m" : key === "short" ? "15m" : key === "flow" ? "25m" : "50m"}
              </button>
            ))}
          </div>
        )}

        {/* Active session indicator */}
        {focusState !== "idle" && (
          <div className="text-12 text-tertiary" aria-live="polite">
            {sessionTypeLabel}
          </div>
        )}

        {/* Controls */}
        <div className="flex gap-2" role="group" aria-label="Timer controls">
          {focusState === "working" && (
            <button
              onClick={handlePause}
              aria-label={t("execuflow.focus_timer.pause")}
              className="flex items-center gap-1.5 min-h-[44px] px-4 py-2 rounded-md bg-surface-3 text-secondary text-13 font-medium hover:text-primary transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
            >
              <Pause className="h-3.5 w-3.5" aria-hidden="true" /> {t("execuflow.focus_timer.pause")}
            </button>
          )}
          {focusState === "paused" && (
            <>
              <button
                onClick={handleResume}
                aria-label={t("execuflow.focus_timer.resume")}
                className="flex items-center gap-1.5 min-h-[44px] px-4 py-2 rounded-md bg-amber-500 text-white text-13 font-medium hover:bg-amber-600 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" /> {t("execuflow.focus_timer.resume")}
              </button>
              <button
                onClick={handleReset}
                aria-label={t("execuflow.focus_timer.reset")}
                className="flex items-center gap-1.5 min-h-[44px] px-4 py-2 rounded-md bg-surface-3 text-secondary text-13 font-medium hover:text-primary transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> {t("execuflow.focus_timer.reset")}
              </button>
            </>
          )}
          {focusState === "break" && (
            <button
              onClick={handleReset}
              aria-label={t("execuflow.focus_timer.new_session")}
              className="flex items-center gap-1.5 min-h-[44px] px-4 py-2 rounded-md bg-green-500 text-white text-13 font-medium hover:bg-green-600 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-300"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> {t("execuflow.focus_timer.new_session")}
            </button>
          )}
        </div>

        {focusState === "break" && (
          <p
            className="text-13 text-green-500 font-medium motion-safe:animate-pulse"
            role="status"
            aria-live="assertive"
          >
            {t("execuflow.focus_timer.session_complete")}
          </p>
        )}
      </div>
    </section>
  );
});
