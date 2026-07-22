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
  path_exploration: {
    title: "Module — Path Exploration",
    starting_event: "session_start",
    starting_count: 3949333,
    total_events: 11004035,
    narrative:
      "The session_start → page_view flow is healthy (99% of sessions register a page view). The drop happens after the first page: only a small share reach engagement-style events, and conversion events (form_submit, file_download) are a tiny fraction. Highest-impact fix: surface a clear next action above the fold on landing pages to pull users from page_view into engagement.",
    steps: [
      { label: "Starting point", nodes: [{ event_name: "session_start", event_count: 3949333 }] },
      { label: "Step +1", nodes: [{ event_name: "page_view", event_count: 3895723 }] },
      {
        label: "Step +2",
        nodes: [
          { event_name: "user_engagement", event_count: 1780400 },
          { event_name: "scroll", event_count: 1253907 },
          { event_name: "view_search_results", event_count: 32283 },
          { event_name: "+5 More", event_count: 92620, is_rollup: true },
        ],
      },
    ],
    events: [
      { event_name: "page_view", event_count: 3895723, pct: 35.4 },
      { event_name: "session_start", event_count: 3949333, pct: 35.9 },
      { event_name: "user_engagement", event_count: 1780400, pct: 16.2 },
      { event_name: "scroll", event_count: 1253907, pct: 11.4 },
      { event_name: "first_visit", event_count: 39220, pct: 0.4 },
      { event_name: "view_search_results", event_count: 32283, pct: 0.3 },
      { event_name: "form_start", event_count: 21850, pct: 0.2 },
      { event_name: "click", event_count: 14399, pct: 0.1 },
      { event_name: "form_submit", event_count: 9120, pct: 0.1 },
      { event_name: "file_download", event_count: 4870, pct: 0.0 },
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
    bands: {
      "1-3": [
        { query: "ultratech cement price list", position: 2.1, impressions: 21000 },
        { query: "ultratech cement dealers", position: 2.8, impressions: 14000 },
        { query: "waterproofing cost india", position: 3.8, impressions: 12000 },
      ],
      "4-10": [
        { query: "waterproofing solutions", position: 4.2, impressions: 18400 },
        { query: "roof leakage repair", position: 5.5, impressions: 9800 },
        { query: "cement grades explained", position: 6.1, impressions: 42300 },
        { query: "best cement brand india", position: 9.1, impressions: 40000 },
      ],
      "11-20": [
        { query: "concrete mix ratio guide", position: 12.5, impressions: 15000 },
        { query: "waterproofing solution for terrace", position: 14.3, impressions: 11000 },
        { query: "cement plaster wall guide", position: 18.4, impressions: 6200 },
      ],
      "21-50": [
        { query: "load bearing wall construction", position: 22.3, impressions: 5400 },
        { query: "earthquake resistant house design", position: 31.5, impressions: 4800 },
      ],
    },
    new_queries: [
      { query: "monsoon roof protection", clicks: 140, impressions: 8200, position: 7.8 },
      { query: "cement price today india", clicks: 95, impressions: 6100, position: 9.2 },
      { query: "सीमेंट की कीमत", clicks: 210, impressions: 6800, position: 4.9 },
    ],
    lost_queries: [
      { query: "terrace waterproofing tips", clicks: 180, impressions: 9500, position: 7.2 },
      { query: "site leveling cost per sqft", clicks: 95, impressions: 4100, position: 16.8 },
    ],
    opportunities: [
      { query: "waterproofing solutions", position: 4.2, impressions: 18400, current_clicks: 640, potential_clicks: 2100, click_uplift: 1460 },
      { query: "cement grades explained", position: 6.1, impressions: 42300, current_clicks: 210, potential_clicks: 3800, click_uplift: 3590 },
      { query: "roof leakage repair", position: 5.5, impressions: 9800, current_clicks: 300, potential_clicks: 1200, click_uplift: 900 },
    ],
  },
  keyword_opportunities: {
    title: "Top Keyword Opportunities",
    regional_filter_regex: ".[^ -~].",
    total_count: 7,
    regional_count: 3,
    total_uplift: 9860,
    regional_uplift: 1290,
    narrative:
      "The biggest overall quick win is 'cement grades explained' (42k impressions at pos 6.1). On the regional side, three Indian-language cement queries sit in striking distance with strong CTR already — a dedicated vernacular content + hreflang play could capture under-served demand that English pages don't rank for.",
    opportunities: [
      { query: "cement grades explained", position: 6.1, impressions: 42300, current_clicks: 210, potential_clicks: 4230, click_uplift: 4020, is_regional: false },
      { query: "waterproofing solutions", position: 4.2, impressions: 18400, current_clicks: 640, potential_clicks: 1840, click_uplift: 1200, is_regional: false },
      { query: "best cement brand india", position: 9.1, impressions: 40000, current_clicks: 480, potential_clicks: 4000, click_uplift: 3520, is_regional: false },
      { query: "अल्ट्राटेक cement", position: 4.9, impressions: 6800, current_clicks: 260, potential_clicks: 680, click_uplift: 420, is_regional: true },
      { query: "அல்ட்ரா cement", position: 5.4, impressions: 5200, current_clicks: 180, potential_clicks: 520, click_uplift: 340, is_regional: true },
      { query: "అల్ట్రా cement", position: 6.8, impressions: 4300, current_clicks: 145, potential_clicks: 430, click_uplift: 285, is_regional: true },
      { query: "roof leakage repair", position: 5.5, impressions: 9800, current_clicks: 300, potential_clicks: 980, click_uplift: 680, is_regional: false },
    ],
  },
  uplift: {
    title: "Uplift Tracker — The Middle Band",
    narrative:
      "The single biggest middle-band win is /roof-leakage-solutions: position 4.3 but CTR 3.0% vs 7.0% expected — a title/meta rewrite worth ~3,800 clicks. Live SERP checks show three middle keywords within 1–2 positions of page one dominance; drfixit.co.in and civilread.com are the competitors to displace. Content team owns the CTR fixes, SEO owns the internal-link pushes.",
    total_clicks_lost: 4210,
    tracked_queries: 4,
    ctr_gap: [
      { page: "/roof-leakage-solutions", position: 4.3, impressions: 95000, ctr_pct: 3.0, expected_ctr_pct: 7.0, clicks_lost: 3800 },
      { page: "/cement-grades", position: 6.1, impressions: 42300, ctr_pct: 3.1, expected_ctr_pct: 4.0, clicks_lost: 380 },
      { page: "/vastu-tips", position: 8.9, impressions: 28100, ctr_pct: 1.9, expected_ctr_pct: 2.0, clicks_lost: 30 },
    ],
    flatliners: [
      { page: "/home-loans", sessions: 7200, delta_pct: 2.9, impressions: 41000, position: 6.2, ctr_pct: 5.1 },
      { page: "/foundation-info", sessions: 3100, delta_pct: 1.6, impressions: 18000, position: 9.8, ctr_pct: 2.1 },
    ],
    serp_tracker: [
      { query: "best cement brand india", gsc_position: 9.1, live_position: 8, delta: 1.1, checked_gl: "in",
        competitors_above: [
          { position: 1, domain: "acc.in", title: "ACC Cement" },
          { position: 2, domain: "ambujacement.com", title: "Ambuja Cement" },
          { position: 3, domain: "jkcement.com", title: "JK Super Cement" }] },
      { query: "concrete mix ratio guide", gsc_position: 12.5, live_position: 11, delta: 1.5, checked_gl: "in",
        competitors_above: [
          { position: 1, domain: "civilread.com", title: "Concrete Mix Ratios" },
          { position: 2, domain: "theconstructor.org", title: "Grades of Concrete" }] },
      { query: "waterproofing solution for terrace", gsc_position: 14.3, live_position: 13, delta: 1.3, checked_gl: "in",
        competitors_above: [
          { position: 1, domain: "drfixit.co.in", title: "Terrace Waterproofing" },
          { position: 2, domain: "asianpaints.com", title: "SmartCare Terrace" }] },
      { query: "cement plaster wall guide", gsc_position: 18.4, live_position: null, delta: null, checked_gl: "in",
        competitors_above: [
          { position: 1, domain: "civiljungle.com", title: "Wall Plastering Guide" },
          { position: 2, domain: "happho.com", title: "Cement Plastering Steps" }] },
    ],
    internal_links: [
      { query: "best cement brand india", target: "/best-cement-guide", anchor: "best cement brand india",
        sources: [{ page: "/house-construction-guide", clicks: 390 }, { page: "/foundation-info", clicks: 115 }] },
      { query: "waterproofing solution for terrace", target: "/roof-leakage-solutions", anchor: "terrace waterproofing solution",
        sources: [{ page: "/waterproofing", clicks: 505 }] },
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
      { page: "/roof-leakage-solutions", session_change_pct: -34, sessions: 2600, avg_position: 8.2, pagespeed_score: null, lcp: null, cls: null, inp: null, crux_lcp: null, crux_cls: null, crux_inp: null, dead_clicks: 96, rage_clicks: 12, risk_level: "🟡 Medium" },
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
      "Of 12,400 submitted URLs, only ~4,050 receive Search impressions — a large index-bloat gap. Most of the unseen URLs are thin tag/param pages worth a noindex to reclaim crawl budget.",
    submitted_urls: 12400,
    indexed_urls: 4050,
    unindexed_urls: 8350,
    indexation_rate: 32.7,
    pages_in_search: 4050,
    indexed_source: "search_impressions",
    sitemap_indexed_available: false,
    crawled_not_indexed: 0,
    discovered_not_indexed: 0,
    sitemaps: [
      { path: "https://www.example.com/sitemap-pages.xml", submitted: 5200, indexed: 0 },
      { path: "https://www.example.com/sitemap-blog.xml", submitted: 7200, indexed: 0 },
    ],
  },
};
