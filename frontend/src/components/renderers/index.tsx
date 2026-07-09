"use client";

import type { StockReport } from "@/lib/api";
import { StockReportCard } from "./stock-report";

export function DynamicRenderer({ data }: { data: StockReport }) {
  switch (data.render) {
    case "stock-report":
      return <StockReportCard data={data} />;
    default:
      return (
        <div className="p-4 bg-zinc-900 rounded-xl text-zinc-400 text-sm">
          Tipe render &quot;{data.render}&quot; belum tersedia
        </div>
      );
  }
}
