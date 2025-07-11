import httpx
import yaml

# Load YAML config
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

SEARX_URL = config["SEARX_API_URL"]
LISTICLE_KEYWORDS = ["top", "best"]

def search_searx(query: str, categories="general", language="en", max_results=6, tag=None):
    """
    Sends a search query to a SearxNG instance and retrieves filtered web results.

    The function uses HTTP GET to perform a meta search. It filters out generic
    listicle-style results (e.g., "Top 10 things to do") and optionally tags each result
    with a custom category. If no meaningful results are found, fallback raw results are returned.

    Args:
        query (str): The search query string.
        categories (str, optional): Comma-separated Searx categories to target (e.g., "news,images").
        language (str, optional): ISO language code for search results (default is "en").
        max_results (int, optional): Maximum number of search results to return (default is 6).
        tag (str, optional): Optional tag/category to assign to the returned results.

    Returns:
        list[dict]: A list of result dictionaries, each containing:
            - title (str): The result title.
            - url (str): The result URL.
            - content (str): A short description or snippet.
            - category (str): Either the provided tag or "general".
        
        If an error occurs, a single-item list with an error message is returned.
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
