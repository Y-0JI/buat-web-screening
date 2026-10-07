"use client";

import type { AccumulationCandidate, AccumulationResult } from "@/lib/chat";

const DEPTHS = [
  {
    key: "broker",
    label: "Broker besar",
    badge: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30",
    desc: "dihitung dari data broker",
  },
  {
    key: "foreign",
    label: "Arus asing",
    badge: "bg-sky-500/15 text-sky-500 border-sky-500/30",
    desc: "dihitung dari data arus asing",
  },
  {
    key: "hv",
    label: "Harga-volume",
    badge: "bg-text-muted/15 text-text-secondary border-border/30",
    desc: "dihitung dari data harga-volume",
  },
] as const;

function fmt(v: number | null, digits = 2): string {
  if (v == null) return "-";
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(digits) + "T";
  if (a >= 1e9) return (v / 1e9).toFixed(digits) + "B";
  if (a >= 1e6) return (v / 1e6).toFixed(digits) + "M";
  return v.toFixed(digits);
}

function contradictions(c: AccumulationCandidate): string[] {
  const out: string[] = [];
  if (c.foreign_net != null && c.foreign_net < 0) out.push("arus asing net jual");
  if (c.cmf != null && c.cmf < 0) out.push("CMF negatif");
  if (c.obv_slope != null && c.obv_slope < 0) out.push("OBV turun");
  if (c.ad_slope != null && c.ad_slope < 0) out.push("A/D turun");
  if (c.runup != null && c.runup > 0.15) out.push("harga sudah lari");
  return out;
}

function CandidateRow({ c }: { c: AccumulationCandidate }) {
  const contra = contradictions(c);
  return (
    <div className="rounded-lg border border-border bg-surface-1/50 px-2.5 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-text-primary">{c.ticker}</span>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-text-secondary">
          skor {c.score ?? "-"}
        </span>
      </div>
      {c.reasons ? (
        <p className="mt-1 text-[11px] leading-relaxed text-text-secondary">{c.reasons}</p>
      ) : null}
      <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-text-muted">
        <span>asing {fmt(c.foreign_net)}</span>
        <span>· CMF {fmt(c.cmf)}</span>
        <span>· run {c.runup == null ? "-" : `${(c.runup * 100).toFixed(1)}%`}</span>
      </div>
      {c.broker_checked && !c.broker_confirmed ? (
        <div className="mt-1">
          <span className="rounded border border-border bg-surface-2/60 px-1.5 py-0.5 text-[10px] text-text-secondary">
            broker dicek, tidak mengonfirmasi
          </span>
        </div>
      ) : null}
      {contra.length ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {contra.map((t) => (
            <span
              key={t}
              className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function AccumulationCard({ data }: { data: AccumulationResult }) {
  if (data.error) {
    return (
      <div className="my-2 rounded-xl border border-border bg-surface-1/40 p-3 text-[12px] text-red-500">
        {data.error}
      </div>
    );
  }

  const candidates = data.candidates || [];
  const grouped = DEPTHS.map((d) => ({
    ...d,
    rows: candidates.filter((c) => c.depth === d.key),
  })).filter((g) => g.rows.length > 0);

  return (
    <div className="my-2 rounded-xl border border-border bg-surface-1/40 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12px] font-medium text-text-primary">
          Screening akumulasi (deskriptif)
        </span>
        {data.scan_date ? (
          <span className="text-[11px] text-text-muted">data {data.scan_date}</span>
        ) : null}
        {data.status === "partial" ? (
          <span className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500">
            scan tidak lengkap
          </span>
        ) : null}
        {data.stale ? (
          <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 text-[10px] text-red-500">
            data basi
          </span>
        ) : null}
        {data.stale && data.stale_trading_days != null ? (
          <span className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500">
            hari bursa ke-{data.stale_trading_days}
          </span>
        ) : null}
      </div>

      {!candidates.length ? (
        <p className="mt-2 text-[12px] text-text-secondary">
          Tidak ada kandidat pada scan terakhir.
        </p>
      ) : (
        <div className="mt-2 space-y-3">
          {grouped.map((g) => (
            <div key={g.key}>
              <div className="mb-1.5 flex items-center gap-2">
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] ${g.badge}`}
                >
                  {g.label}
                </span>
                <span className="text-[10px] text-text-muted">{g.desc}</span>
              </div>
              <div className="space-y-1.5">
                {g.rows.map((c) => (
                  <CandidateRow key={c.ticker} c={c} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
        Hasil screening deskriptif dari aliran harga/arus asing/broker besar.
        Belum terbukti prediktif. Bukan label institusi, bukan saran investasi.
        Kedalaman data: broker &gt; arus asing &gt; harga-volume.
      </p>
    </div>
  );
}
