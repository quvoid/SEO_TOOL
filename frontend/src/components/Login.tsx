import { USE_MOCK, api } from "../api";
import { SchbangLogo } from "./Logo";

export function Login({ onDemo }: { onDemo: () => void }) {
  return (
    <div className="login-wrap">
      <div className="login-card">
        <SchbangLogo />
        <div className="login-title" style={{ marginTop: 20 }}>AI Growth Analyst</div>
        <div className="login-company">Schbang Analytics Platform</div>
        <div className="login-desc">
          Unified GA4 · Search Console · Keyword Intelligence, powered by AI — for Schbang teams only.
        </div>

        {USE_MOCK ? (
          <button className="btn" onClick={onDemo}>Continue in Demo Mode</button>
        ) : (
          <a className="btn" href={api.loginUrl()}>Sign in with Google</a>
        )}

        <p className="login-lock">
          {USE_MOCK ? "Demo mode — no backend required" : "Restricted to @schbang.com accounts"}
        </p>
      </div>
    </div>
  );
}
