"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "../theme/theme-provider";

const SRC = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";

interface Props {
  symbol: string;
}

export function TradingViewChart({ symbol }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.innerHTML = "";
    const holder = document.createElement("div");
    holder.className = "tradingview-widget-container__widget";
    holder.style.height = "480px";
    holder.style.width = "100%";
    const script = document.createElement("script");
    script.src = SRC;
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval: "5",
      timezone: "Asia/Jakarta",
      theme: theme === "light" ? "light" : "dark",
      style: "1",
      locale: "id",
      allow_symbol_change: false,
      withdateranges: true,
      hide_side_toolbar: false,
      details: false,
    });
    el.appendChild(holder);
    el.appendChild(script);
  }, [symbol, theme]);

  return <div ref={ref} className="tradingview-widget-container rounded-lg overflow-hidden" style={{ height: 480 }} />;
}
