// GA4/GSC-style date range with an explicit comparison window.
// Current range = start..end. Comparison = auto (previous equal period) or custom.
import { useEffect, useMemo } from "react";

export interface Range {
  start: string; // YYYY-MM-DD
  end: string;
  compareMode: "auto" | "custom";
  compareStart?: string;
  compareEnd?: string;
}

const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const yesterday = () => addDays(new Date(), -1);

export function presetRange(days: number): Range {
  const end = yesterday();
  return { start: iso(addDays(end, -(days - 1))), end: iso(end), compareMode: "auto" };
}

export function autoCompare(start: string, end: string): { start: string; end: string } {
  const s = new Date(start), e = new Date(end);
  const d = Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
  const pEnd = addDays(s, -1);
  return { start: iso(addDays(pEnd, -(d - 1))), end: iso(pEnd) };
}

const PRESETS = [{ label: "7d", days: 7 }, { label: "28d", days: 28 }, { label: "30d", days: 30 }, { label: "90d", days: 90 }];

export function DateRange({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
  useEffect(() => {
    if (!value.start || !value.end) onChange(presetRange(30));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { days, cmp } = useMemo(() => {
    if (!value.start || !value.end) return { days: 0, cmp: null as { start: string; end: string } | null };
    const s = new Date(value.start), e = new Date(value.end);
    const d = Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
    const cmp = value.compareMode === "custom" && value.compareStart && value.compareEnd
      ? { start: value.compareStart, end: value.compareEnd }
      : autoCompare(value.start, value.end);
    return { days: d, cmp };
  }, [value]);

  const activePreset = PRESETS.find((p) => p.days === days && value.compareMode === "auto")?.days;

  return (
    <div className="daterange">
      <div className="dr-row">
        <input type="date" className="date-input" value={value.start} max={value.end || undefined}
          onChange={(e) => onChange({ ...value, start: e.target.value })} />
        <span className="dr-sep">→</span>
        <input type="date" className="date-input" value={value.end} min={value.start || undefined} max={iso(yesterday())}
          onChange={(e) => onChange({ ...value, end: e.target.value })} />
        <div className="dr-presets">
          {PRESETS.map((p) => (
            <button key={p.days} type="button" className={`preset ${activePreset === p.days ? "active" : ""}`}
              onClick={() => onChange(presetRange(p.days))}>{p.label}</button>
          ))}
        </div>
      </div>

      <div className="dr-cmp">
        <span className="dr-cmp-label">Compare to</span>
        <select className="cmp-select" value={value.compareMode}
          onChange={(e) => {
            const mode = e.target.value as "auto" | "custom";
            if (mode === "custom") {
              const a = cmp || autoCompare(value.start, value.end);
              onChange({ ...value, compareMode: "custom", compareStart: a.start, compareEnd: a.end });
            } else {
              onChange({ ...value, compareMode: "auto" });
            }
          }}>
          <option value="auto">Previous period</option>
          <option value="custom">Custom</option>
        </select>
        {value.compareMode === "custom" && (
          <>
            <input type="date" className="date-input sm" value={value.compareStart || ""}
              onChange={(e) => onChange({ ...value, compareStart: e.target.value })} />
            <span className="dr-sep">→</span>
            <input type="date" className="date-input sm" value={value.compareEnd || ""}
              onChange={(e) => onChange({ ...value, compareEnd: e.target.value })} />
          </>
        )}
        {cmp && value.compareMode === "auto" && (
          <span className="cmp-note">{days} days · vs {cmp.start} → {cmp.end}</span>
        )}
      </div>
    </div>
  );
}
