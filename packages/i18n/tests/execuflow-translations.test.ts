/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, it, expect } from "vitest";
import enTranslations from "../src/locales/en/translations";

describe("ExecuFlow Translations", () => {
  describe("Focus Timer Translations", () => {
    it("should have execuflow.focus_timer namespace", () => {
      expect(enTranslations).toHaveProperty("execuflow");
      expect(enTranslations.execuflow).toHaveProperty("focus_timer");
    });

    it("should have title translation", () => {
      expect(enTranslations.execuflow.focus_timer.title).toBe("Focus Timer");
    });

    it("should have sessions_today translation with singular form", () => {
      expect(enTranslations.execuflow.focus_timer.sessions_today).toBe("{{count}} session today");
    });

    it("should have sessions_today_plural translation", () => {
      expect(enTranslations.execuflow.focus_timer.sessions_today_plural).toBe("{{count}} sessions today");
    });

    it("should have session type labels", () => {
      expect(enTranslations.execuflow.focus_timer.micro_focus).toBe("Micro focus");
      expect(enTranslations.execuflow.focus_timer.short_session).toBe("Short session");
      expect(enTranslations.execuflow.focus_timer.flow_session).toBe("Flow session");
      expect(enTranslations.execuflow.focus_timer.deep_work).toBe("Deep work");
    });

    it("should have control button labels", () => {
      expect(enTranslations.execuflow.focus_timer.pause).toBe("Pause");
      expect(enTranslations.execuflow.focus_timer.resume).toBe("Resume");
      expect(enTranslations.execuflow.focus_timer.reset).toBe("Reset");
      expect(enTranslations.execuflow.focus_timer.new_session).toBe("New Session");
    });

    it("should have completion message", () => {
      expect(enTranslations.execuflow.focus_timer.session_complete).toBe(
        "Focus session complete! Take a break."
      );
    });
  });

  describe("Energy Tracker Translations", () => {
    it("should have execuflow.energy_tracker namespace", () => {
      expect(enTranslations).toHaveProperty("execuflow");
      expect(enTranslations.execuflow).toHaveProperty("energy_tracker");
    });

    it("should have title translation", () => {
      expect(enTranslations.execuflow.energy_tracker.title).toBe("Energy Tracker");
    });

    it("should have energy level labels", () => {
      expect(enTranslations.execuflow.energy_tracker.depleted).toBe("Depleted");
      expect(enTranslations.execuflow.energy_tracker.low_energy).toBe("Low Energy");
      expect(enTranslations.execuflow.energy_tracker.steady).toBe("Steady");
      expect(enTranslations.execuflow.energy_tracker.powered_up).toBe("Powered Up");
      expect(enTranslations.execuflow.energy_tracker.dragon_mode).toBe("Dragon Mode 🐉");
    });

    it("should have AI suggestions label", () => {
      expect(enTranslations.execuflow.energy_tracker.ai_suggestions).toBe("AI Suggestions");
    });

    it("should have AI tips for each energy level", () => {
      const tips = enTranslations.execuflow.energy_tracker.tips;

      expect(tips.depleted).toBeInstanceOf(Array);
      expect(tips.depleted).toHaveLength(3);
      expect(tips.depleted[0]).toBe("Take a 10-minute walk outside");

      expect(tips.low).toBeInstanceOf(Array);
      expect(tips.low).toHaveLength(3);
      expect(tips.low[0]).toBe("Try a 5-minute micro-focus session");

      expect(tips.medium).toBeInstanceOf(Array);
      expect(tips.medium).toHaveLength(3);
      expect(tips.medium[0]).toBe("Good time for code review or writing");

      expect(tips.high).toBeInstanceOf(Array);
      expect(tips.high).toHaveLength(3);
      expect(tips.high[0]).toBe("Perfect for deep feature work");

      expect(tips.dragon).toBeInstanceOf(Array);
      expect(tips.dragon).toHaveLength(3);
      expect(tips.dragon[0]).toBe("🔥 You're unstoppable — go for the hardest task");
    });
  });
});
