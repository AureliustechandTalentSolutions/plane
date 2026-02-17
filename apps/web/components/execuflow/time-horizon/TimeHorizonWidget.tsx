// TimeHorizonWidget.tsx — Self-contained widget that composes hook + bar.
// Drop this into any project sidebar / dashboard.

import React from "react";
import { TimeHorizonBar } from "./TimeHorizonBar";
import { useTimeHorizon } from "./useTimeHorizon";

interface TimeHorizonWidgetProps {
  workspaceSlug: string;
  projectId: string;
}

export const TimeHorizonWidget: React.FC<TimeHorizonWidgetProps> = ({ workspaceSlug, projectId }) => {
  const { blocks, totalMinutes, elapsedMinutes, percentComplete, activeBlockId } = useTimeHorizon(
    workspaceSlug,
    projectId
  );

  return (
    <section aria-label="Time Horizon">
      <TimeHorizonBar
        blocks={blocks}
        totalMinutes={totalMinutes}
        elapsedMinutes={elapsedMinutes}
        percentComplete={percentComplete}
        activeBlockId={activeBlockId}
      />
    </section>
  );
};

export default TimeHorizonWidget;
