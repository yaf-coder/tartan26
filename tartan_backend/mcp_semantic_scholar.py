"""
Semantic Scholar MCP Server

An MCP (Model Context Protocol) server that provides tools for searching and
retrieving research papers from the Semantic Scholar Academic Graph API.

Run with: python mcp_semantic_scholar.py
Or use with MCP-compatible clients via stdio transport.
"""

import os
import json
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    "Semantic Scholar",
    instructions="Search and retrieve academic papers from Semantic Scholar Academic Graph API"
)

# API Configuration
BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = "title,abstract,openAccessPdf,venue,year,authors,externalIds,citationCount,influentialCitationCount"


def _get_headers() -> dict:
    """Get API headers, including API key if available."""
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


@mcp.tool()
async def search_papers(
    query: str,
    limit: int = 20,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    open_access_only: bool = False,
) -> str:
    """
    Search for academic papers on Semantic Scholar.

    Args:
        query: Search query string (natural language or keywords)
        limit: Maximum number of results (1-100, default 20)
        year_from: Optional start year filter
        year_to: Optional end year filter
        open_access_only: If True, only return papers with Open Access PDFs

    Returns:
        JSON string with paper results including titles, abstracts, authors, and PDF links
    """
    limit = max(1, min(100, limit))
    
    params = {
        "query": query,
        "limit": limit,
        "fields": DEFAULT_FIELDS,
    }
    
    # Add year filter if specified
    if year_from or year_to:
        year_filter = ""
        if year_from and year_to:
            year_filter = f"{year_from}-{year_to}"
        elif year_from:
            year_filter = f"{year_from}-"
        else:
            year_filter = f"-{year_to}"
        params["year"] = year_filter

    async with httpx.AsyncClient(timeout=30.0) as client:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.get(
                    f"{BASE_URL}/paper/search",
                    params=params,
                    headers=_get_headers(),
                )
                response.raise_for_status()
                data = response.json()
                break  # Success
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        import asyncio
                        wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                        await asyncio.sleep(wait_time)
                        continue
                    return json.dumps({
                        "error": "Rate limit exceeded",
                        "message": "Semantic Scholar API rate limit reached. Please try again in a few moments.",
                        "hint": "Consider using an API key for higher rate limits"
                    })
                return json.dumps({"error": f"API error: {e.response.status_code}", "message": str(e)})
            except Exception as e:
                return json.dumps({"error": "Request failed", "message": str(e)})

    papers = data.get("data", [])
    
    # Filter to open access only if requested
    if open_access_only:
        papers = [p for p in papers if p.get("openAccessPdf")]

    # Format results
    results = []
    for paper in papers:
        pdf_info = paper.get("openAccessPdf") or {}
        authors = paper.get("authors", [])
        author_names = [a.get("name", "") for a in authors[:5]]  # First 5 authors
        if len(authors) > 5:
            author_names.append(f"et al. (+{len(authors) - 5})")

        results.append({
            "paperId": paper.get("paperId"),
            "title": paper.get("title"),
            "abstract": paper.get("abstract"),
            "authors": author_names,
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "citationCount": paper.get("citationCount"),
            "pdfUrl": pdf_info.get("url"),
            "externalIds": paper.get("externalIds"),
        })

    return json.dumps({
        "total": data.get("total", len(results)),
        "returned": len(results),
        "papers": results,
    }, indent=2)


@mcp.tool()
async def get_paper_details(paper_id: str) -> str:
    """
    Get detailed information about a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI (doi:xxx), arXiv ID (arXiv:xxx), 
                  or other supported ID formats

    Returns:
        JSON string with full paper details including abstract, authors, 
        citations, and PDF link if available
    """
    fields = f"{DEFAULT_FIELDS},references.title,references.authors,citations.title,citations.authors"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.get(
                    f"{BASE_URL}/paper/{paper_id}",
                    params={"fields": fields},
                    headers=_get_headers(),
                )
                response.raise_for_status()
                paper = response.json()
                break  # Success
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return json.dumps({"error": "Paper not found", "paperId": paper_id})
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        import asyncio
                        wait_time = (attempt + 1) * 2
                        await asyncio.sleep(wait_time)
                        continue
                    return json.dumps({"error": "Rate limit exceeded", "message": "API rate limit reached"})
                return json.dumps({"error": f"API error: {e.response.status_code}", "message": str(e)})
            except Exception as e:
                return json.dumps({"error": "Request failed", "message": str(e)})

    # Format authors
    authors = paper.get("authors", [])
    author_list = [{"name": a.get("name"), "authorId": a.get("authorId")} for a in authors]

    # Format references (first 10)
    references = paper.get("references", []) or []
    ref_list = [{"title": r.get("title"), "authors": [a.get("name") for a in (r.get("authors") or [])[:3]]} 
                for r in references[:10]]

    # Format citations (first 10)
    citations = paper.get("citations", []) or []
    cite_list = [{"title": c.get("title"), "authors": [a.get("name") for a in (c.get("authors") or [])[:3]]} 
                 for c in citations[:10]]

    pdf_info = paper.get("openAccessPdf") or {}

    result = {
        "paperId": paper.get("paperId"),
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
        "authors": author_list,
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "citationCount": paper.get("citationCount"),
        "influentialCitationCount": paper.get("influentialCitationCount"),
        "pdfUrl": pdf_info.get("url"),
        "externalIds": paper.get("externalIds"),
        "topReferences": ref_list,
        "topCitations": cite_list,
    }

    return json.dumps(result, indent=2)


@mcp.tool()
async def search_papers_for_research(
    research_prompt: str,
    max_papers: int = 10,
) -> str:
    """
    Search for papers relevant to a research prompt. Returns only papers with
    downloadable Open Access PDFs, suitable for automated research pipelines.

    Args:
        research_prompt: Natural language research question or topic description
        max_papers: Maximum number of papers to return (default 10)

    Returns:
        JSON with papers that have Open Access PDFs available for download
    """
    max_papers = max(1, min(50, max_papers))
    
    # Search with higher limit to account for filtering
    params = {
        "query": research_prompt,
        "limit": min(100, max_papers * 3),  # Fetch more to filter
        "fields": DEFAULT_FIELDS,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.get(
                    f"{BASE_URL}/paper/search",
                    params=params,
                    headers=_get_headers(),
                )
                response.raise_for_status()
                data = response.json()
                break  # Success
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        import asyncio
                        wait_time = (attempt + 1) * 2
                        await asyncio.sleep(wait_time)
                        continue
                    return json.dumps({"error": "Rate limit exceeded", "message": "API rate limit reached"})
                return json.dumps({"error": f"API error: {e.response.status_code}", "message": str(e)})
            except Exception as e:
                return json.dumps({"error": "Request failed", "message": str(e)})

    papers = data.get("data", [])
    
    # Filter to papers with Open Access PDFs and sort by citation count
    oa_papers = [p for p in papers if p.get("openAccessPdf") and p.get("openAccessPdf", {}).get("url")]
    oa_papers.sort(key=lambda p: p.get("citationCount") or 0, reverse=True)
    oa_papers = oa_papers[:max_papers]

    # Format for research pipeline
    results = []
    for paper in oa_papers:
        pdf_info = paper.get("openAccessPdf", {})
        authors = paper.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in authors[:3]])
        if len(authors) > 3:
            author_names += f" et al."

        results.append({
            "paperId": paper.get("paperId"),
            "title": paper.get("title"),
            "abstract": (paper.get("abstract") or "")[:500],  # Truncate for readability
            "authors": author_names,
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "citationCount": paper.get("citationCount"),
            "pdfUrl": pdf_info.get("url"),
            "doi": (paper.get("externalIds") or {}).get("DOI"),
            "arxivId": (paper.get("externalIds") or {}).get("ArXiv"),
        })

    return json.dumps({
        "query": research_prompt,
        "totalFound": data.get("total", 0),
        "openAccessCount": len(results),
        "papers": results,
    }, indent=2)


@mcp.tool()
async def get_paper_by_doi(doi: str) -> str:
    """
    Get paper details by DOI.

    Args:
        doi: The DOI of the paper (e.g., "10.1038/nature12373")

    Returns:
        JSON string with paper details
    """
    return await get_paper_details(f"DOI:{doi}")


@mcp.tool()
async def get_paper_by_arxiv(arxiv_id: str) -> str:
    """
    Get paper details by arXiv ID.

    Args:
        arxiv_id: The arXiv ID (e.g., "2103.14030")

    Returns:
        JSON string with paper details
    """
    return await get_paper_details(f"ARXIV:{arxiv_id}")


# Resources for paper metadata
@mcp.resource("semanticscholar://info")
async def get_api_info() -> str:
    """Get information about the Semantic Scholar API and this MCP server."""
    return json.dumps({
        "name": "Semantic Scholar MCP Server",
        "description": "Provides access to the Semantic Scholar Academic Graph API",
        "capabilities": [
            "Search papers by query",
            "Get paper details by ID",
            "Filter by year range",
            "Filter to Open Access papers only",
            "Get papers by DOI or arXiv ID",
        ],
        "api_docs": "https://api.semanticscholar.org/api-docs/",
        "rate_limits": {
            "without_key": "100 requests per 5 minutes",
            "with_key": "100 requests per second",
        },
    }, indent=2)


if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run()
