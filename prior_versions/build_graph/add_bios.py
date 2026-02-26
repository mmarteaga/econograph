#!/usr/bin/env python3
"""
add_bios.py — adds a 'bio' field (Wikipedia intro text) to every node
in graph_v3.js, used by the MiniSearch-powered Research Assistant.

Run from the build_graph/ directory:
    python3 add_bios.py

Output: ../visualize_v3/js/graph_v3.js (updated in place, backup saved)
"""

import json, re, shutil, time
from urllib.parse import unquote
import requests

GRAPH_PATH = '../visualize_v3/js/graph_v3.js'
WIKI_API   = 'https://en.wikipedia.org/w/api.php'
BATCH_SIZE = 20      # Wikipedia API hard cap for prop=extracts with exintro
BIO_CHARS  = 450     # characters to store per economist


def load_graph():
    with open(GRAPH_PATH, encoding='utf-8') as f:
        raw = f.read()
    assert raw.startswith('var graph = '), 'Unexpected graph file format'
    return json.loads(raw[len('var graph = '):])


def save_graph(data):
    backup = GRAPH_PATH + '.bak_prebio'
    shutil.copy(GRAPH_PATH, backup)
    print(f'Backup saved to {backup}')
    with open(GRAPH_PATH, 'w', encoding='utf-8') as f:
        f.write('var graph = ')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Written to {GRAPH_PATH}')


def title_from_url(url):
    if not url:
        return None
    parts = url.split('/wiki/')
    if len(parts) < 2:
        return None
    return unquote(parts[1].split('#')[0]).replace('_', ' ')


def fetch_batch(titles):
    """Fetch Wikipedia intro extracts for up to BATCH_SIZE titles."""
    r = requests.get(WIKI_API, params={
        'action':      'query',
        'titles':      '|'.join(titles),
        'prop':        'extracts',
        'exintro':     True,
        'explaintext': True,
        'exsentences': 4,
        'format':      'json',
        'formatversion': 2,
    }, headers={'User-Agent': 'econograph/2.0 (contact: github.com/mmarteaga)'}, timeout=20)
    r.raise_for_status()
    out = {}
    for page in r.json().get('query', {}).get('pages', []):
        title   = page.get('title', '')
        extract = (page.get('extract') or '').strip()
        if extract:
            # Collapse extra whitespace, truncate
            extract = re.sub(r'\s+', ' ', extract)
            out[title] = extract[:BIO_CHARS]
    return out


def main():
    data  = load_graph()
    nodes = data['nodes']
    print(f'{len(nodes)} nodes loaded')

    # Build title → [nodes] map
    title_map = {}
    for n in nodes:
        t = title_from_url(n.get('url'))
        if t:
            title_map.setdefault(t, []).append(n)
    print(f'URLs found for {len(title_map)} nodes')

    titles  = list(title_map.keys())
    batches = [titles[i:i + BATCH_SIZE] for i in range(0, len(titles), BATCH_SIZE)]
    extracts = {}

    for i, batch in enumerate(batches, 1):
        print(f'  batch {i}/{len(batches)}…', end=' ', flush=True)
        try:
            got = fetch_batch(batch)
            extracts.update(got)
            print(f'{len(got)}')
        except Exception as e:
            print(f'ERROR: {e}')
        time.sleep(0.08)   # be polite to Wikipedia

    print(f'Got extracts for {len(extracts)}/{len(title_map)} economists')

    # Stamp bio onto each node
    added = 0
    for title, ns in title_map.items():
        bio = extracts.get(title, '')
        for n in ns:
            n['bio'] = bio
            if bio:
                added += 1

    # Nodes with no URL or no extract → empty string (so field always exists)
    for n in nodes:
        n.setdefault('bio', '')

    print(f'Bio added to {added} nodes, empty string on remaining {len(nodes) - added}')
    save_graph(data)
    print('Done.')


if __name__ == '__main__':
    main()
