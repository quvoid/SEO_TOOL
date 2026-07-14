// Lightweight, flat visualization primitives (SVG/CSS — no chart lib).
import type { ReactNode } from "react";

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

export function StatTiles({ tiles }: { tiles: { k: string; v: ReactNode; cls?: string }[] }) {
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

export function Card({ title, children, sub }: { title?: string; children: ReactNode; sub?: string }) {
  return (
    <div className="card">
      {title && <h2 style={{ fontSize: 15 }}>{title}</h2>}
      {sub && <div className="muted" style={{ marginBottom: 4 }}>{sub}</div>}
      {children}
    </div>
  );
}
