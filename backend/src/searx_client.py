import httpx

SEARX_URL = "http://127.0.0.1:4000/search"
LISTICLE_KEYWORDS = ["top", "best"]

def search_searx(query: str, categories="general", language="en", max_results=6, tag=None):
    """
    Sends a search query to the SearxNG instance.
    Filters out generic listicle results like 'Top 10 ...' and adds category tags.
    Returns a list of search result dicts.
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    params = {
        "q": query,
        "categories": categories,
        "language": language,
        "format": "json"
    }

    try:
        r = httpx.get(SEARX_URL, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        raw_results = r.json().get("results", [])

        filtered = [
            result for result in raw_results
            if not any(
                keyword in result.get("title", "").lower()
                for keyword in LISTICLE_KEYWORDS
            ) and result.get("content")
        ][:max_results]

        results_to_use = filtered if filtered else raw_results[:max_results]

        return [
            {
                "title": r.get("title", "").strip(),
                "url": r.get("url", "").strip(),
                "content": r.get("content", "").strip(),
                "category": tag or "general"
            }
            for r in results_to_use if r.get("content")
        ]

    except Exception as e:
        return [{
            "title": "SearxNG Error",
            "url": SEARX_URL,
            "content": f"Live search failed: {str(e)}",
            "category": tag or "error"
        }]
