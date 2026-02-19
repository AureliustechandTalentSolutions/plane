// DragonAvatar.tsx — Animated companion avatar reflecting current mood.
// Uses CSS-only animations — no hardcoded asset URLs.

import React from "react";
import { useTranslation } from "@plane/i18n";
import type { DragonMood } from "./useDragonState";
import styles from "./dragon-companion.module.css";

interface DragonAvatarProps {
  mood: DragonMood;
  size?: number;
}

const MOOD_EMOJI: Record<DragonMood, string> = {
  idle: "🐉",
  happy: "😊",
  focused: "🔥",
  celebrating: "🎉",
  resting: "😴",
};

export const DragonAvatar: React.FC<DragonAvatarProps> = ({ mood, size = 56 }) => {
  const { t } = useTranslation();

  return (
    <div
      className={`${styles.avatar} ${styles[mood]}`}
      style={{ "--avatar-size": `${size}px` } as React.CSSProperties}
      role="img"
      aria-label={t("execuflow.dragon_companion.avatar_label", { mood })}
    >
      <span className={styles.face}>{MOOD_EMOJI[mood]}</span>
    </div>
  );
};

export default DragonAvatar;
