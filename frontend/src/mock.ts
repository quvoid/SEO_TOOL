// Sample data so the UI renders fully without a live backend.
// Shapes mirror analysis.py module return dicts.
import type { Client, Results, User } from "./types";

export const MOCK_USER: User = {
  id: "u_demo",
  email: "analytics.schbang@gmail.com",
  name: "Schbang Analytics",
  picture: "",
  role: "admin",
};

export const MOCK_CLIENTS: Client[] = [
  {
    id: "c_demo",
    display_name: "🎯 Demo — BuildMart (Sample Data)",
    gsc_site_url: "https://www.buildmart-demo.com/",
    organic_only: true,
    use_demo_data: true,
    credential_label: "analytics.schbang gmail",
    ga4_property_id_masked: null,
  },
  {
    id: "c_ultra",
    display_name: "Ultratech Cement",
    gsc_site_url: "https://www.ultratechcement.com/",
    organic_only: true,
    use_demo_data: false,
    credential_label: "analytics.schbang gmail",
    ga4_property_id_masked: "•••4846",
  },
];

export const MOCK_RESULTS: Results = {
  _meta: {
    site: "https://www.buildmart-demo.com/",
    is_demo: true,
    days: 30,
    generated: "2026-07-12 19:40",
    analyst: "Schbang Analytics",
    errors: [],
  },
  _ga4_totals: { current_total: 84210, prev_total: 91530 },
  exec: {
    title: "Module 10 — Executive Summary & Growth Strategy",
    key_points: [
      "Organic sessions -8% vs prior period.",
      "Biggest SEO issue: /roof-leakage-solutions sessions -34%.",
      "Biggest UX issue: /home-loans (bounce 71%, scroll 38%).",
      "PageSpeed: /house-construction-guide is slowest with 45% score.",
      "SEO Opportunity: '/cement-grades' is a Zombie page with 42,300 impressions but low CTR.",
    ],
    narrative:
      "### Executive Health Verdict\nOrganic demand is softening (-8%) driven by a handful of high-value pages losing rankings and speed regressions on mobile.\n\n### Top 3 Prioritised Actions\n1. **Fix Core Web Vitals** on /house-construction-guide (LCP 3.8s → <2.5s). Est. recover ~1,900 sessions/mo.\n2. **Rewrite title/meta** on /cement-grades to capture 42k impressions at higher CTR. Est. +600 clicks/mo.\n3. **Resolve cannibalization** between /roof-leakage-solutions and /waterproofing.\n\n### Month 1 — Speed & CRO Fixes\nMobile LCP/CLS fixes; eliminate rage/dead clicks on /home-loans; ship faster hero images.\n\n### Month 2 — Low-Hanging SEO Wins\nRewrite Zombie page titles; push positions 4–20 into top 3; internal linking.\n\n### Month 3 — Content Expansion\nBuild out unexplored gems; consolidate cannibalized URLs; earn authority links.",
  },
  organic: {
    title: "Module 1 — Organic Performance",
    overall_delta_pct: -8,
    total_sessions: 84210,
    total_prev_sessions: 91530,
    narrative:
      "Organic sessions declined 8% overall. The decline is concentrated in 3 pages where CTR fell while position held — a classic title/meta/snippet problem rather than an algorithmic hit. Prioritise snippet rewrites before assuming ranking loss.",
    losers: [
      { page: "/roof-leakage-solutions", session_delta_pct: -34, ctr_delta_pct: -22, position: 8.2, position_delta: 0.3 },
      { page: "/home-loans", session_delta_pct: -19, ctr_delta_pct: -11, position: 5.1, position_delta: -0.2 },
      { page: "/house-construction-guide", session_delta_pct: -14, ctr_delta_pct: -8, position: 6.7, position_delta: 0.1 },
    ],
    gainers: [
      { page: "/waterproofing", session_delta_pct: 21, ctr_delta_pct: 9, position: 3.4, position_delta: -1.1 },
      { page: "/cement-calculator", session_delta_pct: 12, ctr_delta_pct: 5, position: 2.8, position_delta: -0.4 },
    ],
  },
  journey: {
    title: "Module 2 — User Journey",
    narrative:
      "Two high-traffic pages show a bounce/scroll mismatch: users arrive but leave before engaging. /home-loans has 71% bounce with only 38% scroll depth — the value proposition is likely below the fold or load is too slow.",
    flagged: [
      { page: "/home-loans", bounce_rate: 0.71, scroll_percent: 38 },
      { page: "/roof-leakage-solutions", bounce_rate: 0.64, scroll_percent: 44 },
    ],
  },
  funnel: {
    title: "Module 3 — Funnel Drop-off",
    narrative:
      "Mobile funnel leaks hardest at the lead-form step. Desktop holds far better. The gap points to a mobile form UX issue — too many fields or a broken input on small screens.",
    overall_completion_pct: 14.2,
    biggest_drop: { step: "Lead Form", drop_pct: 44 },
    steps: [
      { step: "Landing", users: 10000, drop_pct: 0 },
      { step: "Product View", users: 6800, drop_pct: 32 },
      { step: "Lead Form", users: 3800, drop_pct: 44 },
      { step: "Submit", users: 1420, drop_pct: 63 },
    ],
    device_steps: {
      mobile: [
        { step: "Landing", users: 6200, drop_pct: 0 },
        { step: "Product View", users: 3900, drop_pct: 37 },
        { step: "Lead Form", users: 1500, drop_pct: 62 },
        { step: "Submit", users: 520, drop_pct: 65 },
      ],
      desktop: [
        { step: "Landing", users: 3800, drop_pct: 0 },
        { step: "Product View", users: 3100, drop_pct: 18 },
        { step: "Lead Form", users: 2700, drop_pct: 13 },
        { step: "Submit", users: 1480, drop_pct: 45 },
      ],
    },
  },
  heatmap: {
    title: "Module 4 — Heatmap / Click",
    narrative:
      "High dead-click volume on the hero CTA of /home-loans suggests users expect it to be clickable but it isn't wired, or the tap target is too small on mobile.",
    flagged: [
      { url: "/home-loans", dead_clicks: 214, rage_clicks: 47, quickback_clicks: 33, total_sessions: 4200 },
      { url: "/roof-leakage-solutions", dead_clicks: 96, rage_clicks: 12, quickback_clicks: 18, total_sessions: 2600 },
      { url: "/house-construction-guide", dead_clicks: 61, rage_clicks: 9, quickback_clicks: 11, total_sessions: 3100 },
    ],
  },
  scroll: {
    title: "Module 5 — Scroll Analysis",
    narrative:
      "On /house-construction-guide only 41% of users reach the mid-article CTA. Moving the primary CTA higher could lift conversions without new traffic.",
    all_pages: [
      { url: "/home-loans", avg_scroll_percent: 38, total_sessions: 4200 },
      { url: "/house-construction-guide", avg_scroll_percent: 41, total_sessions: 3100 },
      { url: "/roof-leakage-solutions", avg_scroll_percent: 58, total_sessions: 2600 },
      { url: "/waterproofing", avg_scroll_percent: 72, total_sessions: 1900 },
    ],
  },
  keywords: {
    title: "Module 6 — Keyword Intelligence",
    narrative:
      "Several non-branded keywords sit in positions 4–10 — the highest-ROI striking-distance band. Small on-page optimisations here can move them into the top 3.",
    brand_clicks: 12400,
    non_brand_clicks: 28600,
    brand_click_pct: 30.2,
    opportunities: [
      { query: "waterproofing solutions", position: 4.2, impressions: 18400, current_clicks: 640, potential_clicks: 2100, click_uplift: 1460 },
      { query: "cement grades explained", position: 6.1, impressions: 42300, current_clicks: 210, potential_clicks: 3800, click_uplift: 3590 },
      { query: "roof leakage repair", position: 5.5, impressions: 9800, current_clicks: 300, potential_clicks: 1200, click_uplift: 900 },
    ],
  },
  cannibalization: {
    title: "Module 6b — Keyword Cannibalization",
    narrative:
      "Two URLs compete for 'roof waterproofing'. Google alternates between them, splitting authority and suppressing both. Consolidate into one canonical page.",
    conflicts: [
      {
        query: "roof waterproofing",
        severity: "🔴 High",
        num_pages: 3,
        total_impressions: 15200,
        winner: "/waterproofing",
        winner_click_share: 48,
        competing_pages: [
          { page: "/waterproofing", clicks: 210, impressions: 7200, ctr: 0.029, position: 4.1 },
          { page: "/roof-leakage-solutions", clicks: 150, impressions: 5100, ctr: 0.029, position: 6.3 },
          { page: "/blog/roof-care", clicks: 78, impressions: 2900, ctr: 0.027, position: 9.8 },
        ],
      },
    ],
  },
  ux_audit: {
    title: "Module 7 — Declining Pages UX & Performance Audit",
    audit_rows: [
      { page: "/house-construction-guide", session_change_pct: -14, sessions: 3100, avg_position: 6.7, pagespeed_score: 45, lcp: 3.8, cls: 0.18, inp: 280, crux_lcp: 3.9, crux_cls: 0.19, crux_inp: 290, dead_clicks: 61, rage_clicks: 9, risk_level: "🔴 High" },
      { page: "/home-loans", session_change_pct: -19, sessions: 4200, avg_position: 5.1, pagespeed_score: 58, lcp: 3.1, cls: 0.09, inp: 190, crux_lcp: 3.2, crux_cls: 0.08, crux_inp: 180, dead_clicks: 214, rage_clicks: 47, risk_level: "🟡 Medium" },
      { page: "/roof-leakage-solutions", session_change_pct: -34, sessions: 2600, avg_position: 8.2, pagespeed_score: 63, lcp: 2.7, cls: 0.06, inp: 150, crux_lcp: 2.6, crux_cls: 0.05, crux_inp: 140, dead_clicks: 96, rage_clicks: 12, risk_level: "🟡 Medium" },
    ],
  },
  hidden_insights: {
    title: "Module 8 — Hidden Growth Insights",
    narrative:
      "Zombie pages (high impressions, low CTR) and Cash Cows (convert but frustrate) represent the fastest ROI.",
    zombies: [
      { page: "/cement-grades", impressions: 42300, ctr: 0.005 },
      { page: "/vastu-tips", impressions: 28100, ctr: 0.008 },
    ],
    gems: [{ page: "/waterproofing", avg_scroll_percent: 72 }],
    cows: [{ page: "/home-loans", dead_clicks: 214 }],
  },
  indexation: {
    title: "Module 9 — Indexation & Technical Health",
    narrative:
      "94% of submitted URLs are indexed. The 6% gap is mostly thin tag pages — worth a noindex to preserve crawl budget.",
    submitted_urls: 1240,
    indexed_urls: 1166,
    unindexed_urls: 74,
    indexation_rate: 94.0,
    crawled_not_indexed: 42,
    discovered_not_indexed: 32,
    sitemaps: [
      { path: "/sitemap-pages.xml", submitted: 520, indexed: 505 },
      { path: "/sitemap-blog.xml", submitted: 720, indexed: 661 },
    ],
  },
};
