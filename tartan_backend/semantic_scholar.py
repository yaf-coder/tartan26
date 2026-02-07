import os
import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SemanticScholarClient:
    """
    Client for the Semantic Scholar Academic Graph API.
    Focuses on finding Open Access papers with PDF links.
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key

    def search_papers(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for papers using a query string.
        Returns a list of paper objects with metadata and Open Access PDF links.
        """
        endpoint = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,openAccessPdf,venue,year,authors,externalIds"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []

    def get_paper_details(self, paper_id: str) -> Optional[Dict]:
        """Fetch full details for a specific paper."""
        endpoint = f"{self.BASE_URL}/paper/{paper_id}"
        params = {
            "fields": "title,abstract,openAccessPdf,venue,year,authors,externalIds"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id}: {e}")
            return None

def test_search():
    client = SemanticScholarClient()
    results = client.search_papers("PFAS innovations", limit=5)
    for res in results:
        pdf_url = res.get("openAccessPdf", {}).get("url") if res.get("openAccessPdf") else None
        print(f"Title: {res['title']}")
        print(f"PDF: {pdf_url}")
        print("---")

if __name__ == "__main__":
    test_search()
