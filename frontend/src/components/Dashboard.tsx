import { useCallback, useEffect, useMemo, useState } from "react";
import { LayoutDashboard, Search, LogOut, Download, History as HistoryIcon } from "lucide-react";
import { USE_MOCK, api } from "../api";
import { MODULE_ORDER, type Client, type Results, type User } from "../types";
import { DateRange, type Range, presetRange } from "./DateRange";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { SchbangLogo } from "./Logo";
import { ModuleRouter } from "./ModuleViews";
import { OnPage } from "./OnPage";
import { Select } from "./Select";

type Tab = "exec" | (typeof MODULE_ORDER)[number]["key"] | "onpage";

export function Dashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState<string>("");
  const [range, setRange] = useState<Range>(presetRange(30));
  const [results, setResults] = useState<Results | null>(null);
  const [status, setStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<Tab>("exec");
  const [history, setHistory] = useState<any[]>([]);

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

  async function run() {
    setRunning(true);
    setResults(null);
    setTab("exec");
    try {
      const r = await api.runReport(clientId, range, setStatus);
      setResults(r);
      loadHistory();
    } catch (e) {
      setStatus(`Error: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  }

  async function openReport(id: string) {
    setRunning(true); setResults(null); setTab("exec"); setStatus("Loading saved report…");
    try {
      const r = await api.getReport(id);
      if (r) setResults(r);
      else setStatus("This report has no saved results.");
    } catch (e) {
      setStatus(`Error: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <SchbangLogo size={38} />

        <div className="nav-label">Report</div>
        <button className={`nav-item ${tab === "exec" ? "active" : ""}`} onClick={() => setTab("exec")}>
          <span className="ico"><LayoutDashboard size={17} /></span> Executive Summary
        </button>

        <div className="nav-label">Modules</div>
        {MODULE_ORDER.map((m) => (
          <button
            key={m.key as string}
            className={`nav-item ${tab === m.key ? "active" : ""}`}
            onClick={() => setTab(m.key as Tab)}
            disabled={!results}
          >
            <span className="ico"><m.Icon size={17} /></span> {m.label}
          </button>
        ))}

        <div className="nav-label">Tools</div>
        <button className={`nav-item ${tab === "onpage" ? "active" : ""}`} onClick={() => setTab("onpage")}>
          <span className="ico"><Search size={17} /></span> On-Page SEO
        </button>

        {history.length > 0 && (
          <>
            <div className="nav-label">History</div>
            <div className="history-list">
              {history.slice(0, 12).map((h) => (
                <button className="hist-item" key={h.id} onClick={() => openReport(h.id)} disabled={h.status !== "done"}>
                  <HistoryIcon size={13} className="hist-ico" />
                  <span className="hist-body">
                    <span className="hist-name">{h.client_name}</span>
                    <span className="hist-meta">
                      {h.start_date && h.end_date ? `${h.start_date} → ${h.end_date}` : (h.created_at || "").slice(0, 10)}
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
          <div>
            <h1 className="page-title">Growth Dashboard</h1>
            <div className="page-sub">{activeClient ? activeClient.display_name : "Select a client to begin"}</div>
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

        {tab !== "onpage" && (
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

        {running && <div className="empty"><span className="spinner" />&nbsp; {status}</div>}

        {!running && !results && tab !== "onpage" && (
          <div className="empty">Choose a client and click <strong>Run Report</strong> to generate the 10-module analysis.</div>
        )}

        {/* Executive Summary = one full-page report: exec + every module stacked */}
        {!running && results && tab === "exec" && (
          <div className="report-page">
            <div className="report-actions no-print">
              <button className="btn ghost" onClick={() => window.print()}>
                <Download size={15} /> &nbsp;Download PDF
              </button>
            </div>
            <ExecutiveSummary exec={results.exec} meta={results._meta} />
            {MODULE_ORDER.map((m) => (
              <div key={m.key as string} style={{ marginTop: 8 }}>
                <ModuleRouter tab={String(m.key)} results={results} label={m.label} />
              </div>
            ))}
          </div>
        )}

        {!running && results && tab !== "exec" && tab !== "onpage" && (
          <ModuleRouter tab={String(tab)} results={results} label={MODULE_ORDER.find((m) => m.key === tab)?.label || String(tab)} />
        )}

        {tab === "onpage" && <OnPage />}
      </main>
    </div>
  );
}
