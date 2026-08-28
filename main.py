#!/usr/bin/env python3
"""
Competitive Intelligence Agent
Usage: python main.py <company name>
       python main.py "Notion"
       python main.py Linear
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv

from agent import run_competitive_intelligence
from models import CompetitiveBriefing, CompetitorAnalysis

load_dotenv()

DIVIDER = "=" * 72
THIN = "─" * 72

DIMENSION_LABELS = {
    "pricing": "💰  PRICING",
    "key_features": "⚡  KEY FEATURES",
    "market_positioning": "🎯  MARKET POSITIONING",
    "target_audience": "👥  TARGET AUDIENCE",
    "recent_developments": "📰  RECENT DEVELOPMENTS",
}


def _render_competitor(comp: CompetitorAnalysis) -> str:
    lines = [
        f"\n{THIN}",
        f"  {comp.name.upper()}",
    ]
    if comp.website:
        lines.append(f"  {comp.website}")
    lines.append(THIN)

    for attr, label in DIMENSION_LABELS.items():
        dim = getattr(comp, attr)
        lines.append(f"\n  {label}")
        for line in dim.content.splitlines():
            lines.append(f"  {line}")
        if dim.sources:
            lines.append("\n  Sources:")
            for src in dim.sources:
                lines.append(f"    • {src.summary}")
                lines.append(f"      {src.url}")

    return "\n".join(lines)


def format_briefing(briefing: CompetitiveBriefing) -> str:
    lines = [
        f"\n{DIVIDER}",
        f"  COMPETITIVE INTELLIGENCE BRIEFING — {briefing.company.upper()}",
        DIVIDER,
        "",
        "EXECUTIVE SUMMARY",
        THIN,
    ]
    lines.extend(briefing.executive_summary.splitlines())
    lines.append("")

    lines += [
        f"\n{DIVIDER}",
        "  COMPETITOR PROFILES",
    ]
    for comp in briefing.competitors:
        lines.append(_render_competitor(comp))

    lines += [
        f"\n{DIVIDER}",
        "  KEY THREATS",
        THIN,
    ]
    for comp in briefing.competitors:
        for threat in comp.key_threats:
            lines.append(f"  ⚠️   [{comp.name}] {threat}")

    lines += [
        f"\n{DIVIDER}",
        "  OPPORTUNITIES",
        THIN,
    ]
    for comp in briefing.competitors:
        for opp in comp.opportunities:
            lines.append(f"  ✅  [{comp.name}] {opp}")

    if briefing.feature_comparison:
        lines += [
            f"\n{DIVIDER}",
            "  FEATURE COMPARISON",
            THIN,
        ]
        for row in briefing.feature_comparison:
            lines.append(f"\n  {row.feature}")
            for entry in row.support:
                lines.append(f"    • {entry.competitor}: {entry.level}")

    lines += [
        f"\n{DIVIDER}",
        "  RECOMMENDED ACTIONS  (impact / effort, 1-5)",
        THIN,
    ]
    for i, item in enumerate(briefing.recommended_actions, 1):
        lines.append(f"  {i:>2}.  [{item.impact}/{item.effort}]  {item.action}")
        if item.rationale:
            lines.append(f"        {item.rationale}")

    lines.append(f"\n{DIVIDER}\n")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py <company name>")
        print("Example: python main.py Notion")
        sys.exit(1)

    company = " ".join(sys.argv[1:])

    try:
        briefing = run_competitive_intelligence(company)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)

    report = format_briefing(briefing)
    print(report)

    slug = company.lower().replace(" ", "_")
    json_path = Path(f"{slug}_briefing.json")
    json_path.write_text(json.dumps(briefing.model_dump(), indent=2))
    print(f"Full briefing saved → {json_path}")


if __name__ == "__main__":
    main()
