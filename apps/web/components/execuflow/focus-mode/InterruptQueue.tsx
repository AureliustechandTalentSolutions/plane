// InterruptQueue.tsx — Standalone queue list for sidebar usage.

import React from "react";
import { useTranslation } from "@plane/i18n";
import styles from "./focus-mode.module.css";

export interface InterruptItem {
  type: string;
  note: string;
  at: number;
}

interface InterruptQueueProps {
  items: InterruptItem[];
}

export const InterruptQueue: React.FC<InterruptQueueProps> = ({ items }) => {
  const { t } = useTranslation();

  if (items.length === 0) {
    return (
      <div className={styles.emptyQueue}>
        <span>{t("execuflow.interrupt_queue.empty")}</span>
      </div>
    );
  }

  return (
    <ul className={styles.queueList}>
      {items.map((item, i) => (
        <li key={i} className={styles.queueItem}>
          <span className={styles.queueBadge}>{item.type}</span>
          <span className={styles.queueNote}>{item.note}</span>
        </li>
      ))}
    </ul>
  );
};

export default InterruptQueue;
