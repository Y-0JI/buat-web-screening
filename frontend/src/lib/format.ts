export function fmtRp(v: number | null | undefined): string {
  return v == null ? "-" : Math.round(v).toLocaleString("id-ID");
}

export function fmtSigned(v: number | null | undefined): string {
  if (v == null) return "-";
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  return `${sign}${Math.abs(Math.round(v)).toLocaleString("id-ID")}`;
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null) return "-";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

export function fmtCompact(v: number | null | undefined): string {
  if (v == null) return "-";
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (a >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return String(Math.round(v));
}
