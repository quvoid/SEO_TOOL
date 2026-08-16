import { useEffect, useState } from "react";
import { UserPlus, KeyRound, Building2, Trash2, Tag, Wand2 } from "lucide-react";
import { api } from "../api";

/**
 * Per-client branded-query terms.
 *
 * Left empty, brand terms are derived from the domain — which works for
 * bodycraft.co.in ("body craft") but cannot know hdfcbank.com is also searched
 * as plain "hdfc". Suggestions are mined from Search Console (navigational
 * queries have unmistakably high CTR at strong positions) but are never applied
 * automatically: a false positive silently reclassifies real traffic.
 */
function BrandTermsEditor({ client, onSaved }: { client: any; onSaved: () => void }) {
  const [terms, setTerms] = useState<string>(client.brand_terms || "");
  const [sugg, setSugg] = useState<{ term: string; clicks: number; queries: number; partial?: boolean }[]>([]);
  const [reason, setReason] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchSuggestions = async () => {
    setBusy(true);
    try {
      const r = await api.adminBrandSuggestions(client.id);
      setSugg(r.suggestions || []);
      setReason(r.reason || (r.suggestions?.length ? "" : "No additional brand-like queries found."));
    } catch (e) { setReason((e as Error).message); }
    finally { setBusy(false); }
  };

  const add = (t: string) => {
    const list = terms.split(",").map((s) => s.trim()).filter(Boolean);
    if (!list.some((x) => x.toLowerCase() === t.toLowerCase())) list.push(t);
    setTerms(list.join(", "));
  };

  const save = async () => {
    setSaving(true);
    try { await api.adminUpdateBrand(client.id, { brand_terms: terms }); onSaved(); }
    finally { setSaving(false); }
  };

  return (
    <div className="card" style={{ marginTop: 12, background: "var(--bg-2)" }}>
      <h2 style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 7 }}>
        <Tag size={14} /> Branded queries — {client.display_name}
      </h2>
      <div className="muted" style={{ marginBottom: 10 }}>
        Comma-separated variants, including misspellings and other scripts. Leave blank to
        derive them from the domain.
      </div>
      <input className="onpage-input" style={{ width: "100%" }}
             placeholder="e.g. hdfc, hdfc bank, hdfcbank"
             value={terms} onChange={(e) => setTerms(e.target.value)} />
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn sm" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
        <button className="btn ghost sm" onClick={fetchSuggestions} disabled={busy}>
          <Wand2 size={13} /> {busy ? "Scanning…" : "Suggest from Search Console"}
        </button>
      </div>
      {reason && <div className="muted" style={{ marginTop: 9, fontSize: 12 }}>{reason}</div>}
      {sugg.length > 0 && (
        <div style={{ marginTop: 11 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 7 }}>
            Terms related to your domain that the automatic pattern misses. The number
            is the traffic each would reclassify as brand — click to add:
          </div>
          <div className="chip-row">
            {sugg.map((s) => (
              <button className={`chip ${s.partial ? "warn" : ""}`} key={s.term} onClick={() => add(s.term)}
                      title={s.partial
                        ? `Fragment of your domain — check it isn't an ordinary word. Would move ${s.queries} queries / ${s.clicks} clicks into brand.`
                        : `Would move ${s.queries} queries / ${s.clicks} clicks into brand.`}
                      style={{ cursor: "pointer" }}>
                <b>{s.term}</b> {s.clicks.toLocaleString()} clicks
              </button>
            ))}
          </div>
          {sugg.some((s) => s.partial) && (
            <div className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>
              Amber chips are fragments of your domain name. They catch shortened brand
              searches (<code>hdfc</code> for hdfcbank), but a fragment that is also a
              common word (<code>body</code> for bodycraft) would wrongly pull generic
              traffic into brand. Check before adding.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function Admin({ onClientsChanged }: { onClientsChanged?: () => void } = {}) {
  const [users, setUsers] = useState<any[]>([]);
  const [creds, setCreds] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [msg, setMsg] = useState<string>("");
  const [editing, setEditing] = useState<string | null>(null);

  const load = () => {
    api.adminUsers().then(setUsers).catch(() => {});
    api.adminCredentials().then(setCreds).catch(() => {});
    api.clients().then(setClients).catch(() => {});
  };
  useEffect(load, []);

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 3500); };

  // --- forms ---
  const [uEmail, setUEmail] = useState(""); const [uRole, setURole] = useState("analyst");
  const [c, setC] = useState({ label: "", client_id: "", client_secret: "", refresh_token: "" });
  const [b, setB] = useState({ display_name: "", ga4_property_id: "", gsc_site_url: "", credential_id: "" });

  async function addUser() {
    try { await api.adminAddUser(uEmail.trim(), uRole); setUEmail(""); flash("Member added"); load(); }
    catch (e) { flash("Error: " + (e as Error).message); }
  }
  async function addCred() {
    try { await api.adminAddCredential(c); setC({ label: "", client_id: "", client_secret: "", refresh_token: "" }); flash("Gmail account added"); load(); }
    catch (e) { flash("Error: " + (e as Error).message); }
  }
  async function addBrand() {
    try { await api.adminAddBrand({ ...b, organic_only: true }); setB({ display_name: "", ga4_property_id: "", gsc_site_url: "", credential_id: "" }); flash("Brand added"); load(); onClientsChanged?.(); }
    catch (e) { flash("Error: " + (e as Error).message); }
  }

  return (
    <div>
      <h1 className="section-title">Admin</h1>
      {msg && <div className="banner">{msg}</div>}

      {/* Members */}
      <div className="card">
        <h2 style={{ fontSize: 15, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={16} /> Team members</h2>
        <div className="muted" style={{ marginBottom: 12 }}>Add a @schbang.com Gmail and a role. They sign in with Google to get access. Only admins see this panel.</div>
        <div className="admin-form">
          <input className="onpage-input" placeholder="name@schbang.com" value={uEmail} onChange={(e) => setUEmail(e.target.value)} />
          <select className="cmp-select" value={uRole} onChange={(e) => setURole(e.target.value)}>
            <option value="analyst">Member</option>
            <option value="admin">Admin</option>
          </select>
          <button className="btn sm" onClick={addUser} disabled={!uEmail.trim()}>Add member</button>
        </div>
        <div className="table-scroll"><table className="data" style={{ marginTop: 14 }}>
          <thead><tr><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.role === "admin" ? "Admin" : "Member"}</td>
                <td>{u.is_active ? <span className="pos">active</span> : <span className="muted">disabled</span>}</td>
                <td style={{ textAlign: "right" }}>
                  {u.role !== "admin" && (
                    <button className="btn ghost" onClick={() => api.adminUpdateUser(u.id, { is_active: !u.is_active }).then(load)}>
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>

      {/* Gmail accounts */}
      <div className="card">
        <h2 style={{ fontSize: 15, display: "flex", alignItems: "center", gap: 8 }}><KeyRound size={16} /> Google (Gmail) accounts</h2>
        <div className="muted" style={{ marginBottom: 12 }}>
          A data-source account whose GA4/GSC properties you want to analyze. Paste its OAuth <code>client_id</code>,
          <code>client_secret</code> and <code>refresh_token</code> (read-only GA4 + Search Console scopes).
          Generate the refresh token once signed in as that Gmail — see the note below.
        </div>
        <div className="admin-grid">
          <input className="onpage-input" placeholder="Label (e.g. brand-team gmail)" value={c.label} onChange={(e) => setC({ ...c, label: e.target.value })} />
          <input className="onpage-input" placeholder="OAuth client_id" value={c.client_id} onChange={(e) => setC({ ...c, client_id: e.target.value })} />
          <input className="onpage-input" placeholder="OAuth client_secret" value={c.client_secret} onChange={(e) => setC({ ...c, client_secret: e.target.value })} />
          <input className="onpage-input" placeholder="refresh_token" value={c.refresh_token} onChange={(e) => setC({ ...c, refresh_token: e.target.value })} />
        </div>
        <button className="btn sm" style={{ marginTop: 10 }} onClick={addCred} disabled={!c.client_id || !c.refresh_token}>Add account</button>
        <div className="table-scroll"><table className="data" style={{ marginTop: 14 }}>
          <thead><tr><th>Label</th><th>Type</th><th>Brands</th></tr></thead>
          <tbody>{creds.map((x) => <tr key={x.id}><td>{x.label}</td><td>{x.kind}</td><td>{x.brand_count}</td></tr>)}</tbody>
        </table></div>
      </div>

      {/* Brands */}
      <div className="card">
        <h2 style={{ fontSize: 15, display: "flex", alignItems: "center", gap: 8 }}><Building2 size={16} /> Brands</h2>
        <div className="muted" style={{ marginBottom: 12 }}>Add a brand and link it to the Gmail account that can read its GA4/GSC. It appears in everyone's client dropdown.</div>
        <div className="admin-grid">
          <input className="onpage-input" placeholder="Brand name" value={b.display_name} onChange={(e) => setB({ ...b, display_name: e.target.value })} />
          <input className="onpage-input" placeholder="GA4 property ID" value={b.ga4_property_id} onChange={(e) => setB({ ...b, ga4_property_id: e.target.value })} />
          <input className="onpage-input" placeholder="GSC site URL (https://…)" value={b.gsc_site_url} onChange={(e) => setB({ ...b, gsc_site_url: e.target.value })} />
          <select className="cmp-select" value={b.credential_id} onChange={(e) => setB({ ...b, credential_id: e.target.value })}>
            <option value="">— Gmail account —</option>
            {creds.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
          </select>
        </div>
        <button className="btn sm" style={{ marginTop: 10 }} onClick={addBrand} disabled={!b.display_name || !b.credential_id}>Add brand</button>
        <div className="table-scroll"><table className="data" style={{ marginTop: 14 }}>
          <thead><tr><th>Brand</th><th>GA4</th><th>Account</th><th>Brand terms</th><th></th></tr></thead>
          <tbody>
            {clients.map((x) => (
              <tr key={x.id}>
                <td>{x.display_name}</td>
                <td>{x.ga4_property_id_masked || "—"}</td>
                <td>{x.credential_label || "—"}</td>
                <td>
                  <button className="btn ghost sm" title="Edit branded-query terms"
                    onClick={() => setEditing(editing === x.id ? null : x.id)}>
                    <Tag size={13} /> {x.brand_terms ? "custom" : "auto"}
                  </button>
                </td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn ghost" title="Delete brand"
                    onClick={() => confirm(`Delete ${x.display_name}?`) && api.adminDeleteBrand(x.id).then(() => { load(); onClientsChanged?.(); })}>
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {editing && <BrandTermsEditor client={clients.find((c) => c.id === editing)!}
                                      onSaved={() => { setEditing(null); load(); flash("Brand terms saved"); }} />}
      </div>
    </div>
  );
}
