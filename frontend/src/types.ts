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
  compare_start?: string | null;
  compare_end?: string | null;
  clarity_available?: boolean;
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

import {
  TrendingUp, Route, Filter, MousePointerClick, ScrollText, KeyRound,
  Swords, Zap, Gem, FileStack, type LucideIcon,
} from "lucide-react";

// The ordered module tabs — mirrors the Streamlit module structure exactly.
export const MODULE_ORDER: { key: keyof Results; label: string; Icon: LucideIcon }[] = [
  { key: "organic", label: "Organic Performance", Icon: TrendingUp },
  { key: "journey", label: "User Journey", Icon: Route },
  { key: "funnel", label: "Funnel Drop-off", Icon: Filter },
  { key: "heatmap", label: "Heatmap / Click", Icon: MousePointerClick },
  { key: "scroll", label: "Scroll Analysis", Icon: ScrollText },
  { key: "keywords", label: "Keyword Intelligence", Icon: KeyRound },
  { key: "cannibalization", label: "Cannibalization", Icon: Swords },
  { key: "ux_audit", label: "UX & Speed Audit", Icon: Zap },
  { key: "hidden_insights", label: "Hidden Insights", Icon: Gem },
  { key: "indexation", label: "Indexation Health", Icon: FileStack },
];
