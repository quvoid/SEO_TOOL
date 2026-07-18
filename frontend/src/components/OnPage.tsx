import { useState } from "react";
import { Search } from "lucide-react";
import { api } from "../api";
import { Markdown } from "./Markdown";
import { ScoreRing, fmt } from "./viz";

export function OnPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<{ blueprint: string; pagespeed?: Record<string, unknown> } | null>(null);

  async function run() {
    if (!url.trim()) return;
    setLoading(true); setErr(""); setResult(null);
    try {
      const r = await api.onpage(url.trim());
      setResult(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const ps = result?.pagespeed || {};
  return (
    <div>
      <h1 className="section-title">On-Page SEO Optimizer</h1>
      <div className="card">
        <div className="muted" style={{ marginBottom: 12 }}>
          Enter a page URL to generate an AI on-page blueprint (title/meta, headings, content gaps, Core Web Vitals).
        </div>
        <div className="onpage-row">
          <input
            className="onpage-input"
            type="url"
            placeholder="https://www.ultratechcement.com/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
          />
          <button className="btn sm" onClick={run} disabled={loading || !url.trim()}>
            {loading ? <><span className="spinner" />&nbsp; Analyzing…</> : <><Search size={15} /> &nbsp;Analyze</>}
          </button>
        </div>
        {err && <div className="banner" style={{ marginTop: 12, color: "var(--bad)" }}>Error: {err}</div>}
      </div>

      {result && (
        <>
          {ps.performance_score != null && (
            <div className="card">
              <h2 style={{ fontSize: 15 }}>PageSpeed</h2>
              <div className="ux-row" style={{ marginTop: 8 }}>
                <ScoreRing score={Number(ps.performance_score)} label="Performance" />
                <div className="cwv-row">
                  {ps.lcp != null && <div className="cwv"><span className="cwv-k">LCP</span>{fmt(ps.lcp)}s</div>}
                  {ps.cls != null && <div className="cwv"><span className="cwv-k">CLS</span>{fmt(ps.cls)}</div>}
                  {ps.inp != null && <div className="cwv"><span className="cwv-k">INP</span>{fmt(ps.inp)}ms</div>}
                </div>
              </div>
            </div>
          )}
          <div className="card">
            <Markdown>{result.blueprint}</Markdown>
          </div>
        </>
      )}
    </div>
  );
}
