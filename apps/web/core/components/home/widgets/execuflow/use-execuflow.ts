/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState, useCallback, useSyncExternalStore } from "react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// store hook (MobX)
import { useExecuFlow as useExecuFlowStore } from "@/hooks/store/use-execuflow";
// local utilities
import { toApiSessionType, WIDGET_PLANNED_DURATION_MAP } from "./session-type-mapper";

// Local storage keys
const STORAGE_KEYS = {
  ACTIVE_SESSION: "execuflow_active_session",
  COMPLETED_SESSIONS_TODAY: "execuflow_completed_today",
} as const;

// Session types
export type TSessionType = "micro" | "short" | "flow" | "deep";

const DURATION_MAP: Record<TSessionType, number> = {
  micro: 5,
  short: 15,
  flow: 25,
  deep: 50,
};

interface LocalSession {
  sessionType: TSessionType;
  plannedMinutes: number;
  startedAt: string;
  secondsLeft: number;
  isPaused: boolean;
}

interface StoredCompleted {
  count: number;
  date: string;
}

interface UseExecuFlowOptions {
  workspaceSlug: string;
}

interface UseExecuFlowReturn {
  activeSession: LocalSession | null;
  completedToday: number;
  startSession: (sessionType: TSessionType) => void;
  pauseSession: () => void;
  resumeSession: () => void;
  endSession: () => void;
  updateSecondsLeft: (seconds: number) => void;
}

// Helper to safely read from localStorage
function getStoredSession(): LocalSession | null {
  if (typeof window === "undefined") return null;
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.ACTIVE_SESSION);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as LocalSession;
    const sessionDate = new Date(parsed.startedAt).toDateString();
    const today = new Date().toDateString();
    if (sessionDate !== today) {
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_SESSION);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function getStoredCompletedCount(): number {
  if (typeof window === "undefined") return 0;
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.COMPLETED_SESSIONS_TODAY);
    if (!saved) return 0;
    const { count, date } = JSON.parse(saved) as StoredCompleted;
    if (date !== new Date().toDateString()) {
      localStorage.setItem(
        STORAGE_KEYS.COMPLETED_SESSIONS_TODAY,
        JSON.stringify({ count: 0, date: new Date().toDateString() })
      );
      return 0;
    }
    return count;
  } catch {
    return 0;
  }
}

// Subscribe to storage changes (for useSyncExternalStore)
function subscribeToStorage(callback: () => void): () => void {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

export function useExecuFlow(_options: UseExecuFlowOptions): UseExecuFlowReturn {
  // MobX store for API sync
  const execuFlowStore = useExecuFlowStore();

  // Use useSyncExternalStore for SSR-safe localStorage access
  const storedSession = useSyncExternalStore(subscribeToStorage, getStoredSession, () => null);
  const storedCompleted = useSyncExternalStore(subscribeToStorage, getStoredCompletedCount, () => 0);

  // Local state that syncs with storage
  const [activeSession, setActiveSession] = useState<LocalSession | null>(storedSession);
  const [completedToday, setCompletedToday] = useState(storedCompleted);

  // Persist active session to localStorage
  const persistSession = useCallback((session: LocalSession | null) => {
    if (session) {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_SESSION, JSON.stringify(session));
    } else {
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_SESSION);
    }
    setActiveSession(session);
  }, []);

  // Start a new session — persists locally first for offline-first continuity,
  // then fires the API sync in the background.
  const startSession = useCallback(
    (sessionType: TSessionType) => {
      const plannedMinutes = DURATION_MAP[sessionType];
      const now = new Date().toISOString();

      const localSession: LocalSession = {
        sessionType,
        plannedMinutes,
        startedAt: now,
        secondsLeft: plannedMinutes * 60,
        isPaused: false,
      };

      // 1. Persist locally immediately so the timer starts regardless of network.
      persistSession(localSession);

      // 2. Sync to API in background — failures are non-fatal.
      const apiSessionType = toApiSessionType(sessionType);
      const apiPlannedDuration = WIDGET_PLANNED_DURATION_MAP[sessionType];

      execuFlowStore
        .startFocusSession(apiSessionType)
        .then(() => {
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: "Focus session started",
            message: `${apiPlannedDuration}-minute ${apiSessionType.replace("_", " ")} session synced.`,
          });
        })
        .catch((err: unknown) => {
          const message = err instanceof Error ? err.message : "Session saved locally; will sync when online.";
          setToast({
            type: TOAST_TYPE.WARNING,
            title: "Couldn't sync to server",
            message,
          });
        });
    },
    [persistSession, execuFlowStore]
  );

  // Pause session
  const pauseSession = useCallback(() => {
    if (activeSession) {
      persistSession({ ...activeSession, isPaused: true });
    }
  }, [activeSession, persistSession]);

  // Resume session
  const resumeSession = useCallback(() => {
    if (activeSession) {
      persistSession({ ...activeSession, isPaused: false });
    }
  }, [activeSession, persistSession]);

  // End session — updates local state first, then syncs end to API.
  const endSession = useCallback(() => {
    if (!activeSession) return;

    const newCount = completedToday + 1;
    setCompletedToday(newCount);
    localStorage.setItem(
      STORAGE_KEYS.COMPLETED_SESSIONS_TODAY,
      JSON.stringify({ count: newCount, date: new Date().toDateString() })
    );

    // 1. Clear localStorage immediately so the timer resets without waiting on the network.
    persistSession(null);

    // 2. Sync session end to API in background — failures are non-fatal.
    execuFlowStore
      .endFocusSession()
      .then(() => {
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Session complete",
          message: `Great work! You've completed ${newCount} session${newCount !== 1 ? "s" : ""} today.`,
        });
      })
      .catch((err: unknown) => {
        // If there is no active API session (e.g. started offline), the error is expected.
        // We still show a completion toast so the user gets positive feedback.
        const isNoSessionError =
          err instanceof Error && (err.message.includes("No active session") || err.message.includes("404"));

        if (isNoSessionError) {
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: "Session complete",
            message: `Great work! You've completed ${newCount} session${newCount !== 1 ? "s" : ""} today.`,
          });
        } else {
          setToast({
            type: TOAST_TYPE.WARNING,
            title: "Session ended locally",
            message: "Couldn't sync completion to server. Your progress is saved locally.",
          });
        }
      });
  }, [activeSession, completedToday, persistSession, execuFlowStore]);

  // Update seconds left (called by timer)
  const updateSecondsLeft = useCallback(
    (seconds: number) => {
      if (activeSession) {
        persistSession({ ...activeSession, secondsLeft: seconds });
      }
    },
    [activeSession, persistSession]
  );

  return {
    activeSession,
    completedToday,
    startSession,
    pauseSession,
    resumeSession,
    endSession,
    updateSecondsLeft,
  };
}
