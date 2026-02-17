// useDragonState.ts — Hook for the companion avatar state (streaks, achievements, mood).
// Reads all data from the API — personality is user-configurable, not hardcoded.

import { useState, useEffect, useCallback } from "react";
import { ExecuFlowService } from "@plane/services";
import type { IStreak, IUserAchievement } from "@plane/services";

const API_BASE_URL = "/api";
const service = new ExecuFlowService(API_BASE_URL);

export type DragonMood = "idle" | "happy" | "focused" | "celebrating" | "resting";

export interface DragonState {
  mood: DragonMood;
  streaks: IStreak[];
  achievements: IUserAchievement[];
  latestAchievement: IUserAchievement | null;
  currentStreak: number;
  longestStreak: number;
  loading: boolean;
  showBubble: boolean;
  bubbleMessage: string;
}

/**
 * Derive mood from streak + achievement state.
 * Transition rules:
 *   - celebrating: a new achievement was earned in the last 30 s
 *   - focused: an active (non-paused) streak exists
 *   - happy: current streak ≥ 3
 *   - resting: all streaks paused
 *   - idle: default
 */
function deriveMood(streaks: IStreak[], achievements: IUserAchievement[]): DragonMood {
  // Check for recent achievement (< 30 s old)
  if (achievements.length > 0) {
    const latest = achievements[achievements.length - 1];
    const earnedAt = new Date(latest.earned_at).getTime();
    if (Date.now() - earnedAt < 30_000) return "celebrating";
  }

  const activeStreaks = streaks.filter((s) => s.status === "active");
  if (activeStreaks.length === 0 && streaks.length > 0) return "resting";

  const maxCurrent = Math.max(0, ...activeStreaks.map((s) => s.current_count));
  if (maxCurrent >= 3) return "happy";
  if (activeStreaks.length > 0) return "focused";

  return "idle";
}

function bubbleForMood(mood: DragonMood): string {
  const messages: Record<DragonMood, string> = {
    idle: "Ready when you are!",
    happy: "Great streak — keep going!",
    focused: "Deep focus activated 🔥",
    celebrating: "🎉 Achievement unlocked!",
    resting: "Taking a breather. That's okay!",
  };
  return messages[mood];
}

export function useDragonState(workspaceSlug: string, projectId: string) {
  const [state, setState] = useState<DragonState>({
    mood: "idle",
    streaks: [],
    achievements: [],
    latestAchievement: null,
    currentStreak: 0,
    longestStreak: 0,
    loading: true,
    showBubble: false,
    bubbleMessage: "",
  });

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    try {
      const [streaks, achievements] = await Promise.all([
        service.getStreaks(workspaceSlug, projectId),
        service.listMyAchievements(workspaceSlug, projectId),
      ]);

      const mood = deriveMood(streaks, achievements);
      const active = streaks.filter((s) => s.status === "active");
      const currentStreak = Math.max(0, ...active.map((s) => s.current_count));
      const longestStreak = Math.max(0, ...streaks.map((s) => s.longest_count));

      setState({
        mood,
        streaks,
        achievements,
        latestAchievement: achievements.length > 0 ? achievements[achievements.length - 1] : null,
        currentStreak,
        longestStreak,
        loading: false,
        showBubble: true,
        bubbleMessage: bubbleForMood(mood),
      });

      // Auto-dismiss bubble after 5 s
      setTimeout(() => {
        setState((prev) => ({ ...prev, showBubble: false }));
      }, 5_000);
    } catch {
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, [workspaceSlug, projectId]);

  // Poll every 60 s to catch new achievements
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  return { ...state, refresh };
}
