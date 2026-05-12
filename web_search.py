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


def _extract_signals(text: str) -> dict:
    """Extract geography, roles, and industry from ICP/business model text."""
    low = text.lower()

    # Geography
    geo = "Dubai UAE" if any(w in low for w in ["dubai", "uae", "emirates", "mena", "abu dhabi", "gulf"]) else \
          "London UK" if any(w in low for w in ["london", "uk", "britain"]) else \
          "global"

    # Decision-maker roles (in priority order)
    roles = []
    if any(w in low for w in ["cfo", "chief financial", "finance director", "financial officer"]):
        roles.append("CFO")
    if any(w in low for w in ["hr director", "chro", "chief human", "head of hr", "hr manager", "people director"]):
        roles.append("HR Director")
    if any(w in low for w in ["ceo", "chief executive", "founder", "co-founder", "managing director"]):
        roles.append("CEO")
    if any(w in low for w in ["coo", "chief operating", "operations director"]):
        roles.append("COO")
    if not roles:
        roles = ["CEO", "founder"]

    # Industry
    industry = ""
    for ind, keywords in {
        "compliance HR": ["emiratization", "compliance", "mohre", "workforce nationalization"],
        "fintech": ["fintech", "financial services", "banking", "payments", "insurance"],
        "real estate": ["real estate", "property", "construction", "proptech"],
        "healthcare": ["healthcare", "health tech", "medical", "hospital", "clinic"],
        "e-commerce": ["ecommerce", "e-commerce", "retail", "d2c", "consumer"],
        "SaaS": ["saas", "b2b software", "enterprise software"],
        "logistics": ["logistics", "supply chain", "freight", "shipping"],
    }.items():
        if any(kw in low for kw in keywords):
            industry = ind
            break

    # Company size signal
    size = "enterprise" if any(w in low for w in ["200+", "500+", "1000+", "large enterprise", "multinational"]) else \
           "SME" if any(w in low for w in ["50+", "100+", "mid-market", "sme"]) else "startup"

    return {"geo": geo, "roles": roles, "industry": industry, "size": size}


def search_leads(biz_model: str, opportunity: str = "", max_per_query: int = 4) -> str:
    """
    Generate targeted lead searches from the business model and opportunity.
    Extracts geography, job titles, and industry to build specific queries.
    """
    signals = _extract_signals(biz_model + " " + opportunity)
    geo = signals["geo"]
    role1 = signals["roles"][0] if signals["roles"] else "CEO"
    role2 = signals["roles"][1] if len(signals["roles"]) > 1 else "founder"
    industry = signals["industry"]
    size = signals["size"]

    queries = [
        # Decision-maker contact search
        f'"{role1}" OR "{role2}" {geo} {industry} email contact 2025',
        # Company pain point search
        f'{geo} {industry} {size} company "{role1}" site:linkedin.com OR site:crunchbase.com',
        # News/forum signal — companies actively dealing with this pain
        f'{geo} {industry} company {" ".join(biz_model.split()[:8])} 2025 problem challenge',
    ]

    all_results = []
    for q in queries:
        result = search(q, max_results=max_per_query)
        if result:
            all_results.append(f"[Query: {q}]\n{result}")

    return "\n\n---\n\n".join(all_results) if all_results else ""
