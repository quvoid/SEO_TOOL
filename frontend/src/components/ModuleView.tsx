// Generic, robust renderer for any analysis module dict.
// - `narrative`  -> prose block
// - `key_points` -> bullet list
// - scalar numbers/strings -> stat tiles
// - arrays of objects -> tables
// This keeps the preserved module structure while tolerating shape differences.
import type { ModuleResult } from "../types";
import { cleanTitle } from "../util";
import { Markdown } from "./Markdown";

const HIDDEN_KEYS = new Set(["title", "narrative", "key_points"]);

function isTable(v: unknown): v is Record<string, unknown>[] {
  return Array.isArray(v) && v.length > 0 && typeof v[0] === "object" && v[0] !== null;
}

function isScalar(v: unknown): v is string | number | boolean {
  return ["string", "number", "boolean"].includes(typeof v);
}

function humanize(k: string): string {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmt(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2);
  return String(v ?? "");
}

function deltaClass(key: string, v: unknown): string {
  if (typeof v !== "number") return "";
  if (/delta|change|pct|growth/i.test(key)) return v > 0 ? "pos" : v < 0 ? "neg" : "";
  return "";
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  return (
    <div className="table-scroll">
      <table className="data num">
        <thead>
          <tr>{cols.map((c) => <th key={c}>{humanize(c)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className={deltaClass(c, r[c])}>
                  {typeof r[c] === "number" && /delta|change|pct/i.test(c) && (r[c] as number) > 0 ? "+" : ""}
                  {fmt(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ModuleView({ mod, label }: { mod?: ModuleResult; label: string }) {
  if (!mod) return <div className="empty">No data for this module.</div>;

  const scalars = Object.entries(mod).filter(([k, v]) => !HIDDEN_KEYS.has(k) && isScalar(v));
  const tables = Object.entries(mod).filter(([k, v]) => !HIDDEN_KEYS.has(k) && isTable(v));

  return (
    <div>
      <div className="card">
        <h2>{cleanTitle(mod.title as string, label)}</h2>
        {scalars.length > 0 && (
          <div className="stat-row">
            {scalars.map(([k, v]) => (
              <div className="stat" key={k}>
                <div className="k">{humanize(k)}</div>
                <div className={`v ${deltaClass(k, v)}`}>
                  {typeof v === "number" && /delta|change|pct/i.test(k) && (v as number) > 0 ? "+" : ""}
                  {fmt(v)}
                  {/pct|rate/i.test(k) ? "%" : ""}
                </div>
              </div>
            ))}
          </div>
        )}
        {mod.narrative ? <Markdown>{mod.narrative as string}</Markdown> : null}
      </div>

      {tables.map(([k, v]) => (
        <div className="card" key={k}>
          <h2 style={{ fontSize: 15 }}>{humanize(k)}</h2>
          <DataTable rows={v as Record<string, unknown>[]} />
        </div>
      ))}
    </div>
  );
}
