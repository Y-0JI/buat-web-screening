// Warna chrome chart (teks, grid, garis sumbu) per tema. Candle & indikator tetap.
export interface ChartChrome {
  textColor: string;
  grid: string;
  border: string;
}

export const CHART_CHROME: Record<"dark" | "light", ChartChrome> = {
  dark: {
    textColor: "#a1a1aa",
    grid: "rgba(63,63,70,0.35)",
    border: "rgba(63,63,70,0.6)",
  },
  light: {
    textColor: "#71717a",
    grid: "rgba(9,9,11,0.07)",
    border: "rgba(9,9,11,0.18)",
  },
};
