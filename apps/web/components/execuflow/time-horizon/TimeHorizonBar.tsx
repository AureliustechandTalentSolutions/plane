// TimeHorizonBar.tsx — Segmented progress bar showing focus-session time blocks.
// All colours & labels driven by the hook which reads API data.

import React from "react";
import type { TimeBlock } from "./useTimeHorizon";
import styles from "./time-horizon.module.css";

interface TimeHorizonBarProps {
  blocks: TimeBlock[];
  totalMinutes: number;
  elapsedMinutes: number;
  percentComplete: number;
  activeBlockId: string | null;
}

export const TimeHorizonBar: React.FC<TimeHorizonBarProps> = ({
  blocks,
  totalMinutes,
  elapsedMinutes,
  percentComplete,
  activeBlockId,
}) => {
  if (blocks.length === 0) {
    return (
      <div className={styles.emptyBar}>
        <span className={styles.emptyLabel}>No active session</span>
      </div>
    );
  }

  const remaining = Math.max(totalMinutes - elapsedMinutes, 0);

  return (
    <div className={styles.wrapper}>
      {/* Segmented bar */}
      <div
        className={styles.bar}
        role="progressbar"
        aria-valuenow={percentComplete}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {blocks.map((block) => {
          const widthPercent = totalMinutes ? (block.durationMinutes / totalMinutes) * 100 : 0;
          const isActive = block.id === activeBlockId;

          return (
            <div
              key={block.id}
              className={`${styles.segment} ${isActive ? styles.active : ""}`}
              style={{
                width: `${widthPercent}%`,
                backgroundColor: block.color,
              }}
              title={`${block.label} — ${block.durationMinutes} min`}
            >
              <span className={styles.segmentLabel}>{block.label}</span>
            </div>
          );
        })}

        {/* Elapsed overlay */}
        <div className={styles.elapsed} style={{ width: `${percentComplete}%` }} />
      </div>

      {/* Meta row */}
      <div className={styles.meta}>
        <span className={styles.timeLabel}>
          {elapsedMinutes} / {totalMinutes} min
        </span>
        <span className={styles.remaining}>{remaining} min remaining</span>
      </div>
    </div>
  );
};

export default TimeHorizonBar;
