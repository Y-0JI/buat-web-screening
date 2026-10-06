// Pure helpers untuk tabel seasonality (gaya Stockbit): bulan = kolom, tahun = baris.
// Dipisah dari komponen agar bisa diuji tanpa React.

export interface YearRow {
  year: string;
  cells: (number | null)[]; // satu nilai per bulan, urut kolom
  total: number | null; // return majemuk setahun (%)
}

export interface SeasonalityTable {
  months: string[];
  average: (number | null)[];
  averageTotal: number | null;
  rows: YearRow[]; // urut tahun menurun
  up: (number | null)[];
  down: (number | null)[];
  total: (number | null)[];
  upProb: (number | null)[];
  annualUp: number | null;
  annualDown: number | null;
  annualTotal: number | null;
  annualUpProb: number | null;
  hasStats: boolean;
}

// Return majemuk beberapa return bulanan (%) -> (∏(1+r/100) - 1) * 100.
// Bulan tanpa data dilewati; tanpa data sama sekali -> null.
export function yearlyReturn(cells: (number | null)[]): number | null {
  let acc = 1;
  let n = 0;
  for (const r of cells) {
    if (r == null || !Number.isFinite(r)) continue;
    acc *= 1 + r / 100;
    n += 1;
  }
  return n > 0 ? (acc - 1) * 100 : null;
}

interface RawSeasonality {
  years?: string[];
  months?: string[];
  monthly_returns?: Record<string, Record<string, number>>;
  monthly_stats?: {
    month: string;
    avg?: number | null;
    up?: number | null;
    down?: number | null;
    total?: number | null;
    up_prob?: number | null;
  }[];
}

export function buildSeasonalityTable(data: RawSeasonality): SeasonalityTable {
  const months = data.months ?? [];
  const years = [...(data.years ?? [])].sort((a, b) => b.localeCompare(a));
  const stats = data.monthly_stats ?? [];
  const statOf = (m: string) => stats.find((s) => s.month === m);
  const valueOf = (m: string, y: string): number | null => {
    const v = data.monthly_returns?.[m]?.[y];
    return typeof v === "number" && Number.isFinite(v) ? v : null;
  };

  const rows: YearRow[] = years.map((year) => {
    const cells = months.map((m) => valueOf(m, year));
    return { year, cells, total: yearlyReturn(cells) };
  });

  const totals = rows.map((r) => r.total);
  const known = totals.filter((t): t is number => t != null);
  const averageTotal = known.length
    ? known.reduce((a, b) => a + b, 0) / known.length
    : null;

  const annualUp = known.filter((t) => t > 0).length;
  const annualDown = known.filter((t) => t < 0).length;
  const annualTotal = known.length;

  return {
    months,
    average: months.map((m) => statOf(m)?.avg ?? null),
    averageTotal,
    rows,
    up: months.map((m) => statOf(m)?.up ?? null),
    down: months.map((m) => statOf(m)?.down ?? null),
    total: months.map((m) => statOf(m)?.total ?? null),
    upProb: months.map((m) => statOf(m)?.up_prob ?? null),
    annualUp,
    annualDown,
    annualTotal,
    annualUpProb: annualTotal ? (annualUp / annualTotal) * 100 : null,
    hasStats: stats.length > 0,
  };
}