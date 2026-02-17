// FocusModeOverlay.tsx — Full-screen dimmer + interrupt queue display.
// Appears when focus mode is active, reduces visual clutter.

import React from "react";
import { useTranslation } from "@plane/i18n";
import styles from "./focus-mode.module.css";

interface FocusModeOverlayProps {
  isActive: boolean;
  interruptQueue: Array<{ type: string; note: string; at: number }>;
  onDismiss: () => void;
}

export const FocusModeOverlay: React.FC<FocusModeOverlayProps> = ({ isActive, interruptQueue, onDismiss }) => {
  const { t } = useTranslation();

  if (!isActive) return null;

  return (
    <div className={styles.overlay} role="dialog" aria-label={t("execuflow.focus_mode.active_title")}>
      <div className={styles.overlayPanel}>
        <h3 className={styles.overlayTitle}>🔒 {t("execuflow.focus_mode.title")}</h3>
        <p className={styles.overlayHint}>{t("execuflow.focus_mode.hint")}</p>

        {interruptQueue.length > 0 && (
          <ul className={styles.queueList}>
            {interruptQueue.map((item, i) => (
              <li key={i} className={styles.queueItem}>
                <span className={styles.queueNote}>{item.note}</span>
                <span className={styles.queueTime}>
                  {new Date(item.at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </li>
            ))}
          </ul>
        )}

        <button className={styles.dismissBtn} onClick={onDismiss}>
          {t("execuflow.focus_mode.end_focus")}
        </button>
      </div>
    </div>
  );
};

export default FocusModeOverlay;
