import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { LayoutDashboard, ListChecks, Search, LogOut, Download, History as HistoryIcon, Menu, Shield } from "lucide-react";
import { USE_MOCK, api, type RunProgress } from "../api";
import { MODULE_ORDER, type Client, type Results, type User } from "../types";
import { ActionPlan } from "./ActionPlan";
import { Card, Delta, Progress, StatTiles, fmt } from "./viz";
import { Admin } from "./Admin";
import { DateRange, type Range, presetRange } from "./DateRange";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { SchbangLogo } from "./Logo";
import { ModuleRouter } from "./ModuleViews";
import { OnPage } from "./OnPage";
import { Select } from "./Select";

type Tab = "exec" | "actions" | (typeof MODULE_ORDER)[number]["key"] | "onpage" | "admin";

const nn = (v: unknown) => (typeof v === "number" ? v : Number(v) || 0);

/* "Since last report" — the diff nobody wants to eyeball manually. */
function SinceLastReport({ cur, prev }: { cur: Results; prev: Results }) {
  const pct = (a: number, b: number) => (b ? Math.round(((a - b) / b) * 1000) / 10 : 0);
  const sessions = nn(cur.organic?.total_sessions), prevSessions = nn(prev.organic?.total_sessions);
  const top3 = (cur.keywords?.bands as any)?.["1-3"]?.length;
  const prevTop3 = (prev.keywords?.bands as any)?.["1-3"]?.length;
  const striking = nn(cur.keyword_opportunities?.total_count), prevStriking = nn(prev.keyword_opportunities?.total_count);
  const idx = nn(cur.indexation?.indexation_rate), prevIdx = nn(prev.indexation?.indexation_rate);
  const curLosers = ((cur.organic?.losers as any[]) || []).map((p) => p.page);
  const prevLosers = new Set(((prev.organic?.losers as any[]) || []).map((p) => p.page));
  const newDecliners = curLosers.filter((p) => !prevLosers.has(p)).slice(0, 4);
  const prevMeta = prev._meta || {};
  return (
    <Card
      title="Since last report"
      sub={`Compared with the ${prevMeta.start_date && prevMeta.end_date ? `${prevMeta.start_date} → ${prevMeta.end_date}` : "previous"} run`}
    >
      <StatTiles tiles={[
        { k: "Organic sessions", v: <>{fmt(sessions)} <Delta value={pct(sessions, prevSessions)} /></> },
        ...(top3 != null && prevTop3 != null
          ? [{ k: "Top-3 keywords", v: <>{fmt(top3)} <Delta value={top3 - prevTop3} suffix="" /></> }]
          : []),
        { k: "Striking-distance", v: <>{fmt(striking)} <Delta value={striking - prevStriking} suffix="" /></> },
        { k: "Indexation rate", v: <>{fmt(idx)}% <Delta value={Math.round((idx - prevIdx) * 10) / 10} /></> },
      ]} />
      {newDecliners.length > 0 && (
        <div className="muted" style={{ marginTop: 10 }}>
          Newly declining since last run: {newDecliners.join(" · ")}
        </div>
      )}
    </Card>
  );
}

const relTime = (iso?: string) => {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};

export function Dashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState<string>("");
  const [range, setRange] = useState<Range>(presetRange(30));
  const [results, setResults] = useState<Results | null>(null);
  const [status, setStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<Tab>("exec");
  const [history, setHistory] = useState<any[]>([]);
  const [navOpen, setNavOpen] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [loadedReportId, setLoadedReportId] = useState<string | null>(null);
  const [prevResults, setPrevResults] = useState<Results | null>(null);

  const loadHistory = useCallback(() => {
    api.history().then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    api.clients().then((c) => {
      setClients(c);
      if (c[0]) setClientId(c[0].id);
    });
    loadHistory();
  }, [loadHistory]);

  const activeClient = useMemo(() => clients.find((c) => c.id === clientId), [clients, clientId]);

  // Start each tab at the top — otherwise deep scroll positions carry over.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [tab]);

  // Escape closes the mobile nav drawer.
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [navOpen]);

  async function run() {
    setRunning(true);
    setResults(null);
    setError("");
    setProgress(null);
    setLoadedReportId(null);
    setPrevResults(null);
    setTab("exec");
    // Snapshot the latest finished run for this client BEFORE this run lands in
    // history — it becomes the "since last report" comparison baseline.
    const prevRec = history.find((h) => h.status === "done" && h.client_id === clientId);
    try {
      const r = await api.runReport(clientId, range, setStatus, setProgress);
      setResults(r);
      loadHistory();
      if (prevRec) api.getReport(prevRec.id).then((p) => setPrevResults(p)).catch(() => {});
    } catch (e) {
      setError(`Report failed: ${(e as Error).message}`);
    } finally {
      setRunning(false);
      setProgress(null);
    }
  }

  async function openReport(id: string) {
    setRunning(true); setResults(null); setError(""); setPrevResults(null); setTab("exec");
    setStatus("Loading saved report…");
    try {
      const r = await api.getReport(id);
      if (r) {
        setResults(r);
        setLoadedReportId(id);
        const rec = history.find((h) => h.id === id);
        const prevRec = rec && history.find(
          (h) => h.status === "done" && h.client_id === rec.client_id && h.created_at < rec.created_at,
        );
        if (prevRec) api.getReport(prevRec.id).then((p) => setPrevResults(p)).catch(() => {});
      } else setError("This report has no saved results.");
    } catch (e) {
      setError(`Couldn't load the report: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="shell">
      {navOpen && <div className="nav-scrim" onClick={() => setNavOpen(false)} aria-hidden />}
      <aside
        className={`sidebar ${navOpen ? "open" : ""}`}
        onClick={(e) => {
          // Any nav action inside the drawer closes it (no-op on desktop).
          if ((e.target as HTMLElement).closest("button")) setNavOpen(false);
        }}
      >
        <SchbangLogo size={38} />

        <div className="nav-label">Report</div>
        <button className={`nav-item ${tab === "exec" ? "active" : ""}`} onClick={() => setTab("exec")}>
          <span className="ico"><LayoutDashboard size={17} /></span> Executive Summary
        </button>
        <button className={`nav-item ${tab === "actions" ? "active" : ""}`} onClick={() => setTab("actions")} disabled={!results}>
          <span className="ico"><ListChecks size={17} /></span> Action Plan
        </button>

        {MODULE_ORDER.map((m, i) => (
          <Fragment key={m.key as string}>
            {(i === 0 || MODULE_ORDER[i - 1].group !== m.group) && (
              <div className="nav-label">{m.group}</div>
            )}
            <button
              className={`nav-item ${tab === m.key ? "active" : ""}`}
              onClick={() => setTab(m.key as Tab)}
              disabled={!results}
            >
              <span className="ico"><m.Icon size={17} /></span> {m.label}
            </button>
          </Fragment>
        ))}

        <div className="nav-label">Tools</div>
        <button className={`nav-item ${tab === "onpage" ? "active" : ""}`} onClick={() => setTab("onpage")}>
          <span className="ico"><Search size={17} /></span> On-Page SEO
        </button>
        {user.role === "admin" && (
          <button className={`nav-item ${tab === "admin" ? "active" : ""}`} onClick={() => setTab("admin")}>
            <span className="ico"><Shield size={17} /></span> Admin
          </button>
        )}

        {history.length > 0 && (
          <>
            <div className="nav-label">History</div>
            <div className="history-list">
              {history.slice(0, 12).map((h) => (
                <button
                  className={`hist-item ${loadedReportId === h.id ? "active" : ""}`}
                  key={h.id}
                  onClick={() => openReport(h.id)}
                  disabled={h.status !== "done"}
                  title={h.created_at ? `Generated ${relTime(h.created_at)} · ${h.created_at.slice(0, 16).replace("T", " ")}` : undefined}
                >
                  <HistoryIcon size={13} className="hist-ico" />
                  <span className="hist-body">
                    <span className="hist-name">{h.client_name}</span>
                    <span className="hist-meta">
                      {h.start_date && h.end_date ? `${h.start_date} → ${h.end_date}` : relTime(h.created_at)}
                      {h.status !== "done" ? ` · ${h.status}` : ""}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </>
        )}

        <div style={{ flex: 1, minHeight: 20 }} />
        <button className="nav-item" onClick={onLogout}>
          <span className="ico"><LogOut size={17} /></span> Sign out
        </button>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <button className="nav-toggle no-print" onClick={() => setNavOpen(true)} aria-label="Open menu">
              <Menu size={19} />
            </button>
            <div>
              <h1 className="page-title">Growth Dashboard</h1>
              <div className="page-sub">{activeClient ? activeClient.display_name : "Select a client to begin"}</div>
            </div>
          </div>
          <div className="user-chip">
            <div className="who">
              <div className="n">{user.name}</div>
              <div className="r">{user.role}</div>
            </div>
            <div className="avatar">{user.name.slice(0, 1).toUpperCase()}</div>
          </div>
        </div>

        {USE_MOCK && (
          <div className="banner">
            Demo mode — sample data (no backend). Set <code>VITE_USE_MOCK=true</code> off for the live API.
          </div>
        )}

        {tab !== "onpage" && tab !== "admin" && (
          <>
            <div className="controls">
              <div className="field client-field">
                <label>Client</label>
                <Select
                  value={clientId}
                  onChange={setClientId}
                  options={clients.map((c) => ({ value: c.id, label: c.display_name }))}
                  placeholder="Choose client"
                />
              </div>
              <div className="field range-field">
                <label>Date range</label>
                <DateRange value={range} onChange={setRange} />
              </div>
              <button className="btn sm run-btn" onClick={run} disabled={running || !clientId}>
                {running ? <><span className="spinner" />&nbsp; Running…</> : "Run Report"}
              </button>
            </div>
            {activeClient && (
              <div style={{ marginBottom: 18 }}>
                <span className={`pill ${activeClient.use_demo_data ? "demo" : "live"}`}>
                  {activeClient.use_demo_data ? "DEMO" : "LIVE"}
                  {activeClient.ga4_property_id_masked ? ` · GA4 ${activeClient.ga4_property_id_masked}` : ""}
                </span>
              </div>
            )}
          </>
        )}

        {running && (
          progress ? (
            <div className="card run-progress">
              <div className="rp-top">
                <span className="spinner" />
                <span>Running <strong>{progress.label}</strong></span>
                <span className="rp-count">{progress.i + 1} of {progress.t}</span>
              </div>
              <Progress pct={(progress.i / progress.t) * 100} />
            </div>
          ) : (
            <div className="empty"><span className="spinner" />&nbsp; {status}</div>
          )
        )}

        {!running && error && tab !== "onpage" && tab !== "admin" && (
          <div className="banner error">{error}</div>
        )}

        {!running && !results && !error && tab !== "onpage" && (
          <div className="empty">Choose a client and click <strong>Run Report</strong> to generate the 10-module analysis.</div>
        )}

        {/* Executive Summary = one full-page report: exec + every module stacked */}
        {!running && results && tab === "exec" && (
          <div className="report-page">
            {(results._meta?.errors?.length ?? 0) > 0 && (
              <div className="banner warn no-print">
                <strong>Partial data:</strong> some sources failed for this run — {results._meta!.errors!.join(" · ")}
              </div>
            )}
            {prevResults && <SinceLastReport cur={results} prev={prevResults} />}
            <ExecutiveSummary exec={results.exec} meta={results._meta} />
            {MODULE_ORDER.map((m) => (
              <div key={m.key as string} style={{ marginTop: 8 }}>
                <ModuleRouter tab={String(m.key)} results={results} label={m.label} />
              </div>
            ))}
            <div className="report-actions report-actions-bottom no-print">
              <button className="btn ghost" onClick={() => window.print()}>
                <Download size={15} /> &nbsp;Download PDF
              </button>
            </div>
          </div>
        )}

        {!running && results && tab === "actions" && <ActionPlan results={results} />}

        {!running && results && tab !== "exec" && tab !== "actions" && tab !== "onpage" && tab !== "admin" && (
          <ModuleRouter tab={String(tab)} results={results} label={MODULE_ORDER.find((m) => m.key === tab)?.label || String(tab)} />
        )}

        {tab === "onpage" && <OnPage />}
        {tab === "admin" && user.role === "admin" && <Admin />}
      </main>
    </div>
  );
}
