"use client";

import type { AppResult } from "@/lib/api";
import { StockReportCard } from "./stock-report";
import { ComparisonView } from "./comparison";
import { RankingView } from "./ranking";
import { VisionAnalysisView } from "./vision-analysis";

export function DynamicRenderer({ result }: { result: AppResult }) {
  switch (result.type) {
    case "stock-report":
      return <StockReportCard data={result.data} />;
    case "comparison":
      return <ComparisonView reports={result.data} />;
    case "ranking":
      return <RankingView items={result.data} />;
    case "vision-analysis":
      return <VisionAnalysisView data={result.data} />;
    default:
      return (
        <div className="p-4 bg-zinc-900 rounded-xl text-zinc-400 text-sm">
          Tipe render tidak dikenal
        </div>
      );
  }
}
