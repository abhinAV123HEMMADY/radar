import asyncio
import os
import re
import sys
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient

from models import CompetitiveBriefing, CompetitorAnalysis, BriefingOverview

_MCP_SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"
_URL_RE = re.compile(r"https?://[^\s\)\]]+")

# The 5 research queries per competitor are fixed templates, not something an LLM
# needs to decide turn-by-turn — so the whole research phase runs as one wave of
# concurrent search calls instead of an agentic tool-call loop. (An earlier ReAct
# version called one tool per turn instead of batching as instructed, with per-turn
# LLM latency that grew with conversation length — 0.7s -> 26s -> 32s+ — making a
# ~21-query research phase take minutes.)
DIMENSION_QUERY_TEMPLATES = {
    "pricing": "{c} pricing plans cost",
    "key_features": "{c} key features capabilities",
    "market_positioning": "{c} market positioning vs {company}",
    "target_audience": "{c} target customers use cases",
    "recent_developments": "{c} news funding launch 2024 2025",
}


class _CompetitorList(BaseModel):
    names: list[str] = Field(description="Exactly 4 real, distinct direct competitor company names")


# Synthesis is split into an "overview" call (executive summary, feature matrix,
# recommended actions — needs all competitors as context) plus one call PER
# competitor profile, all run concurrently. A single call asked to emit all 4
# competitor profiles at once measured ~97s (autoregressive decode of one huge
# response); splitting it into 5 concurrent smaller calls parallelizes that decode
# instead of serializing it — mirrors the same fix applied to the research phase.

OVERVIEW_SYSTEM = """\
You are a competitive intelligence analyst. From the research notes, produce the \
cross-competitor parts of a briefing: executive summary, feature comparison, and \
recommended actions.

REQUIREMENTS — follow these exactly:
0. The research notes start with a "SEARCHES COMPLETED" section listing every query that \
   was run. The competitors are given to you explicitly below — use exactly that list.
1. executive_summary: 2-3 paragraphs covering the competitive landscape overall.
2. feature_comparison: 5-8 rows comparing concrete features across ALL competitors (e.g. "Free tier", \
   "API access", "Mobile app", "Team collaboration", "AI features"). Pick features that actually \
   appeared in the research notes. Every row's `support` list must have exactly one entry per \
   competitor, each with level "Yes", "No", or "Partial" — infer "No" only when the research notes \
   give no evidence the feature exists.
3. recommended_actions: 4-6 items. Each is a PrioritizedAction with an `action` string plus `impact` \
   and `effort` scored 1-5 (5 = highest), and a one-sentence `rationale`. Score impact by how much \
   the action improves competitive position; score effort by the engineering/GTM lift required. Use \
   the full 1-5 range across the set — don't score everything a 3.\
"""

OVERVIEW_HUMAN = """\
Company being analysed: {company}
Competitors (use exactly this list, in this order): {competitors}

Research notes:
{research_notes}

Produce the executive summary, feature comparison, and recommended actions.\
"""

COMPETITOR_SYSTEM = """\
You are a competitive intelligence analyst. From the research notes, produce the complete \
CompetitorAnalysis for ONE named competitor — ignore every other competitor's data even if \
it appears in the notes.

REQUIREMENTS — follow these exactly:
1. Every DimensionData.content must be 3-5 sentences covering the key facts for that dimension \
   with specific details (numbers, names, dates).
2. Every DimensionData.sources list MUST contain 3-5 SourceCitation entries, ONLY drawn from that \
   dimension's own "Query: ..." block in the research notes — never borrow a URL from a different \
   dimension's block just to fill the list.
3. Each SourceCitation.summary must state the actual facts from that URL — real numbers, \
   feature names, or direct claims. \
   GOOD: "$11.99/month for Prime, $14.99 standalone; includes HD audio and offline downloads." \
   BAD: "Outlines pricing plans." or "Describes Amazon Music's features."
4. If the research notes' block for a dimension has no usable information, write \
   "No public information found." in content and leave that dimension's sources list EMPTY. \
   Do not attach a URL from another dimension or a generic "X is a competitor of Y" mention just \
   to avoid an empty list — an empty sources list is correct when there is nothing to cite.
5. key_threats: 3-5 items. Name the exact feature, bundle, pricing lever, or distribution \
   advantage that is the threat. Never write vague statements like "has a large user base" — \
   say WHY that specific thing is dangerous and what it blocks. \
   GOOD: "Amazon Music is bundled free with Prime ($139/yr) across 200M+ members — Spotify \
   cannot price-match this without destroying margins." \
   BAD: "Amazon's ecosystem could hurt Spotify's market share."
6. opportunities: 3-5 items. Name the specific product gap or weak feature in this competitor's \
   offering and state what the company should build or improve to exploit it. \
   GOOD: "Amazon Music lacks collaborative playlists and social listening — Spotify should \
   expand Blend and group sessions to retain social-first users Amazon cannot serve." \
   BAD: "Spotify can improve its AI features to stay competitive."\
"""

COMPETITOR_HUMAN = """\
Company being analysed: {company}
Competitor to profile: {competitor}

Research notes for {competitor} (already scoped to just this competitor):
{research_notes}

Produce the complete CompetitorAnalysis for {competitor}.\
"""


def _make_search_tool():
    if os.getenv("TAVILY_API_KEY"):
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        @tool
        def web_search(query: str) -> str:
            """Search the web. Returns titles, URLs, and content snippets."""
            resp = client.search(query, max_results=5)
            out = []
            for r in resp.get("results", []):
                out.append(f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}")
            return "\n---\n".join(out) or "No results found."

        return web_search

    from ddgs import DDGS
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
    _ddgs_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ddgs")

    @tool
    def web_search(query: str) -> str:
        """Search the web. Returns titles, URLs, and content snippets."""
        # ddgs sets no internal timeout and can hang indefinitely under rate limiting —
        # bound it hard so one stuck query never stalls the whole research run.
        try:
            future = _ddgs_pool.submit(lambda: list(DDGS().text(query, max_results=5)))
            results = future.result(timeout=8)
        except FutureTimeoutError:
            return "Search timed out — try a narrower query."
        except Exception as exc:
            return f"Search failed: {exc}"
        if not results:
            return "No results found."
        out = []
        for r in results:
            out.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}")
        return "\n---\n".join(out)

    return web_search


async def discover_competitors(company: str, search_tool, llm) -> tuple[list[str], str]:
    """One search + one small structured-output call to find exactly 4 real competitors."""
    discovery_query = f"{company} top competitors 2025"
    raw = await asyncio.to_thread(search_tool.invoke, {"query": discovery_query})

    extractor = llm.with_structured_output(_CompetitorList)
    extracted = await extractor.ainvoke(
        f"Company: {company}\n\nSearch results about its competitors:\n{raw}\n\n"
        f"Extract exactly 4 real, distinct competitor company names. Never include {company} itself."
    )
    competitors = list(dict.fromkeys(n.strip() for n in extracted.names if n.strip()))[:4]
    return competitors, f"Query: {discovery_query}\n{raw}"


async def _get_fetch_tool():
    """MCP fetch_page tool, or None if the MCP server can't be reached.

    mcp_server.py runs as a subprocess over stdio via langchain-mcp-adapters and
    returns full page text, used to enrich thin search snippets below.
    """
    try:
        client = MultiServerMCPClient({
            "compintel-fetch": {
                "command": sys.executable,
                "args": [str(_MCP_SERVER_SCRIPT)],
                "transport": "stdio",
            }
        })
        tools = await client.get_tools()
        return next((t for t in tools if t.name == "fetch_page"), None)
    except Exception as exc:
        print(f"MCP fetch tool unavailable, continuing with search snippets only: {exc}")
        return None


def _is_thin(result: str) -> bool:
    return (
        len(result) < 400
        or "No results found" in result
        or "Search failed" in result
        or "Search timed out" in result
    )


async def _fetch_text(fetch_tool, url: str) -> str:
    raw = await asyncio.wait_for(fetch_tool.ainvoke({"url": url}), timeout=12)
    if isinstance(raw, list):
        return " ".join(part.get("text", "") for part in raw if isinstance(part, dict))
    return str(raw)


async def gather_research_notes(company: str, search_tool=None, llm=None) -> tuple[str, list[str], dict[str, str]]:
    """Run the whole research phase as one wave of concurrent search calls.

    The 5 queries per competitor are fixed templates (see DIMENSION_QUERY_TEMPLATES),
    so there's nothing for an LLM to decide turn-by-turn — running them concurrently
    is simpler and far faster than an agentic tool-call loop. Returns (research_notes,
    competitor_names, per_competitor_notes) — the last one has each competitor's own
    5 dimension results pre-sliced, so the synthesis step never has to locate the
    right section inside a blob shared across all competitors.
    """
    search_tool = search_tool or _make_search_tool()
    # gpt-4o-mini, not a Groq fast-path: this single small extraction call isn't a
    # speed bottleneck (research is dominated by search I/O, ~11s), and Groq's
    # gpt-oss-120b was observed to occasionally ignore forced structured output
    # entirely and return plain text, crashing the run.
    llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    competitors, discovery_pair = await discover_competitors(company, search_tool, llm)
    fetch_tool = await _get_fetch_tool()

    dimension_queries = [
        template.format(c=comp, company=company)
        for comp in competitors
        for template in DIMENSION_QUERY_TEMPLATES.values()
    ]

    search_sem = asyncio.Semaphore(8)
    fetch_sem = asyncio.Semaphore(6)

    async def run_query(query: str) -> str:
        async with search_sem:
            result = await asyncio.to_thread(search_tool.invoke, {"query": query})
        # A thin/empty snippet doesn't necessarily mean no page exists — pull the
        # first URL's full text instead of letting synthesis see nothing at all.
        if fetch_tool is not None and _is_thin(result):
            match = _URL_RE.search(result)
            if match:
                url = match.group(0).rstrip(".,;:")
                try:
                    async with fetch_sem:
                        full_text = await _fetch_text(fetch_tool, url)
                    if len(full_text) > len(result):
                        result = f"{result}\n\n[Full page text from {url}]:\n{full_text[:4000]}"
                except Exception as exc:
                    result = f"{result}\n\n[fetch_page failed for a thin result: {exc}]"
        return f"Query: {query}\n{result}"

    dimension_pairs = await asyncio.gather(*(run_query(q) for q in dimension_queries))

    all_queries = [f"{company} top competitors 2025"] + dimension_queries
    query_log = "\n".join(f"Searching: {q}" for q in all_queries)
    raw_results = "\n\n---\n\n".join([discovery_pair] + dimension_pairs)
    research_notes = (
        f"SEARCHES COMPLETED (every company that appears here is a competitor "
        f"and must have its own profile):\n{query_log}"
        f"\n\n{'='*60}\n\nFULL SEARCH RESULTS:\n{raw_results}"
    )

    n_dims = len(DIMENSION_QUERY_TEMPLATES)
    per_competitor_notes = {
        comp: "\n\n---\n\n".join(dimension_pairs[i * n_dims:(i + 1) * n_dims])
        for i, comp in enumerate(competitors)
    }

    return research_notes, competitors, per_competitor_notes


async def synthesize_briefing(
    company: str,
    research_notes: str,
    competitors: list[str],
    per_competitor_notes: dict[str, str] | None = None,
) -> CompetitiveBriefing:
    """Overview + one profile per competitor, all generated concurrently (see note above).

    Each competitor call gets ONLY that competitor's own research notes (pre-sliced by
    gather_research_notes), not the full multi-competitor blob — this was found to be
    necessary: given the shared blob, the model would sometimes fail to locate one
    competitor's section at all and report "No public information found" despite the
    data being present, then backfill unrelated URLs as sources to avoid an empty list.
    """
    per_competitor_notes = per_competitor_notes or {c: research_notes for c in competitors}
    overview_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(BriefingOverview)
    competitor_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(CompetitorAnalysis)

    overview_chain = (
        ChatPromptTemplate.from_messages([("system", OVERVIEW_SYSTEM), ("human", OVERVIEW_HUMAN)])
        | overview_llm
    )
    competitor_chain = (
        ChatPromptTemplate.from_messages([("system", COMPETITOR_SYSTEM), ("human", COMPETITOR_HUMAN)])
        | competitor_llm
    )

    overview_task = overview_chain.ainvoke({
        "company": company,
        "competitors": ", ".join(competitors),
        "research_notes": research_notes,
    })
    competitor_tasks = [
        competitor_chain.ainvoke({
            "company": company,
            "competitor": c,
            "research_notes": per_competitor_notes.get(c, research_notes),
        })
        for c in competitors
    ]

    overview: BriefingOverview
    profiles: list[CompetitorAnalysis]
    overview, *profiles = await asyncio.gather(overview_task, *competitor_tasks)

    return CompetitiveBriefing(
        company=company,
        executive_summary=overview.executive_summary,
        competitors=profiles,
        feature_comparison=overview.feature_comparison,
        recommended_actions=overview.recommended_actions,
    )


async def _run_competitive_intelligence_async(company: str) -> CompetitiveBriefing:
    print(f"\nResearching competitors of '{company}' ...")
    research_notes, competitors, per_competitor_notes = await gather_research_notes(company)
    print(f"\nResearch complete ({len(research_notes)} chars, {len(competitors)} competitors). Synthesising briefing ...")

    briefing = await synthesize_briefing(company, research_notes, competitors, per_competitor_notes)
    return briefing


def run_competitive_intelligence(company: str) -> CompetitiveBriefing:
    return asyncio.run(_run_competitive_intelligence_async(company))
