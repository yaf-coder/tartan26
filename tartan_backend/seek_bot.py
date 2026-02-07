"""
seek_bot.py – Recursive arXiv research agent.

Connects to a LOCAL arxiv-mcp-server (spawned as a subprocess) for paper
search / download / read, and uses Dedalus + Claude for keyword extraction.

Setup:
    pip install arxiv-mcp-server mcp dedalus_labs python-dotenv

Usage:
    python seek_bot.py --prompt "Your research problem …" --depth 2
    python seek_bot.py --prompt_file problem.txt   --depth 3
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import textwrap

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS_DIR = os.path.join(HERE, "papers")
os.makedirs(PAPERS_DIR, exist_ok=True)

# Track papers we've already downloaded/processed so we don't loop
_seen_ids: set[str] = set()

MODEL = "anthropic/claude-opus-4-5"

# ── Resolve the arxiv-mcp-server command ─────────────────────────────────────
# Prefer the installed entry-point; fall back to running as a Python module.
_arxiv_cmd = shutil.which("arxiv-mcp-server")
if _arxiv_cmd:
    ARXIV_SERVER_PARAMS = StdioServerParameters(
        command=_arxiv_cmd,
        args=["--storage-path", PAPERS_DIR],
    )
else:
    ARXIV_SERVER_PARAMS = StdioServerParameters(
        command=sys.executable,
        args=["-m", "arxiv_mcp_server", "--storage-path", PAPERS_DIR],
    )


# ── helpers ──────────────────────────────────────────────────────────────────


def _extract_text(result: types.CallToolResult) -> str:
    """Pull the concatenated text from an MCP CallToolResult."""
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
    return "\n".join(parts)


async def _prompt_claude(text: str) -> str:
    """Send *text* to Claude via Dedalus and return the response string."""
    client = AsyncDedalus()
    runner = DedalusRunner(client)
    response = await runner.run(input=text, model=MODEL)
    return response.final_output


# ── retrieve ─────────────────────────────────────────────────────────────────


async def retrieve(
    keyword: str,
    depth: int,
    mcp_session: ClientSession,
) -> None:
    """
    Use the local arXiv MCP server to search for *keyword*, download &
    read the top result, then recurse into main() with depth-1.
    """
    if depth <= 0:
        return

    print(f"\n🔎  retrieve(depth={depth}): searching arXiv for '{keyword}'")

    # ── 1. Search ──
    try:
        search_result = await mcp_session.call_tool(
            "search_papers",
            {"query": keyword, "max_results": 3},
        )
    except Exception as e:
        print(f"   ⚠ search_papers failed: {e}")
        return

    search_text = _extract_text(search_result)
    if not search_text.strip():
        print(f"   ⚠ No arXiv results for '{keyword}'")
        return

    # Parse paper IDs from the search output.
    # The MCP server typically returns structured text; we look for arXiv IDs.
    # Common patterns: "2401.12345" or "2401.12345v2"
    id_pattern = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
    found_ids = id_pattern.findall(search_text)

    # Pick the first ID we haven't visited yet
    paper_id = None
    for pid in found_ids:
        if pid not in _seen_ids:
            paper_id = pid
            break

    if not paper_id:
        print(f"   ⚠ No new paper IDs found for '{keyword}'")
        print(f"      Search output (first 300 chars): {search_text[:300]}")
        return

    _seen_ids.add(paper_id)
    print(f"   🔗 Paper ID: {paper_id}")

    # ── 2. Download ──
    try:
        dl_result = await mcp_session.call_tool(
            "download_paper",
            {"paper_id": paper_id},
        )
        dl_text = _extract_text(dl_result)
        print(f"   ⬇  Download: {dl_text[:120]}")
    except Exception as e:
        print(f"   ⚠ download_paper failed for {paper_id}: {e}")
        return

    # ── 3. Read ──
    try:
        read_result = await mcp_session.call_tool(
            "read_paper",
            {"paper_id": paper_id},
        )
    except Exception as e:
        print(f"   ⚠ read_paper failed for {paper_id}: {e}")
        return

    paper_text = _extract_text(read_result)

    if not paper_text.strip():
        print(f"   ⚠ MCP returned empty text for {paper_id}")
        return

    # Try to grab the title from the first line of text
    first_line = paper_text.split("\n", 1)[0].strip()
    print(f"   📄 Title : {first_line[:100]}")

    # Truncate extremely long papers to avoid token blowup
    MAX_CHARS = 60_000
    if len(paper_text) > MAX_CHARS:
        paper_text = paper_text[:MAX_CHARS] + "\n\n[…truncated…]"

    print(f"   📝 Got {len(paper_text)} chars – recursing with depth={depth - 1}")

    # Recurse
    await main(paper_text, depth - 1, mcp_session)


# ── main ─────────────────────────────────────────────────────────────────────


async def main(
    prompt_text: str,
    depth: int,
    mcp_session: ClientSession,
) -> None:
    """
    Core loop.
    1. Prompt Claude (via Dedalus) to extract search keywords + cited titles.
    2. Call retrieve() for each keyword / title with depth.
    """
    if depth <= 0:
        print(f"\n⏹  depth=0 – stopping recursion.")
        return

    print(f"\n{'='*60}")
    print(f"  main() called  |  depth={depth}  |  prompt length={len(prompt_text)} chars")
    print(f"{'='*60}")

    # ── Step 1: Ask Claude for keywords + cited paper titles ──
    extraction_prompt = textwrap.dedent(f"""\
        You are a research librarian AI. Given the following research text,
        produce a JSON object with exactly two keys:

        • "keywords" – a list of 1 highly specific, descriptive search
          strings (each ~5 words) that would help find closely related work
          on arXiv. Avoid generic terms; be precise and technical.

        • "cited_titles" – a list of the 1 most relevant paper titles explicitly referenced or
          cited in the text. If none are clearly cited, return an empty list.

        Return ONLY the raw JSON object (no markdown fences, no commentary).

        --- BEGIN TEXT ---
        {prompt_text}
        --- END TEXT ---
    """)

    print("\n🤖 Asking Claude for keywords & cited titles …")
    raw_response = await _prompt_claude(extraction_prompt)

    # ── Step 2: Parse the JSON ──
    # Strip markdown code fences if Claude wraps them
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"   ⚠ Claude returned non-JSON – attempting regex fallback")
        # Try to find a JSON object in the response
        m = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                print(f"   ❌ Could not parse JSON at all. Raw response:\n{raw_response[:500]}")
                return
        else:
            print(f"   ❌ No JSON found. Raw response:\n{raw_response[:500]}")
            return

    keywords: list[str] = data.get("keywords", [])
    cited_titles: list[str] = data.get("cited_titles", [])

    print(f"\n   Keywords ({len(keywords)}):")
    for kw in keywords:
        print(f"     • {kw}")
    print(f"   Cited titles ({len(cited_titles)}):")
    for t in cited_titles:
        print(f"     • {t}")

    # ── Step 3: Retrieve every keyword + cited title ──
    all_queries = keywords + cited_titles
    for query in all_queries:
        await retrieve(query, depth, mcp_session)


# ── CLI entry point ──────────────────────────────────────────────────────────


async def _run(prompt_text: str, depth: int) -> None:
    """Spawn the arXiv MCP server, open a session, and kick off main()."""
    print(f"🚀 Starting arXiv MCP server …")
    print(f"   Command: {ARXIV_SERVER_PARAMS.command} {' '.join(ARXIV_SERVER_PARAMS.args)}")
    print(f"   Storage: {PAPERS_DIR}\n")

    async with stdio_client(ARXIV_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Quick sanity check: list available tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"   MCP tools available: {tool_names}\n")

            await main(prompt_text, depth, session)

    print("\n✅ Done. arXiv MCP server shut down.")


def cli():
    parser = argparse.ArgumentParser(
        description="Recursive arXiv research agent powered by Claude + arXiv MCP."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", type=str, help="Inline research prompt text.")
    group.add_argument("--prompt_file", type=str, help="Path to a .txt file with the prompt.")
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Recursion depth (0 = do nothing). Default: 1",
    )
    args = parser.parse_args()

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    else:
        prompt_text = args.prompt

    if args.depth < 0:
        raise SystemExit("depth must be a non-negative integer.")

    asyncio.run(_run(prompt_text, args.depth))


if __name__ == "__main__":
    cli()
