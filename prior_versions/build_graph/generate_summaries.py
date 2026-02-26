"""
generate_summaries.py — AI contribution summaries + keywords for Econograph
============================================================================
For each economist, fetches their Wikipedia article (first ~3 000 chars) then
asks Claude Haiku to write one holistic paragraph about their contributions and
pull out 8 identifying keywords.

Results are stored as `summary` and `keywords` directly on each node in
graph_v3.js so the front-end can render them without any API calls.

Features
--------
- Incremental  : checkpoint JSON saves after every batch — crash-safe, resume
- Parallel     : up to CONCURRENCY simultaneous Claude calls
- Dry-run      : --dry-run processes only the first 20 economists
- Force        : --force re-generates economists that already have summaries

Usage
-----
    export ANTHROPIC_API_KEY="sk-ant-..."
    cd build_graph/
    python3 generate_summaries.py ../visualize_v3/js/graph_v3.js
    python3 generate_summaries.py ../visualize_v3/js/graph_v3.js --dry-run
    python3 generate_summaries.py ../visualize_v3/js/graph_v3.js --resume
    python3 generate_summaries.py ../visualize_v3/js/graph_v3.js --force
"""

import asyncio
import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
from pathlib import Path

import anthropic
import requests

# ── Configuration ──────────────────────────────────────────────────────────
MODEL       = "claude-haiku-4-5-20251001"
CONCURRENCY = 8     # parallel Claude calls
WIKI_BATCH  = 20    # Wikipedia Action API titles-per-request cap
WIKI_CHARS  = 3000  # characters of article text to send to LLM
CHECKPOINT  = "summaries_checkpoint.json"


# ── Prompt ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert in the history of economic thought writing for an educational platform.
Given a Wikipedia article about an economist, produce:
1. ONE holistic paragraph (3–5 sentences) summarising their most important contributions
   and intellectual legacy. Be specific about ideas, theorems, models, or insights they
   introduced. Use active sentences ("Arrow proved…", "Friedman argued…").
2. Exactly 8 short keywords (1–4 words each) that best identify this person. Draw from:
   specific theories/theorems/models they created, institutions they are central to,
   core research areas, major intellectual influences they had, or famous results/books.

Respond with ONLY valid JSON in exactly this format — no markdown, no explanation:
{"summary":"...","keywords":["...","...","...","...","...","...","...","..."]}"""


def make_user_message(name: str, school: str, text: str) -> str:
    return (
        f"Economist: {name}\n"
        f"School of thought: {school}\n\n"
        f"Wikipedia article (excerpt):\n{text[:WIKI_CHARS]}"
    )


# ── Wikipedia fetch ────────────────────────────────────────────────────────
def fetch_wiki_extracts(nodes: list) -> dict:
    """
    Batch-fetch Wikipedia article text for all nodes.
    Returns {node_id: text}.
    Uses exintro=true&excharacters=3000 to get a substantial intro excerpt.
    """
    title_to_id: dict = {}
    for n in nodes:
        url = n.get("url", "")
        if "/wiki/" in url:
            raw_title = url.split("/wiki/")[-1].split("#")[0]
            title = urllib.parse.unquote(raw_title).replace("_", " ")
            title_to_id[title] = n["id"]

    titles  = list(title_to_id.keys())
    results = {}

    total_batches = (len(titles) + WIKI_BATCH - 1) // WIKI_BATCH
    for i in range(0, len(titles), WIKI_BATCH):
        batch     = titles[i : i + WIKI_BATCH]
        batch_num = i // WIKI_BATCH + 1
        print(f"  Wikipedia batch {batch_num}/{total_batches}…", end=" ", flush=True)

        api_url = (
            "https://en.wikipedia.org/w/api.php"
            "?action=query&prop=extracts"
            "&exintro=true&explaintext=true"
            f"&excharacters={WIKI_CHARS}"
            f"&titles={'|'.join(batch)}"
            "&format=json&origin=*"
        )
        try:
            resp = requests.get(
                api_url, timeout=30,
                headers={"User-Agent": "EconographBot/1.0 (summaries)"},
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            got = 0
            for page in pages.values():
                text  = page.get("extract", "") or ""
                title = page.get("title",   "") or ""
                if text and title:
                    pid = (title_to_id.get(title)
                           or title_to_id.get(title.replace(" ", "_")))
                    if pid:
                        results[pid] = text
                        got += 1
            print(f"got {got}")
        except Exception as exc:
            print(f"FAILED ({exc})")

        time.sleep(0.4)

    return results


# ── LLM summary generation ─────────────────────────────────────────────────
async def summarise_one(client, sem, node: dict, text: str):
    """
    Call Claude for a single economist.
    Returns (node_id, {"summary": str, "keywords": list} | None, name).
    None result means the call failed and should NOT be checkpointed.
    """
    async with sem:
        msg_text = make_user_message(node["name"], node.get("school", ""), text)
        for attempt in range(3):
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=600,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg_text}],
                )
                raw = response.content[0].text.strip()
                # Extract JSON (handle occasional leading/trailing prose)
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if not m:
                    raise ValueError(f"No JSON in response: {raw[:120]!r}")
                data = json.loads(m.group(0))

                summary  = str(data.get("summary", "")).strip()
                keywords = data.get("keywords", [])
                if not isinstance(keywords, list):
                    keywords = []
                keywords = [str(k).strip() for k in keywords[:8] if str(k).strip()]

                if not summary:
                    raise ValueError("Empty summary")

                return node["id"], {"summary": summary, "keywords": keywords}, node["name"]

            except anthropic.RateLimitError:
                wait = 2 ** attempt * 5
                print(f"\n  Rate limit for {node['name']!r}, waiting {wait}s…")
                await asyncio.sleep(wait)
            except Exception as exc:
                if attempt == 2:
                    print(f"\n  Failed {node['name']!r}: {exc}")
                    return node["id"], None, node["name"]
                await asyncio.sleep(2)

    return node["id"], None, node["name"]


async def summarise_all(client, candidates: list, extracts: dict) -> dict:
    """Run all summary calls concurrently. Returns {node_id: {summary, keywords}}."""
    sem   = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        summarise_one(client, sem, node, extracts.get(node["id"], ""))
        for node in candidates
        if extracts.get(node["id"])
    ]

    results = {}
    failed  = []
    done    = 0
    total   = len(tasks)

    for coro in asyncio.as_completed(tasks):
        pid, data, name = await coro
        if data is not None:
            results[pid] = data
        else:
            failed.append(name)
        done += 1
        if done % 50 == 0 or done == total:
            print(f"  LLM progress {done}/{total}  "
                  f"({len(results)} succeeded, {len(failed)} failed)…")

    if failed:
        print(f"\n  ⚠ {len(failed)} calls failed (will retry on next run):")
        for n in failed[:10]:
            print(f"    {n}")
        if len(failed) > 10:
            print(f"    … and {len(failed) - 10} more")

    return results


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Generate AI contribution summaries + keywords for graph_v3.js"
    )
    parser.add_argument("graph_path", help="Path to graph_v3.js")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Process only the first 20 economists (for testing)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip economists already in the checkpoint file",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-generate even economists that already have summaries in graph_v3.js",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    # ── Load graph ────────────────────────────────────────────────────────
    print(f"Loading {args.graph_path}…")
    with open(args.graph_path, encoding="utf-8") as f:
        raw = f.read()
    prefix     = "var graph = "
    graph_data = json.loads(raw[len(prefix):])
    nodes      = graph_data["nodes"]
    print(f"  {len(nodes)} nodes")

    # ── Load checkpoint ───────────────────────────────────────────────────
    graph_dir       = os.path.dirname(os.path.abspath(args.graph_path))
    checkpoint_path = os.path.join(graph_dir, CHECKPOINT)
    checkpoint: dict = {}
    if args.resume and os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        print(f"  Resuming from checkpoint: {len(checkpoint)} already done")

    # ── Identify candidates ───────────────────────────────────────────────
    def needs_summary(n) -> bool:
        if not n.get("url"):
            return False
        if args.force:
            return True
        if n["id"] in checkpoint:
            return False
        if n.get("summary") and n.get("keywords"):
            return False  # already in graph data from a previous run
        return True

    candidates = [n for n in nodes if needs_summary(n)]

    if args.dry_run:
        candidates = candidates[:20]
        print(f"  DRY RUN — processing first {len(candidates)} economists only")
    else:
        print(f"  {len(candidates)} economists need summaries")

    if not candidates:
        print("  Nothing to do — all economists already have summaries.")
        print("  (Use --force to regenerate anyway.)")
    else:
        # ── Fetch Wikipedia text ──────────────────────────────────────────
        print(f"\nFetching Wikipedia text ({len(candidates)} economists)…")
        extracts = fetch_wiki_extracts(candidates)
        print(f"  Got text for {len(extracts)}/{len(candidates)} economists")

        # ── Run LLM ──────────────────────────────────────────────────────
        print(f"\nGenerating summaries with {MODEL} (concurrency={CONCURRENCY})…")
        client     = anthropic.AsyncAnthropic(api_key=api_key)
        llm_results = asyncio.run(summarise_all(client, candidates, extracts))
        print(f"  LLM returned {len(llm_results)} results")

        checkpoint.update(llm_results)

        # Save checkpoint
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        print(f"  Checkpoint saved → {checkpoint_path}")

    # ── Merge checkpoint into nodes ───────────────────────────────────────
    print("\nMerging results into graph…")
    updated = 0
    for node in nodes:
        pid = node["id"]
        if pid in checkpoint:
            data = checkpoint[pid]
            node["summary"]  = data.get("summary",  "")
            node["keywords"] = data.get("keywords", [])
            updated += 1

    # Summary stats
    with_summary = sum(1 for n in nodes if n.get("summary"))
    print(f"  {updated} nodes updated from checkpoint")
    print(f"  {with_summary}/{len(nodes)} nodes now have AI summaries")

    # ── Backup + write ────────────────────────────────────────────────────
    backup = args.graph_path + ".bak"
    print(f"\nBacking up to {backup}…")
    shutil.copy2(args.graph_path, backup)

    print(f"Writing {args.graph_path}…")
    with open(args.graph_path, "w", encoding="utf-8") as f:
        f.write(prefix)
        json.dump(graph_data, f, ensure_ascii=False)

    size_kb = Path(args.graph_path).stat().st_size // 1024
    print(f"\n✓ Done. {with_summary} economists have AI summaries. "
          f"File size: {size_kb} KB")


if __name__ == "__main__":
    main()
