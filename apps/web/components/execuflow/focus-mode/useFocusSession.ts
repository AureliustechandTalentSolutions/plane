// useFocusSession.ts — Hook for starting, ending, and tracking focus sessions.
// All values from the ExecuFlowService API.

import { useState, useCallback, useRef, useEffect } from "react";
import { ExecuFlowService } from "@plane/services";
import type { IFocusSession } from "@plane/services";

const API_BASE_URL = "/api";
const service = new ExecuFlowService(API_BASE_URL);

export interface FocusState {
  session: IFocusSession | null;
  isActive: boolean;
  secondsElapsed: number;
  interruptQueue: unknown[];
  loading: boolean;
  error: string | null;
}

export function useFocusSession(workspaceSlug: string, projectId: string) {
  const [state, setState] = useState<FocusState>({
    session: null,
    isActive: false,
    secondsElapsed: 0,
    interruptQueue: [],
    loading: false,
    error: null,
  });

  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start a new session
  const start = useCallback(
    async (data: {
      session_type: string;
      planned_duration_minutes: number;
      mood_before?: number;
      body_double_enabled?: boolean;
    }) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const session = await service.createFocusSession(workspaceSlug, projectId, data as Partial<IFocusSession>);
        setState({
          session,
          isActive: true,
          secondsElapsed: 0,
          interruptQueue: [],
          loading: false,
          error: null,
        });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: String(err),
        }));
      }
    },
    [workspaceSlug, projectId]
  );

  // End current session
  const end = useCallback(
    async (moodAfter?: number) => {
      if (!state.session) return;
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const updated = await service.updateFocusSession(workspaceSlug, projectId, state.session.id, {
          ended_at: new Date().toISOString(),
          mood_after: moodAfter,
        });
        setState({
          session: updated,
          isActive: false,
          secondsElapsed: 0,
          interruptQueue: [],
          loading: false,
          error: null,
        });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: String(err),
        }));
      }
    },
    [workspaceSlug, projectId, state.session]
  );

  // Queue an interruption
  const addInterrupt = useCallback((item: { type: string; note: string }) => {
    setState((prev) => ({
      ...prev,
      interruptQueue: [...prev.interruptQueue, { ...item, at: Date.now() }],
    }));
  }, []);

  // Tick every second while active
  useEffect(() => {
    if (state.isActive) {
      tickerRef.current = setInterval(() => {
        setState((prev) => ({
          ...prev,
          secondsElapsed: prev.secondsElapsed + 1,
        }));
      }, 1_000);
    }

    return () => {
      if (tickerRef.current) clearInterval(tickerRef.current);
    };
  }, [state.isActive]);

  return { ...state, start, end, addInterrupt };
}
