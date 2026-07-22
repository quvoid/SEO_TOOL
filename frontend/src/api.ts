// API client. In mock mode it returns sample data with no network calls so the
// UI can be verified standalone. Otherwise it talks to the FastAPI backend via
// the /api proxy (cookies are sent automatically with credentials: "include").
import { MOCK_CLIENTS, MOCK_RESULTS, MOCK_USER } from "./mock";
import { MODULE_ORDER, type Client, type Results, type User } from "./types";

export interface RunProgress {
  i: number;
  t: number;
  label: string;
}

// Live by default (production). Opt INTO demo data with VITE_USE_MOCK=true.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface Account {
  role: string;
  permissions: string[];
  serper: { balance: number | null; used: number; remaining: number | null };
}

export const api = {
  async me(): Promise<User> {
    if (USE_MOCK) return MOCK_USER;
    return req<User>("/auth/me");
  },

  async account(): Promise<Account> {
    if (USE_MOCK) {
      return {
        role: "admin",
        permissions: ["Run reports for any brand", "Manage members & access", "Add / edit Google credentials", "Add / remove brands"],
        serper: { balance: 2500, used: 40, remaining: 2460 },
      };
    }
    return req<Account>("/auth/account");
  },

  loginUrl(): string {
    return "/api/auth/login";
  },

  async logout(): Promise<void> {
    if (USE_MOCK) return;
    await req("/auth/logout", { method: "POST" });
  },

  async clients(): Promise<Client[]> {
    if (USE_MOCK) return MOCK_CLIENTS;
    return req<Client[]>("/clients");
  },

  // Kick off a report and poll until done. In mock mode, simulate the pipeline.
  async runReport(
    clientId: string,
    range: { start: string; end: string; compareMode?: "auto" | "custom"; compareStart?: string; compareEnd?: string },
    onStatus?: (s: string) => void,
    onProgress?: (p: RunProgress | null) => void,
  ): Promise<Results> {
    if (USE_MOCK) {
      const labels = [...MODULE_ORDER.map((m) => m.label), "Executive Summary"];
      for (let i = 0; i < labels.length; i++) {
        onStatus?.(`Running — ${labels[i]}…`);
        onProgress?.({ i, t: labels.length, label: labels[i] });
        await delay(350);
      }
      return MOCK_RESULTS;
    }
    const body: Record<string, unknown> = { client_id: clientId, start_date: range.start, end_date: range.end };
    if (range.compareMode === "custom" && range.compareStart && range.compareEnd) {
      body.compare_start = range.compareStart;
      body.compare_end = range.compareEnd;
    }
    const { id } = await req<{ id: string }>("/reports", { method: "POST", body: JSON.stringify(body) });
    // Poll
    for (;;) {
      await delay(2500);
      const r = await req<{ status: string; results?: Results; error?: string; progress?: RunProgress }>(`/reports/${id}`);
      onStatus?.(`Status: ${r.status}…`);
      onProgress?.(r.progress ?? null);
      if (r.status === "done" && r.results) return r.results;
      if (r.status === "failed") throw new Error(r.error || "Report failed");
    }
  },

  async history(): Promise<any[]> {
    if (USE_MOCK) return [];
    return req<any[]>("/reports");
  },

  // ---- admin ----
  adminUsers: () => req<any[]>("/admin/users"),
  adminAddUser: (email: string, role: string) =>
    req("/admin/users", { method: "POST", body: JSON.stringify({ email, role }) }),
  adminUpdateUser: (id: string, patch: { role?: string; is_active?: boolean }) =>
    req(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  adminCredentials: () => req<any[]>("/admin/credentials"),
  adminAddCredential: (body: { label: string; client_id: string; client_secret: string; refresh_token: string }) =>
    req("/admin/credentials", { method: "POST", body: JSON.stringify(body) }),
  adminAddBrand: (body: Record<string, unknown>) =>
    req("/admin/clients", { method: "POST", body: JSON.stringify(body) }),
  adminDeleteBrand: (id: string) => req(`/admin/clients/${id}`, { method: "DELETE" }),

  async getReport(id: string): Promise<Results | null> {
    if (USE_MOCK) return MOCK_RESULTS;
    const r = await req<{ status: string; results?: Results }>(`/reports/${id}`);
    return r.results || null;
  },

  async onpage(url: string): Promise<{ url: string; blueprint: string; pagespeed?: Record<string, unknown> }> {
    if (USE_MOCK) {
      await delay(800);
      return {
        url,
        blueprint: `## On-Page SEO Blueprint for ${url}\n\n### Title & Meta\n- Rewrite the title to lead with the primary keyword.\n- Meta description under 155 chars with a clear CTA.\n\n### Headings\n- Use a single H1; add H2s for each subtopic.\n\n### Core Web Vitals\n- Compress the hero image; defer non-critical JS.`,
        pagespeed: { performance_score: 62, lcp: 3.1, cls: 0.08 },
      };
    }
    return req("/onpage", { method: "POST", body: JSON.stringify({ url }) });
  },
};
