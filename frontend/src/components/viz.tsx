// Lightweight, flat visualization primitives (SVG/CSS — no chart lib).
import { useRef, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Check, Copy, Download } from "lucide-react";

const num = (v: unknown) => (typeof v === "number" ? v : Number(v) || 0);
export const fmt = (v: unknown) => {
  const n = num(v);
  return Number.isInteger(n) ? n.toLocaleString() : n.toFixed(1);
};

export function Delta({ value, suffix = "%" }: { value: number; suffix?: string }) {
  const cls = value > 0 ? "pos" : value < 0 ? "neg" : "";
  return <span className={cls}>{value > 0 ? "+" : ""}{fmt(value)}{suffix}</span>;
}

/** Horizontal labelled bars, scaled to the max value. */
export function HBars({
  data,
  color = "var(--accent)",
  fmtValue = (v: number) => fmt(v),
}: {
  data: { label: string; value: number; color?: string; sub?: string }[];
  color?: string;
  fmtValue?: (v: number) => string;
}) {
  const max = Math.max(1, ...data.map((d) => Math.abs(d.value)));
  return (
    <div className="hbars">
      {data.map((d, i) => (
        <div className="hbar" key={i}>
          <div className="hbar-label" title={d.label}>{d.label}</div>
          <div className="hbar-track">
            <div
              className="hbar-fill"
              style={{ width: `${(Math.abs(d.value) / max) * 100}%`, background: d.color || color }}
            />
          </div>
          <div className="hbar-val">{fmtValue(d.value)}{d.sub ? <span className="hbar-sub"> {d.sub}</span> : null}</div>
        </div>
      ))}
    </div>
  );
}

/**
 * Multi-series line chart on ONE shared y axis.
 *
 * The previous version scaled each series to its own max so that different
 * magnitudes "fit together". That is a dual-axis chart, and it invents
 * correlations that aren't in the data — plotting impressions (0-350k) against
 * average position (0-20) made the two look coupled when nothing linked them.
 * Series on one plot must therefore share a unit and a scale; anything else
 * belongs in its own chart beside it (see the two-up small multiples in
 * Daily Trends).
 *
 * `invertY` flips the axis for rank-like measures where 1 is best.
 */
export function LineChart({
  points,
  series,
  height = 210,
  xLabel,
  yFormat = fmt,
  invertY = false,
  area = false,
  valueSuffix = "",
  vbWidth = 800,
}: {
  points: Record<string, unknown>[];
  series: { key: string; label: string; color: string }[];
  height?: number;
  xLabel?: (p: Record<string, unknown>, i: number) => string;
  yFormat?: (v: unknown) => string;
  invertY?: boolean;
  area?: boolean;
  valueSuffix?: string;
  /** viewBox width. The SVG scales proportionally, so a half-width card needs a
   *  narrower box or the plot renders squat (800-wide in a 430px column collapses
   *  to ~114px tall). Pass ~440 for small multiples. */
  vbWidth?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length < 2) return <div className="empty">Not enough data to plot.</div>;

  const W = vbWidth, PAD_L = 52, PAD_R = 16, PAD_T = 14, PAD_B = 24;
  const H = Math.max(120, height), iw = W - PAD_L - PAD_R, ih = H - PAD_T - PAD_B;

  // One domain over EVERY series — never per-series.
  const all = series.flatMap((s) => points.map((p) => num(p[s.key])));
  const dataMin = Math.min(...all), dataMax = Math.max(...all);
  // A filled area encodes magnitude by the size of the fill, so it must sit on
  // zero. A plain line encodes CHANGE by slope, and forcing zero there buries
  // the trend in dead space — 8k-12.5k on a 0-15k axis is a flat ribbon in the
  // top third. Fit the domain to the data for lines; keep zero for areas.
  const zeroBase = area || dataMin <= 0;
  const floor = invertY || !zeroBase ? dataMin : Math.min(0, dataMin);
  const ticks = niceTicks(floor, dataMax, 4);
  const lo = ticks[0], hi = ticks[ticks.length - 1];
  const span = Math.max(1e-9, hi - lo);

  const x = (i: number) => PAD_L + (i / (points.length - 1)) * iw;
  const y = (v: number) => {
    const t = (v - lo) / span;
    return PAD_T + (invertY ? t * ih : ih - t * ih);
  };

  const idx = hover == null ? null : Math.max(0, Math.min(points.length - 1, hover));
  const single = series.length === 1;

  return (
    <div className="linechart">
      {/* A legend is mandatory for 2+ series; one series is named by the title. */}
      {!single && (
        <div className="lc-legend">
          {series.map((s) => (
            <span className="lc-key" key={s.key}>
              <i style={{ background: s.color }} /> {s.label}
            </span>
          ))}
        </div>
      )}
      <div className="lc-plot">
        <svg viewBox={`0 0 ${W} ${H}`} className="lc-svg" role="img"
             aria-label={`${series.map((s) => s.label).join(" and ")} over time`}
             onMouseLeave={() => setHover(null)}
             onMouseMove={(e) => {
               const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
               const rel = ((e.clientX - r.left) / r.width) * W;
               setHover(Math.round(((rel - PAD_L) / iw) * (points.length - 1)));
             }}>
          {/* Solid hairline grid + y ticks — never dashed, always recessive. */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD_L} x2={W - PAD_R} y1={y(t)} y2={y(t)}
                    stroke="var(--viz-grid)" strokeWidth="1" />
              <text x={PAD_L - 8} y={y(t) + 3.5} textAnchor="end" className="lc-tick">
                {yFormat(t)}
              </text>
            </g>
          ))}
          {series.map((s) => {
            const vals = points.map((p) => num(p[s.key]));
            const d = vals.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
            return (
              <g key={s.key}>
                {area && single && (
                  <path d={`${d} L${x(points.length - 1).toFixed(1)},${y(lo)} L${x(0).toFixed(1)},${y(lo)} Z`}
                        fill={s.color} opacity="0.10" />
                )}
                <path d={d} fill="none" stroke={s.color} strokeWidth="2"
                      strokeLinejoin="round" strokeLinecap="round" />
              </g>
            );
          })}
          {idx != null && (
            <>
              <line x1={x(idx)} x2={x(idx)} y1={PAD_T} y2={PAD_T + ih}
                    stroke="var(--viz-axis)" strokeWidth="1" />
              {series.map((s) => (
                // 2px surface ring keeps the marker legible where lines cross.
                <circle key={s.key} cx={x(idx)} cy={y(num(points[idx][s.key]))} r="4"
                        fill={s.color} stroke="var(--viz-surface)" strokeWidth="2" />
              ))}
            </>
          )}
        </svg>
        {idx != null && (
          <div className="lc-tooltip"
               style={{ left: `${(x(idx) / W) * 100}%`,
                        transform: `translateX(${idx > points.length / 2 ? "-104%" : "4%"})` }}>
            <div className="lc-tt-x">{xLabel ? xLabel(points[idx], idx) : `#${idx}`}</div>
            {series.map((s) => (
              <div className="lc-tt-row" key={s.key}>
                <i style={{ background: s.color }} />
                <b>{yFormat(num(points[idx][s.key]))}{valueSuffix}</b>
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="lc-axis">
        <span>{xLabel ? xLabel(points[0], 0) : ""}</span>
        <span>{xLabel ? xLabel(points[points.length - 1], points.length - 1) : ""}</span>
      </div>
    </div>
  );
}

/** Axis ticks on clean round numbers (0 / 500 / 1,000), never raw data extremes. */
function niceTicks(min: number, max: number, count = 4): number[] {
  if (!isFinite(min) || !isFinite(max) || max <= min) return [min || 0, (max || 0) + 1];
  const raw = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  // 1/2/5 only — a 2.5 multiplier yields .25 steps that print as 6.8 / 7.3
  // rather than the clean round numbers an axis is supposed to carry.
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag * 10;
  // A zero/!finite step would make the loop below never terminate and hang the
  // render — bail to a plain two-tick axis instead.
  if (!isFinite(step) || step <= 0) return [min, max];
  // The domain MUST contain the data. Rounding the top tick down (e.g. stopping
  // at 10,000 when the peak is 12,500) pushes those points above the plot, where
  // `overflow: visible` happily draws them straight through the legend.
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const out: number[] = [];
  for (let v = start; v <= end + step * 0.5 && out.length < 64; v += step) {
    out.push(Math.round(v * 1e6) / 1e6);
  }
  return out.length >= 2 ? out : [min, max];
}

/** Donut for 2+ segments. */
export function Donut({
  segments,
  size = 132,
  thickness = 16,
  center,
}: {
  segments: { label: string; value: number; color: string }[];
  size?: number;
  thickness?: number;
  center?: ReactNode;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`translate(${size / 2},${size / 2}) rotate(-90)`}>
          <circle r={r} fill="none" stroke="var(--line-soft)" strokeWidth={thickness} />
          {segments.map((s, i) => {
            const len = (s.value / total) * c;
            const el = (
              <circle
                key={i}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth={thickness}
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
              />
            );
            offset += len;
            return el;
          })}
        </g>
      </svg>
      {center && <div className="donut-center">{center}</div>}
    </div>
  );
}

/** Semicircle-ish gauge ring for a 0..100 score. */
export function ScoreRing({ score, label }: { score: number; label?: string }) {
  const color = score >= 90 ? "var(--good)" : score >= 50 ? "var(--warn)" : "var(--bad)";
  const size = 76, thickness = 8;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const len = (Math.max(0, Math.min(100, score)) / 100) * c;
  return (
    <div className="ring">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`translate(${size / 2},${size / 2}) rotate(-90)`}>
          <circle r={r} fill="none" stroke="var(--line-soft)" strokeWidth={thickness} />
          <circle r={r} fill="none" stroke={color} strokeWidth={thickness}
            strokeDasharray={`${len} ${c - len}`} strokeLinecap="round" />
        </g>
      </svg>
      <div className="ring-center" style={{ color }}>{Math.round(score)}</div>
      {label && <div className="ring-label">{label}</div>}
    </div>
  );
}

/** Thin progress bar (0..100). */
export function Progress({ pct, color = "var(--accent)" }: { pct: number; color?: string }) {
  return (
    <div className="prog"><div className="prog-fill" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} /></div>
  );
}

export function StatTiles({ tiles }: { tiles: { k: ReactNode; v: ReactNode; cls?: string }[] }) {
  return (
    <div className="stat-row">
      {tiles.map((t, i) => (
        <div className="stat" key={i}>
          <div className="k">{t.k}</div>
          <div className={`v ${t.cls || ""}`}>{t.v}</div>
        </div>
      ))}
    </div>
  );
}

export function Card({ title, children, sub }: { title?: ReactNode; children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="card">
      {title && <h2 style={{ fontSize: 15 }}>{title}</h2>}
      {sub && <div className="muted" style={{ marginBottom: 4 }}>{sub}</div>}
      {children}
    </div>
  );
}

/* ---- Shared click-to-sort helpers for data tables ---- */
export interface SortState {
  key: string;
  dir: "asc" | "desc";
  toggle: (k: string) => void;
}

export function useSort<T extends Record<string, unknown>>(
  rows: T[], initialKey: string, initialDir: "asc" | "desc" = "desc",
) {
  const [key, setKey] = useState(initialKey);
  const [dir, setDir] = useState<"asc" | "desc">(initialDir);
  const sorted = [...rows].sort((a, b) => {
    const av = a[key], bv = b[key];
    const cmp = typeof av === "number" || typeof bv === "number"
      ? (Number(av) || 0) - (Number(bv) || 0)
      : String(av ?? "").localeCompare(String(bv ?? ""));
    return dir === "asc" ? cmp : -cmp;
  });
  const toggle = (k: string) => {
    if (k === key) setDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setKey(k); setDir("desc"); }
  };
  const sort: SortState = { key, dir, toggle };
  return { sorted, sort };
}

/**
 * Wraps a <table className="data"> and adds Copy (TSV → paste into Excel/Sheets)
 * and CSV download. Reads the rendered table's DOM, so it works for every table
 * with no per-table wiring. Replaces the old `<div className="table-scroll">`.
 */
export function DataTable({ children, name = "table" }: { children: ReactNode; name?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  const rows = (): string[][] => {
    const table = ref.current?.querySelector("table");
    if (!table) return [];
    const out: string[][] = [];
    table.querySelectorAll("tr").forEach((tr) => {
      const cells = [...tr.querySelectorAll("th,td")].map((c) => (c.textContent || "").replace(/\s+/g, " ").trim());
      if (cells.length) out.push(cells);
    });
    return out;
  };

  const copy = async () => {
    const tsv = rows().map((r) => r.join("\t")).join("\n");
    try {
      await navigator.clipboard.writeText(tsv);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked — CSV download still works */ }
  };

  const download = () => {
    const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const csv = rows().map((r) => r.map(esc).join(",")).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="dt-wrap">
      <div className="dt-tools no-print">
        <button className="dt-btn" onClick={copy} title="Copy for Excel / Sheets">
          {copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
        </button>
        <button className="dt-btn" onClick={download} title="Download as CSV"><Download size={12} /> CSV</button>
      </div>
      <div className="table-scroll" ref={ref}>{children}</div>
    </div>
  );
}

export function SortTh({ k, sort, children }: { k: string; sort: SortState; children: ReactNode }) {
  const active = sort.key === k;
  return (
    <th className={`sortable ${active ? "active" : ""}`} onClick={() => sort.toggle(k)}>
      <span className="th-inner">
        {children} {active && (sort.dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
      </span>
    </th>
  );
}
