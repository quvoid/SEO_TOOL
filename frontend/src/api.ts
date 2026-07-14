// API client. In mock mode it returns sample data with no network calls so the
// UI can be verified standalone. Otherwise it talks to the FastAPI backend via
// the /api proxy (cookies are sent automatically with credentials: "include").
import { MOCK_CLIENTS, MOCK_RESULTS, MOCK_USER } from "./mock";
import type { Client, Results, User } from "./types";

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

export const api = {
  async me(): Promise<User> {
    if (USE_MOCK) return MOCK_USER;
    return req<User>("/auth/me");
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
  ): Promise<Results> {
    if (USE_MOCK) {
      const steps = ["Organic Performance", "User Journey", "Keyword Intelligence", "UX & Speed Audit", "Executive Summary"];
      for (const s of steps) {
        onStatus?.(`Running — ${s}…`);
        await delay(500);
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
      const r = await req<{ status: string; results?: Results; error?: string }>(`/reports/${id}`);
      onStatus?.(`Status: ${r.status}…`);
      if (r.status === "done" && r.results) return r.results;
      if (r.status === "failed") throw new Error(r.error || "Report failed");
    }
  },
};
