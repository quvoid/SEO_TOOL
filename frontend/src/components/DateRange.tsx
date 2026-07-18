// GA4-style date range picker: a popover calendar where the primary period is
// picked in accent (two clicks: start, then end) and the comparison window in
// amber — same visual logic as GA4's explorer. Draft state commits on Apply.
// The exported Range contract is unchanged, so Dashboard/api need no edits.
import { useEffect, useMemo, useRef, useState } from "react";
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";

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
// Build ISO from local Y/M/D so calendar cells never drift a day across timezones.
const isoOf = (y: number, m: number, d: number) =>
  `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

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
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DOW = ["S", "M", "T", "W", "T", "F", "S"];

const fmtDay = (s?: string) => {
  if (!s) return "—";
  const [y, m, d] = s.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
};

function Month({ y, m, primary, cmp, maxIso, onPick }: {
  y: number; m: number;
  primary: { start: string; end: string };
  cmp: { start: string; end: string } | null;
  maxIso: string;
  onPick: (d: string) => void;
}) {
  const firstDow = new Date(y, m, 1).getDay();
  const count = new Date(y, m + 1, 0).getDate();
  const cells: (number | null)[] = [...Array(firstDow).fill(null), ...Array.from({ length: count }, (_, i) => i + 1)];
  return (
    <div className="drp-month">
      <div className="drp-month-name">{MONTHS[m]} {y}</div>
      <div className="drp-grid">
        {DOW.map((d, i) => <div className="drp-dow" key={`d${i}`}>{d}</div>)}
        {cells.map((d, i) => {
          if (d === null) return <div key={i} />;
          const ds = isoOf(y, m, d);
          const disabled = ds > maxIso;
          const cls = ["drp-day"];
          if (disabled) cls.push("off");
          if (cmp && ds >= cmp.start && ds <= cmp.end) cls.push("cmp");
          if (cmp && (ds === cmp.start || ds === cmp.end)) cls.push("cmp-edge");
          if (ds > primary.start && ds < primary.end) cls.push("in");
          if (ds === primary.start || ds === primary.end) cls.push("edge");
          return (
            <button key={i} type="button" className={cls.join(" ")} disabled={disabled} onClick={() => onPick(ds)}>
              {d}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function DateRange({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Range>(value);
  const [picking, setPicking] = useState<"primary" | "compare">("primary");
  const [pendingFor, setPendingFor] = useState<"primary" | "compare" | null>(null);
  const [view, setView] = useState<{ y: number; m: number }>(() => {
    const [y, m] = (value.start || iso(yesterday())).split("-").map(Number);
    return { y, m: m - 1 };
  });
  const ref = useRef<HTMLDivElement>(null);
  const maxIso = iso(yesterday());

  useEffect(() => {
    if (!value.start || !value.end) onChange(presetRange(30));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const days = useMemo(() => {
    if (!value.start || !value.end) return 0;
    return Math.round((new Date(value.end).getTime() - new Date(value.start).getTime()) / 86400000) + 1;
  }, [value]);

  // The compare window shown on the calendar: custom picks, else auto preview.
  const draftCmp = useMemo(() => {
    if (!draft.start || !draft.end) return null;
    if (draft.compareMode === "custom" && draft.compareStart && draft.compareEnd)
      return { start: draft.compareStart, end: draft.compareEnd };
    return autoCompare(draft.start, draft.end);
  }, [draft]);

  const openPop = () => {
    setDraft(value);
    setPendingFor(null);
    setPicking("primary");
    const [y, m] = (value.start || iso(yesterday())).split("-").map(Number);
    setView({ y, m: m - 1 });
    setOpen(true);
  };

  const pick = (d: string) => {
    const tgt = draft.compareMode === "custom" && picking === "compare" ? "compare" : "primary";
    if (tgt === "primary") {
      if (pendingFor !== "primary") {
        setDraft({ ...draft, start: d, end: d });
        setPendingFor("primary");
      } else if (d < draft.start) {
        setDraft({ ...draft, start: d, end: d }); // restart earlier — keep waiting for end
      } else {
        setDraft({ ...draft, end: d });
        setPendingFor(null);
      }
    } else {
      if (pendingFor !== "compare") {
        setDraft({ ...draft, compareStart: d, compareEnd: d });
        setPendingFor("compare");
      } else if (d < (draft.compareStart || d)) {
        setDraft({ ...draft, compareStart: d, compareEnd: d });
      } else {
        setDraft({ ...draft, compareEnd: d });
        setPendingFor(null);
      }
    }
  };

  const setMode = (mode: "auto" | "custom") => {
    if (mode === "custom") {
      const a = draftCmp || autoCompare(draft.start, draft.end);
      setDraft({ ...draft, compareMode: "custom", compareStart: a.start, compareEnd: a.end });
      setPicking("compare");
    } else {
      setDraft({ ...draft, compareMode: "auto" });
      setPicking("primary");
    }
    setPendingFor(null);
  };

  const applyPreset = (d: number) => {
    const p = presetRange(d);
    setDraft(p);
    setPendingFor(null);
    setPicking("primary");
    const [y, m] = p.start.split("-").map(Number);
    setView({ y, m: m - 1 });
  };

  const shift = (n: number) => {
    setView((v) => {
      const dt = new Date(v.y, v.m + n, 1);
      return { y: dt.getFullYear(), m: dt.getMonth() };
    });
  };

  const apply = () => {
    onChange(draft);
    setOpen(false);
  };

  const next = new Date(view.y, view.m + 1, 1);
  const activePreset = PRESETS.find((p) => {
    const pr = presetRange(p.days);
    return pr.start === draft.start && pr.end === draft.end && draft.compareMode === "auto";
  })?.days;

  return (
    <div className="drp" ref={ref}>
      <button type="button" className="drp-btn" onClick={() => (open ? setOpen(false) : openPop())}>
        <CalendarDays size={15} className="drp-ico" />
        <span className="drp-btn-text">{fmtDay(value.start)} → {fmtDay(value.end)}</span>
        <span className="drp-days">{days}d</span>
        <ChevronDown size={14} className={`select-caret ${open ? "up" : ""}`} />
      </button>

      {open && (
        <div className="drp-pop">
          <div className="drp-row">
            <div className="drp-inputs">
              <input type="date" className="date-input" value={draft.start} max={draft.end || maxIso}
                onChange={(e) => e.target.value && setDraft({ ...draft, start: e.target.value })} />
              <span className="dr-sep">→</span>
              <input type="date" className="date-input" value={draft.end} min={draft.start || undefined} max={maxIso}
                onChange={(e) => e.target.value && setDraft({ ...draft, end: e.target.value })} />
            </div>
            <div className="dr-presets">
              {PRESETS.map((p) => (
                <button key={p.days} type="button" className={`preset ${activePreset === p.days ? "active" : ""}`}
                  onClick={() => applyPreset(p.days)}>{p.label}</button>
              ))}
            </div>
          </div>

          <div className="drp-row drp-cmp">
            <span className="dr-cmp-label">Compare</span>
            <div className="drp-chips">
              <button type="button" className={`preset ${draft.compareMode === "auto" ? "active" : ""}`}
                onClick={() => setMode("auto")}>Previous period</button>
              <button type="button" className={`preset ${draft.compareMode === "custom" ? "active" : ""}`}
                onClick={() => setMode("custom")}>Custom</button>
            </div>
            {draft.compareMode === "custom" && (
              <>
                <input type="date" className="date-input sm" value={draft.compareStart || ""}
                  onChange={(e) => e.target.value && setDraft({ ...draft, compareStart: e.target.value })} />
                <span className="dr-sep">→</span>
                <input type="date" className="date-input sm" value={draft.compareEnd || ""} max={maxIso}
                  onChange={(e) => e.target.value && setDraft({ ...draft, compareEnd: e.target.value })} />
                <div className="drp-chips drp-pick-toggle">
                  <button type="button" className={`preset ${picking === "primary" ? "active" : ""}`}
                    onClick={() => { setPicking("primary"); setPendingFor(null); }}>Pick: period</button>
                  <button type="button" className={`preset cmp-chip ${picking === "compare" ? "active" : ""}`}
                    onClick={() => { setPicking("compare"); setPendingFor(null); }}>Pick: compare</button>
                </div>
              </>
            )}
          </div>

          <div className="drp-cal">
            <button type="button" className="drp-nav" onClick={() => shift(-1)} aria-label="Previous month">
              <ChevronLeft size={15} />
            </button>
            <Month y={view.y} m={view.m} primary={{ start: draft.start, end: draft.end }}
              cmp={draftCmp} maxIso={maxIso} onPick={pick} />
            <Month y={next.getFullYear()} m={next.getMonth()} primary={{ start: draft.start, end: draft.end }}
              cmp={draftCmp} maxIso={maxIso} onPick={pick} />
            <button type="button" className="drp-nav" onClick={() => shift(1)} aria-label="Next month">
              <ChevronRight size={15} />
            </button>
          </div>

          <div className="drp-foot">
            <span className="drp-note">
              {pendingFor
                ? "Now click the end date…"
                : draftCmp ? `vs ${fmtDay(draftCmp.start)} → ${fmtDay(draftCmp.end)}` : ""}
            </span>
            <div className="drp-actions">
              <button type="button" className="preset" onClick={() => setOpen(false)}>Cancel</button>
              <button type="button" className="btn sm" onClick={apply}
                disabled={!draft.start || !draft.end || draft.end < draft.start}>Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
