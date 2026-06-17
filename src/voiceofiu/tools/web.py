"""Web search — DuckDuckGo (no API key needed) → fallback Wikipedia."""

import logging

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "VoiceOfIU/1.0"}


def search(query: str, max_results: int = 3) -> str | None:
    result = _ddg(query, max_results) or _wikipedia(query)
    return result


def _ddg(query: str, max_results: int) -> str | None:
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=_HEADERS,
            timeout=8,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        snippets = []
        for result in soup.select(".result__snippet")[:max_results]:
            text = result.get_text(strip=True)
            if text:
                snippets.append(text)
        return " | ".join(snippets) if snippets else None
    except Exception as e:
        log.warning(f"DDG search failed: {e}")
        return None


def fetch_page(url: str, max_chars: int = 3000) -> str | None:
    """Fetch and extract readable text from a full web page."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text[:max_chars] if text else None
    except Exception as e:
        log.warning(f"Page fetch failed: {e}")
        return None


def _wikipedia(query: str) -> str | None:
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,  # type: ignore[arg-type]
                    "format": "json", "srlimit": 1},
            headers=_HEADERS,
            timeout=6,
        )
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return None
        title = results[0]["title"]
        snippet = BeautifulSoup(results[0]["snippet"], "html.parser").get_text()
        return f"{title}: {snippet}"
    except Exception as e:
        log.warning(f"Wikipedia search failed: {e}")
        return None
