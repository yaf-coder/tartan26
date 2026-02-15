"""
=============================================================================
OPENALEX CLIENT — Open Access paper search (backup source)
=============================================================================

Synchronous client for the OpenAlex API. Used by the Veritas API as a third
source when running global research: arXiv and Semantic Scholar are tried
first; OpenAlex fills remaining slots when needed. Results are normalized to
the same shape as Semantic Scholar (title, abstract, openAccessPdf.url) for
unified ranking and PDF download.

Usage
-----
  client = OpenAlexClient()  # optional: api_key or OPENALEX_API_KEY
  papers = client.search_papers("machine learning", limit=25)

Environment
----------
- OPENALEX_API_KEY : Optional; can improve rate limits.
"""
import os
import logging
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


def _inverted_index_to_abstract(idx: Optional[Dict[str, List[int]]]) -> str:
    """Convert OpenAlex abstract_inverted_index to plain text."""
    if not idx or not isinstance(idx, dict):
        return ""
    pairs: List[tuple] = []
    for word, positions in idx.items():
        for pos in positions:
            pairs.append((pos, word))
    pairs.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pairs)


def _pdf_url_from_work(work: Dict[str, Any]) -> Optional[str]:
    """Extract a PDF URL from a work: best_oa_location.pdf_url or first location with pdf_url."""
    best = work.get("best_oa_location") or {}
    if best.get("pdf_url"):
        return best["pdf_url"]
    for loc in work.get("locations") or []:
        if loc.get("pdf_url"):
            return loc["pdf_url"]
    return None


class OpenAlexClient:
    """
    Client for the OpenAlex API.
    Returns papers in the same shape as Semantic Scholar (title, abstract, openAccessPdf)
    for compatibility with the research pipeline.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        self.session = requests.Session()
        self.session.timeout = 30

    def search_papers(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for works with open-access PDFs.
        Returns list of dicts compatible with app pipeline: title, abstract, openAccessPdf.url.
        """
        params: Dict[str, Any] = {
            "search": query,
            "per_page": min(limit, 25),
            "filter": "is_oa:true",  # open access only
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{BASE_URL}/works",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []

        results: List[Dict] = []
        for work in data.get("results") or []:
            pdf_url = _pdf_url_from_work(work)
            if not pdf_url:
                continue
            title = work.get("title") or work.get("display_name") or "Untitled"
            abstract = _inverted_index_to_abstract(work.get("abstract_inverted_index"))
            results.append({
                "title": title,
                "abstract": abstract or None,
                "openAccessPdf": {"url": pdf_url},
                "year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count"),
            })
        return results


def test_search():
    client = OpenAlexClient()
    results = client.search_papers("machine learning", limit=5)
    for r in results:
        print(r["title"][:60], r["openAccessPdf"]["url"])


if __name__ == "__main__":
    test_search()
