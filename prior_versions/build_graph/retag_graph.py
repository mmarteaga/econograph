"""
retag_graph.py — Standalone retagger for graph_v3.js
=====================================================
Reads graph_v3.js directly (no economists_v3.json needed), reassigns school
of thought for every economist using:

  1. Seed assignment (normalized name matching — strips middle initials)
  2. Wikipedia NLP for all non-seed economists with a URL
  3. Keeps existing school only for those with no URL and no seed match

Writes the result back to graph_v3.js (backs up original to graph_v3.js.bak).

Usage:
    cd build_graph/
    python3 retag_graph.py ../visualize_v3/js/graph_v3.js
"""

import json
import re
import sys
import time
import shutil
import requests
from collections import defaultdict


# ── Seed definitions (authoritative, never overridden by NLP) ─────────────
SCHOOL_SEEDS = {
    'Austrian School': [
        'Carl Menger', 'Ludwig von Mises', 'Friedrich Hayek', 'Eugen von Böhm-Bawerk',
        'Murray Rothbard', 'Israel Kirzner', 'Friedrich von Wieser', 'Hans-Hermann Hoppe',
        'Jesús Huerta de Soto', 'Peter Boettke', 'Roger Garrison', 'Henry Hazlitt',
        'F. A. Harper', 'Leonard Read', 'Walter Block', 'Hans Sennholz', 'George Reisman',
        'Gottfried Haberler', 'Fritz Machlup', 'Oskar Morgenstern', 'Joseph Salerno',
    ],
    'Chicago School': [
        'Milton Friedman', 'George Stigler', 'Gary Becker', 'Robert Lucas Jr.',
        'Eugene Fama', 'Richard Posner', 'Ronald Coase', 'Aaron Director',
        'Frank Knight', 'Jacob Viner', 'Henry Simons', 'Thomas Sowell',
        'Sam Peltzman', 'Harold Demsetz', 'Sherwin Rosen', 'Kevin Murphy',
        'Robert Fogel', 'Douglass North', 'Lars Peter Hansen', 'John Cochrane',
        'Steven Levitt', 'Casey Mulligan', 'Steven Cheung', 'Armen Alchian',
    ],
    'Keynesian': [
        'John Maynard Keynes', 'John Hicks', 'Paul Samuelson', 'James Tobin',
        'Franco Modigliani', 'Robert Solow', 'Lawrence Klein', 'Alvin Hansen',
        'Joan Robinson', 'Nicholas Kaldor', 'Michal Kalecki', 'Roy Harrod',
        'Abba Lerner', 'Evsey Domar', 'Richard Kahn', 'Austin Robinson',
        'James Meade', 'Richard Musgrave', 'Arthur Okun', 'Walter Heller',
    ],
    'New Keynesian': [
        'Joseph Stiglitz', 'Paul Krugman', 'Gregory Mankiw', 'Olivier Blanchard',
        'Janet Yellen', 'Ben Bernanke', 'Michael Woodford', 'Jordi Galí',
        'Lawrence Summers', 'Stanley Fischer', 'John Taylor', 'Julio Rotemberg',
        'David Romer', 'Alan Blinder', 'Frederic Mishkin', 'Mark Gertler',
        'Nobuhiro Kiyotaki', 'Gauti Eggertsson', 'Ivan Werning', 'Emmanuel Farhi',
    ],
    'Classical/Neoclassical': [
        'Adam Smith', 'David Ricardo', 'John Stuart Mill', 'Alfred Marshall',
        'Léon Walras', 'William Stanley Jevons', 'Vilfredo Pareto', 'Jean-Baptiste Say',
        'Nassau William Senior', 'Thomas Malthus', 'Francis Edgeworth', 'Knut Wicksell',
        'Irving Fisher', 'Arthur Pigou', 'Philip Wicksteed', 'John Bates Clark',
        'Frédéric Bastiat', 'Richard Cantillon', 'Anne Robert Jacques Turgot',
        'Gustave de Molinari', 'David Hume', 'François Quesnay', 'Henry George',
    ],
    'Marxian': [
        'Karl Marx', 'Friedrich Engels', 'Rosa Luxemburg', 'Rudolf Hilferding',
        'Paul Sweezy', 'Ernest Mandel', 'Maurice Dobb', 'Paul Baran',
        'Piero Sraffa', 'Ian Steedman', 'Andrew Kliman', 'Anwar Shaikh',
        'Michael Hudson', 'David Harvey', 'Richard Wolff', 'Samuel Bowles',
        'Herbert Gintis', 'Duncan Foley', 'John Roemer', 'Gerald Cohen',
    ],
    'Institutional': [
        'Thorstein Veblen', 'John Commons', 'Wesley Mitchell', 'John Kenneth Galbraith',
        'Clarence Ayres', 'Gunnar Myrdal', 'Geoffrey Hodgson', 'Ha-Joon Chang',
        'Douglass North', 'Oliver Williamson', 'Elinor Ostrom', 'Daron Acemoglu',
        'Karl Polanyi', 'Albert Hirschman', 'Kenneth Boulding', 'Warren Samuels',
    ],
    'Behavioral': [
        'Daniel Kahneman', 'Amos Tversky', 'Richard Thaler', 'Robert Shiller',
        'George Akerlof', 'Colin Camerer', 'Dan Ariely', 'Sendhil Mullainathan',
        'Cass Sunstein', 'Matthew Rabin', 'Ernst Fehr', 'David Laibson',
        'Stefano DellaVigna', 'Ulrike Malmendier', 'Xavier Gabaix',
        # NOTE: Raj Chetty intentionally NOT here — see Labor Economics
    ],
    'Welfare & Public Economics': [
        'Martin Feldstein',   # public finance — Wikipedia intro doesn't say "public finance"
        'James Poterba',      # same: public finance, tax policy
        'N. Gregory Mankiw',  # also New Keynesian seed, but tax/fiscal work fits here
        'Peter Diamond',      # also Labor seed — pension/social security work fits here
    ],
    'Development': [
        'Theodore Schultz',   # Nobel 1979 — "agricultural economist" in intro, not "development economics"
        'W. Arthur Lewis',    # Nobel 1979 — development economist
    ],
    'Game Theory': [
        'John von Neumann', 'John Nash', 'John Harsanyi', 'Reinhard Selten',
        'Robert Aumann', 'Thomas Schelling', 'Lloyd Shapley', 'Alvin Roth',
        'Jean Tirole', 'Eric Maskin', 'Roger Myerson', 'Drew Fudenberg',
        'Ariel Rubinstein', 'Ken Binmore', 'Ehud Kalai', 'David Kreps',
        'Robert Wilson', 'Paul Milgrom', 'Bengt Holmström', 'Oliver Hart',
    ],
    'Development': [
        'Amartya Sen', 'Abhijit Banerjee', 'Esther Duflo', 'Michael Kremer',
        'William Easterly', 'Jeffrey Sachs', 'Daron Acemoglu', 'James Robinson',
        'Arthur Lewis', 'Albert Hirschman', 'Raúl Prebisch', 'Hans Singer',
        'Paul Rosenstein-Rodan', 'Ragnar Nurkse', 'W. W. Rostow', 'Hernando de Soto',
        'Robert Barro', 'Xavier Sala-i-Martin', 'Partha Dasgupta', 'Angus Deaton',
    ],
    'Public Choice': [
        'James Buchanan', 'Gordon Tullock', 'Mancur Olson', 'William Niskanen',
        'Bryan Caplan', 'Anthony Downs', 'Dennis Mueller', 'Geoffrey Brennan',
        'Dwight Lee', 'Robert Tollison', 'Randall Holcombe', 'Peter Leeson',
    ],
    'Econometrics': [
        'Ragnar Frisch', 'Jan Tinbergen', 'Trygve Haavelmo', 'Lawrence Klein',
        'Clive Granger', 'Christopher Sims', 'James Heckman', 'Daniel McFadden',
        'Joshua Angrist', 'Guido Imbens', 'David Card', 'Robert Engle',
        'Halbert White', 'Jerry Hausman', 'Whitney Newey', 'Lars Peter Hansen',
        'Edward Leamer', 'Arnold Zellner', 'Takeshi Amemiya', 'Peter Phillips',
    ],
    'Finance': [
        'Harry Markowitz', 'William Sharpe', 'Fischer Black', 'Myron Scholes',
        'Robert Merton', 'Eugene Fama', 'Kenneth French', 'John Campbell',
        'Stephen Ross', 'Michael Jensen', 'Stewart Myers', 'John Lintner',
        'Franco Modigliani', 'Merton Miller', 'Andrew Lo', 'Robert Shiller',
    ],
    'Labor Economics': [
        'Jacob Mincer', 'Gary Becker', 'James Heckman', 'David Card',
        'Alan Krueger', 'Lawrence Katz', 'Claudia Goldin', 'George Borjas',
        'Orley Ashenfelter', 'Edward Lazear', 'Sherwin Rosen', 'Richard Freeman',
        'Raj Chetty', 'David Autor', 'Lawrence Summers', 'Peter Diamond',
        'Henry Farber', 'Sandra Black', 'Jeffrey Liebman',
    ],
    'International Trade': [
        'Paul Krugman', 'Elhanan Helpman', 'Gene Grossman', 'Marc Melitz',
        'Jagdish Bhagwati', 'Anne Krueger', 'Avinash Dixit', 'Robert Feenstra',
        'Dani Rodrik', 'Douglas Irwin', 'Robert Baldwin', 'Ronald Jones',
    ],
}

# ── NLP keyword taxonomy ───────────────────────────────────────────────────
FIELD_KEYWORDS = {
    'Classical/Neoclassical': [
        'classical economics', 'neoclassical economics', 'general equilibrium',
        'marginalist', 'marginal utility', 'laissez-faire', 'invisible hand',
        'political economy of', 'physiocrat', 'mercantil',
    ],
    'Keynesian': [
        'keynesian', 'aggregate demand', 'fiscal stimulus', 'liquidity trap',
        'effective demand', 'post-keynesian', 'income-expenditure',
    ],
    'New Keynesian': [
        'new keynesian', 'sticky prices', 'nominal rigidities', 'dsge',
        'dynamic stochastic general equilibrium', 'new neoclassical synthesis',
    ],
    'Austrian School': [
        'austrian school', 'praxeology', 'spontaneous order', 'von mises',
        'hayekian', 'capital theory', 'business cycle theory',
    ],
    'Chicago School': [
        'chicago school', 'price theory', 'law and economics',
        'rational expectations', 'monetarism', 'free-market economics',
    ],
    'Marxian': [
        'marxian', 'marxist economics', 'historical materialism',
        'surplus value', 'capital accumulation', 'class struggle',
        'mode of production', 'political economy of capitalism',
    ],
    'Institutional': [
        'institutional economics', 'institutionalism', 'transaction cost',
        'path dependence', 'evolutionary economics', 'veblenian',
        'new institutional economics',
    ],
    'Behavioral': [
        'behavioral economics', 'behavioural economics', 'cognitive bias',
        'bounded rationality', 'prospect theory', 'nudge theory',
        'heuristics and biases', 'dual process',
    ],
    'Game Theory': [
        'game theory', 'nash equilibrium', 'mechanism design',
        'auction theory', 'matching theory', 'cooperative game',
        'non-cooperative game', 'bargaining theory',
    ],
    'Development': [
        'development economics', 'economic development',
        'poverty trap', 'aid effectiveness', 'structural transformation',
        'dependency theory', 'modernization theory',
    ],
    'Public Choice': [
        'public choice', 'constitutional economics', 'rent-seeking',
        'social choice theory', 'voting theory', 'bureaucracy theory',
    ],
    'Econometrics': [
        'econometrics', 'instrumental variables', 'regression discontinuity',
        'difference-in-differences', 'panel data', 'time series analysis',
        'causal inference', 'identification strategy',
    ],
    'Finance': [
        'financial economics', 'asset pricing', 'efficient market hypothesis',
        'portfolio theory', 'option pricing', 'financial intermediation',
        'corporate finance', 'investment theory',
    ],
    'Labor Economics': [
        'labor economics', 'labour economics', 'wage determination',
        'human capital theory', 'job search theory', 'minimum wage',
        'labor market', 'collective bargaining',
    ],
    'International Trade': [
        'international trade', 'trade theory', 'comparative advantage',
        'heckscher-ohlin', 'new trade theory', 'gravity model of trade',
        'trade policy', 'globalization',
    ],
    'Economic History': [
        'economic history', 'cliometrics', 'historical economics',
        'industrial revolution', 'great depression', 'economic historian',
        'long-run economic', 'archival economic',
    ],
    'Political Economy': [
        'political economy', 'political economics', 'electoral economics',
        'distributive politics', 'state capacity', 'economic institutions',
        'political institutions',
    ],
    'Welfare & Public Economics': [
        'welfare economics', 'public economics', 'public finance',
        'taxation theory', 'public goods', 'social welfare function',
        'optimal taxation', 'externalities',
    ],
    'Environmental Economics': [
        'environmental economics', 'resource economics', 'carbon tax',
        'climate economics', 'natural resource economics',
        'ecological economics', 'environmental policy',
    ],
}


def normalize_name(name):
    name = re.sub(r'\s*\(.*?\)', '', name).strip()
    name = re.sub(r'\b[A-Z]\.\s*', '', name).strip()
    name = re.sub(r'\s+', ' ', name).strip()
    return name.lower()


def build_seed_map(nodes):
    """
    Return {pageid: school} for all seed economists, using normalized matching.
    Also returns the set of seed pageids (never overridden by NLP).
    """
    # Build lookup: normalized_name → pageid
    norm_to_pageid = {}
    for node in nodes:
        norm = normalize_name(node['name'])
        norm_to_pageid[norm] = node['id']

    seed_map = {}
    unmatched = []
    for school, names in SCHOOL_SEEDS.items():
        for name in names:
            pid = norm_to_pageid.get(normalize_name(name))
            if pid:
                seed_map[pid] = school
            else:
                unmatched.append((school, name))

    if unmatched:
        print(f"  ⚠  {len(unmatched)} seed names had no match in graph data:")
        for school, name in unmatched:
            print(f"       [{school}] {name!r}")

    return seed_map


def fetch_extracts_batch(titles, batch_size=20):
    # NOTE: Wikipedia prop=extracts with exintro=true silently caps at 20 results
    # per request regardless of how many titles you send. Always use batch_size=20.
    """
    Batch-fetch Wikipedia intro extracts for a list of URL-encoded titles.
    Returns {normalized_title: extract_text}.
    """
    results = {}
    total_batches = (len(titles) + batch_size - 1) // batch_size

    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Fetching batch {batch_num}/{total_batches} ({len(batch)} titles)…", end=' ', flush=True)

        titles_param = '|'.join(batch)
        api_url = (
            'https://en.wikipedia.org/w/api.php'
            '?action=query&prop=extracts&exintro=true&explaintext=true'
            f'&titles={titles_param}&format=json&origin=*'
        )
        try:
            resp = requests.get(api_url, timeout=30, headers={'User-Agent': 'EconographBot/1.0'})
            resp.raise_for_status()
            pages = resp.json().get('query', {}).get('pages', {})
            got = 0
            for page in pages.values():
                extract = page.get('extract', '')
                title   = page.get('title', '')
                if extract and title:
                    results[title.replace(' ', '_')] = extract
                    results[title] = extract
                    got += 1
            print(f"got {got}")
        except Exception as exc:
            print(f"FAILED ({exc})")

        time.sleep(0.4)  # be polite to Wikipedia

    return results


def score_extract(text):
    """Return the best-matching school and its score, or (None, 0) if no signal."""
    text = text[:3000].lower()
    scores = {}
    for field, keywords in FIELD_KEYWORDS.items():
        s = sum(1 for kw in keywords if kw in text)
        if s > 0:
            scores[field] = s
    if not scores:
        return None, 0
    best = max(scores.items(), key=lambda x: x[1])
    return best[0], best[1]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 retag_graph.py <path/to/graph_v3.js>")
        sys.exit(1)

    graph_path = sys.argv[1]

    # ── Load ──────────────────────────────────────────────────────────────
    print(f"Loading {graph_path}…")
    with open(graph_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    prefix = 'var graph = '
    graph_data = json.loads(raw[len(prefix):])
    nodes = graph_data['nodes']
    print(f"  {len(nodes)} nodes loaded")

    # ── Before snapshot ───────────────────────────────────────────────────
    before_counts = defaultdict(int)
    for n in nodes:
        before_counts[n['school']] += 1

    # ── Step 1: Seed assignment ────────────────────────────────────────────
    print("\nStep 1: Assigning seeds (normalized name matching)…")
    seed_map = build_seed_map(nodes)
    print(f"  {len(seed_map)} seed economists identified")

    # ── Step 2: Wikipedia NLP for non-seeds ───────────────────────────────
    print("\nStep 2: Fetching Wikipedia extracts for non-seed economists…")
    candidates = [n for n in nodes if n['id'] not in seed_map and n.get('url')]
    no_url     = [n for n in nodes if n['id'] not in seed_map and not n.get('url')]
    print(f"  {len(candidates)} to classify via NLP  |  {len(no_url)} have no URL (kept as-is)")

    # Build title → pageid map
    title_to_id = {}
    for n in candidates:
        url = n['url']
        if '/wiki/' in url:
            title = url.split('/wiki/')[-1].split('#')[0]
            title_to_id[title] = n['id']

    extracts = fetch_extracts_batch(list(title_to_id.keys()))

    # ── Step 3: Score and assign ───────────────────────────────────────────
    print("\nStep 3: Scoring extracts and assigning schools…")
    nlp_assignments = {}   # pageid → school (NLP result)
    nlp_no_signal   = []   # nodes where NLP found nothing

    for title, pageid in title_to_id.items():
        extract = extracts.get(title) or extracts.get(title.replace('_', ' '), '')
        if extract:
            school, score = score_extract(extract)
            if school:
                nlp_assignments[pageid] = school
            else:
                nlp_no_signal.append(pageid)
        else:
            nlp_no_signal.append(pageid)

    print(f"  NLP classified: {len(nlp_assignments)}")
    print(f"  NLP no signal:  {len(nlp_no_signal)} (keeping existing school)")

    # ── Step 4: Apply all assignments to nodes ────────────────────────────
    print("\nStep 4: Writing assignments back to nodes…")
    changes = []
    for node in nodes:
        pid = node['id']
        old = node['school']

        if pid in seed_map:
            new = seed_map[pid]
        elif pid in nlp_assignments:
            new = nlp_assignments[pid]
        else:
            new = old  # keep existing (no URL or no NLP signal)

        if new != old:
            changes.append((node['name'], old, new))
            node['school'] = new

    print(f"  {len(changes)} school assignments changed")

    # ── Print changes summary ─────────────────────────────────────────────
    if changes:
        print("\n  Notable changes (first 40):")
        for name, old, new in sorted(changes, key=lambda x: x[0])[:40]:
            print(f"    {name:<35}  {old:<30} → {new}")
        if len(changes) > 40:
            print(f"    … and {len(changes) - 40} more")

    # ── After snapshot ────────────────────────────────────────────────────
    after_counts = defaultdict(int)
    for n in nodes:
        after_counts[n['school']] += 1

    all_schools = sorted(set(list(before_counts.keys()) + list(after_counts.keys())))
    print("\n  School distribution (before → after):")
    for school in sorted(all_schools, key=lambda s: -after_counts.get(s, 0)):
        b = before_counts.get(school, 0)
        a = after_counts.get(school, 0)
        diff = a - b
        diff_str = f"({'+' if diff >= 0 else ''}{diff})" if diff != 0 else ''
        print(f"    {school:<32}  {b:4d} → {a:4d}  {diff_str}")

    # ── Backup + write ─────────────────────────────────────────────────────
    backup_path = graph_path + '.bak'
    print(f"\nBacking up original to {backup_path}…")
    shutil.copy2(graph_path, backup_path)

    print(f"Writing updated {graph_path}…")
    with open(graph_path, 'w', encoding='utf-8') as f:
        f.write(prefix)
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Done. {len(changes)} nodes retagged.")


if __name__ == '__main__':
    main()
