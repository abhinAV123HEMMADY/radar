# Radar — Competitive Intelligence Agent

Turns "who are our competitors and what should we do about them" from a multi-hour
research task into a ~30-second, source-linked briefing: a feature comparison matrix,
per-competitor profiles (pricing, features, positioning, audience, recent news — each
claim cited to a real URL), named threats and opportunities, and a set of recommended
actions scored on an impact/effort matrix (Quick Win / Big Bet / Fill-In / Money Pit).

**Live app:** https://io7hxxdsqhswhud9lngnwm.streamlit.app

## How it works

1. **Discovery** — one search + one small LLM call finds the company's 4 real
   competitors.
2. **Research** — 20 search queries (4 competitors × 5 dimensions: pricing, features,
   positioning, audience, recent news) run as a single wave of *concurrent* calls, not
   an agentic tool-loop. The 5 queries per competitor are fixed templates, so there's
   nothing for an LLM to decide turn-by-turn — an earlier ReAct-agent version of this
   step called one search per LLM turn instead of batching as instructed, with
   per-turn latency that grew across the conversation (0.7s → 26s → 32s+), turning a
   ~21-query research phase into several minutes. Thin/empty results get a fallback:
   an MCP tool (`mcp_server.py`, over stdio via `langchain-mcp-adapters`) fetches the
   full page text of the most relevant URL instead of settling for a bad snippet.
3. **Synthesis** — split into one "overview" call (executive summary, feature matrix,
   recommended actions) plus one call *per competitor*, all run concurrently. A single
   call asked to emit all 4 competitor profiles at once measured ~97s of serial
   decoding; splitting it into 5 smaller concurrent calls parallelizes that instead of
   serializing it. Each competitor call gets only that competitor's own research notes
   (sliced deterministically in Python), not the full multi-competitor blob — feeding
   the shared blob to every call was found to sometimes make the model lose track of
   one competitor's section entirely and silently backfill unrelated links as sources.
4. **Cache** — the finished briefing is cached to disk per company (case-insensitive).
   Searching the same company again returns the exact same result instantly rather
   than re-running research and hoping it comes out the same — live web search isn't
   repeatable, and LLMs aren't bit-identical across calls even at `temperature=0`, so
   determinism comes from not re-running the pipeline rather than from the pipeline
   itself. A "Run fresh search" control appears next to any cached result if you want
   an updated read.

## Tech stack

Python · Streamlit · LangChain (`langchain-openai`) · OpenAI (gpt-4o / gpt-4o-mini,
structured output) · MCP (`langchain-mcp-adapters`) · Tavily / DuckDuckGo (`ddgs`) ·
Pydantic

## Project structure

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — landing page, results rendering, caching glue |
| `agent.py` | Research (concurrent search) + synthesis (parallel structured-output calls) pipeline |
| `models.py` | Pydantic schemas for the briefing and its nested structures |
| `mcp_server.py` | Standalone MCP server exposing `fetch_page`, used for thin-snippet enrichment |
| `main.py` | CLI entry point (`python main.py <company>`) |
| `scripts/keep_alive.py` | Visits the deployed app with a real headless browser (see below) |
| `.github/workflows/keep-alive.yml` | Runs the keep-alive script on a schedule |

## Running locally

Requires Python 3.11+ (the `mcp` dependency needs ≥3.10).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY at minimum
streamlit run app.py
```

Environment variables (`.env`):

- `OPENAI_API_KEY` — required.
- `TAVILY_API_KEY` — optional. Gives cleaner, more reliable search results than the
  DuckDuckGo fallback (`ddgs`), which has no built-in timeout and can occasionally
  return thin or rate-limited results; the search tool wraps it in an 8s hard timeout
  regardless. Free tier: 1,000 searches/month.

CLI usage instead of the UI: `python main.py "Company Name"`.

## Deployment

Deployed on Streamlit Community Cloud from this repo (`app.py` as the entry point,
`requirements.txt` for dependencies, `runtime.txt` pins Python 3.11). A `render.yaml`
Blueprint is also included as an alternative host, since Streamlit Cloud requires a
one-time interactive GitHub sign-in to connect that this repo can't do on its own.

**Keep-alive:** Streamlit Cloud's free tier sleeps an app after ~12h with no real
visits — and a plain HTTP/uptime-monitor ping does *not* prevent this, since it
returns `200 OK` with a static HTML shell without ever booting the Python app; only an
actual browser visit counts. `.github/workflows/keep-alive.yml` runs
`scripts/keep_alive.py` on a schedule (every 8h) to genuinely visit the app with
headless Chromium, clicking through Streamlit's "wake this app back up" control if
needed.
