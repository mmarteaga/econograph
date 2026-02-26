"""
annotate_connections.py

Adds advisorIds, studentIds, and influencedByIds fields to each node in
../visualize_v3/js/graph_v3.js, using data from ../scrape/economists_wikidata.json.

Usage:
    python annotate_connections.py
(Run from /Users/mardoqueo/Documents/Website/econograph/build_graph/)
"""

import json
import shutil
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to this script's directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
GRAPH_JS   = SCRIPT_DIR / "../visualize_v3/js/graph_v3.js"
WIKIDATA   = SCRIPT_DIR / "../scrape/economists_wikidata.json"
BACKUP     = GRAPH_JS.with_suffix(".js.bak_preconn")

GRAPH_PREFIX = "var graph = "


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize_name(name: str) -> str:
    """Strip diacritics, lowercase, strip whitespace."""
    nfd = unicodedata.normalize("NFD", name)
    ascii_bytes = nfd.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii").lower().strip()


# ---------------------------------------------------------------------------
# 1. Load graph_v3.js
# ---------------------------------------------------------------------------
print("Loading graph_v3.js …")
raw = GRAPH_JS.read_text(encoding="utf-8")
if not raw.startswith(GRAPH_PREFIX):
    raise ValueError(f"graph_v3.js does not start with '{GRAPH_PREFIX}'")

graph = json.loads(raw[len(GRAPH_PREFIX):])
nodes = graph["nodes"]
print(f"  {len(nodes)} nodes, {len(graph['links'])} links")


# ---------------------------------------------------------------------------
# 2. Load economists_wikidata.json
# ---------------------------------------------------------------------------
print("Loading economists_wikidata.json …")
wikidata_list = json.loads(WIKIDATA.read_text(encoding="utf-8"))
print(f"  {len(wikidata_list)} wikidata entries")


# ---------------------------------------------------------------------------
# 3. Build pageid → wikidata_entry dict (pageids as strings)
# ---------------------------------------------------------------------------
pageid_to_entry: dict[str, dict] = {}
for entry in wikidata_list:
    pid = str(entry["pageid"])
    pageid_to_entry[pid] = entry

print(f"  {len(pageid_to_entry)} unique pageids in wikidata")


# ---------------------------------------------------------------------------
# 4. Build normalized_name → graph_node_id dict
# ---------------------------------------------------------------------------
norm_name_to_node_id: dict[str, str] = {}
for node in nodes:
    nname = normalize_name(node["name"])
    # If two nodes share the same normalized name, last one wins (edge case)
    norm_name_to_node_id[nname] = node["id"]

print(f"  {len(norm_name_to_node_id)} unique normalized names in graph")


# ---------------------------------------------------------------------------
# 5. Annotate each node
# ---------------------------------------------------------------------------
nodes_with_wikidata = 0
total_advisors      = 0
total_students      = 0
total_influences    = 0

# Build a set of all valid node IDs for fast membership check
valid_node_ids = {node["id"] for node in nodes}

for node in nodes:
    node_id = node["id"]
    entry   = pageid_to_entry.get(node_id)

    if entry is None:
        # No wikidata entry — set empty arrays
        node["advisorIds"]      = []
        node["studentIds"]      = []
        node["influencedByIds"] = []
        continue

    nodes_with_wikidata += 1

    # Helper: resolve a list of names → matched node IDs (strings)
    def resolve_names(names: list) -> list[str]:
        result = []
        for raw_name in names:
            nname = normalize_name(raw_name)
            matched_id = norm_name_to_node_id.get(nname)
            if matched_id and matched_id in valid_node_ids and matched_id != node_id:
                result.append(matched_id)
        return result

    advisor_ids   = resolve_names(entry.get("doctoral_advisors", []))
    student_ids   = resolve_names(entry.get("doctoral_students",  []))
    influence_ids = resolve_names(entry.get("influences",         []))

    node["advisorIds"]      = advisor_ids
    node["studentIds"]      = student_ids
    node["influencedByIds"] = influence_ids

    total_advisors   += len(advisor_ids)
    total_students   += len(student_ids)
    total_influences += len(influence_ids)


# ---------------------------------------------------------------------------
# 6. Ensure every node has the three fields (belt-and-suspenders)
# ---------------------------------------------------------------------------
for node in nodes:
    node.setdefault("advisorIds",      [])
    node.setdefault("studentIds",      [])
    node.setdefault("influencedByIds", [])


# ---------------------------------------------------------------------------
# 7. Backup and write graph_v3.js
# ---------------------------------------------------------------------------
print(f"Backing up graph_v3.js → {BACKUP.name} …")
shutil.copy2(GRAPH_JS, BACKUP)

print("Writing updated graph_v3.js …")
compact_json = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
GRAPH_JS.write_text(GRAPH_PREFIX + compact_json, encoding="utf-8")
print(f"  Written {GRAPH_JS.stat().st_size:,} bytes")


# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
print()
print("=== Summary ===")
print(f"  Total graph nodes           : {len(nodes)}")
print(f"  Nodes with wikidata entries : {nodes_with_wikidata}")
print(f"  Total advisor links found   : {total_advisors}")
print(f"  Total student links found   : {total_students}")
print(f"  Total influence links found : {total_influences}")
print(f"  Grand total connection links: {total_advisors + total_students + total_influences}")
