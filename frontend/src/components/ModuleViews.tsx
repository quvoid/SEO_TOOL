// Data-driven visual views per module. These bind to the STRUCTURED fields each
// analysis module computes (not the AI narrative), so they render even when the
// AI quota is exhausted. Falls back to the generic ModuleView for unknowns.
import { Ghost, Gem as GemIcon, Frown } from "lucide-react";
import type { ModuleResult, Results } from "../types";
import { cleanTitle } from "../util";
import { Markdown } from "./Markdown";
import { ModuleView } from "./ModuleView";
import { Card, Delta, Donut, HBars, Progress, ScoreRing, StatTiles, fmt } from "./viz";

const pct = (v: unknown) => `${(Number(v) * 100 || 0).toFixed(1)}%`;
const dur = (s: unknown) => {
  const t = Number(s) || 0;
  const m = Math.floor(t / 60);
  return `${m}m ${Math.round(t - m * 60)}s`;
};

const arr = (v: unknown): any[] => (Array.isArray(v) ? v : []);
const n = (v: unknown) => (typeof v === "number" ? v : Number(v) || 0);
const shortUrl = (u?: string) => {
  if (!u) return "—";
  try { return new URL(u).pathname || "/"; } catch { return u.replace(/^https?:\/\/[^/]+/, "") || u; }
};

function Narrative({ mod }: { mod: ModuleResult }) {
  if (!mod.narrative) return null;
  return (
    <Card title="AI Analysis">
      <Markdown>{mod.narrative as string}</Markdown>
    </Card>
  );
}

function Title({ mod, fallback }: { mod: ModuleResult; fallback: string }) {
  return <h1 className="section-title">{cleanTitle(mod.title as string, fallback)}</h1>;
}

/* ---- Module 1: Organic Performance ---- */
function Organic({ mod, results }: { mod: ModuleResult; results: Results }) {
  const gainers = arr(mod.gainers), losers = arr(mod.losers);
  const delta = n(mod.overall_delta_pct);
  const t = (results._ga4_totals || {}) as Record<string, unknown>;
  const hasTotals = t.total_users != null || t.engagement_rate != null;
  const PageCol = ({ items, tone }: { items: any[]; tone: "up" | "down" }) => (
    <div className="pc-grid">
      {items.slice(0, 6).map((p, i) => (
        <div className={`pcard ${tone}`} key={i}>
          <div className="pcard-path" title={p.page}>{shortUrl(p.page)}</div>
          <div className="pcard-metrics">
            <span className={tone === "up" ? "pos" : "neg"}>
              {n(p.session_delta_pct) > 0 ? "+" : ""}{fmt(p.session_delta_pct)}% sessions
            </span>
            {p.position != null && <span className="muted">pos {fmt(p.position)}</span>}
          </div>
        </div>
      ))}
      {items.length === 0 && <div className="muted">None.</div>}
    </div>
  );
  return (
    <div>
      <Title mod={mod} fallback="Organic Performance" />
      <Card>
        <StatTiles tiles={[
          { k: "Organic sessions", v: fmt(mod.total_sessions) },
          { k: "Prior period", v: fmt(mod.total_prev_sessions) },
          { k: "Change", v: <Delta value={delta} />, cls: delta >= 0 ? "good" : "bad" },
        ]} />
      </Card>
      {hasTotals && (
        <Card title="Audience metrics" sub="GA4 · selected period (organic)">
          <StatTiles tiles={[
            { k: "Total users", v: fmt(t.total_users) },
            { k: "New users", v: fmt(t.new_users) },
            { k: "Returning users", v: fmt(t.returning_users) },
            { k: "Active users", v: fmt(t.active_users) },
            { k: "Engagement rate", v: pct(t.engagement_rate) },
            { k: "Bounce rate", v: pct(t.bounce_rate) },
            { k: "Avg. session", v: dur(t.avg_session_duration) },
            { k: "Sessions / active user", v: (Number(t.sessions_per_user) || 0).toFixed(2) },
          ]} />
        </Card>
      )}
      <div className="two-col">
        <Card title={`▲ Growing pages (${gainers.length})`}><PageCol items={gainers} tone="up" /></Card>
        <Card title={`▼ Declining pages (${losers.length})`}><PageCol items={losers} tone="down" /></Card>
      </div>
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 3: Funnel ---- */
function Funnel({ mod }: { mod: ModuleResult }) {
  const steps = arr(mod.steps);
  const devices = (mod.device_steps || {}) as Record<string, any[]>;
  const hasDevices = Object.keys(devices).length > 0;
  const FunnelBars = ({ data }: { data: any[] }) => {
    const max = Math.max(1, ...data.map((s) => n(s.users)));
    return (
      <div className="funnel">
        {data.map((s, i) => (
          <div className="funnel-step" key={i}>
            <div className="funnel-top"><span>{s.step}</span><span className="muted">{fmt(s.users)}</span></div>
            <div className="funnel-track"><div className="funnel-fill" style={{ width: `${(n(s.users) / max) * 100}%` }} /></div>
            {n(s.drop_pct) > 0 && <div className="funnel-drop neg">↓ {fmt(s.drop_pct)}% drop</div>}
          </div>
        ))}
      </div>
    );
  };
  return (
    <div>
      <Title mod={mod} fallback="Funnel Drop-off" />
      <Card>
        <StatTiles tiles={[
          { k: "Overall completion", v: `${fmt(mod.overall_completion_pct)}%` },
          { k: "Biggest drop", v: (mod.biggest_drop as any)?.step || "—", cls: "bad" },
        ]} />
      </Card>
      {hasDevices ? (
        <div className="two-col">
          {Object.entries(devices).map(([dev, st]) => (
            <Card title={dev[0].toUpperCase() + dev.slice(1)} key={dev}><FunnelBars data={st} /></Card>
          ))}
        </div>
      ) : (
        <Card title="Conversion funnel"><FunnelBars data={steps} /></Card>
      )}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 4: Heatmap / Click ---- */
function Heatmap({ mod }: { mod: ModuleResult }) {
  const flagged = arr(mod.flagged);
  const totalDead = flagged.reduce((s, c) => s + n(c.dead_clicks), 0);
  const totalRage = flagged.reduce((s, c) => s + n(c.rage_clicks), 0);
  const totalQuick = flagged.reduce((s, c) => s + n(c.quickback_clicks), 0);
  return (
    <div>
      <Title mod={mod} fallback="Heatmap / Click" />
      <Card>
        <StatTiles tiles={[
          { k: "Pages with friction", v: fmt(flagged.length) },
          { k: "Dead clicks", v: fmt(totalDead), cls: "bad" },
          { k: "Rage clicks", v: fmt(totalRage), cls: "bad" },
          { k: "Quick-backs", v: fmt(totalQuick), cls: "bad" },
        ]} />
      </Card>
      <Card title="Click frustration by page" sub="Dead clicks (non-interactive) + rage clicks (repeated frustration)">
        <HBars
          data={flagged.slice(0, 8).map((c) => ({
            label: shortUrl(c.url), value: n(c.dead_clicks) + n(c.rage_clicks) * 2,
            sub: `${n(c.dead_clicks)} dead · ${n(c.rage_clicks)} rage`,
          }))}
          color="var(--bad)"
          fmtValue={() => ""}
        />
      </Card>
      <div className="two-col">
        {flagged.slice(0, 6).map((c, i) => (
          <div className="card" key={i} style={{ marginBottom: 0 }}>
            <div className="pcard-path" title={c.url}>{shortUrl(c.url)}</div>
            <div className="stat-row" style={{ marginTop: 12 }}>
              <div className="stat"><div className="k">Dead clicks</div><div className="v bad">{fmt(c.dead_clicks)}</div></div>
              <div className="stat"><div className="k">Rage clicks</div><div className="v bad">{fmt(c.rage_clicks)}</div></div>
              <div className="stat"><div className="k">Sessions</div><div className="v">{fmt(c.total_sessions)}</div></div>
            </div>
          </div>
        ))}
      </div>
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 5: Scroll ---- */
function Scroll({ mod }: { mod: ModuleResult }) {
  const pages = (arr(mod.all_pages).length ? arr(mod.all_pages) : arr(mod.low_scroll_pages)).slice(0, 10);
  return (
    <div>
      <Title mod={mod} fallback="Scroll Analysis" />
      <Card title="Average scroll depth" sub="Pages below 40% mean most users never reach mid-page CTAs">
        <div className="scroll-list">
          {pages.map((p, i) => {
            const d = n(p.avg_scroll_percent);
            const color = d < 40 ? "var(--bad)" : d < 65 ? "var(--warn)" : "var(--good)";
            return (
              <div className="scroll-row" key={i}>
                <div className="scroll-path" title={p.url}>{shortUrl(p.url)}</div>
                <Progress pct={d} color={color} />
                <div className="scroll-val" style={{ color }}>{fmt(d)}%</div>
              </div>
            );
          })}
        </div>
      </Card>
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 6: Keyword Intelligence ---- */
function Keywords({ mod }: { mod: ModuleResult }) {
  const opps = arr(mod.opportunities);
  const bc = n(mod.brand_clicks), nbc = n(mod.non_brand_clicks);
  const brandPct = n(mod.brand_click_pct);
  return (
    <div>
      <Title mod={mod} fallback="Keyword Intelligence" />
      <div className="two-col">
        <Card title="Branded vs non-branded clicks">
          <div className="donut-row">
            <Donut
              size={140}
              segments={[
                { label: "Branded", value: bc, color: "var(--accent)" },
                { label: "Non-branded", value: nbc, color: "var(--good)" },
              ]}
              center={<><div className="donut-big">{fmt(bc + nbc)}</div><div className="donut-small">clicks</div></>}
            />
            <div className="legend">
              <div className="lg"><span className="dot" style={{ background: "var(--accent)" }} />Branded <b>{brandPct}%</b> ({fmt(bc)})</div>
              <div className="lg"><span className="dot" style={{ background: "var(--good)" }} />Non-branded <b>{fmt(100 - brandPct)}%</b> ({fmt(nbc)})</div>
              <div className="muted" style={{ marginTop: 6 }}>Higher non-branded = healthier organic discovery.</div>
            </div>
          </div>
        </Card>
        <Card title="Striking distance (pos 4–20)" sub={`${arr(mod.opportunities).length} opportunities`}>
          <HBars
            data={opps.slice(0, 6).map((o) => ({
              label: o.query, value: n(o.impressions), sub: `pos ${fmt(o.position)}`,
            }))}
            fmtValue={(v) => `${fmt(v)} impr`}
          />
        </Card>
      </div>
      {opps.length > 0 && (
        <Card title="Top keyword opportunities">
          <div className="table-scroll"><table className="data">
            <thead><tr><th>Query</th><th>Position</th><th>Impressions</th><th>Clicks now</th><th>Potential</th><th>Uplift</th></tr></thead>
            <tbody>
              {opps.slice(0, 12).map((o, i) => (
                <tr key={i}>
                  <td>{o.query}</td><td>{fmt(o.position)}</td><td>{fmt(o.impressions)}</td>
                  <td>{fmt(o.current_clicks)}</td><td>{fmt(o.potential_clicks)}</td>
                  <td className="pos">+{fmt(o.click_uplift)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 6b: Cannibalization (fixes the [object Object] bug) ---- */
function Cannibalization({ mod }: { mod: ModuleResult }) {
  const conflicts = arr(mod.conflicts);
  return (
    <div>
      <Title mod={mod} fallback="Keyword Cannibalization" />
      {conflicts.length === 0 && <Card><div className="muted">No cannibalization detected — clean URL-to-topic mapping.</div></Card>}
      {conflicts.slice(0, 8).map((c, i) => (
        <Card key={i}>
          <div className="cann-head">
            <div><span className="cann-q">"{c.query}"</span> <span className="badge">{c.severity}</span></div>
            <div className="muted">{fmt(c.total_impressions)} impressions · winner has {fmt(c.winner_click_share)}% of clicks</div>
          </div>
          <div className="table-scroll"><table className="data">
            <thead><tr><th>Competing page</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Position</th></tr></thead>
            <tbody>
              {arr(c.competing_pages).map((p: any, j: number) => (
                <tr key={j}>
                  <td>{shortUrl(p.page)} {p.page === c.winner && <span className="badge win">winner</span>}</td>
                  <td>{fmt(p.clicks)}</td><td>{fmt(p.impressions)}</td>
                  <td>{(n(p.ctr) * 100).toFixed(1)}%</td><td>{fmt(p.position)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      ))}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 7: UX & Speed Audit ---- */
function UxAudit({ mod }: { mod: ModuleResult }) {
  const rows = arr(mod.audit_rows);
  const cwv = (v: unknown, good: number, poor: number, unit: string) => {
    const x = n(v); const cls = x <= good ? "good" : x <= poor ? "warn" : "bad";
    return <span className={cls}>{v == null ? "—" : `${fmt(v)}${unit}`}</span>;
  };
  return (
    <div>
      <Title mod={mod} fallback="Declining Pages UX & Speed Audit" />
      {rows.map((r, i) => (
        <Card key={i}>
          <div className="ux-row">
            <ScoreRing score={n(r.pagespeed_score)} label="PageSpeed" />
            <div className="ux-body">
              <div className="ux-path" title={r.page}>{shortUrl(r.page)}</div>
              <div className="ux-sub">
                sessions <span className={n(r.session_change_pct) >= 0 ? "pos" : "neg"}>
                  {n(r.session_change_pct) > 0 ? "+" : ""}{fmt(r.session_change_pct)}%</span>
                {r.avg_position != null && <> · avg rank {fmt(r.avg_position)}</>}
                {r.risk_level && <> · <span className="badge">{r.risk_level}</span></>}
              </div>
              <div className="cwv-row">
                <div className="cwv"><span className="cwv-k">LCP</span>{cwv(r.crux_lcp ?? r.lcp, 2.5, 4, "s")}</div>
                <div className="cwv"><span className="cwv-k">CLS</span>{cwv(r.crux_cls ?? r.cls, 0.1, 0.25, "")}</div>
                <div className="cwv"><span className="cwv-k">INP</span>{cwv(r.crux_inp ?? r.inp, 200, 500, "ms")}</div>
                <div className="cwv"><span className="cwv-k">Dead/Rage</span><span className="neg">{n(r.dead_clicks)}/{n(r.rage_clicks)}</span></div>
              </div>
            </div>
          </div>
        </Card>
      ))}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 8: Hidden Insights ---- */
function Hidden({ mod }: { mod: ModuleResult }) {
  const groups: [any, string, string, any[], string][] = [
    [Ghost, "Zombie Pages", "High impressions, low CTR — rewrite titles/meta", arr(mod.zombies), "warn"],
    [GemIcon, "Unexplored Gems", "High engagement, low visibility — needs SEO push", arr(mod.gems), "up"],
    [Frown, "Friction Cash Cows", "Convert but frustrate — needs CRO fixes", arr(mod.cows), "down"],
  ];
  return (
    <div>
      <Title mod={mod} fallback="Hidden Growth Insights" />
      {groups.map(([Icon, t, sub, items, tone]) => (
        <div className="card" key={t}>
          <h2 style={{ fontSize: 15, display: "flex", alignItems: "center", gap: 8 }}>
            <Icon size={16} /> {t} ({items.length})
          </h2>
          <div className="muted" style={{ marginBottom: 4 }}>{sub}</div>
          <div className="pc-grid">
            {items.slice(0, 6).map((p: any, i: number) => (
              <div className={`pcard ${tone}`} key={i}>
                <div className="pcard-path" title={p.page}>{shortUrl(p.page)}</div>
                <div className="pcard-metrics">
                  {p.impressions != null && <span className="muted">{fmt(p.impressions)} impr</span>}
                  {p.ctr != null && <span className="muted">{(n(p.ctr) * 100).toFixed(1)}% CTR</span>}
                  {p.dead_clicks != null && <span className="neg">{fmt(p.dead_clicks)} dead</span>}
                  {p.avg_scroll_percent != null && <span className="muted">{fmt(p.avg_scroll_percent)}% scroll</span>}
                </div>
              </div>
            ))}
            {items.length === 0 && <div className="muted">None found.</div>}
          </div>
        </div>
      ))}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 9: Indexation ---- */
function Indexation({ mod }: { mod: ModuleResult }) {
  const submitted = n(mod.submitted_urls), indexed = n(mod.indexed_urls), rate = n(mod.indexation_rate);
  const sitemaps = arr(mod.sitemaps);
  const color = rate >= 90 ? "var(--good)" : rate >= 75 ? "var(--warn)" : "var(--bad)";
  return (
    <div>
      <Title mod={mod} fallback="Indexation & Technical Health" />
      <div className="two-col">
        <Card title="Indexation rate">
          <div className="donut-row">
            <Donut size={140}
              segments={[
                { label: "Indexed", value: indexed, color },
                { label: "Not indexed", value: Math.max(0, submitted - indexed), color: "var(--line)" },
              ]}
              center={<><div className="donut-big" style={{ color }}>{fmt(rate)}%</div><div className="donut-small">indexed</div></>}
            />
            <div className="legend">
              <div className="lg"><span className="dot" style={{ background: color }} />Indexed <b>{fmt(indexed)}</b></div>
              <div className="lg"><span className="dot" style={{ background: "var(--line)" }} />Unindexed <b>{fmt(mod.unindexed_urls)}</b></div>
            </div>
          </div>
        </Card>
        <Card title="Crawl status">
          <StatTiles tiles={[
            { k: "Submitted", v: fmt(submitted) },
            { k: "Crawled · not indexed", v: fmt(mod.crawled_not_indexed), cls: "bad" },
            { k: "Discovered · not indexed", v: fmt(mod.discovered_not_indexed), cls: "bad" },
          ]} />
        </Card>
      </div>
      {sitemaps.length > 0 && (
        <Card title="Sitemaps">
          <div className="table-scroll"><table className="data">
            <thead><tr><th>Sitemap</th><th>Submitted</th><th>Indexed</th><th>Rate</th></tr></thead>
            <tbody>
              {sitemaps.map((s: any, i: number) => (
                <tr key={i}><td>{s.path}</td><td>{fmt(s.submitted)}</td><td>{fmt(s.indexed)}</td>
                  <td>{s.submitted ? Math.round((s.indexed / s.submitted) * 100) : 0}%</td></tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}
      <Narrative mod={mod} />
    </div>
  );
}

const VIEWS: Record<string, (p: { mod: ModuleResult; results: Results }) => JSX.Element> = {
  organic: Organic, funnel: Funnel, heatmap: Heatmap, scroll: Scroll,
  keywords: Keywords, cannibalization: Cannibalization, ux_audit: UxAudit,
  hidden_insights: Hidden, indexation: Indexation,
};

export function ModuleRouter({ tab, results, label }: { tab: string; results: Results; label: string }) {
  const mod = results[tab] as ModuleResult | undefined;
  if (!mod) return <div className="empty">No data for this module.</div>;
  const View = VIEWS[tab];
  return View ? <View mod={mod} results={results} /> : <ModuleView mod={mod} label={label} />;
}
