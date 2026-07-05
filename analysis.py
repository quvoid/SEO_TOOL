"""
analysis.py — Analysis modules + AI reasoning layer.

Each module is a pure function: takes already-fetched data (demo or live),
computes structured findings, then builds a Claude prompt for narrative.

Modules:
  1  Organic Performance Intelligence  (GA4 + GSC)
  2  User Journey Intelligence         (GA4 + Clarity)
  3  Funnel Drop-off                   (funnel steps)
  4  Heatmap / Click Interpretation    (Clarity)
  5  Scroll Analysis                   (Clarity)
  6  Keyword Intelligence              (GSC queries + Ads Keyword Planner)
  10 Executive Summary                 (synthesises all modules)

If no Anthropic key is set, reasoning() returns a placeholder so the app
stays fully usable in demo / no-key mode.
"""

from __future__ import annotations

DEFAULT_MODEL = "gemini-2.5-flash"


# ===========================================================================
# AI reasoning layer
# ===========================================================================
import time as _time


def reasoning(
    prompt: str,
    api_key: str | None,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 700,
) -> str:
    """Call Gemini to narrate findings. Falls back gracefully if no key.
    Retries with exponential backoff on quota/rate-limit errors."""
    if not api_key:
        return (
            "_[AI narrative disabled — add a Gemini API key in secrets.toml "
            "to generate written analysis. All tables and charts above are real "
            "computed findings.]_"
        )

    sys = system or (
        "You are a senior SEO and CRO analyst writing for a digital agency. "
        "Be concise, specific and actionable. Reference the exact numbers given. "
        "Output 2-4 short paragraphs or tight bullets. No preamble, no fluff. "
        "End with a clearly labelled 'Recommendation:' line."
    )

    import google.generativeai as genai
    model_name = model
    if "claude" in model_name or "grok" in model_name:
        model_name = "gemini-2.5-flash"

    genai.configure(api_key=api_key)
    config_gen = genai.types.GenerationConfig(max_output_tokens=max_tokens, temperature=0.2)
    gemini_model = genai.GenerativeModel(model_name=model_name, system_instruction=sys)

    max_attempts, base_wait = 4, 8
    for attempt in range(max_attempts):
        try:
            response = gemini_model.generate_content(prompt, generation_config=config_gen)
            return response.text
        except Exception as exc:
            msg = str(exc).lower()
            is_quota = any(k in msg for k in ("quota", "rate", "429", "resource_exhausted", "exhausted"))
            if is_quota and attempt < max_attempts - 1:
                wait = base_wait * (2 ** attempt)  # 8s, 16s, 32s
                _time.sleep(wait)
                continue
            return (
                f"_[AI narrative unavailable: {exc}. "
                "Structured findings above are still valid.]_"
            )
    return "_[AI narrative unavailable: max retries exceeded.]_"


def grok_reasoning(
    prompt: str,
    api_key: str | None,
    system: str | None = None,
    max_tokens: int = 1200,
) -> str:
    """Call xAI Grok (or Groq if api_key starts with 'gsk_') for deep AI Strategic Analysis.
    Falls back to placeholder if no key.
    Uses the OpenAI-compatible chat completions endpoint."""
    if not api_key:
        return "_[AI strategic analysis disabled — add xai.api_key in secrets.toml for strategic insights.]_"

    sys = system or (
        "You are a world-class SEO strategist and digital growth consultant. "
        "You write precise, insightful, boardroom-ready analysis that connects data to business outcomes. "
        "Be specific — cite exact metrics. Use clear structure with headers/bullets. "
        "Never hedge. Be directive. End every section with a concrete, prioritised action."
    )

    # Automatically detect if Groq key is used (starts with gsk_)
    is_groq = api_key.startswith("gsk_")
    endpoint = "https://api.groq.com/openai/v1/chat/completions" if is_groq else "https://api.x.ai/v1/chat/completions"
    model = "llama-3.3-70b-versatile" if is_groq else "grok-3-mini"
    label = "Groq" if is_groq else "Grok"

    max_attempts, base_wait = 4, 10
    for attempt in range(max_attempts):
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            resp = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=90,
            )
            if resp.status_code == 429:
                if attempt < max_attempts - 1:
                    _time.sleep(base_wait * (2 ** attempt))
                    continue
                return f"_[{label} rate limit reached. Structured findings above are still valid.]_"
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            msg = str(exc).lower()
            if ("429" in msg or "rate" in msg) and attempt < max_attempts - 1:
                _time.sleep(base_wait * (2 ** attempt))
                continue
            return (
                f"_[{label} strategic analysis unavailable: {exc}. "
                "Structured findings above are still valid.]_"
            )
    return f"_[{label} analysis unavailable: max retries exceeded.]_"



def _pct(cur, prev):
    if not prev:
        return None
    return (cur - prev) / prev * 100.0


def _normalize_page(p: str) -> str:
    """Extracts path part from a URL/path to allow matching between GA4 (paths) and GSC/Clarity (URLs)."""
    if not p:
        return ""
    if "://" in p:
        p = p.split("://", 1)[1]
    if "/" in p:
        p = "/" + p.split("/", 1)[1]
    else:
        p = "/"
    return p.split("?")[0].rstrip("/") or "/"


def _detect_brand_terms(site_url: str) -> list[str]:
    """Auto-detect brand terms from the domain name of site_url."""
    try:
        url = site_url if "://" in site_url else "https://" + site_url
        domain = url.split("://", 1)[1].split("/")[0].replace("www.", "")
        brand_raw = domain.split(".")[0].lower()
        terms = [brand_raw]
        # If compound domain (>12 chars), add shorter prefix heuristic
        if len(brand_raw) > 12:
            terms.append(brand_raw[:8])
        return [t for t in terms if t]
    except Exception:
        return []


# ===========================================================================
# Module 1 — Organic Performance Intelligence
# ===========================================================================
def module_organic_performance(ga4_rows, gsc_rows, ga4_totals, api_key, model):
    # Normalize GSC keys
    gsc_by_page = {_normalize_page(r["page"]): r for r in gsc_rows}

    total_sessions = ga4_totals.get("current_total", 0) or sum(r["sessions"] for r in ga4_rows)
    total_prev = ga4_totals.get("prev_total", 0) or sum(r["prev_sessions"] for r in ga4_rows)
    overall_delta = _pct(total_sessions, total_prev)

    page_findings = []
    for r in ga4_rows:
        delta = _pct(r["sessions"], r["prev_sessions"])
        norm_path = _normalize_page(r["page_path"])
        g = gsc_by_page.get(norm_path, {})
        ctr_delta = (
            _pct(g.get("ctr", 0), g.get("prev_ctr", 0)) if g else None
        )
        pos_delta = (
            (g.get("position", 0) - g.get("prev_position", 0)) if g else None
        )
        page_findings.append({
            "page": r["page_path"],
            "sessions": r["sessions"],
            "session_delta_pct": delta,
            "ctr": g.get("ctr"),
            "ctr_delta_pct": ctr_delta,
            "position": g.get("position"),
            "position_delta": pos_delta,
        })

    losers = sorted(
        [p for p in page_findings if (p["session_delta_pct"] or 0) < 0],
        key=lambda p: p["session_delta_pct"],
    )[:5]
    gainers = sorted(
        [p for p in page_findings if (p["session_delta_pct"] or 0) > 0],
        key=lambda p: p["session_delta_pct"],
        reverse=True,
    )[:3]

    loser_lines = "\n".join(
        f"- {p['page']}: sessions {p['session_delta_pct']:+.0f}%, "
        f"CTR {('%+.0f%%' % p['ctr_delta_pct']) if p['ctr_delta_pct'] is not None else 'n/a'}, "
        f"avg position {f'{p['position']:.1f}' if p['position'] is not None else 'n/a'} "
        f"({f'{p['position_delta']:+.1f}' if p['position_delta'] is not None else 'n/a'})"
        for p in losers
    ) or "- none"

    prompt = (
        f"Overall organic sessions changed {overall_delta:+.0f}% vs the prior period "
        f"({total_prev:,} → {total_sessions:,}).\n\n"
        f"Top declining pages (page: session change, CTR change, avg position + change):\n"
        f"{loser_lines}\n\n"
        "For each declining page, identify the most likely cause (CTR erosion vs "
        "ranking loss vs impression loss) and give a specific fix. A page where CTR "
        "fell but position held points to title/meta/snippet problems, not algorithm loss."
    )
    narrative = reasoning(prompt, api_key, model)

    return {
        "title": "Module 1 — Organic Performance",
        "overall_delta_pct": overall_delta,
        "total_sessions": total_sessions,
        "total_prev_sessions": total_prev,
        "losers": losers,
        "gainers": gainers,
        "all_pages": page_findings,
        "narrative": narrative,
    }


# ===========================================================================
# Module 2 — User Journey Intelligence (GA4 + Clarity)
# ===========================================================================
def module_user_journey(ga4_rows, clarity_rows, api_key, model):
    clarity_by_url = {_normalize_page(c["url"]): c for c in clarity_rows}
    flagged = []
    for r in ga4_rows:
        norm_path = _normalize_page(r["page_path"])
        c = clarity_by_url.get(norm_path)
        if not c:
            continue
        high_bounce = r["bounce_rate"] >= 0.60
        low_scroll = c["avg_scroll_percent"] < 40
        many_dead = c["dead_clicks"] >= 100
        if high_bounce and (low_scroll or many_dead):
            flagged.append({
                "page": r["page_path"],
                "bounce_rate": r["bounce_rate"],
                "scroll_percent": c["avg_scroll_percent"],
                "dead_clicks": c["dead_clicks"],
                "rage_clicks": c["rage_clicks"],
                "avg_session_duration": r["avg_session_duration"],
            })
    flagged.sort(
        key=lambda f: (f["bounce_rate"], -f["scroll_percent"]), reverse=True
    )

    if flagged:
        lines = "\n".join(
            f"- {f['page']}: bounce {f['bounce_rate']*100:.0f}%, "
            f"scroll depth {f['scroll_percent']:.0f}%, "
            f"{f['dead_clicks']} dead clicks, {f['rage_clicks']} rage clicks, "
            f"avg time {f['avg_session_duration']:.0f}s"
            for f in flagged
        )
        prompt = (
            "These landing pages combine high bounce with shallow scrolling and/or "
            f"dead clicks — a UX problem signature:\n{lines}\n\n"
            "For each, explain what users are likely doing and the single "
            "highest-impact fix."
        )
    else:
        prompt = (
            "No landing pages show the high-bounce + low-scroll/dead-click pattern. "
            "Briefly confirm UX looks healthy."
        )
    narrative = reasoning(prompt, api_key, model)
    return {
        "title": "Module 2 — User Journey",
        "flagged": flagged,
        "narrative": narrative,
    }


# ===========================================================================
# Module 3 — Funnel Drop-off (with device segmentation)
# ===========================================================================
def module_funnel(funnel_data, api_key, model):
    """
    funnel_data: flat list OR dict {mobile:[...], desktop:[...], tablet:[...]}
    When device-segmented, the analysis focuses on mobile vs desktop gap.
    """
    # Detect device-segmented format
    if isinstance(funnel_data, dict) and "mobile" in funnel_data:
        devices = funnel_data
        flat = funnel_data.get("desktop", list(funnel_data.values())[0])
    else:
        devices = None
        flat = funnel_data

    def _compute_steps(funnel_list):
        steps = []
        for i, s in enumerate(funnel_list):
            prev = funnel_list[i - 1]["users"] if i else None
            drop = (1 - s["users"] / prev) * 100 if prev else 0.0
            steps.append({"step": s["step"], "users": s["users"], "drop_pct": drop})
        return steps

    steps = _compute_steps(flat)
    biggest = max(steps[1:], key=lambda s: s["drop_pct"]) if len(steps) > 1 else None
    overall = (steps[-1]["users"] / steps[0]["users"] * 100) if steps else 0.0

    # Compute per-device steps
    device_steps = {}
    if devices:
        for device_name, device_funnel in devices.items():
            device_steps[device_name] = _compute_steps(device_funnel)

    # Build prompt
    if device_steps:
        mob = device_steps.get("mobile", [])
        desk = device_steps.get("desktop", [])
        mob_completion = (mob[-1]["users"] / mob[0]["users"] * 100) if mob and mob[0]["users"] else 0
        desk_completion = (desk[-1]["users"] / desk[0]["users"] * 100) if desk and desk[0]["users"] else 0
        mob_lines = " → ".join(f"{s['step']} ({s['users']}{'  ↓'+str(int(s['drop_pct']))+'%' if s['drop_pct'] else ''})" for s in mob)
        desk_lines = " → ".join(f"{s['step']} ({s['users']}{'  ↓'+str(int(s['drop_pct']))+'%' if s['drop_pct'] else ''})" for s in desk)
        prompt = (
            f"Device-segmented conversion funnel:\n"
            f"Mobile ({mob_completion:.1f}% completion): {mob_lines}\n"
            f"Desktop ({desk_completion:.1f}% completion): {desk_lines}\n\n"
            "Mobile drop-off is almost always worse than desktop — identify the exact step where "
            "mobile loses the most relative to desktop, explain why (form friction, slow mobile load, "
            "small tap targets, above-the-fold CTA hidden) and give one high-impact fix per device."
        )
    else:
        lines = "\n".join(
            f"- {s['step']}: {s['users']} users"
            + (f" ({s['drop_pct']:.0f}% drop from previous)" if s["drop_pct"] else "")
            for s in steps
        )
        prompt = (
            f"Conversion funnel:\n{lines}\n\n"
            f"Overall completion: {overall:.1f}%. Biggest single drop: "
            f"{biggest['step'] if biggest else 'n/a'} "
            f"({biggest['drop_pct']:.0f}% if applicable).\n"
            "Identify the biggest friction point and give a concrete fix plus a realistic "
            "estimate of conversion lift if fixed."
        )
    narrative = reasoning(prompt, api_key, model)
    return {
        "title": "Module 3 — Funnel Drop-off",
        "steps": steps,
        "device_steps": device_steps,
        "biggest_drop": biggest,
        "overall_completion_pct": overall,
        "narrative": narrative,
    }


# ===========================================================================
# Module 4 — Heatmap / Click Interpretation
# ===========================================================================
def module_heatmap(clarity_rows, api_key, model):
    ranked = sorted(
        clarity_rows,
        key=lambda c: c["dead_clicks"] + c["rage_clicks"] * 2,
        reverse=True,
    )[:5]
    flagged = [
        c for c in ranked if c["dead_clicks"] >= 50 or c["rage_clicks"] >= 10
    ]
    lines = "\n".join(
        f"- {c['url']}: {c['dead_clicks']} dead clicks, {c['rage_clicks']} rage clicks, "
        f"{c['quickback_clicks']} quickbacks across {c['total_sessions']} sessions"
        for c in (flagged or ranked[:3])
    )
    prompt = (
        f"Clarity click-frustration signals by page:\n{lines}\n\n"
        "Dead clicks = users clicking non-interactive elements (often images that look "
        "clickable). Rage clicks = repeated frustrated clicks. Quickbacks = users "
        "bouncing straight back. For the worst pages, infer the likely UX cause and the fix."
    )
    narrative = reasoning(prompt, api_key, model)
    return {
        "title": "Module 4 — Heatmap / Click",
        "flagged": flagged,
        "narrative": narrative,
    }


# ===========================================================================
# Module 5 — Scroll Analysis
# ===========================================================================
def module_scroll(clarity_rows, api_key, model):
    # Sort all pages by scroll depth ascending (worst first)
    all_pages = sorted(
        clarity_rows,
        key=lambda c: c["avg_scroll_percent"]
    )
    low = [c for c in all_pages if c["avg_scroll_percent"] < 40]
    
    lines = "\n".join(
        f"- {c['url']}: avg scroll depth {c['avg_scroll_percent']:.0f}% "
        f"({c['total_sessions']} sessions)"
        for c in low
    ) or "- no pages below 40% scroll depth"
    prompt = (
        f"Pages where most users never scroll far (below 40% average depth):\n{lines}\n\n"
        "Explain the likely cause (long intros, heavy banners, mismatched expectation) "
        "and recommend content re-ordering to surface key sections / CTAs higher."
    )
    narrative = reasoning(prompt, api_key, model)
    return {
        "title": "Module 5 — Scroll Analysis",
        "low_scroll_pages": low,
        "all_pages": all_pages,
        "narrative": narrative,
    }


# ===========================================================================
# Module 6 — Keyword Intelligence (GSC ranking queries)
# ===========================================================================
def module_keyword_intelligence(
    gsc_queries: list[dict],
    api_key: str | None,
    model: str,
    prev_queries: list[dict] | None = None,
    site_url: str | None = None,
) -> dict:
    """
    Analyzes GSC queries to find high-impression keywords ranking in
    positions 4–20, representing high-value, quick-win SEO opportunities.

    Opportunity logic:
      - Keywords ranking in positions 4–20 (close to top 3, fixable with optimization)
      - Monthly impressions >= 100 (has traffic visibility)
      - Sorted by click uplift potential (impressions * target top-3 CTR - current clicks)
    """
    ESTIMATED_CTR_TOP3 = 0.10
    MIN_IMPRESSIONS = 100

    # ── Position Bands ──────────────────────────────────────────────────────
    bands: dict[str, list] = {"1-3": [], "4-10": [], "11-20": [], "21-50": []}
    for row in gsc_queries:
        pos = row.get("position", 100)
        if pos <= 3:
            bands["1-3"].append(row)
        elif pos <= 10:
            bands["4-10"].append(row)
        elif pos <= 20:
            bands["11-20"].append(row)
        elif pos <= 50:
            bands["21-50"].append(row)

    # ── Striking Distance Opportunities (pos 4-20) ──────────────────────────
    opportunities = []
    for row in gsc_queries:
        query = row.get("query", "")
        position = row.get("position", 100)
        current_clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        if impressions >= MIN_IMPRESSIONS and 4 <= position <= 20:
            potential_clicks = int(impressions * ESTIMATED_CTR_TOP3)
            click_uplift = max(0, potential_clicks - current_clicks)
            opportunities.append({
                "query": query,
                "position": round(position, 1),
                "impressions": impressions,
                "current_clicks": current_clicks,
                "potential_clicks": potential_clicks,
                "click_uplift": click_uplift,
            })
    opportunities.sort(key=lambda o: o["click_uplift"], reverse=True)
    top_opps = opportunities[:10]

    # ── New vs Lost Queries WoW ─────────────────────────────────────────────
    new_queries: list[dict] = []
    lost_queries: list[dict] = []
    if prev_queries is not None:
        cur_set = {r["query"] for r in gsc_queries}
        prev_set = {r["query"] for r in prev_queries}
        cur_map = {r["query"]: r for r in gsc_queries}
        prev_map = {r["query"]: r for r in prev_queries}
        new_queries = sorted(
            [cur_map[q] for q in (cur_set - prev_set)],
            key=lambda r: r.get("impressions", 0), reverse=True
        )[:20]
        lost_queries = sorted(
            [prev_map[q] for q in (prev_set - cur_set)],
            key=lambda r: r.get("impressions", 0), reverse=True
        )[:20]

    # ── Brand vs Non-Brand Split ────────────────────────────────────────────
    brand_terms = _detect_brand_terms(site_url) if site_url else []
    brand_clicks = brand_imps = non_brand_clicks = non_brand_imps = 0
    branded_queries: list[dict] = []
    non_branded_queries: list[dict] = []
    for row in gsc_queries:
        q = row.get("query", "").lower()
        is_brand = any(term in q for term in brand_terms) if brand_terms else False
        if is_brand:
            brand_clicks += row.get("clicks", 0)
            brand_imps += row.get("impressions", 0)
            branded_queries.append(row)
        else:
            non_brand_clicks += row.get("clicks", 0)
            non_brand_imps += row.get("impressions", 0)
            non_branded_queries.append(row)
    total_clicks = brand_clicks + non_brand_clicks
    brand_click_pct = round((brand_clicks / total_clicks * 100), 1) if total_clicks else 0.0

    # ── AI Prompt ───────────────────────────────────────────────────────────
    if not top_opps:
        lines = "- No keywords found in position 4–20 range with significant impressions."
        prompt = (
            f"Keyword opportunity scan:\n{lines}\n\n"
            "Briefly note that the site either ranks very well already (top 3) or "
            "targets low-volume terms. Suggest next steps."
        )
    else:
        lines = "\n".join(
            f"- '{o['query']}': position {o['position']}, "
            f"{o['impressions']:,} impressions, "
            f"{o['current_clicks']} current clicks → ~{o['potential_clicks']:,} at top 3 (est), "
            f"potential click uplift: +{o['click_uplift']:,}"
            for o in top_opps[:6]
        )
        brand_note = f"\nBrand dependency: {brand_click_pct:.0f}% of all clicks are branded searches — non-branded discovery is {100-brand_click_pct:.0f}%." if brand_terms else ""
        lost_note = f"\nLost {len(lost_queries)} queries vs prior period — possible ranking drops to investigate." if lost_queries else ""
        prompt = (
            f"Keyword opportunity analysis:\n{lines}\n{brand_note}{lost_note}\n\n"
            "For the top 3 opportunities, explain: "
            "(1) why this keyword is worth targeting, "
            "(2) the specific on-page or technical change to push it into top 3, "
            "(3) realistic monthly click uplift and SEO timeline. Order by ROI."
        )
    narrative = reasoning(prompt, api_key, model)

    return {
        "title": "Module 6 — Keyword Intelligence",
        "opportunities": top_opps,
        "total_queries_analysed": len(gsc_queries),
        "bands": bands,
        "new_queries": new_queries,
        "lost_queries": lost_queries,
        "brand_clicks": brand_clicks,
        "non_brand_clicks": non_brand_clicks,
        "brand_impressions": brand_imps,
        "non_brand_impressions": non_brand_imps,
        "brand_click_pct": brand_click_pct,
        "brand_terms": brand_terms,
        "narrative": narrative,
    }


# ===========================================================================
# Module 7 — Declining Pages UX Audit (GSC × Clarity × PageSpeed)
# ===========================================================================
def module_ux_audit(ga4_rows, gsc_rows, clarity_rows, pagespeed_data, api_key, model, crux_data=None, grok_key=None):
    gsc_by_page = {_normalize_page(r["page"]): r for r in gsc_rows}
    clarity_by_page = {_normalize_page(c["url"]): c for c in clarity_rows}

    # Find the top declining landing pages (top 5 worst session drops)
    declining = sorted(
        [r for r in ga4_rows if (r.get("sessions", 0) - r.get("prev_sessions", 0)) < 0],
        key=lambda r: (r.get("sessions", 0) - r.get("prev_sessions", 0))
    )[:5]

    audit_rows = []
    for r in declining:
        norm_path = _normalize_page(r["page_path"])
        g = gsc_by_page.get(norm_path, {})
        c = clarity_by_page.get(norm_path, {})
        ps = pagespeed_data.get(norm_path, {})

        session_delta = r["sessions"] - r["prev_sessions"]
        session_delta_pct = (session_delta / r["prev_sessions"] * 100.0) if r["prev_sessions"] else 0.0

        # Risk level logic
        dead = c.get("dead_clicks", 0)
        rage = c.get("rage_clicks", 0)
        score = ps.get("performance_score")
        
        risk = "Healthy"
        if dead > 50 or rage > 10 or (score is not None and score < 50):
            risk = "🚨 Critical UX Risk"
        elif dead > 20 or rage > 3 or (score is not None and score < 70):
            risk = "⚠️ Medium UX Risk"

        # CrUX real-user field data (separate from PSI lab scores)
        crux = (crux_data or {}).get(norm_path, {})
        conversion_rate = round(r.get("conversions", 0) / r["sessions"] * 100, 2) if r.get("sessions") else 0.0

        audit_rows.append({
            "page": r["page_path"],
            "session_change": session_delta,
            "session_change_pct": session_delta_pct,
            "sessions": r["sessions"],
            "conversions": r.get("conversions", 0),
            "conversion_rate": conversion_rate,
            "avg_position": g.get("position"),
            "dead_clicks": dead,
            "rage_clicks": rage,
            "avg_scroll_percent": c.get("avg_scroll_percent"),
            "pagespeed_score": score,
            "lcp": ps.get("lcp"),
            "cls": ps.get("cls"),
            "inp": ps.get("inp"),
            "crux_lcp": crux.get("lcp_p75"),
            "crux_cls": crux.get("cls_p75"),
            "crux_inp": crux.get("inp_p75"),
            "crux_rating": crux.get("rating"),
            "risk_level": risk
        })

    lines = []
    for row in audit_rows:
        crux_note = ""
        if row.get("crux_lcp") is not None:
            crux_note = f" | CrUX field LCP: {row['crux_lcp']:.2f}s (real-user, {row.get('crux_rating', 'n/a')})"
        lines.append(
            f"- {row['page']}: sessions {row['session_change_pct']:+.0f}% (now {row['sessions']}), "
            f"avg GSC rank: {f"{row['avg_position']:.1f}" if row['avg_position'] is not None else 'n/a'}, "
            f"Lab PageSpeed: {row['pagespeed_score'] if row['pagespeed_score'] is not None else 'n/a'}% | Lab LCP: {row['lcp'] if row['lcp'] is not None else 'n/a'}s"
            f"{crux_note}, "
            f"Dead/Rage Clicks: {row['dead_clicks']}/{row['rage_clicks']}, Risk: {row['risk_level']}"
        )

    prompt = (
        "You are conducting a deep UX & SEO audit on these top declining pages. "
        "You have BOTH Google PageSpeed Insights lab data AND Chrome UX Report (CrUX) real-user field data.\n\n"
        "IMPORTANT: Lab scores measure controlled conditions. CrUX field data (p75) reflects REAL users — "
        "this is what Google actually uses for Core Web Vitals rankings.\n\n"
        "Declining pages:\n"
        + "\n".join(lines)
        + "\n\nFor EACH page, provide a structured diagnosis with:\n"
        "**Primary Drop Driver** — Is it (a) Google algo rank decay, (b) UX friction (rage/dead clicks), "
        "or (c) Core Web Vitals failure (CrUX field LCP > 2.5s / CLS > 0.1 / INP > 200ms)?\n"
        "**3 Specific Fixes** — Prioritised by impact. For speed: exact image/script/render-blocking changes. "
        "For UX: specific element/flow fixes based on dead/rage click patterns. For SEO: schema, title, intent alignment.\n"
        "**Expected Recovery Timeline** — realistic estimate in weeks.\n\n"
        "Be brutally specific. Name elements, not categories."
    )

    # Use Grok for deep strategic analysis when available, fallback to Gemini
    if grok_key:
        narrative = grok_reasoning(prompt, grok_key, max_tokens=1400)
    else:
        narrative = reasoning(prompt, api_key, model, max_tokens=900)

    return {
        "title": "Module 7 — Declining Pages UX & Performance Audit",
        "audit_rows": audit_rows,
        "narrative": narrative
    }


# ===========================================================================
# Module 8 — Hidden Insights Engine
# ===========================================================================
def module_hidden_insights(ga4_rows, gsc_rows, clarity_rows, api_key, model):
    gsc_by_page = {_normalize_page(r["page"]): r for r in gsc_rows}
    clarity_by_page = {_normalize_page(c["url"]): c for c in clarity_rows}

    zombies = []
    gems = []
    cows = []

    # Calculate average impressions to find high-impression threshold
    all_imps = [r["impressions"] for r in gsc_rows]
    avg_imps = sum(all_imps) / len(all_imps) if all_imps else 1000
    imp_threshold = max(avg_imps * 0.5, 500)

    # Calculate average sessions to find high-performing pages
    all_sess = [r["sessions"] for r in ga4_rows]
    avg_sess = sum(all_sess) / len(all_sess) if all_sess else 100

    # 1. Zombie Pages: High impressions but low CTR/click volume
    for r in gsc_rows:
        if r["impressions"] >= imp_threshold and r["ctr"] < 0.015 and r["position"] < 20:
            zombies.append({
                "page": r["page"],
                "impressions": r["impressions"],
                "clicks": r["clicks"],
                "ctr": r["ctr"] * 100.0,
                "position": r["position"]
            })

    # 2. Unexplored Gems: High user engagement (Clarity/GA4) but low search visibility (GSC)
    for r in ga4_rows:
        norm_path = _normalize_page(r["page_path"])
        g = gsc_by_page.get(norm_path, {})
        c = clarity_by_page.get(norm_path, {})
        
        # High scroll depth (>50%) and high engagement time, but low GSC impressions
        has_engagement = c.get("avg_scroll_percent", 0) > 50 or r.get("avg_session_duration", 0) > 90
        low_gsc = not g or g.get("impressions", 0) < 300
        if has_engagement and low_gsc and r["sessions"] > 50:
            gems.append({
                "page": r["page_path"],
                "sessions": r["sessions"],
                "avg_scroll_percent": c.get("avg_scroll_percent", 0.0),
                "avg_duration": r["avg_session_duration"],
                "impressions": g.get("impressions", 0) if g else 0
            })

    # 3. Friction Cash Cows: High converting pages with high UX frustration
    for r in ga4_rows:
        norm_path = _normalize_page(r["page_path"])
        c = clarity_by_page.get(norm_path, {})
        
        high_conv = r.get("conversions", 0) > 0 or r["sessions"] > avg_sess * 1.5
        high_friction = c.get("dead_clicks", 0) > 40 or c.get("rage_clicks", 0) > 10
        if high_conv and high_friction:
            cows.append({
                "page": r["page_path"],
                "conversions": r.get("conversions", 0),
                "sessions": r["sessions"],
                "dead_clicks": c.get("dead_clicks", 0),
                "rage_clicks": c.get("rage_clicks", 0)
            })

    # Sort opportunities
    zombies = sorted(zombies, key=lambda z: z["impressions"], reverse=True)[:5]
    gems = sorted(gems, key=lambda g: g["avg_scroll_percent"], reverse=True)[:5]
    cows = sorted(cows, key=lambda c: c["dead_clicks"], reverse=True)[:5]

    bullets = []
    if zombies:
        bullets.append(f"Zombie Pages (Needs title/snippet rewrite): " + ", ".join(z["page"] for z in zombies[:2]))
    if gems:
        bullets.append(f"Unexplored Gems (Needs SEO push/internal linking): " + ", ".join(g["page"] for g in gems[:2]))
    if cows:
        bullets.append(f"Friction Cash Cows (Needs CRO fixes): " + ", ".join(c["page"] for c in cows[:2]))

    prompt = (
        "Identify hidden patterns and anomalies on the site. We categorized three patterns:\n"
        f"- Zombie Pages (high impressions, low CTR, position < 20): {zombies}\n"
        f"- Unexplored Gems (high engagement/scroll depth, low search visibility): {gems}\n"
        f"- Friction Cash Cows (high converting/traffic pages, high rage/dead clicks): {cows}\n\n"
        "Explain the strategic growth opportunities for these pages. Formulate specific actions "
        "to double traffic/conversions on these flagged URLs."
    )
    narrative = reasoning(prompt, api_key, model)

    return {
        "title": "Module 8 — Hidden Growth Insights",
        "zombies": zombies,
        "gems": gems,
        "cows": cows,
        "narrative": narrative
    }


# ===========================================================================
# Module 9 — On-Page SEO Optimizer (Jina + GSC + PageSpeed + Grok)
# ===========================================================================
def module_onpage_seo(jina_markdown: str, gsc_queries: list, pagespeed_stats: dict, api_key: str | None, model: str, grok_key: str | None = None) -> str:
    """Deep on-page SEO & copy optimization blueprint powered by Grok (with Gemini fallback)."""
    q_lines = "\n".join(
        f"  {i+1}. [{q.get('position', '?'):.1f} avg rank] '{q['query']}' — "
        f"{q.get('impressions', 0):,} impressions, {q.get('clicks', 0):,} clicks, "
        f"CTR: {q.get('ctr', 0)*100:.2f}% "
        f"({'🎯 Striking distance — optimize now' if 4 <= q.get('position', 100) <= 15 else ''})"
        for i, q in enumerate(sorted(gsc_queries, key=lambda x: x.get('impressions', 0), reverse=True)[:15])
    ) or "  - No Search Console queries found for this page."

    score = pagespeed_stats.get("performance_score")
    lcp = pagespeed_stats.get("lcp")
    cls_v = pagespeed_stats.get("cls")
    inp = pagespeed_stats.get("inp")
    fcp = pagespeed_stats.get("fcp")

    # Word count of scraped content for context
    word_count = len(jina_markdown.split()) if jina_markdown else 0
    content_preview = jina_markdown[:18000]  # Give Grok the full page context up to limit

    prompt = f"""You are a world-class SEO specialist and conversion copywriter conducting a professional on-page SEO audit.

You have access to:
1. The live scraped content of the page (via Jina Reader)
2. Real search performance data from Google Search Console
3. Core Web Vitals from Google PageSpeed Insights

---
## LIVE PAGE CONTENT (Jina Reader Scrape — {word_count:,} words)
{content_preview}
---

## GOOGLE SEARCH CONSOLE — RANKING QUERIES FOR THIS PAGE
{q_lines}

## PAGESPEED INSIGHTS (Mobile)
- Performance Score: {f'{score}%' if score is not None else 'n/a'}
- LCP (Largest Contentful Paint): {f'{lcp}s' if lcp is not None else 'n/a'} {'🔴 POOR (>4s)' if lcp and lcp > 4 else '🟡 NEEDS WORK (>2.5s)' if lcp and lcp > 2.5 else '🟢 GOOD' if lcp else ''}
- CLS (Cumulative Layout Shift): {cls_v if cls_v is not None else 'n/a'} {'🔴 POOR (>0.25)' if cls_v and cls_v > 0.25 else '🟡 NEEDS WORK (>0.1)' if cls_v and cls_v > 0.1 else '🟢 GOOD' if cls_v else ''}
- INP (Interaction to Next Paint): {f'{inp}ms' if inp is not None else 'n/a'} {'🔴 POOR (>500ms)' if inp and inp > 500 else '🟡 NEEDS WORK (>200ms)' if inp and inp > 200 else '🟢 GOOD' if inp else ''}
- FCP (First Contentful Paint): {f'{fcp}s' if fcp is not None else 'n/a'}

---

## YOUR TASK: Produce a Complete On-Page SEO Optimization Blueprint

Based on the actual page content scraped above, generate a **copy-paste-ready professional optimization blueprint** with these exact sections:

### 1. 🏷️ Title Tag & Meta Description (Priority: Critical)
Write 3 optimized title tag variants (≤60 chars) and 2 meta description variants (≤160 chars). Include the top GSC query keyword naturally. Format as:
```
Title Option A: [your title here]
Title Option B: [your title here]
Title Option C: [your title here]

Meta Option A: [your meta description here]
Meta Option B: [your meta description here]
```

### 2. 🔍 Keyword Gap Analysis
- Identify which GSC ranking queries are NOT covered in the current H1/H2 headings (based on the scraped content)
- Flag 3–5 semantic keyword gaps the page should target based on ranking intent
- Show the specific heading this should be added under

### 3. 📝 Heading Structure Rewrite
- Propose a complete revised H1 → H2 → H3 heading hierarchy
- The H1 must contain the primary keyword with highest impression volume
- Add new H2 headings that cover the semantic keyword gaps
- Format as a tree structure

### 4. ✍️ Copy Additions (Write the actual copy)
For each major gap or improvement area, write the actual paragraph, list, or table to add to the page. This should be:
- Minimum 2 new content blocks (each 80–150 words)
- Structured to match search intent of the top-impression queries
- Naturally weaving in secondary keywords from the GSC list
- Marked with [INSERT AFTER: "existing text anchor"]

### 5. 🔗 Internal Linking Opportunities
Based on the page's topic, suggest 3–5 specific internal link placements:
- What anchor text to use
- What type of destination page to link to (category, product, blog post)
- Where in the existing content to place it (quote a few words of context)

### 6. ⚡ Core Web Vitals & Speed Fix Roadmap
Map each failing metric to a specific technical fix:
- LCP issue → specific image/font/server cause + fix (lazy loading, preload, CDN, etc.)
- CLS issue → specific layout shift cause + CSS fix
- INP issue → specific JS blocking cause + optimization
Prioritize by ranking impact.

### 7. 📊 Schema Markup Recommendation
Recommend the 1–2 most impactful Schema.org types for this page topic and write a complete ready-to-implement JSON-LD block.

### 8. 🎯 Prioritized Action Plan
A final 5-item ordered checklist ranked by expected SEO impact (high/medium/low), effort (1-3 weeks / 1 month / 3 months), and estimated ranking improvement.

Output in clean, professional Markdown. Be specific — reference actual content from the page."""

    # Prefer Grok for rich, expert on-page SEO analysis
    if grok_key:
        return grok_reasoning(prompt, grok_key, max_tokens=2500)
    return reasoning(prompt, api_key, model, max_tokens=1500)


# ===========================================================================
# Module 10 — Executive Summary & Roadmap Planner
# ===========================================================================
def module_executive_summary(results: dict, api_key: str | None, model: str, grok_key: str | None = None) -> dict:
    m1 = results.get("organic", {})
    bullets = []
    bullets.append(
        f"Organic sessions {m1.get('overall_delta_pct', 0):+.0f}% vs prior period."
    )
    if m1.get("losers"):
        worst = m1["losers"][0]
        bullets.append(
            f"Biggest SEO issue: {worst['page']} sessions {worst['session_delta_pct']:+.0f}%."
        )
    
    uj = results.get("journey", {})
    if uj.get("flagged"):
        bullets.append(
            f"Biggest UX issue: {uj['flagged'][0]['page']} "
            f"(bounce {uj['flagged'][0]['bounce_rate']*100:.0f}%, "
            f"scroll {uj['flagged'][0]['scroll_percent']:.0f}%)."
        )

    m7 = results.get("ux_audit", {})
    if m7.get("audit_rows"):
        worst_speed = sorted(
            [r for r in m7["audit_rows"] if r.get("pagespeed_score") is not None],
            key=lambda r: r["pagespeed_score"]
        )
        if worst_speed:
            bullets.append(
                f"PageSpeed: {worst_speed[0]['page']} is slowest with {worst_speed[0]['pagespeed_score']}% score."
            )

    m8 = results.get("hidden_insights", {})
    if m8.get("zombies"):
        bullets.append(f"SEO Opportunity: '{m8['zombies'][0]['page']}' is a Zombie page with {m8['zombies'][0]['impressions']:,} impressions but low CTR.")
    if m8.get("cows"):
        bullets.append(f"CRO Opportunity: '{m8['cows'][0]['page']}' converts leads but has high frustration ({m8['cows'][0]['dead_clicks']} dead clicks).")

    prompt = (
        "Write a tight executive summary for stakeholders based on these findings:\n"
        + "\n".join(f"- {b}" for b in bullets)
        + "\n\nProduce:\n"
        "1. A one-line executive health verdict.\n"
        "2. The top 3 prioritised actions with expected business impact, ordered by ROI.\n"
        "3. A structured 3-Month Growth Strategy Calendar:\n"
        "   - Month 1: Speed & Immediate CRO Fixes (Core Web Vitals, rage/dead clicks)\n"
        "   - Month 2: Low-Hanging SEO Wins (Zombie page titles, ranking positions 4-20)\n"
        "   - Month 3: Content Expansion & Link Building (Unexplored Gems, cannibalization)\n\n"
        "Keep it professional, highly structured, and boardroom-ready."
    )
    if grok_key:
        narrative = grok_reasoning(prompt, grok_key, max_tokens=1000)
    else:
        narrative = reasoning(prompt, api_key, model, max_tokens=800)
    return {
        "title": "Module 10 — Executive Summary & Growth Strategy",
        "key_points": bullets,
        "narrative": narrative,
    }



# ===========================================================================
# Module 6b — Keyword Cannibalization Detector
# ===========================================================================
def module_cannibalization(gsc_pairs: list[dict], api_key: str | None, model: str) -> dict:
    """
    Detect keyword cannibalization: queries where 2+ different pages compete.
    Input: gsc_pairs — list of {query, page, clicks, impressions, position}.
    """
    from collections import defaultdict
    query_pages: dict = defaultdict(list)
    for row in gsc_pairs:
        query_pages[row["query"]].append(row)

    conflicts = []
    for query, pages in query_pages.items():
        if len(pages) >= 2:
            pages_sorted = sorted(pages, key=lambda p: p.get("clicks", 0), reverse=True)
            total_clicks = sum(p.get("clicks", 0) for p in pages_sorted)
            total_impressions = sum(p.get("impressions", 0) for p in pages_sorted)
            top_share = (pages_sorted[0].get("clicks", 0) / total_clicks * 100) if total_clicks else 0
            severity = "🔴 High" if len(pages_sorted) >= 3 or top_share < 60 else "🟡 Medium"
            conflicts.append({
                "query": query,
                "competing_pages": pages_sorted,
                "num_pages": len(pages_sorted),
                "total_clicks": total_clicks,
                "total_impressions": total_impressions,
                "winner": pages_sorted[0].get("page", ""),
                "winner_click_share": round(top_share, 1),
                "severity": severity,
            })

    conflicts.sort(key=lambda c: c["total_impressions"], reverse=True)
    top_conflicts = conflicts[:10]

    if not top_conflicts:
        prompt = (
            "No keyword cannibalization detected across GSC query-page pairs. "
            "The site has clean URL-to-topic mapping. Confirm this is healthy and "
            "suggest one proactive check to maintain it long-term."
        )
    else:
        lines = "\n".join(
            f"- '{c['query']}': {c['num_pages']} pages competing, {c['total_impressions']:,} impressions, "
            f"winner '{c['winner']}' has {c['winner_click_share']:.0f}% of clicks, severity: {c['severity']}"
            for c in top_conflicts[:5]
        )
        prompt = (
            f"Keyword cannibalization detected — multiple pages competing for the same queries:\n{lines}\n\n"
            "For the top 3 conflicts: (1) which URL should own this keyword and why, "
            "(2) what to do with the losing pages (301 redirect, content consolidation, "
            "noindex, or internal link update), (3) expected ranking improvement after fixing. "
            "Be direct and specific."
        )
    narrative = reasoning(prompt, api_key, model)
    return {
        "title": "Module 6b — Keyword Cannibalization",
        "conflicts": top_conflicts,
        "narrative": narrative,
    }


# ===========================================================================
# Module 9 — Indexation Health
# ===========================================================================
def module_indexation_health(indexation_data: dict, api_key: str | None, model: str) -> dict:
    """
    Analyse sitemap indexation health from GSC Sitemaps API data.
    """
    submitted = indexation_data.get("submitted_urls", 0)
    indexed = indexation_data.get("indexed_urls", 0)
    rate = indexation_data.get("indexation_rate", 0.0)
    crawled_not_indexed = indexation_data.get("crawled_not_indexed", 0)
    discovered_not_indexed = indexation_data.get("discovered_not_indexed", 0)
    sitemaps = indexation_data.get("sitemaps", [])
    unindexed = submitted - indexed

    sm_lines = "\n".join(
        f"  - {s['path']}: submitted {s['submitted']:,}, indexed {s['indexed']:,} "
        f"({int(s['indexed']/s['submitted']*100) if s['submitted'] else 0}%)"
        for s in sitemaps
    ) or "  - No sitemaps found"

    prompt = (
        f"Indexation health summary for the site:\n"
        f"- Total URLs submitted in sitemaps: {submitted:,}\n"
        f"- Total indexed by Google: {indexed:,} ({rate:.1f}% rate)\n"
        f"- Unindexed from sitemaps: {unindexed:,}\n"
        f"- Crawled but not indexed: {crawled_not_indexed:,}\n"
        f"- Discovered but not indexed: {discovered_not_indexed:,}\n"
        f"Sitemap breakdown:\n{sm_lines}\n\n"
        "Diagnose the indexation health. If the indexation rate is below 85%, explain the most likely "
        "causes (thin content, duplicate pages, soft 404s, crawl budget issues, orphaned pages) and "
        "give 3 specific, prioritized technical fixes. Flag if crawled-not-indexed is disproportionately high."
    )
    narrative = reasoning(prompt, api_key, model)

    return {
        "title": "Module 9 — Indexation & Technical Health",
        "submitted_urls": submitted,
        "indexed_urls": indexed,
        "unindexed_urls": unindexed,
        "indexation_rate": rate,
        "crawled_not_indexed": crawled_not_indexed,
        "discovered_not_indexed": discovered_not_indexed,
        "sitemaps": sitemaps,
        "narrative": narrative,
    }
