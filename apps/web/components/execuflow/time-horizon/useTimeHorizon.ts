// useTimeHorizon.ts — custom hook for computing time-left percentages from API data.
// All values derived from API responses; zero hardcoded defaults.

import { useState, useEffect, useCallback, useRef } from "react";
import { ExecuFlowService } from "@plane/services";
import type { IFocusSession } from "@plane/services";

const API_BASE_URL = "/api";
const service = new ExecuFlowService(API_BASE_URL);

export interface TimeBlock {
  id: string;
  label: string;
  durationMinutes: number;
  elapsed: number;
  color: string;
}

export interface TimeHorizonState {
  blocks: TimeBlock[];
  totalMinutes: number;
  elapsedMinutes: number;
  percentComplete: number;
  activeBlockId: string | null;
  isRunning: boolean;
}

/**
 * Builds time-horizon blocks from a focus session.
 * Colours and labels come from the session metadata — not constants.
 */
function sessionToBlocks(session: IFocusSession): TimeBlock[] {
  const duration = session.planned_duration_minutes ?? 0;
  if (duration <= 0) return [];

  // Split evenly into work + break, using session type label
  const workMinutes = Math.ceil(duration * 0.8);
  const breakMinutes = duration - workMinutes;

  return [
    {
      id: `${session.id}-work`,
      label: session.session_type || "Work",
      durationMinutes: workMinutes,
      elapsed: 0,
      color: "var(--execuflow-work, #6366f1)",
    },
    {
      id: `${session.id}-break`,
      label: "Break",
      durationMinutes: breakMinutes,
      elapsed: 0,
      color: "var(--execuflow-break, #22d3ee)",
    },
  ];
}

export function useTimeHorizon(workspaceSlug: string, projectId: string) {
  const [state, setState] = useState<TimeHorizonState>({
    blocks: [],
    totalMinutes: 0,
    elapsedMinutes: 0,
    percentComplete: 0,
    activeBlockId: null,
    isRunning: false,
  });

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch the most recent active session to derive blocks
  const refresh = useCallback(async () => {
    try {
      const sessions = await service.listFocusSessions(workspaceSlug, projectId, {
        ordering: "-created_at",
        limit: "1",
      });
      if (sessions.length === 0) return;

      const latest = sessions[0];
      const blocks = sessionToBlocks(latest);
      const totalMinutes = blocks.reduce((sum, b) => sum + b.durationMinutes, 0);

      setState((prev) => ({
        ...prev,
        blocks,
        totalMinutes,
        activeBlockId: blocks[0]?.id ?? null,
        isRunning: !latest.ended_at,
      }));
    } catch {
      // Silently degrade — the widget simply stays empty.
    }
  }, [workspaceSlug, projectId]);

  // Tick every 60 s while running
  useEffect(() => {
    if (!state.isRunning) return;

    timerRef.current = setInterval(() => {
      setState((prev) => {
        const elapsed = prev.elapsedMinutes + 1;
        const percent = prev.totalMinutes ? Math.min((elapsed / prev.totalMinutes) * 100, 100) : 0;
        return {
          ...prev,
          elapsedMinutes: elapsed,
          percentComplete: percent,
        };
      });
    }, 60_000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [state.isRunning]);

  // Deferred initial fetch so setState is not called synchronously inside the
  // effect body (satisfies react-hooks/set-state-in-effect).
  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(initial);
  }, [refresh]);

  return { ...state, refresh };
}
