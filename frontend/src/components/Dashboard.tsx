import { useEffect, useMemo, useState } from "react";
import { USE_MOCK, api } from "../api";
import { MODULE_ORDER, type Client, type Results, type User } from "../types";
import { DateRange, type Range, presetRange } from "./DateRange";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { SchbangLogo } from "./Logo";
import { ModuleRouter } from "./ModuleViews";
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

  useEffect(() => {
    api.clients().then((c) => {
      setClients(c);
      if (c[0]) setClientId(c[0].id);
    });
  }, []);

  const activeClient = useMemo(() => clients.find((c) => c.id === clientId), [clients, clientId]);

  async function run() {
    setRunning(true);
    setResults(null);
    setTab("exec");
    try {
      const r = await api.runReport(clientId, range, setStatus);
      setResults(r);
    } catch (e) {
      setStatus(`Error: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <SchbangLogo />

        <div className="nav-label">Report</div>
        <button className={`nav-item ${tab === "exec" ? "active" : ""}`} onClick={() => setTab("exec")}>
          <span className="ico">◆</span> Executive Summary
        </button>

        <div className="nav-label">Modules</div>
        {MODULE_ORDER.map((m) => (
          <button
            key={m.key as string}
            className={`nav-item ${tab === m.key ? "active" : ""}`}
            onClick={() => setTab(m.key as Tab)}
            disabled={!results}
          >
            <span className="ico">{m.icon}</span> {m.label}
          </button>
        ))}

        <div className="nav-label">Tools</div>
        <button className={`nav-item ${tab === "onpage" ? "active" : ""}`} onClick={() => setTab("onpage")}>
          <span className="ico">◇</span> On-Page SEO
        </button>

        <div style={{ flex: 1, minHeight: 20 }} />
        <button className="nav-item" onClick={onLogout}>
          <span className="ico">→</span> Sign out
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
            Demo mode — sample data (no backend). Set <code>VITE_USE_MOCK=false</code> for the live API.
          </div>
        )}

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

        {running && <div className="empty"><span className="spinner" />&nbsp; {status}</div>}

        {!running && !results && tab !== "onpage" && (
          <div className="empty">Choose a client and click <strong>Run Report</strong> to generate the 10-module analysis.</div>
        )}

        {!running && results && tab === "exec" && <ExecutiveSummary exec={results.exec} meta={results._meta} />}

        {!running && results && tab !== "exec" && tab !== "onpage" && (
          <ModuleRouter tab={String(tab)} results={results} label={MODULE_ORDER.find((m) => m.key === tab)?.label || String(tab)} />
        )}

        {tab === "onpage" && (
          <div className="card">
            <h2>On-Page SEO Optimizer</h2>
            <p className="muted">
              Enter a URL to generate an AI on-page optimization blueprint (title/meta, headings, content gaps,
              Core Web Vitals). Wired to <code>POST /onpage</code>.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
