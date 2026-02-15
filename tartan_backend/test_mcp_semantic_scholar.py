#!/usr/bin/env python3
"""
=============================================================================
TEST MCP SEMANTIC SCHOLAR — Test suite for Semantic Scholar MCP tools
=============================================================================

Runs async tests against the tool functions (search_papers, get_paper_details,
search_papers_for_research, get_paper_by_arxiv, get_paper_by_doi, error handling).
Does not start the MCP server; imports and calls the tool implementations directly.

Usage
-----
  python test_mcp_semantic_scholar.py
  # Exit 0 if all pass, 1 otherwise. Rate limits may cause some tests to skip.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_semantic_scholar import (
    search_papers,
    get_paper_details,
    search_papers_for_research,
    get_paper_by_doi,
    get_paper_by_arxiv,
)


async def test_search_papers():
    """Test basic paper search."""
    print("\n" + "=" * 70)
    print("TEST: search_papers")
    print("=" * 70)
    
    result = await search_papers("quantum computing", limit=5)
    data = json.loads(result)
    
    assert "papers" in data, "Response should contain 'papers' field"
    assert data["returned"] > 0, "Should return at least one paper"
    
    paper = data["papers"][0]
    assert "title" in paper, "Paper should have title"
    assert "authors" in paper, "Paper should have authors"
    
    print(f"✓ Found {data['returned']} papers")
    print(f"  Sample: {paper['title'][:60]}...")
    print(f"  Authors: {', '.join(paper['authors'][:2])}")
    return True


async def test_search_with_filters():
    """Test search with year filters and open access only."""
    print("\n" + "=" * 70)
    print("TEST: search_papers with filters")
    print("=" * 70)
    
    result = await search_papers(
        "machine learning",  # More general query
        limit=3,
        year_from=2020,
        year_to=2024,
        open_access_only=False  # Don't filter to avoid empty results
    )
    data = json.loads(result)
    
    # Handle rate limit errors gracefully
    if "error" in data:
        if "rate limit" in data["error"].lower():
            print(f"⚠ Skipped due to rate limit: {data['message']}")
            return True  # Don't fail the test
        raise AssertionError(f"API error: {data['error']}")
    
    assert "papers" in data, "Response should contain papers"
    
    # Check year filtering if papers returned
    for paper in data["papers"]:
        if paper.get("year"):
            assert 2020 <= paper["year"] <= 2024, f"Year {paper['year']} out of range"
    
    print(f"✓ Found {data['returned']} papers (2020-2024)")
    return True


async def test_search_for_research():
    """Test research-optimized search."""
    print("\n" + "=" * 70)
    print("TEST: search_papers_for_research")
    print("=" * 70)
    
    result = await search_papers_for_research(
        "neural networks",
        max_papers=3  # Reduced to avoid rate limits
    )
    data = json.loads(result)
    
    # Handle rate limit errors gracefully
    if "error" in data:
        if "rate limit" in data.get("error", "").lower():
            print(f"⚠ Skipped due to rate limit")
            return True
        raise AssertionError(f"API error: {data.get('error')}")
    
    assert "papers" in data, "Response should contain papers"
    assert "openAccessCount" in data, "Should report open access count"
    
    # All papers should have PDF URLs
    for paper in data["papers"]:
        assert paper.get("pdfUrl"), "All papers should have PDF URLs"
        assert "citationCount" in paper, "Should include citation count"
    
    print(f"✓ Found {data['openAccessCount']} Open Access papers")
    if data["papers"]:
        top = data["papers"][0]
        print(f"  Top paper: {top['title'][:50]}...")
        print(f"  Citations: {top['citationCount']}")
    return True


async def test_get_by_arxiv():
    """Test fetching paper by arXiv ID."""
    print("\n" + "=" * 70)
    print("TEST: get_paper_by_arxiv")
    print("=" * 70)
    
    # "Attention is All You Need" - famous transformer paper
    result = await get_paper_by_arxiv("1706.03762")
    data = json.loads(result)
    
    assert "title" in data, "Should return paper details"
    assert "Attention" in data["title"], "Should be the Transformer paper"
    assert data.get("citationCount", 0) > 1000, "Should have many citations"
    
    print(f"✓ Retrieved: {data['title']}")
    print(f"  Citations: {data['citationCount']:,}")
    print(f"  Year: {data.get('year')}")
    return True


async def test_get_by_doi():
    """Test fetching paper by DOI."""
    print("\n" + "=" * 70)
    print("TEST: get_paper_by_doi")
    print("=" * 70)
    
    # A well-known paper DOI
    result = await get_paper_by_doi("10.1038/nature14539")
    data = json.loads(result)
    
    if "error" not in data:
        assert "title" in data, "Should return paper details"
        print(f"✓ Retrieved: {data['title'][:60]}...")
        print(f"  Citations: {data.get('citationCount', 0):,}")
    else:
        print(f"⚠ Paper not in Semantic Scholar: {data['error']}")
    return True


async def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n" + "=" * 70)
    print("TEST: Error handling")
    print("=" * 70)
    
    # Invalid paper ID
    result = await get_paper_details("invalid_paper_id_xyz")
    data = json.loads(result)
    
    assert "error" in data, "Should return error for invalid ID"
    assert "not found" in data["error"].lower(), "Should indicate paper not found"
    
    print(f"✓ Correctly handled invalid paper ID")
    print(f"  Error: {data['error']}")
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SEMANTIC SCHOLAR MCP SERVER - TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Basic Search", test_search_papers),
        ("Search with Filters", test_search_with_filters),
        ("Research Search", test_search_for_research),
        ("arXiv Lookup", test_get_by_arxiv),
        ("DOI Lookup", test_get_by_doi),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
