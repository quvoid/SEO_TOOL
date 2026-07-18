// Data-driven visual views per module. These bind to the STRUCTURED fields each
// analysis module computes (not the AI narrative), so they render even when the
// AI quota is exhausted. Falls back to the generic ModuleView for unknowns.
import { useState } from "react";
import { Ghost, Gem as GemIcon, Frown, Info, ArrowUp, ArrowDown } from "lucide-react";
import type { ModuleResult, Results } from "../types";
import { cleanTitle } from "../util";
import { Markdown } from "./Markdown";
import { ModuleView } from "./ModuleView";
import { Card, Delta, Donut, HBars, Progress, ScoreRing, SortTh, StatTiles, fmt, useSort } from "./viz";
import { Select } from "./Select";

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

function ClarityFallback({ what }: { what: string }) {
  return (
    <div className="banner" style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
      <Info size={15} style={{ marginTop: 1, flexShrink: 0 }} />
      <span>Microsoft Clarity isn't connected for this client, so {what} isn't available. Connect Clarity to unlock it.</span>
    </div>
  );
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
function Heatmap({ mod, results }: { mod: ModuleResult; results: Results }) {
  const flagged = arr(mod.flagged);
  const clarityOk = results._meta?.clarity_available !== false;
  const totalDead = flagged.reduce((s, c) => s + n(c.dead_clicks), 0);
  const totalRage = flagged.reduce((s, c) => s + n(c.rage_clicks), 0);
  const totalQuick = flagged.reduce((s, c) => s + n(c.quickback_clicks), 0);
  if (!clarityOk) {
    return (
      <div>
        <Title mod={mod} fallback="Heatmap / Click" />
        <ClarityFallback what="click-frustration (dead/rage clicks) data" />
      </div>
    );
  }
  return (
    <div>
      <Title mod={mod} fallback="Heatmap / Click" />
      <Card>
        <StatTiles tiles={[
          { k: "Pages with friction", v: fmt(flagged.length) },
          { k: <span title="Clicks on elements that aren't interactive — users expected them to do something">Dead clicks</span>, v: fmt(totalDead), cls: "bad" },
          { k: <span title="Rapid repeated clicks on the same spot — a frustration signal">Rage clicks</span>, v: fmt(totalRage), cls: "bad" },
          { k: <span title="Users who navigated back to the previous page almost immediately">Quick-backs</span>, v: fmt(totalQuick), cls: "bad" },
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
type ScrollKey = "avg_scroll_percent" | "sessions" | "active_users";
function Scroll({ mod }: { mod: ModuleResult }) {
  // Normalize both the new shape (pages) and the old shape (all_pages: {url,total_sessions}).
  const raw = arr(mod.pages).length ? arr(mod.pages) : arr(mod.all_pages);
  const pages = raw.map((p) => ({
    page: p.page ?? p.url ?? "",
    avg_scroll_percent: p.avg_scroll_percent ?? null,
    sessions: p.sessions ?? p.total_sessions ?? 0,
    active_users: p.active_users ?? 0,
  }));
  const clarityOk = mod.clarity_available !== false && pages.some((p) => p.avg_scroll_percent != null);
  const [sortKey, setSortKey] = useState<ScrollKey>(clarityOk ? "avg_scroll_percent" : "sessions");
  const [dir, setDir] = useState<"asc" | "desc">(clarityOk ? "asc" : "desc");

  const sorted = [...pages].sort((a, b) => {
    const av = n(a[sortKey]), bv = n(b[sortKey]);
    return dir === "asc" ? av - bv : bv - av;
  }).slice(0, 25);

  const clickSort = (k: ScrollKey) => {
    if (sortKey === k) setDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setDir(k === "avg_scroll_percent" ? "asc" : "desc"); }
  };
  const Arrow = () => (dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />);
  const Th = ({ k, children }: { k: ScrollKey; children: any }) => (
    <th className={`sortable ${sortKey === k ? "active" : ""}`} onClick={() => clickSort(k)}>
      <span className="th-inner">{children} {sortKey === k && <Arrow />}</span>
    </th>
  );

  return (
    <div>
      <Title mod={mod} fallback="Scroll Analysis" />
      {!clarityOk && <ClarityFallback what="scroll-depth data" />}
      <Card title="Pages by engagement" sub="Click a column to sort ascending / descending">
        <div className="table-scroll"><table className="data num">
          <thead><tr>
            <th>Page</th>
            <Th k="avg_scroll_percent">Scroll depth</Th>
            <Th k="sessions">Organic sessions</Th>
            <Th k="active_users">Active users</Th>
          </tr></thead>
          <tbody>
            {sorted.map((p, i) => {
              const d = p.avg_scroll_percent;
              const color = d == null ? "var(--txt-faint)" : d < 40 ? "var(--bad)" : d < 65 ? "var(--warn)" : "var(--good)";
              return (
                <tr key={i}>
                  <td title={p.page}>{shortUrl(p.page)}</td>
                  <td style={{ minWidth: 160 }}>
                    {d == null ? <span className="muted">—</span> : (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ flex: 1 }}><Progress pct={n(d)} color={color} /></div>
                        <span style={{ color, fontWeight: 700 }}>{fmt(d)}%</span>
                      </div>
                    )}
                  </td>
                  <td>{fmt(p.sessions)}</td>
                  <td>{fmt(p.active_users)}</td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      </Card>
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 6: Keyword Intelligence ---- */
function Keywords({ mod }: { mod: ModuleResult }) {
  const opps = arr(mod.opportunities);
  const { sorted: sortedOpps, sort } = useSort(opps, "click_uplift");
  const bc = n(mod.brand_clicks), nbc = n(mod.non_brand_clicks);
  const brandPct = n(mod.brand_click_pct);
  const bands = (mod.bands || {}) as Record<string, any[]>;
  const bandOrder: [string, string][] = [
    ["1-3", "Top 3 — winning"], ["4-10", "4–10 — quick wins"],
    ["11-20", "11–20 — page-2 purgatory"], ["21-50", "21–50 — long haul"],
  ];
  const hasBands = bandOrder.some(([k]) => arr(bands[k]).length > 0);
  const newQ = arr(mod.new_queries), lostQ = arr(mod.lost_queries);
  const QueryList = ({ items, tone }: { items: any[]; tone: "up" | "down" }) => (
    <div className="pc-grid">
      {items.slice(0, 8).map((q, i) => (
        <div className={`pcard ${tone}`} key={i}>
          <div className="pcard-path" title={q.query}>{q.query}</div>
          <div className="pcard-metrics">
            <span className="muted">{fmt(q.impressions)} impr</span>
            {q.position != null && <span className="muted">pos {fmt(q.position)}</span>}
          </div>
        </div>
      ))}
      {items.length === 0 && <div className="muted">None.</div>}
    </div>
  );
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
        <Card
          title={<span title="Keywords ranking 4–20 — close enough to reach the top 3 with on-page optimisation">Striking distance (pos 4–20)</span>}
          sub={`${arr(mod.opportunities).length} opportunities`}
        >
          <HBars
            data={opps.slice(0, 6).map((o) => ({
              label: o.query, value: n(o.impressions), sub: `pos ${fmt(o.position)}`,
            }))}
            fmtValue={(v) => `${fmt(v)} impr`}
          />
        </Card>
      </div>
      {hasBands && (
        <Card title="Position distribution" sub="Where your queries rank — the middle bands are the highest-ROI targets">
          <HBars
            data={bandOrder.map(([k, label]) => ({
              label, value: arr(bands[k]).length,
              color: k === "4-10" || k === "11-20" ? "var(--warn)" : k === "1-3" ? "var(--good)" : "var(--line)",
              sub: arr(bands[k]).slice(0, 2).map((q) => q.query).join(" · "),
            }))}
            fmtValue={(v) => `${fmt(v)} queries`}
          />
        </Card>
      )}
      {(newQ.length > 0 || lostQ.length > 0) && (
        <div className="two-col">
          <Card title={`▲ New queries (${newQ.length})`} sub="Ranking now, absent last period"><QueryList items={newQ} tone="up" /></Card>
          <Card title={`▼ Lost queries (${lostQ.length})`} sub="Ranked last period, gone now — investigate"><QueryList items={lostQ} tone="down" /></Card>
        </div>
      )}
      {opps.length > 0 && (
        <Card title="Top keyword opportunities" sub="Click a column to sort">
          <div className="table-scroll"><table className="data num">
            <thead><tr>
              <SortTh k="query" sort={sort}>Query</SortTh>
              <SortTh k="position" sort={sort}>Position</SortTh>
              <SortTh k="impressions" sort={sort}>Impressions</SortTh>
              <SortTh k="current_clicks" sort={sort}>Clicks now</SortTh>
              <SortTh k="potential_clicks" sort={sort}>Potential</SortTh>
              <SortTh k="click_uplift" sort={sort}>Uplift</SortTh>
            </tr></thead>
            <tbody>
              {sortedOpps.slice(0, 12).map((o: any, i: number) => (
                <tr key={i}>
                  <td className="trunc" title={o.query}>{o.query}</td>
                  <td>{fmt(o.position)}</td><td>{fmt(o.impressions)}</td>
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
          <div className="table-scroll"><table className="data num">
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
                <div className="cwv"><span className="cwv-k" title="Largest Contentful Paint — how fast the main content loads. Good ≤ 2.5s">LCP</span>{cwv(r.crux_lcp ?? r.lcp, 2.5, 4, "s")}</div>
                <div className="cwv"><span className="cwv-k" title="Cumulative Layout Shift — visual stability while loading. Good ≤ 0.1">CLS</span>{cwv(r.crux_cls ?? r.cls, 0.1, 0.25, "")}</div>
                <div className="cwv"><span className="cwv-k" title="Interaction to Next Paint — how fast the page responds to input. Good ≤ 200ms">INP</span>{cwv(r.crux_inp ?? r.inp, 200, 500, "ms")}</div>
                <div className="cwv"><span className="cwv-k" title="Dead clicks: taps on non-interactive elements · Rage clicks: rapid repeated clicks out of frustration">Dead/Rage</span><span className="neg">{n(r.dead_clicks)}/{n(r.rage_clicks)}</span></div>
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
          <div className="table-scroll"><table className="data num">
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

/* ---- Module 2b: Path Exploration (GA4 event flow) ---- */
function PathExploration({ mod }: { mod: ModuleResult }) {
  const steps = arr(mod.steps);
  const events = arr(mod.events);
  const maxCount = Math.max(1, ...steps.flatMap((s) => arr(s.nodes).map((nd: any) => n(nd.event_count))));
  return (
    <div>
      <Title mod={mod} fallback="Path Exploration" />
      <Card>
        <StatTiles tiles={[
          { k: "Starting point", v: String(mod.starting_event ?? "—") },
          { k: "Start events", v: fmt(mod.starting_count) },
          { k: "Total events", v: fmt(mod.total_events) },
        ]} />
      </Card>
      <Card title="Event path flow" sub="session_start → page_view → the events users trigger next">
        <div className="path-flow">
          {steps.map((s, i) => (
            <div className="path-col" key={i}>
              <div className="path-col-label">{s.label}</div>
              {arr(s.nodes).map((node: any, j: number) => (
                <div className={`path-node ${node.is_rollup ? "rollup" : ""}`} key={j}>
                  <div className="path-node-top">
                    <span className="path-node-name" title={node.event_name}>{node.event_name}</span>
                    <span className="path-node-count">{fmt(node.event_count)}</span>
                  </div>
                  <div className="path-node-track">
                    <div className="path-node-fill" style={{ width: `${(n(node.event_count) / maxCount) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </Card>
      {events.length > 0 && (
        <Card title="Events by volume" sub="All events in the selected period (organic)">
          <HBars
            data={events.map((e) => ({ label: e.event_name, value: n(e.event_count), sub: `${fmt(e.pct)}%` }))}
            fmtValue={(v) => `${fmt(v)}`}
          />
        </Card>
      )}
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 6c: Top Keyword Opportunity (overall + regional filter) ---- */
function KeywordOpportunities({ mod }: { mod: ModuleResult }) {
  const [filter, setFilter] = useState<"overall" | "regional">("overall");
  const all = arr(mod.opportunities);
  const rows = filter === "regional" ? all.filter((o) => o.is_regional) : all;
  const { sorted, sort } = useSort(rows, "click_uplift");
  return (
    <div>
      <Title mod={mod} fallback="Top Keyword Opportunity" />
      <Card>
        <StatTiles tiles={[
          { k: "Opportunities", v: fmt(mod.total_count) },
          { k: "Indian-language", v: fmt(mod.regional_count) },
          { k: "Total click uplift", v: `+${fmt(mod.total_uplift)}`, cls: "good" },
        ]} />
      </Card>
      <Card
        title={<span title="Keywords ranking 4–20 — close enough to reach the top 3 with on-page optimisation">Striking-distance keywords (pos 4–20)</span>}
        sub={`${rows.length} shown · regional filter regex ${mod.regional_filter_regex ?? ".[^ -~]."} · click a column to sort`}
      >
        <div className="kw-filter">
          <label>Filter</label>
          <Select
            value={filter}
            onChange={(v) => setFilter(v as "overall" | "regional")}
            options={[
              { value: "overall", label: "Overall" },
              { value: "regional", label: "Indian language specific" },
            ]}
          />
        </div>
        {rows.length === 0 ? (
          <div className="muted" style={{ marginTop: 12 }}>
            {filter === "regional" ? "No regional-language keywords in the striking-distance band." : "No striking-distance opportunities found."}
          </div>
        ) : (
          <div className="table-scroll"><table className="data num">
            <thead><tr>
              <SortTh k="query" sort={sort}>Query</SortTh>
              <SortTh k="position" sort={sort}>Position</SortTh>
              <SortTh k="impressions" sort={sort}>Impressions</SortTh>
              <SortTh k="current_clicks" sort={sort}>Clicks now</SortTh>
              <SortTh k="potential_clicks" sort={sort}>Potential</SortTh>
              <SortTh k="click_uplift" sort={sort}>Uplift</SortTh>
            </tr></thead>
            <tbody>
              {sorted.slice(0, 25).map((o: any, i: number) => (
                <tr key={i}>
                  <td className="trunc" title={o.query}>{o.query} {o.is_regional && <span className="badge">regional</span>}</td>
                  <td>{fmt(o.position)}</td><td>{fmt(o.impressions)}</td>
                  <td>{fmt(o.current_clicks)}</td><td>{fmt(o.potential_clicks)}</td>
                  <td className="pos">+{fmt(o.click_uplift)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
      <Narrative mod={mod} />
    </div>
  );
}

/* ---- Module 6d: Uplift Tracker (the middle band) ---- */
function UpliftTracker({ mod }: { mod: ModuleResult }) {
  const ctrGap = arr(mod.ctr_gap);
  const flat = arr(mod.flatliners);
  const serp = arr(mod.serp_tracker);
  const links = arr(mod.internal_links);
  const { sorted: sortedGap, sort } = useSort(ctrGap, "clicks_lost");
  return (
    <div>
      <Title mod={mod} fallback="Uplift Tracker" />
      <Card>
        <StatTiles tiles={[
          { k: <span title="Pages earning less CTR than their ranking position should — a title/meta problem, not a ranking one">CTR-gap pages</span>, v: fmt(ctrGap.length) },
          { k: "Est. clicks lost", v: fmt(mod.total_clicks_lost), cls: "bad" },
          { k: <span title="Pages with flat traffic (±5%) but high impressions — stagnant potential nobody looks at">Flatliners</span>, v: fmt(flat.length) },
          { k: "Keywords live-tracked", v: fmt(mod.tracked_queries) },
        ]} />
      </Card>

      {serp.length > 0 && (
        <Card title="Live SERP check — middle keywords" sub="Real Google (India) positions via serper.dev · only pos 4–20 keywords worth uplifting are tracked">
          <div className="table-scroll"><table className="data num">
            <thead><tr><th>Query</th><th>GSC pos</th><th>Live pos</th><th>Δ</th><th style={{ textAlign: "left" }}>Ranking above you</th></tr></thead>
            <tbody>
              {serp.map((s: any, i: number) => (
                <tr key={i}>
                  <td className="trunc" title={s.query}>{s.query}</td>
                  <td>{s.gsc_position != null ? fmt(s.gsc_position) : "—"}</td>
                  <td>{s.live_position != null ? fmt(s.live_position) : <span className="muted" title="Not in the live top 10">&gt;10</span>}</td>
                  <td>{s.delta != null ? <Delta value={n(s.delta)} suffix="" /> : "—"}</td>
                  <td style={{ textAlign: "left" }} className="muted">
                    {arr(s.competitors_above).slice(0, 3).map((c: any) => c.domain).join(" · ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}

      {ctrGap.length > 0 && (
        <Card title="CTR gap — clicks you already earned but don't get" sub="CTR below the expected curve for the position · fix = title/meta rewrite, no ranking work needed">
          <div className="table-scroll"><table className="data num">
            <thead><tr>
              <SortTh k="page" sort={sort}>Page</SortTh>
              <SortTh k="position" sort={sort}>Position</SortTh>
              <SortTh k="impressions" sort={sort}>Impressions</SortTh>
              <SortTh k="ctr_pct" sort={sort}>CTR</SortTh>
              <SortTh k="expected_ctr_pct" sort={sort}>Expected</SortTh>
              <SortTh k="clicks_lost" sort={sort}>Clicks lost</SortTh>
            </tr></thead>
            <tbody>
              {sortedGap.map((c: any, i: number) => (
                <tr key={i}>
                  <td className="trunc" title={c.page}>{shortUrl(c.page)}</td>
                  <td>{fmt(c.position)}</td><td>{fmt(c.impressions)}</td>
                  <td className="neg">{fmt(c.ctr_pct)}%</td><td>{fmt(c.expected_ctr_pct)}%</td>
                  <td className="neg">−{fmt(c.clicks_lost)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}

      <div className="two-col">
        {flat.length > 0 && (
          <Card title="Flatliners" sub="±5% traffic, high impressions — stagnant potential">
            <div className="table-scroll"><table className="data num">
              <thead><tr><th>Page</th><th>Sessions</th><th>Δ</th><th>Impressions</th></tr></thead>
              <tbody>
                {flat.map((f: any, i: number) => (
                  <tr key={i}>
                    <td className="trunc" title={f.page}>{shortUrl(f.page)}</td>
                    <td>{fmt(f.sessions)}</td>
                    <td className="muted">{n(f.delta_pct) > 0 ? "+" : ""}{fmt(f.delta_pct)}%</td>
                    <td>{fmt(f.impressions)}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </Card>
        )}
        {links.length > 0 && (
          <Card title="Internal-link suggestions" sub="Authority pages that should link to your striking-distance pages">
            <div className="link-list">
              {links.map((l: any, i: number) => (
                <div className="link-sug" key={i}>
                  <div className="link-target"><span className="muted">Push</span> {shortUrl(l.target)} <span className="badge">"{l.anchor}"</span></div>
                  <div className="link-sources muted">
                    Link from: {arr(l.sources).map((s: any) => `${shortUrl(s.page)} (${fmt(s.clicks)} clicks)`).join(" · ")}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
      <Narrative mod={mod} />
    </div>
  );
}

const VIEWS: Record<string, (p: { mod: ModuleResult; results: Results }) => JSX.Element> = {
  organic: Organic, funnel: Funnel, heatmap: Heatmap, scroll: Scroll,
  keywords: Keywords, cannibalization: Cannibalization, ux_audit: UxAudit,
  hidden_insights: Hidden, indexation: Indexation,
  path_exploration: PathExploration, keyword_opportunities: KeywordOpportunities,
  uplift: UpliftTracker,
};

export function ModuleRouter({ tab, results, label }: { tab: string; results: Results; label: string }) {
  const mod = results[tab] as ModuleResult | undefined;
  if (!mod) return <div className="empty">No data for this module.</div>;
  const View = VIEWS[tab];
  return View ? <View mod={mod} results={results} /> : <ModuleView mod={mod} label={label} />;
}
