import { useEffect, useState } from "react";
import { UserPlus, KeyRound, Building2, Trash2 } from "lucide-react";
import { api } from "../api";

export function Admin() {
  const [users, setUsers] = useState<any[]>([]);
  const [creds, setCreds] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [msg, setMsg] = useState<string>("");

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
    try { await api.adminAddBrand({ ...b, organic_only: true }); setB({ display_name: "", ga4_property_id: "", gsc_site_url: "", credential_id: "" }); flash("Brand added"); load(); }
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
          <thead><tr><th>Brand</th><th>GA4</th><th>Account</th><th></th></tr></thead>
          <tbody>
            {clients.map((x) => (
              <tr key={x.id}>
                <td>{x.display_name}</td>
                <td>{x.ga4_property_id_masked || "—"}</td>
                <td>{x.credential_label || "—"}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn ghost" title="Delete brand"
                    onClick={() => confirm(`Delete ${x.display_name}?`) && api.adminDeleteBrand(x.id).then(load)}>
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
    </div>
  );
}
