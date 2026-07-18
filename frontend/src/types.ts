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
  path_exploration?: ModuleResult;
  funnel?: ModuleResult;
  heatmap?: ModuleResult;
  scroll?: ModuleResult;
  keywords?: ModuleResult;
  keyword_opportunities?: ModuleResult;
  uplift?: ModuleResult;
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
  TrendingUp, Route, Waypoints, Filter, MousePointerClick, ScrollText, KeyRound,
  Target, Crosshair, Swords, Zap, Gem, FileStack, type LucideIcon,
} from "lucide-react";

// The ordered module tabs — mirrors the Streamlit module structure exactly.
// `group` drives the sidebar section labels.
export const MODULE_ORDER: { key: keyof Results; label: string; Icon: LucideIcon; group: string }[] = [
  { key: "organic", label: "Organic Performance", Icon: TrendingUp, group: "Performance" },
  { key: "journey", label: "User Journey", Icon: Route, group: "Performance" },
  { key: "path_exploration", label: "Path Exploration", Icon: Waypoints, group: "Performance" },
  { key: "funnel", label: "Funnel Drop-off", Icon: Filter, group: "Performance" },
  { key: "heatmap", label: "Heatmap / Click", Icon: MousePointerClick, group: "Engagement" },
  { key: "scroll", label: "Scroll Analysis", Icon: ScrollText, group: "Engagement" },
  { key: "keywords", label: "Keyword Intelligence", Icon: KeyRound, group: "Keywords" },
  { key: "keyword_opportunities", label: "Top Keyword Opportunity", Icon: Target, group: "Keywords" },
  { key: "uplift", label: "Uplift Tracker", Icon: Crosshair, group: "Keywords" },
  { key: "cannibalization", label: "Cannibalization", Icon: Swords, group: "Keywords" },
  { key: "ux_audit", label: "UX & Speed Audit", Icon: Zap, group: "Health" },
  { key: "hidden_insights", label: "Hidden Insights", Icon: Gem, group: "Health" },
  { key: "indexation", label: "Indexation Health", Icon: FileStack, group: "Health" },
];
