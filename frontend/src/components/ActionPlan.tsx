// Action Plan — consolidates every module's findings into one prioritized,
// team-tagged task queue with CSV export. Pure client-side aggregation over
// the results dict: no backend, no manual copy-paste into trackers.
import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import type { Results } from "../types";
import { Card, StatTiles, fmt } from "./viz";
import { Select } from "./Select";

type Team = "SEO" | "Content" | "CRO" | "Dev";

interface ActionItem {
  team: Team;
  action: string;
  target: string;
  impact: number; // comparable priority score
  impactLabel: string;
  module: string;
}

const arr = (v: unknown): any[] => (Array.isArray(v) ? v : []);
const n = (v: unknown) => (typeof v === "number" ? v : Number(v) || 0);

function collect(results: Results): ActionItem[] {
  const items: ActionItem[] = [];
  const push = (i: ActionItem) => items.push(i);

  // Uplift: CTR-gap pages → title/meta rewrites (Content)
  arr(results.uplift?.ctr_gap).slice(0, 6).forEach((c) =>
    push({
      team: "Content", module: "Uplift Tracker",
      action: `Rewrite title & meta — CTR ${c.ctr_pct}% vs ${c.expected_ctr_pct}% expected at pos ${c.position}`,
      target: c.page, impact: n(c.clicks_lost),
      impactLabel: `+${fmt(c.clicks_lost)} clicks/period`,
    }));

  // Uplift: internal links (SEO)
  arr(results.uplift?.internal_links).slice(0, 6).forEach((l) =>
    push({
      team: "SEO", module: "Uplift Tracker",
      action: `Add internal links (anchor "${l.anchor}") from ${arr(l.sources).map((s: any) => s.page).join(", ")}`,
      target: l.target, impact: n(arr(l.sources)[0]?.clicks) / 2,
      impactLabel: "ranking push",
    }));

  // Keyword opportunities → push into top 3 (SEO)
  arr(results.keyword_opportunities?.opportunities).slice(0, 6).forEach((o) =>
    push({
      team: "SEO", module: "Top Keyword Opportunity",
      action: `Push "${o.query}" from pos ${o.position} into top 3${o.is_regional ? " (regional query)" : ""}`,
      target: o.query, impact: n(o.click_uplift),
      impactLabel: `+${fmt(o.click_uplift)} clicks/period`,
    }));

  // Organic losers → investigate (SEO)
  arr(results.organic?.losers).slice(0, 4).forEach((p) =>
    push({
      team: "SEO", module: "Organic Performance",
      action: `Investigate decline (${fmt(p.session_delta_pct)}% sessions)`,
      target: p.page, impact: Math.abs(n(p.session_delta_pct)) * 20,
      impactLabel: `${fmt(p.session_delta_pct)}% sessions`,
    }));

  // Cannibalization → consolidate (Content)
  arr(results.cannibalization?.conflicts).slice(0, 4).forEach((c) =>
    push({
      team: "Content", module: "Cannibalization",
      action: `Consolidate ${n(c.num_pages) || arr(c.competing_pages).length} pages competing for "${c.query}"`,
      target: c.winner || arr(c.competing_pages)[0]?.page || c.query,
      impact: n(c.total_impressions) / 20, impactLabel: `${fmt(c.total_impressions)} impressions split`,
    }));

  // UX audit → CWV fixes (Dev)
  arr(results.ux_audit?.audit_rows).slice(0, 4).forEach((r) =>
    push({
      team: "Dev", module: "UX & Speed Audit",
      action: `Fix Core Web Vitals — PageSpeed ${fmt(r.pagespeed_score)}, LCP ${fmt(r.crux_lcp ?? r.lcp)}s`,
      target: r.page, impact: (100 - n(r.pagespeed_score)) * 15,
      impactLabel: `score ${fmt(r.pagespeed_score)}/100`,
    }));

  // Heatmap friction → CRO
  arr(results.heatmap?.flagged).slice(0, 3).forEach((c) =>
    push({
      team: "CRO", module: "Heatmap / Click",
      action: `Fix click friction — ${fmt(c.dead_clicks)} dead / ${fmt(c.rage_clicks)} rage clicks`,
      target: c.url, impact: n(c.dead_clicks) + n(c.rage_clicks) * 3,
      impactLabel: `${fmt(n(c.dead_clicks) + n(c.rage_clicks))} friction clicks`,
    }));

  // Hidden insights
  arr(results.hidden_insights?.zombies).slice(0, 3).forEach((p) =>
    push({
      team: "Content", module: "Hidden Insights",
      action: "Zombie page — rewrite title/meta to convert impressions into clicks",
      target: p.page, impact: n(p.impressions) / 15,
      impactLabel: `${fmt(p.impressions)} unclaimed impressions`,
    }));
  arr(results.hidden_insights?.cows).slice(0, 3).forEach((p) =>
    push({
      team: "CRO", module: "Hidden Insights",
      action: "Converts despite friction — remove UX blockers for easy CRO gain",
      target: p.page, impact: n(p.dead_clicks) * 2,
      impactLabel: `${fmt(p.dead_clicks)} dead clicks`,
    }));

  // Flatliners → refresh (Content)
  arr(results.uplift?.flatliners).slice(0, 3).forEach((f) =>
    push({
      team: "Content", module: "Uplift Tracker",
      action: `Refresh stagnant content (${f.delta_pct > 0 ? "+" : ""}${f.delta_pct}% traffic, ${fmt(f.impressions)} impressions)`,
      target: f.page, impact: n(f.impressions) / 30,
      impactLabel: "stagnant potential",
    }));

  // Indexation (Dev)
  const cni = n(results.indexation?.crawled_not_indexed);
  if (cni > 20) {
    push({
      team: "Dev", module: "Indexation",
      action: `${fmt(cni)} pages crawled but not indexed — check quality/canonical/robots`,
      target: "site-wide", impact: cni * 5, impactLabel: `${fmt(cni)} URLs`,
    });
  }

  return items.sort((a, b) => b.impact - a.impact);
}

function toCsv(items: ActionItem[]): string {
  const esc = (s: string) => `"${String(s).replace(/"/g, '""')}"`;
  const rows = [
    ["Priority", "Team", "Action", "Target", "Impact", "Source module"],
    ...items.map((i, idx) => [String(idx + 1), i.team, i.action, i.target, i.impactLabel, i.module]),
  ];
  return rows.map((r) => r.map(esc).join(",")).join("\n");
}

const TEAMS: ("All" | Team)[] = ["All", "SEO", "Content", "CRO", "Dev"];

export function ActionPlan({ results }: { results: Results }) {
  const [team, setTeam] = useState<string>("All");
  const all = useMemo(() => collect(results), [results]);
  const items = team === "All" ? all : all.filter((i) => i.team === team);
  const counts = Object.fromEntries(TEAMS.slice(1).map((t) => [t, all.filter((i) => i.team === t).length]));

  const download = () => {
    const blob = new Blob([toCsv(items)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `action-plan-${team.toLowerCase()}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h1 className="section-title">Action Plan</h1>
      <Card sub="Every module's findings, deduplicated into one prioritized queue — export and assign, no copy-pasting.">
        <StatTiles tiles={[
          { k: "Total actions", v: fmt(all.length) },
          { k: "SEO", v: fmt(counts.SEO) },
          { k: "Content", v: fmt(counts.Content) },
          { k: "CRO", v: fmt(counts.CRO) },
          { k: "Dev", v: fmt(counts.Dev) },
        ]} />
      </Card>
      <Card>
        <div className="ap-toolbar">
          <div className="kw-filter" style={{ marginBottom: 0 }}>
            <label>Team</label>
            <Select value={team} onChange={setTeam} options={TEAMS.map((t) => ({ value: t, label: t }))} />
          </div>
          <button className="btn sm ghost" onClick={download}>
            <Download size={15} />&nbsp; Export CSV
          </button>
        </div>
        {items.length === 0 ? (
          <div className="muted" style={{ marginTop: 14 }}>No actions for this team in the current report.</div>
        ) : (
          <div className="table-scroll"><table className="data">
            <thead><tr><th>#</th><th>Team</th><th>Action</th><th>Target</th><th>Impact</th><th>Source</th></tr></thead>
            <tbody>
              {items.map((i, idx) => (
                <tr key={idx}>
                  <td className="muted">{idx + 1}</td>
                  <td><span className={`team-badge t-${i.team.toLowerCase()}`}>{i.team}</span></td>
                  <td>{i.action}</td>
                  <td className="trunc" title={i.target}>{i.target}</td>
                  <td className="muted">{i.impactLabel}</td>
                  <td className="muted">{i.module}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
    </div>
  );
}
