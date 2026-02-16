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
    <div className="rounded-lg border border-subtle bg-surface-1 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame className={`h-4 w-4 ${ENERGY_COLORS[energy]}`} />
          <h3 className="text-14 font-medium text-primary">{t("execuflow.energy_tracker.title")}</h3>
        </div>
        <span className={`text-12 font-medium ${ENERGY_COLORS[energy]}`}>{energyLabels[energy]}</span>
      </div>

      {/* Energy bar */}
      <div className="mb-4">
        <div className="h-2 rounded-full bg-surface-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
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

      {/* Energy selector */}
      <div className="flex gap-1.5 mb-4">
        {(Object.keys(ENERGY_COLORS) as TEnergyLevel[]).map((level) => (
          <button
            key={level}
            onClick={() => handleEnergySelect(level)}
            className={`flex-1 py-1.5 rounded text-11 font-medium transition-colors ${
              energy === level
                ? `${ENERGY_COLORS[level]} bg-surface-3 border border-subtle`
                : "text-tertiary hover:text-secondary hover:bg-surface-2"
            }`}
          >
            {level === "depleted"
              ? "😴"
              : level === "low"
                ? "🔋"
                : level === "medium"
                  ? "⚡"
                  : level === "high"
                    ? "🚀"
                    : "🐉"}
          </button>
        ))}
      </div>

      {/* AI Tips */}
      {showTips && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 mb-2">
            <Brain className="h-3.5 w-3.5 text-purple-400" />
            <span className="text-12 font-medium text-secondary">{t("execuflow.energy_tracker.ai_suggestions")}</span>
            <Sparkles className="h-3 w-3 text-purple-400" />
          </div>
          {tips[energy].map((tip, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-surface-2 hover:bg-surface-3 cursor-pointer transition-colors group"
            >
              <ChevronRight className="h-3.5 w-3.5 text-tertiary group-hover:text-primary transition-colors" />
              <span className="text-12 text-secondary group-hover:text-primary transition-colors">{tip}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
