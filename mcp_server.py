"""
MCP server exposing a page-fetching tool for deeper competitive research.

Runs over stdio. agent.py launches it as a subprocess via langchain-mcp-adapters
and exposes its tools to the research agent alongside web_search, so the agent
can pull full page content (e.g. a pricing page) instead of only a search snippet.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("compintel-fetch")


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch a web page and return its main readable text.

    Use this after a search result looks promising and the snippet isn't enough
    detail (e.g. a pricing page or a features page) — this returns the full text.
    """
    try:
        resp = httpx.get(
            url,
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
    except Exception as exc:
        return f"Fetch failed: {exc}"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    return text[:6000]


if __name__ == "__main__":
    mcp.run(transport="stdio")
