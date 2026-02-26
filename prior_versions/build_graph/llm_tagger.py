"""
llm_tagger.py — LLM-based school-of-thought classifier for graph_v3.js
=======================================================================
For each economist, fetches their Wikipedia intro then asks Claude Haiku
to choose the single best school of thought from the canonical list.

Seed economists (defined below) are never sent to the LLM — their school
is authoritative and kept as-is.

Features:
  - Incremental: saves a checkpoint JSON after every batch so a crash
    can be resumed without re-classifying already-done economists.
  - Parallel: fires up to CONCURRENCY requests simultaneously.
  - Dry-run mode: --dry-run classifies only the first 20 economists.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    cd build_graph/
    python3 llm_tagger.py ../visualize_v3/js/graph_v3.js
    python3 llm_tagger.py ../visualize_v3/js/graph_v3.js --dry-run
    python3 llm_tagger.py ../visualize_v3/js/graph_v3.js --resume   # skip already checkpointed
"""

import json
import os
import re
import sys
import time
import shutil
import asyncio
import argparse
import urllib.parse
from collections import defaultdict

import anthropic
import requests

# ── Configuration ─────────────────────────────────────────────────────────
MODEL       = "claude-haiku-4-5-20251001"
CONCURRENCY = 8    # parallel Claude calls
WIKI_BATCH  = 20   # Wikipedia API cap for exintro (silent limit)
CHECKPOINT  = "llm_tagger_checkpoint.json"

# ── Valid schools (must match exactly what graph_v3.js uses) ───────────────
VALID_SCHOOLS = [
    "Keynesian",
    "New Keynesian",
    "Austrian School",
    "Chicago School",
    "Classical/Neoclassical",
    "Marxian",
    "Institutional",
    "Behavioral",
    "Game Theory",
    "Development",
    "Public Choice",
    "Econometrics",
    "Finance",
    "Labor Economics",
    "International Trade",
    "Economic History",
    "Political Economy",
    "Welfare & Public Economics",
    "Environmental Economics",
    "Other",
]

SCHOOL_DESCRIPTIONS = {
    "Keynesian":                  "fiscal policy, aggregate demand management, IS-LM, business cycles, Keynes's General Theory",
    "New Keynesian":              "DSGE models, nominal rigidities, sticky prices, inflation targeting, modern central banking",
    "Austrian School":            "spontaneous order, praxeology, capital theory, business cycle theory, Hayek/Mises tradition",
    "Chicago School":             "price theory, monetarism, law & economics, rational expectations, free-market micro/macro",
    "Classical/Neoclassical":     "general equilibrium, marginal utility, supply & demand, Walrasian/Marshallian tradition, pre-Keynes",
    "Marxian":                    "surplus value, class struggle, modes of production, capital accumulation critique, historical materialism",
    "Institutional":              "transaction costs, path dependence, evolutionary economics, veblenian tradition, new institutional economics",
    "Behavioral":                 "cognitive biases, prospect theory, bounded rationality, nudges, psychology applied to economic decisions",
    "Game Theory":                "strategic interaction, Nash equilibrium, mechanism design, auction theory, matching theory",
    "Development":                "poverty in developing countries, growth in low-income economies, aid, structural transformation, development aid",
    "Public Choice":              "government failure, rent-seeking, constitutional economics, voting behavior, bureaucracy",
    "Econometrics":               "causal inference, instrumental variables, regression discontinuity, panel data, empirical identification",
    "Finance":                    "asset pricing, capital markets, banking, corporate finance, risk management, financial intermediation",
    "Labor Economics":            "wages, employment, human capital, labor markets, minimum wage, unions, migration",
    "International Trade":        "comparative advantage, trade policy, globalization, tariffs, trade agreements, WTO",
    "Economic History":           "cliometrics, long-run economic growth, historical economic analysis, industrial revolution",
    "Political Economy":          "political institutions, state capacity, electoral economics, political constraints on policy",
    "Welfare & Public Economics": "public finance, optimal taxation, public goods, externalities, social insurance, redistribution",
    "Environmental Economics":    "carbon pricing, climate change economics, natural resource management, pollution policy",
    "Other":                      "does not clearly fit any of the above",
}

# ── Seed map: these economists are never sent to the LLM ──────────────────
# Format: exact scraped name → school
SEEDS = {
    # Austrian School
    "Carl Menger": "Austrian School", "Ludwig von Mises": "Austrian School",
    "Friedrich Hayek": "Austrian School", "Eugen von Böhm-Bawerk": "Austrian School",
    "Murray Rothbard": "Austrian School", "Israel Kirzner": "Austrian School",
    "Friedrich von Wieser": "Austrian School", "Oskar Morgenstern": "Austrian School",
    "Gottfried Haberler": "Austrian School", "Fritz Machlup": "Austrian School",
    # Chicago School
    "Milton Friedman": "Chicago School", "George Stigler": "Chicago School",
    "Gary Becker": "Chicago School", "Eugene Fama": "Chicago School",
    "Ronald Coase": "Chicago School", "Frank Knight": "Chicago School",
    "Jacob Viner": "Chicago School", "Thomas Sowell": "Chicago School",
    "Harold Demsetz": "Chicago School", "Sherwin Rosen": "Chicago School",
    "Robert Fogel": "Chicago School", "Lars Peter Hansen": "Chicago School",
    "Steven Levitt": "Chicago School", "Armen Alchian": "Chicago School",
    # Keynesian
    "John Maynard Keynes": "Keynesian", "Paul Samuelson": "Keynesian",
    "James Tobin": "Keynesian", "Franco Modigliani": "Keynesian",
    "Robert Solow": "Keynesian", "Lawrence Klein": "Keynesian",
    "Alvin Hansen": "Keynesian", "Joan Robinson": "Keynesian",
    "Nicholas Kaldor": "Keynesian", "Abba Lerner": "Keynesian",
    "Evsey Domar": "Keynesian", "James Meade": "Keynesian",
    # New Keynesian
    "Joseph Stiglitz": "New Keynesian", "Paul Krugman": "New Keynesian",
    "Olivier Blanchard": "New Keynesian", "Janet Yellen": "New Keynesian",
    "Ben Bernanke": "New Keynesian", "Jordi Galí": "New Keynesian",
    "Stanley Fischer": "New Keynesian", "John Taylor": "New Keynesian",
    "David Romer": "New Keynesian", "Alan Blinder": "New Keynesian",
    "Mark Gertler": "New Keynesian", "Emmanuel Farhi": "New Keynesian",
    # Classical/Neoclassical
    "Adam Smith": "Classical/Neoclassical", "David Ricardo": "Classical/Neoclassical",
    "John Stuart Mill": "Classical/Neoclassical", "Alfred Marshall": "Classical/Neoclassical",
    "Léon Walras": "Classical/Neoclassical", "William Stanley Jevons": "Classical/Neoclassical",
    "Vilfredo Pareto": "Classical/Neoclassical", "Knut Wicksell": "Classical/Neoclassical",
    "Irving Fisher": "Classical/Neoclassical", "John Bates Clark": "Classical/Neoclassical",
    "David Hume": "Classical/Neoclassical", "François Quesnay": "Classical/Neoclassical",
    # Marxian
    "Karl Marx": "Marxian", "Friedrich Engels": "Marxian",
    "Rosa Luxemburg": "Marxian", "Paul Sweezy": "Marxian",
    "Piero Sraffa": "Marxian", "Anwar Shaikh": "Marxian",
    "David Harvey": "Marxian", "Samuel Bowles": "Marxian",
    "Duncan Foley": "Marxian",
    # Institutional
    "Thorstein Veblen": "Institutional", "John Commons": "Institutional",
    "John Kenneth Galbraith": "Institutional", "Gunnar Myrdal": "Institutional",
    "Oliver Williamson": "Institutional", "Albert Hirschman": "Institutional",
    "Kenneth Boulding": "Institutional",
    # Behavioral
    "Daniel Kahneman": "Behavioral", "Richard Thaler": "Behavioral",
    "Robert Shiller": "Behavioral", "George Akerlof": "Behavioral",
    "Colin Camerer": "Behavioral", "Dan Ariely": "Behavioral",
    "Sendhil Mullainathan": "Behavioral", "Matthew Rabin": "Behavioral",
    "David Laibson": "Behavioral", "Stefano DellaVigna": "Behavioral",
    "Xavier Gabaix": "Behavioral",
    # Game Theory
    "John von Neumann": "Game Theory", "John Harsanyi": "Game Theory",
    "Reinhard Selten": "Game Theory", "Robert Aumann": "Game Theory",
    "Thomas Schelling": "Game Theory", "Lloyd Shapley": "Game Theory",
    "Jean Tirole": "Game Theory", "Eric Maskin": "Game Theory",
    "Roger Myerson": "Game Theory", "Drew Fudenberg": "Game Theory",
    "Ariel Rubinstein": "Game Theory", "David Kreps": "Game Theory",
    "Robert Wilson": "Game Theory", "Paul Milgrom": "Game Theory",
    "Bengt Holmström": "Game Theory", "Oliver Hart": "Game Theory",
    # Development
    "Amartya Sen": "Development", "Abhijit Banerjee": "Development",
    "Esther Duflo": "Development", "Michael Kremer": "Development",
    "William Easterly": "Development", "Jeffrey Sachs": "Development",
    "Arthur Lewis": "Development", "Angus Deaton": "Development",
    "Theodore Schultz": "Development", "W. Arthur Lewis": "Development",
    "Partha Dasgupta": "Development",
    # Public Choice
    "James Buchanan": "Public Choice", "Bryan Caplan": "Public Choice",
    "Anthony Downs": "Public Choice",
    # Econometrics
    "Jan Tinbergen": "Econometrics", "James Heckman": "Econometrics",
    "Daniel McFadden": "Econometrics", "Joshua Angrist": "Econometrics",
    "Guido Imbens": "Econometrics", "David Card": "Econometrics",
    "Robert Engle": "Econometrics", "Jerry Hausman": "Econometrics",
    "Whitney Newey": "Econometrics",
    # Finance
    "Harry Markowitz": "Finance", "William Sharpe": "Finance",
    "Fischer Black": "Finance", "Myron Scholes": "Finance",
    "Robert Merton": "Finance", "Stephen Ross": "Finance",
    "Michael Jensen": "Finance", "Stewart Myers": "Finance",
    "Andrew Lo": "Finance",
    # Labor Economics
    "Jacob Mincer": "Labor Economics", "James Heckman": "Labor Economics",
    "Alan Krueger": "Labor Economics", "Lawrence Katz": "Labor Economics",
    "Claudia Goldin": "Labor Economics", "George Borjas": "Labor Economics",
    "Orley Ashenfelter": "Labor Economics", "Edward Lazear": "Labor Economics",
    "Richard Freeman": "Labor Economics", "Raj Chetty": "Labor Economics",
    "David Autor": "Labor Economics", "Lawrence Summers": "Labor Economics",
    "Peter Diamond": "Labor Economics",
    # International Trade
    "Elhanan Helpman": "International Trade", "Gene Grossman": "International Trade",
    "Jagdish Bhagwati": "International Trade", "Avinash Dixit": "International Trade",
    "Robert Feenstra": "International Trade", "Dani Rodrik": "International Trade",
    # Welfare & Public Economics
    "Martin Feldstein": "Welfare & Public Economics",
    "James Poterba": "Welfare & Public Economics",
    "Richard Musgrave": "Welfare & Public Economics",
    # Environmental Economics
    # (few clear seeds — LLM handles well)
}

# Build a normalize→school lookup for fuzzy seed matching
def normalize_name(name):
    name = re.sub(r'\s*\(.*?\)', '', name).strip()
    name = re.sub(r'\b[A-Z]\.\s*', '', name).strip()
    return re.sub(r'\s+', ' ', name).strip().lower()

NORM_SEEDS = {normalize_name(k): v for k, v in SEEDS.items()}


# ── Prompt ─────────────────────────────────────────────────────────────────
def build_school_list():
    lines = []
    for school in VALID_SCHOOLS:
        desc = SCHOOL_DESCRIPTIONS.get(school, "")
        lines.append(f"  • {school}: {desc}")
    return "\n".join(lines)

SCHOOL_LIST = build_school_list()

SYSTEM_PROMPT = f"""You are an expert in the history of economic thought. Your task is to classify economists into exactly one school of thought based on the provided Wikipedia text.

Valid schools (pick exactly one):
{SCHOOL_LIST}

Critical disambiguation rules:
- "Development" means ONLY research on economic development in poor/developing countries (poverty traps, aid, structural transformation). Financial market development, capital market development, or product development is NOT "Development" — classify those as Finance, Chicago School, etc.
- "Institutional" means new institutional economics, transaction cost theory, veblenian tradition — NOT just someone who studies institutions in a general sense.
- "Political Economy" means the study of how political constraints shape economic outcomes — NOT just any economist who worked on policy.
- "Econometrics" means the primary contribution is empirical methods/causal inference — NOT just an economist who uses econometrics as a tool.
- If an economist spans multiple fields, pick the one most central to their core intellectual contribution.

Respond with ONLY the school name, exactly as written in the list above. No explanation, no punctuation, nothing else."""


def make_user_message(name, extract):
    return f"Economist: {name}\n\nWikipedia extract:\n{extract[:2500]}"


# ── Wikipedia fetch ────────────────────────────────────────────────────────
def fetch_extracts(nodes):
    """Fetch Wikipedia intro extracts for a list of nodes. Returns {pageid: extract}."""
    # Build title → pageid
    title_to_id = {}
    for n in nodes:
        url = n.get("url", "")
        if "/wiki/" in url:
            title = url.split("/wiki/")[-1].split("#")[0]
            title_to_id[title] = n["id"]

    titles  = list(title_to_id.keys())
    results = {}  # pageid → extract

    total_batches = (len(titles) + WIKI_BATCH - 1) // WIKI_BATCH
    for i in range(0, len(titles), WIKI_BATCH):
        batch = titles[i : i + WIKI_BATCH]
        batch_num = i // WIKI_BATCH + 1
        print(f"  Wikipedia batch {batch_num}/{total_batches}…", end=" ", flush=True)

        api_url = (
            "https://en.wikipedia.org/w/api.php"
            "?action=query&prop=extracts&exintro=true&explaintext=true"
            f"&titles={'|'.join(batch)}&format=json&origin=*"
        )
        try:
            resp = requests.get(api_url, timeout=30,
                                headers={"User-Agent": "EconographBot/1.0"})
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            got = 0
            for page in pages.values():
                extract = page.get("extract", "")
                title   = page.get("title", "")
                if extract and title:
                    pid = (title_to_id.get(title.replace(" ", "_"))
                           or title_to_id.get(title))
                    if pid:
                        results[pid] = extract
                        got += 1
            print(f"got {got}")
        except Exception as exc:
            print(f"FAILED ({exc})")

        time.sleep(0.4)

    return results


# ── LLM classification ─────────────────────────────────────────────────────
async def classify_one(client, sem, node, extract):
    """
    Call Claude for a single economist.
    Returns (pageid, school_or_None, name).
    Returns None for school on failure so the caller can skip checkpointing.
    """
    async with sem:
        msg = make_user_message(node["name"], extract)
        for attempt in range(3):
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=20,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg}],
                )
                raw = response.content[0].text.strip().rstrip(".")
                if raw in VALID_SCHOOLS:
                    return node["id"], raw, node["name"]
                match = next((s for s in VALID_SCHOOLS if s.lower() == raw.lower()), None)
                if match:
                    return node["id"], match, node["name"]
                print(f"\n  ⚠ Unexpected LLM output for {node['name']!r}: {raw!r} → Other")
                return node["id"], "Other", node["name"]
            except anthropic.RateLimitError:
                wait = 2 ** attempt * 5
                print(f"\n  Rate limit hit for {node['name']!r}, waiting {wait}s…")
                await asyncio.sleep(wait)
            except Exception as exc:
                if attempt == 2:
                    print(f"\n  Failed {node['name']!r}: {exc}")
                    return node["id"], None, node["name"]  # None = don't checkpoint
                await asyncio.sleep(2)
    return node["id"], None, node["name"]


async def classify_all(client, candidates, extracts):
    """Classify all candidates concurrently. Only checkpoints successful calls."""
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = []
    for node in candidates:
        extract = extracts.get(node["id"], "")
        if not extract:
            continue
        tasks.append(classify_one(client, sem, node, extract))

    results = {}   # pageid → school  (only successful)
    failed  = []
    done = 0
    total = len(tasks)
    for coro in asyncio.as_completed(tasks):
        pid, school, name = await coro
        if school is not None:
            results[pid] = school
        else:
            failed.append(name)
        done += 1
        if done % 50 == 0 or done == total:
            print(f"  LLM progress {done}/{total}  ({len(results)} succeeded, {len(failed)} failed)…")

    if failed:
        print(f"\n  ⚠ {len(failed)} calls failed and were NOT checkpointed (will retry on next run):")
        for name in failed[:10]:
            print(f"    {name}")
        if len(failed) > 10:
            print(f"    … and {len(failed) - 10} more")
    return results


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("graph_path", help="Path to graph_v3.js")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify only first 20 non-seed economists (for testing)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip economists already in checkpoint file")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    # ── Load graph ──────────────────────────────────────────────────────────
    print(f"Loading {args.graph_path}…")
    with open(args.graph_path, encoding="utf-8") as f:
        raw = f.read()
    prefix     = "var graph = "
    graph_data = json.loads(raw[len(prefix):])
    nodes      = graph_data["nodes"]
    print(f"  {len(nodes)} nodes")

    # Before distribution
    before = defaultdict(int)
    for n in nodes:
        before[n["school"]] += 1

    # ── Load checkpoint ─────────────────────────────────────────────────────
    checkpoint_path = os.path.join(os.path.dirname(args.graph_path), CHECKPOINT)
    checkpoint = {}
    if args.resume and os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        print(f"  Resuming from checkpoint: {len(checkpoint)} already classified")

    # ── Identify seeds ──────────────────────────────────────────────────────
    seed_map = {}
    for node in nodes:
        school = NORM_SEEDS.get(normalize_name(node["name"]))
        if school:
            seed_map[node["id"]] = school

    print(f"  {len(seed_map)} seed economists (skipped)")

    # ── Identify candidates ─────────────────────────────────────────────────
    candidates = [
        n for n in nodes
        if n["id"] not in seed_map
        and n["id"] not in checkpoint
        and n.get("url")
    ]

    if args.dry_run:
        candidates = candidates[:20]
        print(f"  DRY RUN — classifying first {len(candidates)} candidates only")
    else:
        print(f"  {len(candidates)} economists to classify via LLM")

    if not candidates:
        print("  Nothing to do.")
    else:
        # ── Fetch Wikipedia extracts ────────────────────────────────────────
        print(f"\nFetching Wikipedia extracts ({len(candidates)} economists)…")
        extracts = fetch_extracts(candidates)
        print(f"  Got extracts for {len(extracts)}/{len(candidates)} economists")

        # ── Run LLM classification ──────────────────────────────────────────
        print(f"\nClassifying with {MODEL} (concurrency={CONCURRENCY})…")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        llm_results = asyncio.run(classify_all(client, candidates, extracts))
        print(f"  LLM returned {len(llm_results)} classifications")

        # Merge into checkpoint
        checkpoint.update(llm_results)

        # Save checkpoint
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, indent=2)
        print(f"  Checkpoint saved to {checkpoint_path}")

    # ── Apply all assignments ───────────────────────────────────────────────
    print("\nApplying assignments…")
    changes = []
    for node in nodes:
        pid = node["id"]
        old = node["school"]

        if pid in seed_map:
            new = seed_map[pid]
        elif pid in checkpoint:
            new = checkpoint[pid]
        else:
            new = old  # no extract available — keep existing

        if new != old:
            changes.append((node["name"], old, new))
            node["school"] = new

    # ── Report ──────────────────────────────────────────────────────────────
    print(f"  {len(changes)} school assignments changed\n")
    if changes:
        col_w = max(len(c[1]) for c in changes)
        for name, old, new in sorted(changes, key=lambda x: x[0]):
            print(f"  {name:<38}  {old:<{col_w}}  →  {new}")

    after = defaultdict(int)
    for n in nodes:
        after[n["school"]] += 1

    all_schools = sorted(set(list(before) + list(after)), key=lambda s: -after.get(s, 0))
    print("\nSchool distribution (before → after):")
    for school in all_schools:
        b, a = before.get(school, 0), after.get(school, 0)
        diff = a - b
        tag  = f"({'+' if diff >= 0 else ''}{diff})" if diff else ""
        print(f"  {school:<32}  {b:4d} → {a:4d}  {tag}")

    # ── Backup + write ───────────────────────────────────────────────────────
    backup = args.graph_path + ".bak"
    print(f"\nBacking up to {backup}…")
    shutil.copy2(args.graph_path, backup)

    print(f"Writing {args.graph_path}…")
    with open(args.graph_path, "w", encoding="utf-8") as f:
        f.write(prefix)
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Done. {len(changes)} nodes retagged.")


if __name__ == "__main__":
    main()
