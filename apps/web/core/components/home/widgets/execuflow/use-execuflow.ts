/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState, useCallback, useSyncExternalStore } from "react";

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

  // Start a new session
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

      persistSession(localSession);
    },
    [persistSession]
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

  // End session
  const endSession = useCallback(() => {
    if (!activeSession) return;

    const newCount = completedToday + 1;
    setCompletedToday(newCount);
    localStorage.setItem(
      STORAGE_KEYS.COMPLETED_SESSIONS_TODAY,
      JSON.stringify({ count: newCount, date: new Date().toDateString() })
    );

    persistSession(null);
  }, [activeSession, completedToday, persistSession]);

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
