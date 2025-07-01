import httpx

SEARX_URL = "http://127.0.0.1:4000/search"

def search_searx(query: str, categories="general", language="en", max_results=6):
    headers = {
        "User-Agent": "Mozilla/5.0",  # Required to prevent 403
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

        # 🧹 Filter out listicles and vague content
        filtered = [
            result for result in raw_results
            if not any(
                bad_word in result.get("title", "").lower()
                for bad_word in ["top", listicle_keyword]
            )
            and "2025" not in result.get("title", "")
            and result.get("content", "")
        ][:max_results]

        return filtered if filtered else raw_results[:max_results]

    except Exception as e:
        return [{
            "title": "SearxNG Error",
            "url": SEARX_URL,
            "content": f"Live search failed: {str(e)}"
        }]

# Helper to catch vague listicle keywords
listicle_keyword = "best"
