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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Solid background */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #0a0714 !important;
    min-height: 100vh;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stToolbar"]         { display: none; }
[data-testid="stDecoration"]      { display: none; }
section[data-testid="stMain"] > div { padding-top: 0; }
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; max-width: 100% !important; }

/* ── Hero: full-viewport centered landing, Google-style ─────────────────── */
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
.st-key-searchbar { max-width: 760px; width: 100%; margin: 3.5rem auto 0; }
.st-key-searchbar > div[data-testid="stHorizontalBlock"] {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 20px !important;
    padding: 0.6rem 0.6rem 0.6rem 1.8rem;
    align-items: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.st-key-searchbar > div[data-testid="stHorizontalBlock"]:focus-within {
    border-color: rgba(167,139,250,0.75);
    box-shadow: 0 10px 40px rgba(0,0,0,0.35), 0 0 0 4px rgba(124,58,237,0.18);
}
.st-key-searchbar [data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1.35rem 0.25rem !important;
    font-size: 1.35rem !important;
}
.st-key-searchbar [data-testid="stTextInput"] input:focus { box-shadow: none !important; }
.st-key-searchbar [data-testid="stTextInput"] input::placeholder { font-size: 1.35rem !important; }

/* ── Results: distinct full-bleed "next page" section ────────────────────── */
.st-key-results {
    width: 100vw;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
    background: #0a0f1c;
    border-radius: 28px 28px 0 0;
    box-shadow: 0 -30px 70px rgba(0,0,0,0.4);
    padding: 4rem max(2rem, calc(50% - 540px)) 6rem;
    scroll-margin-top: 0;
}

/* Typography */
h1, h2, h3, h4 { color: #ffffff !important; font-family: 'Inter', sans-serif !important; }
p, li, span, div { color: rgba(255,255,255,0.82); font-family: 'Inter', sans-serif; }
small { color: rgba(255,255,255,0.45) !important; }

/* Gradient title */
.gradient-title {
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin-bottom: 0.25rem;
    text-align: center !important;
    width: 100%;
}
.subtitle {
    color: rgba(255,255,255,0.45);
    font-size: 0.95rem;
    margin-bottom: 2rem;
    text-align: center !important;
    width: 100%;
}

/* Input */
[data-testid="stTextInput"] input {
    background: rgba(124,58,237,0.12) !important;
    border: 1px solid rgba(167,139,250,0.35) !important;
    border-radius: 4px !important;
    color: white !important;
    font-size: 1rem !important;
    padding: 0.65rem 1rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
[data-testid="stTextInput"] input:focus {
    background: rgba(124,58,237,0.2) !important;
    border-color: rgba(167,139,250,0.8) !important;
    box-shadow: 0 0 0 3px rgba(167,139,250,0.2), 0 0 20px rgba(124,58,237,0.25) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: rgba(167,139,250,0.45) !important; }
[data-testid="stTextInput"] label { color: rgba(255,255,255,0.5) !important; font-size: 0.8rem !important; }

/* Primary button (generic) */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(90deg, #7c3aed, #2563eb) !important;
    border: none !important;
    border-radius: 4px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1.5rem !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease !important;
    width: 100%;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(124,58,237,0.45) !important;
}
[data-testid="stButton"] button[kind="primary"]:active {
    transform: translateY(0) !important;
}
[data-testid="stButton"] button:disabled {
    opacity: 0.35 !important;
}

/* Search-bar button: circular icon button fused into the pill */
.st-key-searchbar [data-testid="stButton"] button[kind="primary"] {
    border-radius: 14px !important;
    width: 64px !important;
    height: 64px !important;
    min-width: 64px !important;
    padding: 0 !important;
    font-size: 1.6rem !important;
    flex-shrink: 0;
}
.st-key-searchbar [data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(0) scale(1.06) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 100px !important;
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 6px 18px !important;
    transition: all 0.2s ease !important;
    margin-bottom: 12px;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.9) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #7c3aed, #2563eb) !important;
    border-color: transparent !important;
    color: white !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.2rem !important; }

/* Expanders as glass cards */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 4px !important;
    margin-bottom: 8px !important;
    overflow: hidden;
    transition: border-color 0.2s ease;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(167,139,250,0.25) !important;
}
[data-testid="stExpander"] summary {
    color: rgba(255,255,255,0.9) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stExpander"] summary:hover { color: white !important; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 0 1rem 1rem 1rem !important;
}

/* Status box */
[data-testid="stStatusWidget"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 4px !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.08) !important; margin: 1.5rem 0 !important; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 4px !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
}

/* Section labels */
.section-label {
    color: rgba(255,255,255,0.4);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
}

/* Risk / opportunity pills */
.risk-item {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 4px;
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}
.opp-item {
    background: rgba(52,211,153,0.08);
    border: 1px solid rgba(52,211,153,0.2);
    border-radius: 4px;
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}
.action-item {
    background: rgba(96,165,250,0.08);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 4px;
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 6px;
    padding: 10px 14px;
}

/* Impact/effort priority badge */
.priority-badge {
    display: inline-block;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 2px 8px;
    margin-right: 8px;
    vertical-align: middle;
}
.priority-quickwin { background: rgba(52,211,153,0.15); border: 1px solid rgba(52,211,153,0.35); color: #34d399 !important; }
.priority-bigbet    { background: rgba(96,165,250,0.15); border: 1px solid rgba(96,165,250,0.35); color: #60a5fa !important; }
.priority-fillin    { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18); color: rgba(255,255,255,0.6) !important; }
.priority-moneypit  { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3); color: #f87171 !important; }

/* Feature comparison matrix */
.feature-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    margin-bottom: 8px;
}
.feature-table th, .feature-table td {
    border: 1px solid rgba(255,255,255,0.08);
    padding: 8px 12px;
    text-align: center;
}
.feature-table th {
    background: rgba(255,255,255,0.04);
    color: rgba(255,255,255,0.6);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.feature-table td:first-child, .feature-table th:first-child {
    text-align: left;
    color: rgba(255,255,255,0.85);
    font-weight: 500;
}
.feature-yes     { color: #34d399 !important; font-weight: 700; }
.feature-partial { color: #fbbf24 !important; font-weight: 700; }
.feature-no      { color: rgba(255,255,255,0.3) !important; }

/* Fade-in animation */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeUp 0.5s ease forwards; }

/* Source link */
.source-url {
    color: rgba(167,139,250,0.7) !important;
    font-size: 0.73rem;
    word-break: break-all;
    text-decoration: none;
}
.source-url:hover { color: #a78bfa !important; text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ── Hero: full-viewport centered landing (Google-style) ────────────────────────
with st.container(key="hero"):
    st.markdown('<div class="gradient-title" style="font-size:4rem;">Radar</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle" style="margin-bottom:0;">Enter a company name. Get a full competitive briefing.</div>', unsafe_allow_html=True)

    with st.container(key="searchbar"):
        col_in, col_btn = st.columns([6, 1])
        with col_in:
            company = st.text_input(
                "Company", placeholder="Spotify · Notion · Figma · Stripe · Vercel",
                label_visibility="collapsed",
            )
        with col_btn:
            run = st.button("→", type="primary", use_container_width=True, disabled=not company)

# ── Analysis ──────────────────────────────────────────────────────────────────
if run and company:
    with st.container(key="results"):
        with st.spinner("Scanning the competitive landscape..."):

            async def _run_analysis() -> CompetitiveBriefing:
                research_notes, competitors = await gather_research_notes(company)
                return await synthesize_briefing(company, research_notes, competitors)

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
                                    f"<div style='margin-bottom:10px;padding-left:4px;border-left:2px solid rgba(167,139,250,0.3)'>"
                                    f"<span style='color:rgba(255,255,255,0.82);font-size:0.875rem'>{src.summary}</span><br>"
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
        st.markdown('<div class="section-label">Recommended Actions — Impact / Effort</div>', unsafe_allow_html=True)

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
                f'<span style="color:rgba(255,255,255,0.4);font-size:0.75rem">I{item.impact}/E{item.effort}</span> '
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
