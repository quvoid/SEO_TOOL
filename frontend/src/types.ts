// Shared types mirroring the backend contract.

export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
  role: string;
}

export interface Client {
  id: string;
  display_name: string;
  gsc_site_url: string;
  organic_only: boolean;
  use_demo_data: boolean;
  credential_label?: string | null;
  ga4_property_id_masked?: string | null;
}

// A module result is an open-ended dict: title + narrative + arbitrary tables/stats.
export type ModuleResult = Record<string, unknown> & {
  title?: string;
  narrative?: string;
  key_points?: string[];
};

export interface ReportMeta {
  site?: string;
  is_demo?: boolean;
  days?: number;
  start_date?: string | null;
  end_date?: string | null;
  generated?: string;
  analyst?: string;
  errors?: string[];
}

// The preserved 10-module results dict.
export interface Results {
  organic?: ModuleResult;
  journey?: ModuleResult;
  funnel?: ModuleResult;
  heatmap?: ModuleResult;
  scroll?: ModuleResult;
  keywords?: ModuleResult;
  cannibalization?: ModuleResult;
  ux_audit?: ModuleResult;
  hidden_insights?: ModuleResult;
  indexation?: ModuleResult;
  exec?: ModuleResult;
  _meta?: ReportMeta;
  _ga4_totals?: Record<string, unknown>;
  [k: string]: unknown;
}

// The ordered module tabs — mirrors the Streamlit module structure exactly.
export const MODULE_ORDER: { key: keyof Results; label: string; icon: string }[] = [
  { key: "organic", label: "Organic Performance", icon: "📈" },
  { key: "journey", label: "User Journey", icon: "🧭" },
  { key: "funnel", label: "Funnel Drop-off", icon: "🔻" },
  { key: "heatmap", label: "Heatmap / Click", icon: "🖱️" },
  { key: "scroll", label: "Scroll Analysis", icon: "📜" },
  { key: "keywords", label: "Keyword Intelligence", icon: "🔑" },
  { key: "cannibalization", label: "Cannibalization", icon: "⚔️" },
  { key: "ux_audit", label: "UX & Speed Audit", icon: "⚡" },
  { key: "hidden_insights", label: "Hidden Insights", icon: "💎" },
  { key: "indexation", label: "Indexation Health", icon: "🗂️" },
];
