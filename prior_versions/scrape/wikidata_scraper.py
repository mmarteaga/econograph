#!/usr/bin/env python3
"""
Wikidata Economist Scraper
==========================
Queries the Wikidata SPARQL endpoint to collect structured data on economists.

Why Wikidata instead of scraping Wikipedia HTML?
- Structured, machine-readable relationships (no fragile HTML parsing)
- Much broader coverage: thousands of economists vs. ~1,300 from the list page
- Explicit school-of-thought / movement tags (P135)
- Clean birth dates, not messy strings to regex-parse
- Exact influence relationships (P737), doctoral advisor (P184), students (P185)

Output: economists_wikidata.json
Format is compatible with build_graph/transform_v3.py

Usage:
    python3 wikidata_scraper.py

    # Resume from a previous partial run:
    python3 wikidata_scraper.py --resume
"""

import requests
import json
import time
import argparse
import sys
import os
import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
OUTPUT_FILE = "economists_wikidata.json"
PROGRESS_FILE = "economists_wikidata_progress.json"

HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "EconographBot/1.0 (educational history-of-economics visualization; non-commercial)"
}

# Wikidata QIDs for economist-adjacent occupations to include
# Q188094 = economist, Q4693352 = economic historian, Q2606656 = political economist
ECONOMIST_TYPES = ["wd:Q188094", "wd:Q4693352", "wd:Q2606656"]

PAGE_SIZE = 5000   # results per SPARQL page (well under the 10k soft limit)
REQUEST_DELAY = 2  # seconds between requests (be nice to Wikidata)


# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------

def sparql_query(query, retries=3):
    """Execute a SPARQL query against the Wikidata endpoint with retry logic."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=90
            )
            resp.raise_for_status()
            return resp.json()["results"]["bindings"]
        except Exception as e:
            wait = REQUEST_DELAY * (2 ** attempt)
            print(f"  Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    print("  All retries exhausted. Returning empty result.")
    return []


def val(binding, key):
    """Safely extract a value from a SPARQL result binding."""
    return binding.get(key, {}).get("value")


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_wikidata_date(date_str):
    """
    Convert a Wikidata date string to a Unix timestamp in seconds.
    Wikidata dates look like: +1883-12-05T00:00:00Z or -0383-01-01T00:00:00Z
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    try:
        date_str = date_str.lstrip("+")
        # Take only the date portion YYYY-MM-DD (or -YYYY-MM-DD for BCE)
        if date_str.startswith("-"):
            date_part = date_str[:11]  # -YYYY-MM-DD
        else:
            date_part = date_str[:10]  # YYYY-MM-DD

        # Wikidata uses 00 for unknown month/day — clamp to 01
        parts = date_part.lstrip("-").split("-")
        if len(parts) < 1:
            return None
        year   = parts[0] if len(parts) > 0 else "01"
        month  = parts[1] if len(parts) > 1 else "01"
        day    = parts[2] if len(parts) > 2 else "01"
        month  = max(1, int(month))
        day    = max(1, int(day))

        prefix = "-" if date_str.startswith("-") else ""
        date_clean = f"{prefix}{year}-{month:02d}-{day:02d}"

        dt = np.datetime64(date_clean)
        return int(dt.astype("datetime64[s]").astype(np.int64))
    except Exception:
        return None


def qid_to_numeric(uri):
    """Extract the numeric part from a Wikidata entity URI or QID string.
    e.g. 'http://www.wikidata.org/entity/Q7174' -> '7174'
    """
    if not uri:
        return None
    # Strip URI prefix if present
    qid = uri.split("/")[-1]
    if qid.startswith("Q"):
        return qid[1:]
    return None


# ---------------------------------------------------------------------------
# SPARQL queries
# ---------------------------------------------------------------------------

def build_type_filter():
    """Build the SPARQL filter clause for economist types."""
    clauses = [f"{{ ?person wdt:P106 {t} }}" for t in ECONOMIST_TYPES]
    return "{\n  " + "\n  UNION\n  ".join(clauses) + "\n}"


def fetch_economists_page(offset):
    """
    Fetch one page of economists with basic biographical info.
    Filtered to those with English Wikipedia articles (more notable, more data).
    This cuts 56k total down to ~13k meaningfully connected economists.
    """
    type_filter = build_type_filter()
    query = f"""
SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?image ?article WHERE {{
  {type_filter}
  # Only include economists with an English Wikipedia article
  ?article schema:about ?person ;
           schema:inLanguage "en" ;
           schema:isPartOf <https://en.wikipedia.org/> .
  OPTIONAL {{ ?person wdt:P569 ?birthDate }}
  OPTIONAL {{ ?person wdt:P570 ?deathDate }}
  OPTIONAL {{ ?person wdt:P18  ?image }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
ORDER BY ?person
LIMIT {PAGE_SIZE}
OFFSET {offset}
"""
    return sparql_query(query)


def fetch_movements():
    """Fetch school-of-thought / movement tags for all economists."""
    type_filter = build_type_filter()
    query = f"""
SELECT DISTINCT ?person ?movementLabel WHERE {{
  {type_filter}
  ?person wdt:P135 ?movement .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
"""
    return sparql_query(query)


def fetch_influences():
    """Fetch 'influenced by' relationships (P737) among economists."""
    type_filter = build_type_filter()
    query = f"""
SELECT DISTINCT ?person ?influencer ?influencerLabel WHERE {{
  {type_filter}
  ?person wdt:P737 ?influencer .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
"""
    return sparql_query(query)


def fetch_advisors():
    """Fetch doctoral advisor relationships (P184)."""
    type_filter = build_type_filter()
    query = f"""
SELECT DISTINCT ?person ?advisor ?advisorLabel WHERE {{
  {type_filter}
  ?person wdt:P184 ?advisor .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
"""
    return sparql_query(query)


def fetch_students():
    """Fetch doctoral student relationships (P185)."""
    type_filter = build_type_filter()
    query = f"""
SELECT DISTINCT ?person ?student ?studentLabel WHERE {{
  {type_filter}
  ?person wdt:P185 ?student .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
"""
    return sparql_query(query)


# ---------------------------------------------------------------------------
# Main scraping logic
# ---------------------------------------------------------------------------

def fetch_all_economists():
    """
    Paginate through Wikidata to collect all economists.
    Returns a dict keyed by QID numeric string.
    """
    economists = {}
    offset = 0
    page = 0

    print("Fetching economists from Wikidata (paginated)...")
    while True:
        page += 1
        print(f"  Page {page} (offset {offset})...", end=" ", flush=True)
        rows = fetch_economists_page(offset)
        print(f"{len(rows)} results")

        if not rows:
            break

        for row in rows:
            person_uri = val(row, "person")
            if not person_uri:
                continue
            qid = qid_to_numeric(person_uri)
            if not qid:
                continue

            # First occurrence of a QID wins for basic fields
            # (DISTINCT may still give multiple rows for different birth dates)
            if qid not in economists:
                economists[qid] = {
                    "pageid": qid,
                    "name": val(row, "personLabel"),
                    "born": parse_wikidata_date(val(row, "birthDate")),
                    "died": parse_wikidata_date(val(row, "deathDate")),
                    "img": val(row, "image"),
                    "url": val(row, "article"),
                    "school": [],
                    "influences": [],
                    "doctoral_advisors": [],
                    "doctoral_students": [],
                }
            else:
                # Fill in fields that might have been missing on first encounter
                entry = economists[qid]
                if entry["born"] is None:
                    entry["born"] = parse_wikidata_date(val(row, "birthDate"))
                if entry["died"] is None:
                    entry["died"] = parse_wikidata_date(val(row, "deathDate"))
                if entry["img"] is None:
                    entry["img"] = val(row, "image")
                if entry["url"] is None:
                    entry["url"] = val(row, "article")

        if len(rows) < PAGE_SIZE:
            # Last page — no more data
            break

        offset += PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    print(f"  Total economists found: {len(economists)}")
    return economists


def enrich_movements(economists):
    """Add school-of-thought labels from Wikidata P135."""
    print("Fetching school-of-thought movements...", end=" ", flush=True)
    rows = fetch_movements()
    print(f"{len(rows)} rows")

    for row in rows:
        person_uri = val(row, "person")
        movement_label = val(row, "movementLabel")
        if not person_uri or not movement_label:
            continue
        qid = qid_to_numeric(person_uri)
        if qid in economists:
            if movement_label not in economists[qid]["school"]:
                economists[qid]["school"].append(movement_label)

    time.sleep(REQUEST_DELAY)


def enrich_influences(economists):
    """Add 'influenced by' relationships (P737)."""
    print("Fetching influence relationships...", end=" ", flush=True)
    rows = fetch_influences()
    print(f"{len(rows)} rows")

    # Build QID -> name map first so we can store names in the output
    qid_to_name = {qid: d["name"] for qid, d in economists.items() if d["name"]}

    for row in rows:
        person_uri = val(row, "person")
        influencer_uri = val(row, "influencer")
        influencer_label = val(row, "influencerLabel")
        if not person_uri or not influencer_uri:
            continue

        person_qid = qid_to_numeric(person_uri)
        influencer_qid = qid_to_numeric(influencer_uri)

        if person_qid not in economists:
            continue

        # Use the canonical name from our economist list if available,
        # otherwise fall back to the label returned by Wikidata.
        name = qid_to_name.get(influencer_qid) or influencer_label
        if name and name not in economists[person_qid]["influences"]:
            economists[person_qid]["influences"].append(name)

    time.sleep(REQUEST_DELAY)


def enrich_advisors(economists):
    """Add doctoral advisor relationships (P184)."""
    print("Fetching doctoral advisor relationships...", end=" ", flush=True)
    rows = fetch_advisors()
    print(f"{len(rows)} rows")

    qid_to_name = {qid: d["name"] for qid, d in economists.items() if d["name"]}

    for row in rows:
        person_uri = val(row, "person")
        advisor_uri = val(row, "advisor")
        advisor_label = val(row, "advisorLabel")
        if not person_uri or not advisor_uri:
            continue

        person_qid = qid_to_numeric(person_uri)
        advisor_qid = qid_to_numeric(advisor_uri)

        if person_qid not in economists:
            continue

        name = qid_to_name.get(advisor_qid) or advisor_label
        if name and name not in economists[person_qid]["doctoral_advisors"]:
            economists[person_qid]["doctoral_advisors"].append(name)

    time.sleep(REQUEST_DELAY)


def enrich_students(economists):
    """Add doctoral student relationships (P185)."""
    print("Fetching doctoral student relationships...", end=" ", flush=True)
    rows = fetch_students()
    print(f"{len(rows)} rows")

    qid_to_name = {qid: d["name"] for qid, d in economists.items() if d["name"]}

    for row in rows:
        person_uri = val(row, "person")
        student_uri = val(row, "student")
        student_label = val(row, "studentLabel")
        if not person_uri or not student_uri:
            continue

        person_qid = qid_to_numeric(person_uri)
        student_qid = qid_to_numeric(student_uri)

        if person_qid not in economists:
            continue

        name = qid_to_name.get(student_qid) or student_label
        if name and name not in economists[person_qid]["doctoral_students"]:
            economists[person_qid]["doctoral_students"].append(name)

    time.sleep(REQUEST_DELAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def print_summary(economists):
    """Print a summary of what was collected."""
    total = len(economists)
    with_born = sum(1 for e in economists.values() if e["born"] is not None)
    with_influences = sum(1 for e in economists.values() if e["influences"])
    with_advisors = sum(1 for e in economists.values() if e["doctoral_advisors"])
    with_school = sum(1 for e in economists.values() if e["school"])
    with_img = sum(1 for e in economists.values() if e["img"])
    with_url = sum(1 for e in economists.values() if e["url"])

    print("\n" + "="*50)
    print("SCRAPE SUMMARY")
    print("="*50)
    print(f"Total economists:          {total:>6}")
    print(f"With birth date:           {with_born:>6}  ({100*with_born/total:.1f}%)")
    print(f"With influences:           {with_influences:>6}  ({100*with_influences/total:.1f}%)")
    print(f"With doctoral advisors:    {with_advisors:>6}  ({100*with_advisors/total:.1f}%)")
    print(f"With school of thought:    {with_school:>6}  ({100*with_school/total:.1f}%)")
    print(f"With image:                {with_img:>6}  ({100*with_img/total:.1f}%)")
    print(f"With Wikipedia URL:        {with_url:>6}  ({100*with_url/total:.1f}%)")

    # Top 10 most connected by influence count
    top = sorted(economists.values(), key=lambda e: len(e["influences"]), reverse=True)[:10]
    print("\nTop 10 by number of listed influences:")
    for e in top:
        print(f"  {len(e['influences']):>3} influences — {e['name']}")

    # School distribution
    from collections import Counter
    school_counts = Counter()
    for e in economists.values():
        for s in e["school"]:
            school_counts[s] += 1
    print("\nTop 15 schools of thought found:")
    for school, count in school_counts.most_common(15):
        print(f"  {count:>4} — {school}")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Scrape economist data from Wikidata")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from a previous partial run (loads progress file)")
    args = parser.parse_args()

    # --- Step 1: Fetch or load economists ---
    if args.resume and os.path.exists(PROGRESS_FILE):
        print(f"Resuming from {PROGRESS_FILE}...")
        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f)
        economists = progress.get("economists", {})
        completed = set(progress.get("completed_steps", []))
        print(f"  Loaded {len(economists)} economists. Completed steps: {completed}")
    else:
        economists = {}
        completed = set()

    if "fetch" not in completed:
        economists = fetch_all_economists()
        completed.add("fetch")
        # Save progress
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"economists": economists, "completed_steps": list(completed)}, f)

    # --- Step 2: Enrich with relationships ---
    if "movements" not in completed:
        enrich_movements(economists)
        completed.add("movements")
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"economists": economists, "completed_steps": list(completed)}, f)

    if "influences" not in completed:
        enrich_influences(economists)
        completed.add("influences")
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"economists": economists, "completed_steps": list(completed)}, f)

    if "advisors" not in completed:
        enrich_advisors(economists)
        completed.add("advisors")
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"economists": economists, "completed_steps": list(completed)}, f)

    if "students" not in completed:
        enrich_students(economists)
        completed.add("students")
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"economists": economists, "completed_steps": list(completed)}, f)

    # --- Step 3: Write final output ---
    output = list(economists.values())
    print(f"\nWriting {len(output)} economists to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print_summary(economists)

    print(f"\nDone. Output written to: scrape/{OUTPUT_FILE}")
    print("Next step: python3 build_graph/transform_v3.py scrape/economists_wikidata.json")

    # Clean up progress file on success
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()
