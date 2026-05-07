"""Live web search using DuckDuckGo — free, no API key needed."""

import logging
logger = logging.getLogger(__name__)


def search(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"• {r['title']}\n  {r['body']}\n  Source: {r['href']}")
        return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return ""


def search_trends(topic: str) -> str:
    queries = [
        f"{topic} problems complaints reddit 2025",
        f"{topic} startup opportunity gap 2025",
        f"{topic} pain points entrepreneurs",
    ]
    all_results = []
    for q in queries:
        result = search(q, max_results=3)
        if result:
            all_results.append(f"[Search: {q}]\n{result}")
    return "\n\n---\n\n".join(all_results)
