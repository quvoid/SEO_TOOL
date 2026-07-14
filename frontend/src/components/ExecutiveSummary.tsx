import type { ModuleResult, ReportMeta } from "../types";
import { cleanTitle } from "../util";
import { Markdown } from "./Markdown";

// Split the strategy narrative into the 3-month calendar + the rest.
function parseCalendar(md?: string): { months: { label: string; body: string }[]; rest: string } {
  if (!md) return { months: [], rest: "" };
  const re = /#+\s*Month\s*([123])\b[^\n]*\n/gi;
  const matches = [...md.matchAll(re)];
  if (matches.length < 2) return { months: [], rest: md };
  const rest = md.slice(0, matches[0].index).trim();
  const months = matches.map((m, i) => {
    const start = (m.index || 0) + m[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : md.length;
    const heading = m[0].replace(/#+\s*/, "").trim();
    return { label: heading, body: md.slice(start, end).trim() };
  });
  return { months, rest };
}

export function ExecutiveSummary({ exec, meta }: { exec?: ModuleResult; meta?: ReportMeta }) {
  if (!exec) return <div className="empty">Run a report to see the executive summary.</div>;
  const points = (exec.key_points as string[]) || [];
  const { months, rest } = parseCalendar(exec.narrative as string | undefined);

  return (
    <div>
      <h1 className="section-title">{cleanTitle(exec.title as string, "Executive Summary & Growth Strategy")}</h1>
      <div className="card">
        <div className="muted">
          {meta?.site} ·{" "}
          {meta?.start_date && meta?.end_date ? `${meta.start_date} → ${meta.end_date}` : `last ${meta?.days} days`}{" "}
          · generated {meta?.generated}{"  "}
          <span className={`pill ${meta?.is_demo ? "demo" : "live"}`}>{meta?.is_demo ? "DEMO DATA" : "LIVE"}</span>
        </div>
        {points.length > 0 && (
          <div className="findings">
            {points.map((p, i) => (
              <div className="finding" key={i}><span className="finding-dot" />{p}</div>
            ))}
          </div>
        )}
      </div>

      {rest && (
        <div className="card">
          <Markdown>{rest}</Markdown>
        </div>
      )}

      {months.length > 0 && (
        <>
          <h2 className="section-sub">3-Month Growth Strategy</h2>
          <div className="calendar">
            {months.map((m, i) => (
              <div className="cal-card" key={i}>
                <div className="cal-head">
                  <span className="cal-num">{i + 1}</span>
                  <span className="cal-title">{m.label.replace(/^Month\s*\d+\s*[:–-]?\s*/i, "")}</span>
                </div>
                <div className="cal-body"><Markdown>{m.body}</Markdown></div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
