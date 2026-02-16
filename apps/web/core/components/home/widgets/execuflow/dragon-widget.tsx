/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

"use client";

import { useState, useCallback, useMemo } from "react";
import { observer } from "mobx-react";
import { Flame, ChevronRight, Brain, Sparkles } from "lucide-react";
// plane imports
import type { THomeWidgetProps } from "@plane/types";
import { useTranslation } from "@plane/i18n";

type TEnergyLevel = "depleted" | "low" | "medium" | "high" | "dragon";

const ENERGY_COLORS: Record<TEnergyLevel, string> = {
  depleted: "text-red-400",
  low: "text-orange-400",
  medium: "text-yellow-400",
  high: "text-green-400",
  dragon: "text-amber-500",
};

const ENERGY_LEVELS: TEnergyLevel[] = ["depleted", "low", "medium", "high", "dragon"];

export const ExecuFlowDragonWidget = observer(function ExecuFlowDragonWidget(_props: THomeWidgetProps) {
  const { t } = useTranslation();
  const [energy, setEnergy] = useState<TEnergyLevel>("medium");
  const [showTips, setShowTips] = useState(false);

  const energyPercent: Record<TEnergyLevel, number> = {
    depleted: 10,
    low: 30,
    medium: 55,
    high: 80,
    dragon: 100,
  };

  const energyLabels: Record<TEnergyLevel, string> = useMemo(
    () => ({
      depleted: t("execuflow.energy_tracker.depleted"),
      low: t("execuflow.energy_tracker.low_energy"),
      medium: t("execuflow.energy_tracker.steady"),
      high: t("execuflow.energy_tracker.powered_up"),
      dragon: t("execuflow.energy_tracker.dragon_mode"),
    }),
    [t]
  );

  const tips: Record<TEnergyLevel, string[]> = useMemo(
    () => ({
      depleted: t("execuflow.energy_tracker.tips.depleted") as unknown as string[],
      low: t("execuflow.energy_tracker.tips.low") as unknown as string[],
      medium: t("execuflow.energy_tracker.tips.medium") as unknown as string[],
      high: t("execuflow.energy_tracker.tips.high") as unknown as string[],
      dragon: t("execuflow.energy_tracker.tips.dragon") as unknown as string[],
    }),
    [t]
  );

  const handleEnergySelect = useCallback((level: TEnergyLevel) => {
    setEnergy(level);
    setShowTips(true);
  }, []);

  return (
    <section
      aria-label={t("execuflow.energy_tracker.title")}
      className="rounded-lg border border-subtle bg-surface-1 p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame className={`h-4 w-4 ${ENERGY_COLORS[energy]}`} aria-hidden="true" />
          <h3 className="text-14 font-medium text-primary">{t("execuflow.energy_tracker.title")}</h3>
        </div>
        <span className={`text-12 font-medium ${ENERGY_COLORS[energy]}`} aria-live="polite">
          {energyLabels[energy]}
        </span>
      </div>

      {/* Energy bar */}
      <div className="mb-4">
        <div
          role="progressbar"
          aria-label={`Energy level: ${energyLabels[energy]}`}
          aria-valuenow={energyPercent[energy]}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuetext={`${energyLabels[energy]}, ${energyPercent[energy]} percent`}
          className="h-2 rounded-full bg-surface-3 overflow-hidden"
        >
          <div
            className={`h-full rounded-full transition-all duration-500 motion-reduce:transition-none ${
              energy === "dragon"
                ? "bg-gradient-to-r from-amber-500 via-orange-500 to-red-500"
                : energy === "high"
                  ? "bg-green-400"
                  : energy === "medium"
                    ? "bg-yellow-400"
                    : energy === "low"
                      ? "bg-orange-400"
                      : "bg-red-400"
            }`}
            style={{ width: `${energyPercent[energy]}%` }}
          />
        </div>
      </div>

      {/* Energy selector - button group with pressed state for mutually exclusive selection */}
      <div className="flex gap-1.5 mb-4" role="group" aria-label="Select your current energy level">
        {ENERGY_LEVELS.map((level) => (
          <button
            key={level}
            aria-pressed={energy === level ? "true" : "false"}
            aria-label={energyLabels[level]}
            onClick={() => handleEnergySelect(level)}
            className={`flex-1 min-h-[44px] py-2 rounded text-11 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500 ${
              energy === level
                ? `${ENERGY_COLORS[level]} bg-surface-3 border border-subtle`
                : "text-tertiary hover:text-secondary hover:bg-surface-2"
            }`}
          >
            <span aria-hidden="true">
              {level === "depleted"
                ? "\u{1F634}"
                : level === "low"
                  ? "\u{1F50B}"
                  : level === "medium"
                    ? "\u26A1"
                    : level === "high"
                      ? "\u{1F680}"
                      : "\u{1F409}"}
            </span>
          </button>
        ))}
      </div>

      {/* AI Tips */}
      {showTips && (
        <div className="space-y-2" role="region" aria-label="Energy-based suggestions">
          <div className="flex items-center gap-1.5 mb-2">
            <Brain className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />
            <span className="text-12 font-medium text-secondary">{t("execuflow.energy_tracker.ai_suggestions")}</span>
            <Sparkles className="h-3 w-3 text-purple-400" aria-hidden="true" />
          </div>
          <ul className="space-y-2" aria-label="Suggestions">
            {tips[energy].map((tip, i) => (
              <li key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-surface-2 transition-colors">
                <ChevronRight className="h-3.5 w-3.5 text-tertiary" aria-hidden="true" />
                <span className="text-12 text-secondary">{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
});
