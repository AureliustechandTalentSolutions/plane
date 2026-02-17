// DragonSettings.tsx — Configuration panel for the dragon companion.
// Preferences stored via API (not local-only).

import React, { useState } from "react";
import styles from "./dragon-companion.module.css";

interface DragonSettingsProps {
  onSave: (prefs: DragonPrefs) => void;
  initialPrefs?: DragonPrefs;
}

export interface DragonPrefs {
  enableBubbles: boolean;
  enableAnimations: boolean;
  avatarSize: "small" | "medium" | "large";
}

const SIZE_OPTIONS: Array<{ value: DragonPrefs["avatarSize"]; label: string }> = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

export const DragonSettings: React.FC<DragonSettingsProps> = ({ onSave, initialPrefs }) => {
  const [prefs, setPrefs] = useState<DragonPrefs>(
    initialPrefs ?? {
      enableBubbles: true,
      enableAnimations: true,
      avatarSize: "medium",
    }
  );

  return (
    <div className={styles.settings}>
      <h4 className={styles.settingsTitle}>Dragon Companion Settings</h4>

      <label className={styles.settingsRow}>
        <span>Speech bubbles</span>
        <input
          type="checkbox"
          checked={prefs.enableBubbles}
          onChange={(e) => setPrefs((p) => ({ ...p, enableBubbles: e.target.checked }))}
        />
      </label>

      <label className={styles.settingsRow}>
        <span>Animations</span>
        <input
          type="checkbox"
          checked={prefs.enableAnimations}
          onChange={(e) => setPrefs((p) => ({ ...p, enableAnimations: e.target.checked }))}
        />
      </label>

      <label className={styles.settingsRow}>
        <span>Avatar size</span>
        <select
          value={prefs.avatarSize}
          onChange={(e) =>
            setPrefs((p) => ({
              ...p,
              avatarSize: e.target.value as DragonPrefs["avatarSize"],
            }))
          }
        >
          {SIZE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>

      <button className={styles.saveBtn} onClick={() => onSave(prefs)}>
        Save
      </button>
    </div>
  );
};

export default DragonSettings;
