import asyncio
import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from agent import gather_research_notes, synthesize_briefing
from models import CompetitiveBriefing

load_dotenv(Path(__file__).parent / ".env")

st.set_page_config(
    page_title="Radar",
    page_icon=None,
    layout="wide",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #111827;
    --body: #374151;
    --muted: #6b7280;
    --faint: #9ca3af;
    --border: #e5e7eb;
    --border-strong: #d1d5db;
    --accent: #4f46e5;
    --accent-hover: #4338ca;
    --accent-light: #eef2ff;
    --accent-border: #c7d2fe;
    --green: #059669;
    --green-bg: #ecfdf5;
    --green-border: #a7f3d0;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --red-border: #fecaca;
    --amber: #d97706;
    --amber-bg: #fffbeb;
    --amber-border: #fde68a;
}

/* Solid, light background */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #ffffff !important;
    min-height: 100vh;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stToolbar"]         { display: none; }
[data-testid="stDecoration"]      { display: none; }
section[data-testid="stMain"] > div { padding-top: 0; }
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; max-width: 100% !important; }

/* Typography */
h1, h2, h3, h4 { color: var(--ink) !important; font-family: 'Inter', sans-serif !important; }
p, li, span, div { color: var(--body); font-family: 'Inter', sans-serif; }
small { color: var(--faint) !important; }

/* ── Hero: full-viewport centered landing ────────────────────────────────── */
.st-key-hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 0.25rem;
    padding: 2rem;
}
.st-key-hero [data-testid="stVerticalBlockBorderWrapper"] { width: 100%; }
.st-key-hero [data-testid="stMarkdown"],
.st-key-hero [data-testid="stMarkdownContainer"],
.st-key-hero [data-testid="stMarkdownContainer"] p { text-align: center !important; width: 100%; }

.eyebrow {
    display: inline-block;
    background: var(--accent-light);
    border: 1px solid var(--accent-border);
    color: var(--accent-hover);
    font-size: 0.78rem;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 100px;
    margin: 0 auto 1.5rem;
}
.gradient-title {
    color: var(--ink);
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 0.6rem;
    text-align: center !important;
    width: 100%;
}
.subtitle {
    color: var(--muted);
    font-size: 1.05rem;
    margin-bottom: 2rem;
    text-align: center !important;
    width: 100%;
}

/* Search bar: a real rectangle, not a pill */
.st-key-searchbar { max-width: 700px; width: 100%; margin: 2.5rem auto 0; }
.st-key-searchbar [data-testid="stHorizontalBlock"] {
    background: #ffffff;
    border: 1.5px solid var(--border-strong);
    border-radius: 14px !important;
    padding: 8px 14px 8px 4px;
    gap: 12px;
    align-items: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.st-key-searchbar [data-testid="stHorizontalBlock"]:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px var(--accent-light);
}
.st-key-searchbar [data-testid="stTextInput"] div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.st-key-searchbar [data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1rem 0.75rem !important;
    font-size: 1.15rem !important;
    color: var(--ink) !important;
}
.st-key-searchbar [data-testid="stTextInput"] input:focus { box-shadow: none !important; }
.st-key-searchbar [data-testid="stTextInput"] input::placeholder { color: var(--faint) !important; font-size: 1.15rem !important; }

/* ── Results: distinct full-bleed "next page" section ────────────────────── */
.st-key-results {
    width: 100vw;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
    background: #f9f8f6;
    border-top: 1px solid var(--border);
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    padding: 4rem max(2rem, calc(50% - 540px)) 6rem;
    scroll-margin-top: 0;
}

/* Input (generic, outside the search bar) */
[data-testid="stTextInput"] input {
    background: #ffffff !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
    font-size: 1rem !important;
    padding: 0.65rem 1rem !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-light) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--faint) !important; }
[data-testid="stTextInput"] label { color: var(--muted) !important; font-size: 0.8rem !important; }

/* Primary button */
[data-testid="stButton"] button[kind="primary"] {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1.5rem !important;
    transition: background 0.15s ease, transform 0.1s ease !important;
    width: 100%;
}
[data-testid="stButton"] button[kind="primary"] p,
[data-testid="stButton"] button[kind="primary"] div,
[data-testid="stButton"] button[kind="primary"] span {
    color: white !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: var(--accent-hover) !important;
}
[data-testid="stButton"] button[kind="primary"]:active {
    transform: scale(0.98) !important;
}
[data-testid="stButton"] button:disabled {
    opacity: 0.4 !important;
}

/* Search-bar button: sized to match the bar, rectangular */
.st-key-searchbar [data-testid="stButton"] button[kind="primary"] {
    border-radius: 10px !important;
    height: 56px !important;
    min-width: 100px !important;
    padding: 0 1.5rem !important;
    font-size: 1rem !important;
    flex-shrink: 0;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 8px 8px 0 0 !important;
    color: var(--muted) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
    margin-bottom: -1px;
}
.stTabs [data-baseweb="tab"]:hover {
    background: var(--accent-light) !important;
    color: var(--accent-hover) !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    border-bottom: 2px solid var(--accent) !important;
    color: var(--accent) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.4rem !important; }

/* Expanders as clean cards */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
    overflow: hidden;
    transition: border-color 0.15s ease;
}
[data-testid="stExpander"]:hover {
    border-color: var(--border-strong) !important;
}
[data-testid="stExpander"] summary {
    color: var(--ink) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stExpander"] summary:hover { color: var(--accent) !important; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 0 1rem 1rem 1rem !important;
}

/* Status box */
[data-testid="stStatusWidget"] {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}

/* Divider */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: #ffffff !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 8px !important;
    color: var(--body) !important;
    font-size: 0.85rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: var(--accent-light) !important;
    border-color: var(--accent-border) !important;
    color: var(--accent-hover) !important;
}

/* Section labels */
.section-label {
    color: var(--faint);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
}

/* Risk / opportunity / action rows */
.risk-item {
    background: var(--red-bg);
    border: 1px solid var(--red-border);
    border-radius: 8px;
    color: #7f1d1d !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}
.opp-item {
    background: var(--green-bg);
    border: 1px solid var(--green-border);
    border-radius: 8px;
    color: #065f46 !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}
.action-item {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--body) !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}

/* Impact/effort priority badge */
.priority-badge {
    display: inline-block;
    border-radius: 100px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    padding: 3px 10px;
    margin-right: 8px;
    vertical-align: middle;
}
.priority-quickwin { background: var(--green-bg); border: 1px solid var(--green-border); color: var(--green) !important; }
.priority-bigbet    { background: var(--accent-light); border: 1px solid var(--accent-border); color: var(--accent-hover) !important; }
.priority-fillin    { background: #f3f4f6; border: 1px solid var(--border); color: var(--muted) !important; }
.priority-moneypit  { background: var(--amber-bg); border: 1px solid var(--amber-border); color: var(--amber) !important; }

/* Feature comparison matrix */
.feature-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    margin-bottom: 8px;
    background: #ffffff;
}
.feature-table th, .feature-table td {
    border: 1px solid var(--border);
    padding: 10px 14px;
    text-align: center;
}
.feature-table th {
    background: #f9fafb;
    color: var(--muted);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.feature-table td:first-child, .feature-table th:first-child {
    text-align: left;
    color: var(--ink);
    font-weight: 500;
}
.feature-yes     { color: var(--green) !important; font-weight: 700; }
.feature-partial { color: var(--amber) !important; font-weight: 700; }
.feature-no      { color: var(--faint) !important; }

/* Source link */
.source-url {
    color: var(--accent) !important;
    font-size: 0.73rem;
    word-break: break-all;
    text-decoration: none;
}
.source-url:hover { color: var(--accent-hover) !important; text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ── Hero: full-viewport centered landing (Google-style) ────────────────────────
with st.container(key="hero"):
    st.markdown('<div class="eyebrow">AI-powered competitive research</div>', unsafe_allow_html=True)
    st.markdown('<div class="gradient-title" style="font-size:3.4rem;">Radar</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Enter a company name. Get a full competitive briefing.</div>', unsafe_allow_html=True)

    with st.container(key="searchbar"):
        col_in, col_btn = st.columns([6, 1])
        with col_in:
            company = st.text_input(
                "Company", placeholder="Spotify · Notion · Figma · Stripe · Vercel",
                label_visibility="collapsed",
            )
        with col_btn:
            run = st.button("Search", type="primary", use_container_width=True, disabled=not company)

# ── Analysis ──────────────────────────────────────────────────────────────────
if run and company:
    with st.container(key="results"):
        with st.spinner("Scanning the competitive landscape..."):

            async def _run_analysis() -> CompetitiveBriefing:
                research_notes, competitors, per_competitor_notes = await gather_research_notes(company)
                return await synthesize_briefing(company, research_notes, competitors, per_competitor_notes)

            briefing: CompetitiveBriefing = asyncio.run(_run_analysis())

        # ── Executive Summary ──────────────────────────────────────────────────
        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
        st.write(briefing.executive_summary)

        # ── Feature Comparison Matrix ────────────────────────────────────────────
        if briefing.feature_comparison:
            st.markdown('<div class="section-label">Feature Comparison</div>', unsafe_allow_html=True)
            comp_names = [c.name for c in briefing.competitors]
            header_cells = "".join(f"<th>{name}</th>" for name in comp_names)
            rows_html = ""
            level_class = {"Yes": "feature-yes", "Partial": "feature-partial", "No": "feature-no"}
            for row in briefing.feature_comparison:
                support_by_name = {s.competitor: s.level for s in row.support}
                cells = ""
                for name in comp_names:
                    level = support_by_name.get(name, "No")
                    cells += f'<td class="{level_class.get(level, "feature-no")}">{level}</td>'
                rows_html += f"<tr><td>{row.feature}</td>{cells}</tr>"
            st.markdown(
                f'<table class="feature-table"><thead><tr><th>Feature</th>{header_cells}</tr></thead>'
                f'<tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True,
            )

        # ── Competitor Profiles ──────────────────────────────────────────────────
        st.markdown('<div class="section-label">Competitor Profiles</div>', unsafe_allow_html=True)

        DIMS = [
            ("Pricing",              "pricing"),
            ("Key Features",         "key_features"),
            ("Market Positioning",   "market_positioning"),
            ("Target Audience",      "target_audience"),
            ("Recent Developments",  "recent_developments"),
        ]

        tabs = st.tabs([c.name for c in briefing.competitors])
        for tab, comp in zip(tabs, briefing.competitors):
            with tab:
                if comp.website:
                    st.markdown(f'<small>{comp.website}</small>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                for label, attr in DIMS:
                    dim = getattr(comp, attr)
                    with st.expander(label, expanded=False):
                        if not dim.content and not dim.sources:
                            st.markdown('<small>No information found.</small>', unsafe_allow_html=True)
                            continue
                        if dim.content:
                            st.write(dim.content)
                        if dim.sources:
                            st.markdown("&nbsp;", unsafe_allow_html=True)
                            for src in dim.sources:
                                st.markdown(
                                    f"<div style='margin-bottom:10px;padding-left:10px;border-left:2px solid #e5e7eb'>"
                                    f"<span style='color:#374151;font-size:0.875rem'>{src.summary}</span><br>"
                                    f"<a class='source-url' href='{src.url}' target='_blank'>{src.url}</a>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

                # Risks and Opportunities
                st.markdown("<br>", unsafe_allow_html=True)
                col_r, col_o = st.columns(2)
                with col_r:
                    st.markdown('<div class="section-label">Key Risks</div>', unsafe_allow_html=True)
                    for t in comp.key_threats:
                        st.markdown(f'<div class="risk-item">{t}</div>', unsafe_allow_html=True)
                with col_o:
                    st.markdown('<div class="section-label">Opportunities</div>', unsafe_allow_html=True)
                    for o in comp.opportunities:
                        st.markdown(f'<div class="opp-item">{o}</div>', unsafe_allow_html=True)

        # ── Recommended Actions ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Recommended Actions</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.82rem;color:#6b7280;margin-top:-0.5rem;margin-bottom:1rem;line-height:1.6;'>"
            "Each action is scored 1-5 on <b>impact</b> (how much it improves competitive position) and "
            "<b>effort</b> (engineering/GTM lift to execute), then bucketed: "
            "<b style='color:#059669;'>Quick Win</b> = high impact, low effort &middot; "
            "<b style='color:#4338ca;'>Big Bet</b> = high impact, high effort &middot; "
            "<b style='color:#6b7280;'>Fill-In</b> = low impact, low effort &middot; "
            "<b style='color:#d97706;'>Money Pit</b> = low impact, high effort."
            "</div>",
            unsafe_allow_html=True,
        )

        def _quadrant(impact: int, effort: int) -> tuple[str, str]:
            if impact >= 3 and effort <= 2:
                return "priority-quickwin", "Quick Win"
            if impact >= 3 and effort >= 3:
                return "priority-bigbet", "Big Bet"
            if impact <= 2 and effort <= 2:
                return "priority-fillin", "Fill-In"
            return "priority-moneypit", "Money Pit"

        sorted_actions = sorted(briefing.recommended_actions, key=lambda a: (-a.impact, a.effort))
        for i, item in enumerate(sorted_actions, 1):
            css_class, label = _quadrant(item.impact, item.effort)
            rationale_html = f'<br><small>{item.rationale}</small>' if item.rationale else ""
            st.markdown(
                f'<div class="action-item">'
                f'<span class="priority-badge {css_class}">{label}</span>'
                f'<span style="color:#9ca3af;font-size:0.75rem">&nbsp;Impact {item.impact} &middot; Effort {item.effort}</span> '
                f'<b>{i}.</b> {item.action}{rationale_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Download ──────────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            "Download full briefing (JSON)",
            data=json.dumps(briefing.model_dump(), indent=2),
            file_name=f"{company.lower().replace(' ', '_')}_briefing.json",
            mime="application/json",
        )

    # Scroll the freshly rendered results into view, like landing on a new page.
    st.components.v1.html(
        """<script>
        setTimeout(function () {
            var doc = window.parent.document;
            var el = doc.getElementsByClassName('st-key-results')[0];
            if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
        }, 200);
        </script>""",
        height=0,
    )
