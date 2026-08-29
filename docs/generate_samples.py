"""Regenerates docs/samples.html from docs/sample-data/*.json.

Run this after refreshing a sample company's cached output (e.g. python main.py
"Notion" then copy cache/notion.json into docs/sample-data/) to rebuild the
static page. Reads the real CompetitiveBriefing structure directly — no
hand-transcription — so the page can never drift from actual tool output.

Usage: python docs/generate_samples.py
"""
import html as h
import json
from pathlib import Path

HERE = Path(__file__).parent
SAMPLE_DATA_DIR = HERE / "sample-data"
SHELL_PATH = HERE / "_samples_shell.html"
OUTPUT_PATH = HERE / "samples.html"

COMPANIES = ["notion", "linear", "figma"]
DIMS = [
    ("Pricing", "pricing"),
    ("Key Features", "key_features"),
    ("Market Positioning", "market_positioning"),
    ("Target Audience", "target_audience"),
    ("Recent Developments", "recent_developments"),
]


def esc(s) -> str:
    return h.escape(str(s), quote=True)


def quadrant(impact: int, effort: int) -> tuple[str, str]:
    if impact >= 3 and effort <= 2:
        return "qw", "Quick Win"
    if impact >= 3 and effort >= 3:
        return "bb", "Big Bet"
    if impact <= 2 and effort <= 2:
        return "fi", "Fill-In"
    return "mp", "Money Pit"


def render_company(slug: str, briefing: dict, cached_at: str, active: bool) -> str:
    b = briefing
    comp_names = [c["name"] for c in b["competitors"]]

    header_cells = "".join(f"<th>{esc(n)}</th>" for n in comp_names)
    level_class = {"Yes": "tag-yes", "Partial": "tag-partial", "No": "tag-no"}
    rows_html = ""
    for row in b["feature_comparison"]:
        support = {s["competitor"]: s["level"] for s in row["support"]}
        cells = "".join(
            f'<td class="{level_class.get(support.get(n, "No"), "tag-no")}">{esc(support.get(n, "No"))}</td>'
            for n in comp_names
        )
        rows_html += f"<tr><td>{esc(row['feature'])}</td>{cells}</tr>"

    comp_tabs_nav = "".join(
        f'<button class="ctab" data-ctab="{slug}-{i}" onclick="showCTab(\'{slug}\',{i})">{esc(c["name"])}</button>'
        for i, c in enumerate(b["competitors"])
    )

    comp_panels = ""
    for i, c in enumerate(b["competitors"]):
        dims_html = ""
        for label, key in DIMS:
            dim = c[key]
            sources_html = "".join(
                f'<div class="src"><span>{esc(src["summary"])}</span>'
                f'<a href="{esc(src["url"])}" target="_blank" rel="noopener">{esc(src["url"])}</a></div>'
                for src in dim.get("sources", [])
            )
            dims_html += f'''
            <details class="dim">
              <summary>{esc(label)}</summary>
              <div class="dim-body">
                <p>{esc(dim["content"])}</p>
                {f'<div class="src-list">{sources_html}</div>' if sources_html else ''}
              </div>
            </details>'''

        threats_html = "".join(f'<div class="risk-item">{esc(t)}</div>' for t in c["key_threats"])
        opps_html = "".join(f'<div class="opp-item">{esc(o)}</div>' for o in c["opportunities"])
        website = (
            f'<div class="comp-url"><a href="{esc(c["website"])}" target="_blank" rel="noopener">{esc(c["website"])}</a></div>'
            if c.get("website") else ""
        )

        comp_panels += f'''
        <div class="cpanel" id="{slug}-{i}" style="display:{'block' if i == 0 else 'none'}">
          {website}
          {dims_html}
          <div class="two-col">
            <div><div class="subhead">Key Risks</div>{threats_html}</div>
            <div><div class="subhead">Opportunities</div>{opps_html}</div>
          </div>
        </div>'''

    actions = sorted(b["recommended_actions"], key=lambda a: (-a["impact"], a["effort"]))
    actions_html = ""
    for i, a in enumerate(actions, 1):
        cls, label = quadrant(a["impact"], a["effort"])
        actions_html += f'''
        <div class="action-row">
          <span class="quad-badge {cls}">{label}</span>
          <span class="score">Impact {a["impact"]} &middot; Effort {a["effort"]}</span>
          <b>{i}.</b> {esc(a["action"])}
          {f'<div class="rationale">{esc(a["rationale"])}</div>' if a.get("rationale") else ''}
        </div>'''

    return f'''
    <section class="cbrief" id="brief-{slug}" style="display:{'block' if active else 'none'}">
      <div class="brief-meta">Generated {cached_at[:10]} &middot; competitors: {esc(", ".join(comp_names))}</div>
      <h3 class="section-label">Executive Summary</h3>
      <p class="summary">{esc(b["executive_summary"])}</p>

      <h3 class="section-label">Feature Comparison</h3>
      <div class="table-wrap">
        <table class="feature-table">
          <thead><tr><th>Feature</th>{header_cells}</tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>

      <h3 class="section-label">Competitor Profiles</h3>
      <div class="ctabs">{comp_tabs_nav}</div>
      {comp_panels}

      <h3 class="section-label">Recommended Actions</h3>
      <div class="actions">{actions_html}</div>
    </section>'''


def main() -> None:
    parts, switcher = [], ""
    for i, slug in enumerate(COMPANIES):
        data = json.loads((SAMPLE_DATA_DIR / f"{slug}.json").read_text())
        b = data["briefing"]
        parts.append(render_company(slug, b, data["cached_at"], active=(i == 0)))
        switcher += (
            f'<button class="mtab{" active" if i == 0 else ""}" data-mtab="{slug}" '
            f'onclick="showCompany(\'{slug}\')">{esc(b["company"])}</button>'
        )

    body = "\n".join(parts)
    shell = SHELL_PATH.read_text()
    out = shell.replace("__SWITCHER__", switcher).replace("__BODY__", body)
    OUTPUT_PATH.write_text(out)
    print(f"Wrote {OUTPUT_PATH} ({len(out):,} chars)")


if __name__ == "__main__":
    main()
