// FocusModeToggle.tsx — The on/off switch for focus sessions.
// Renders as a floating pill with session timer when active.

import React, { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { useFocusSession } from "./useFocusSession";
import styles from "./focus-mode.module.css";

interface FocusModeToggleProps {
  workspaceSlug: string;
  projectId: string;
}

function formatTime(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export const FocusModeToggle: React.FC<FocusModeToggleProps> = ({ workspaceSlug, projectId }) => {
  const { t } = useTranslation();
  const { isActive, secondsElapsed, loading, start, end, addInterrupt } = useFocusSession(workspaceSlug, projectId);

  const [interruptNote, setInterruptNote] = useState("");

  const handleToggle = async () => {
    if (isActive) {
      await end();
    } else {
      await start({
        session_type: "deep_work",
        planned_duration_minutes: 25,
      });
    }
  };

  const handleInterrupt = () => {
    if (!interruptNote.trim()) return;
    addInterrupt({ type: "manual", note: interruptNote });
    setInterruptNote("");
  };

  return (
    <div className={`${styles.pill} ${isActive ? styles.active : ""}`}>
      <button
        className={styles.toggle}
        onClick={handleToggle}
        disabled={loading}
        aria-pressed={isActive}
        aria-label={isActive ? t("execuflow.focus_mode.end_session") : t("execuflow.focus_mode.start_session")}
      >
        <span className={styles.icon}>{isActive ? "⏸" : "▶"}</span>
        <span className={styles.label}>{isActive ? t("execuflow.focus_mode.focus_on") : t("execuflow.focus_mode.focus_off")}</span>
      </button>

      {isActive && (
        <>
          <span className={styles.timer}>{formatTime(secondsElapsed)}</span>

          <div className={styles.interruptBar}>
            <input
              className={styles.interruptInput}
              type="text"
              placeholder={t("execuflow.focus_mode.quick_note_placeholder")}
              value={interruptNote}
              onChange={(e) => setInterruptNote(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleInterrupt()}
            />
            <button className={styles.interruptBtn} onClick={handleInterrupt} aria-label={t("execuflow.interrupt_queue.queued_items", { count: 1 })}>
              +
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default FocusModeToggle;
