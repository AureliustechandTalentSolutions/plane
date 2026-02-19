// DragonBubble.tsx — Speech bubble that pops above the avatar.

import React from "react";
import styles from "./dragon-companion.module.css";

interface DragonBubbleProps {
  message: string;
  visible: boolean;
}

export const DragonBubble: React.FC<DragonBubbleProps> = ({ message, visible }) => {
  if (!visible) return null;

  return (
    <div className={styles.bubble} role="status" aria-live="polite">
      <span className={styles.bubbleText}>{message}</span>
      <div className={styles.bubbleTail} />
    </div>
  );
};

export default DragonBubble;
