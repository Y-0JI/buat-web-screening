"use client";

import { useWorkspace } from "@/lib/workspace-context";
import { DashboardView } from "./dashboard-view";
import { ResearchView } from "./research-view";
import { ScreeningView } from "./screening-view";
import { CompareView } from "./compare-view";
import { WatchlistView } from "./watchlist-view";

const viewMap = {
  dashboard: DashboardView,
  research: ResearchView,
  screening: ScreeningView,
  compare: CompareView,
  watchlist: WatchlistView,
} as const;

export function WorkspaceView() {
  const { state } = useWorkspace();
  const View = viewMap[state.view] ?? DashboardView;

  return (
    <div className="h-full overflow-y-auto">
      <View />
    </div>
  );
}
