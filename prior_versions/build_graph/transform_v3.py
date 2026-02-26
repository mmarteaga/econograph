"""
Graph Transform V3
==================
Transforms scraped economist data into a network graph with PageRank scores.

Input:  economists_v3.json (from scraper)
Output: graph_v3.js (for D3.js visualization)

Process:
1. Load and validate data
2. Build directed graph from relationships
3. Calculate PageRank centrality scores
4. Assign schools of thought:
   a. Seed assignment (normalized name matching — handles middle initials, parentheticals)
   b. Wikipedia NLP for all non-seed economists (runs BEFORE community detection)
   c. Louvain community detection as fallback for those NLP couldn't classify
   d. Advisor/influence inheritance for final stragglers
5. Format as D3.js-compatible JSON

NOTE: Wikipedia NLP intentionally runs before community detection.
Community detection groups by network proximity, which is not the same as
intellectual school — a misplaced seed contaminates entire clusters.
NLP is slower but directly reads each economist's Wikipedia page.
"""

import json
import re
import sys
import time
import requests
import networkx as nx
from collections import defaultdict
from networkx.algorithms import community


def normalize_name(name):
    """
    Normalize an economist name for fuzzy matching against scraped data.

    Handles:
    - Parenthetical disambiguators: "John Smith (economist)" → "John Smith"
    - Middle initials: "Lawrence F. Katz" → "Lawrence Katz"
    - Extra whitespace
    - Case

    Use this on BOTH the seed name and the scraped name before comparing.
    """
    # Strip parenthetical suffixes
    name = re.sub(r'\s*\(.*?\)', '', name).strip()
    # Remove middle initials (single uppercase letter followed by a period)
    name = re.sub(r'\b[A-Z]\.\s*', '', name).strip()
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name.lower()


def main():
    """Main entry point for the transform script."""
    if len(sys.argv) < 2:
        print("Usage: python3 transform_v3.py <input.json>")
        print("Example: python3 transform_v3.py ../scrape/economists_v3.json")
        sys.exit(1)

    input_file = sys.argv[1]

    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"Loaded {len(raw_data)} raw entries")

    # Step 1: Clean and validate
    print("\nStep 1: Cleaning and validating data...")
    cleaned_data = clean_data(raw_data)
    print(f"  ✓ {len(cleaned_data)} valid entries after cleaning")

    # Step 2: Build name->pageid lookup
    print("\nStep 2: Building name-to-pageid lookup...")
    name_to_pageid = build_name_lookup(cleaned_data)
    print(f"  ✓ Created lookup for {len(name_to_pageid)} economists")

    # Step 3: Build graph
    print("\nStep 3: Building directed graph from relationships...")
    graph = build_graph(cleaned_data, name_to_pageid)
    print(f"  ✓ Graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")

    # Step 3b: Drop isolated nodes (no connections = no value in the visualization)
    isolated = [n for n, deg in graph.degree() if deg == 0]
    graph.remove_nodes_from(isolated)
    connected_ids = set(graph.nodes())
    cleaned_data = [e for e in cleaned_data if e['pageid'] in connected_ids]
    name_to_pageid = build_name_lookup(cleaned_data)
    print(f"  ✓ Removed {len(isolated)} isolated nodes → {graph.number_of_nodes()} connected nodes remain")

    # Step 4: Calculate PageRank
    print("\nStep 4: Calculating PageRank centrality scores...")
    pagerank_scores = nx.pagerank(graph)
    print(f"  ✓ Calculated scores for {len(pagerank_scores)} nodes")

    # Find top economists by PageRank
    top_economists = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n  Top 10 most central economists:")
    for pageid, score in top_economists:
        name = next(e['name'] for e in cleaned_data if e['pageid'] == pageid)
        print(f"    {score:.6f} - {name}")

    # Step 5: Assign seeds (with normalized name matching)
    print("\nStep 5: Assigning seed economists to known schools of thought...")
    school_assignments = assign_seeds(cleaned_data, name_to_pageid)
    seed_count = sum(1 for s in school_assignments.values() if s != 'Other')
    print(f"  ✓ Assigned {seed_count} seed economists")

    # Step 5b: Wikipedia NLP for ALL non-seed economists with a URL.
    # This runs BEFORE community detection so that accurate Wikipedia signals
    # take priority over network-proximity heuristics.
    print("\nStep 5b: Classifying non-seed economists via Wikipedia NLP...")
    school_assignments = classify_via_wikipedia(cleaned_data, school_assignments, only_others=False)
    nlp_count = sum(1 for s in school_assignments.values() if s != 'Other')
    print(f"  ✓ {nlp_count} economists classified (seeds + NLP)")

    # Step 5c: Community detection as a fallback for those NLP couldn't classify.
    print("\nStep 5c: Using community detection as fallback for remaining economists...")
    school_assignments = assign_communities(graph, cleaned_data, school_assignments)
    comm_count = sum(1 for s in school_assignments.values() if s != 'Other')
    print(f"  ✓ {comm_count} economists classified after community detection")

    # Step 5d: Advisor/influence inheritance for final stragglers.
    print("\nStep 5d: Inheriting school from advisors/influences...")
    school_assignments = inherit_from_network(cleaned_data, name_to_pageid, school_assignments)

    school_counts = defaultdict(int)
    for school in school_assignments.values():
        school_counts[school] += 1
    print(f"\n  Final school distribution:")
    for school, count in sorted(school_counts.items(), key=lambda x: -x[1]):
        print(f"    {school}: {count} economists")

    # Step 6: Build output JSON
    print("\nStep 6: Building D3.js-compatible JSON...")
    graph_json = build_graph_json(cleaned_data, pagerank_scores, school_assignments)
    print(f"  ✓ Created {len(graph_json['nodes'])} nodes and {len(graph_json['links'])} links")

    # Step 7: Write output
    output_file = "graph_v3.js"
    print(f"\nStep 7: Writing output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('var graph = ')
        json.dump(graph_json, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Success! Graph data written to {output_file}")
    print("\nNext steps:")
    print("  1. Copy graph_v3.js to visualize/js/")
    print("  2. Update visualize/index.html to load graph_v3.js")
    print("  3. Open visualize/index.html in a browser")


def clean_data(raw_data):
    """
    Clean and validate the raw scraped data.
    Remove entries that are missing critical fields.
    """
    cleaned = []

    for entry in raw_data:
        # Must have these critical fields
        if not entry.get('pageid'):
            continue
        if not entry.get('name'):
            continue
        if not entry.get('born'):
            continue

        # Ensure pageid is string
        entry['pageid'] = str(entry['pageid'])

        # Ensure lists are actually lists
        for field in ['influences', 'doctoral_advisors', 'doctoral_students']:
            if field not in entry:
                entry[field] = []
            elif not isinstance(entry[field], list):
                entry[field] = [entry[field]]

        # Clean up empty strings in lists
        entry['influences'] = [x for x in entry['influences'] if x]
        entry['doctoral_advisors'] = [x for x in entry['doctoral_advisors'] if x]
        entry['doctoral_students'] = [x for x in entry['doctoral_students'] if x]

        cleaned.append(entry)

    return cleaned


def build_name_lookup(data):
    """
    Build a dictionary mapping names to pageids.
    Handles multiple names mapping to the same pageid (nicknames, etc.)
    """
    lookup = {}

    for entry in data:
        name = entry['name']
        pageid = entry['pageid']

        # Add the primary name
        lookup[name] = pageid

        # Also handle common variations
        # Remove parenthetical suffixes like "(economist)"
        clean_name = name.split('(')[0].strip()
        if clean_name != name:
            lookup[clean_name] = pageid

    return lookup


def build_graph(data, name_to_pageid):
    """
    Build a directed graph from the relationship data.

    Nodes: Individual economists (by pageid)
    Edges:
      - From person -> influence (who influenced them)
      - From doctoral_advisor -> doctoral_student
    """
    graph = nx.DiGraph()

    # Add all economists as nodes
    for entry in data:
        graph.add_node(entry['pageid'])

    # Add edges from relationships
    for entry in data:
        source_pageid = entry['pageid']

        # Add "influences" edges: source was influenced by target
        for influence_name in entry['influences']:
            target_pageid = name_to_pageid.get(influence_name)
            if target_pageid and target_pageid in graph:
                # Edge points FROM influenced TO influencer
                # (shows flow of influence)
                graph.add_edge(source_pageid, target_pageid)

        # Add "doctoral advisor" edges: target advised source
        for advisor_name in entry['doctoral_advisors']:
            target_pageid = name_to_pageid.get(advisor_name)
            if target_pageid and target_pageid in graph:
                # Edge points FROM student TO advisor
                graph.add_edge(source_pageid, target_pageid)

    return graph


def assign_seeds(data, name_to_pageid):
    """
    Step 1: Assign well-known seed economists to their historical schools.

    Uses normalize_name() on both seed names and scraped names so that middle
    initials, parenthetical disambiguators, and minor spelling variants don't
    cause silent misses (e.g. seed "Lawrence Katz" matches "Lawrence F. Katz").
    """
    # Canonical school definitions with seed economists.
    # IMPORTANT: When adding seeds, use the simplest recognizable form of the
    # name — normalize_name() will strip middle initials on both sides, so
    # "Lawrence Katz" and "Lawrence F. Katz" both normalize to "lawrence katz".
    SCHOOL_SEEDS = {
        'Austrian School': [
            'Carl Menger', 'Ludwig von Mises', 'Friedrich Hayek', 'Eugen von Böhm-Bawerk',
            'Murray Rothbard', 'Israel Kirzner', 'Friedrich von Wieser', 'Hans-Hermann Hoppe',
            'Jesús Huerta de Soto', 'Peter Boettke', 'Roger Garrison', 'Henry Hazlitt',
            'F. A. Harper', 'Leonard Read', 'Walter Block', 'Hans Sennholz', 'George Reisman',
            'Gottfried Haberler', 'Fritz Machlup', 'Oskar Morgenstern', 'Joseph Salerno'
        ],
        'Chicago School': [
            'Milton Friedman', 'George Stigler', 'Gary Becker', 'Robert Lucas Jr.',
            'Eugene Fama', 'Richard Posner', 'Ronald Coase', 'Aaron Director',
            'Frank Knight', 'Jacob Viner', 'Henry Simons', 'Thomas Sowell',
            'Sam Peltzman', 'Harold Demsetz', 'Sherwin Rosen', 'Kevin Murphy',
            'Robert Fogel', 'Douglass North', 'Lars Peter Hansen', 'John Cochrane',
            'Steven Levitt', 'Casey Mulligan', 'Steven Cheung', 'Armen Alchian'
        ],
        'Keynesian': [
            'John Maynard Keynes', 'John Hicks', 'Paul Samuelson', 'James Tobin',
            'Franco Modigliani', 'Robert Solow', 'Lawrence Klein', 'Alvin Hansen',
            'Joan Robinson', 'Nicholas Kaldor', 'Michal Kalecki', 'Roy Harrod',
            'Abba Lerner', 'Evsey Domar', 'Richard Kahn', 'Austin Robinson',
            'James Meade', 'Richard Musgrave', 'Arthur Okun', 'Walter Heller'
        ],
        'New Keynesian': [
            'Joseph Stiglitz', 'Paul Krugman', 'Gregory Mankiw', 'Olivier Blanchard',
            'Janet Yellen', 'Ben Bernanke', 'Michael Woodford', 'Jordi Galí',
            'Lawrence Summers', 'Stanley Fischer', 'John Taylor', 'Julio Rotemberg',
            'David Romer', 'Alan Blinder', 'Frederic Mishkin', 'Mark Gertler',
            'Nobuhiro Kiyotaki', 'Gauti Eggertsson', 'Ivan Werning', 'Emmanuel Farhi'
        ],
        'Classical/Neoclassical': [
            'Adam Smith', 'David Ricardo', 'John Stuart Mill', 'Alfred Marshall',
            'Léon Walras', 'William Stanley Jevons', 'Vilfredo Pareto', 'Jean-Baptiste Say',
            'Nassau William Senior', 'Thomas Malthus', 'Francis Edgeworth', 'Knut Wicksell',
            'Irving Fisher', 'Arthur Pigou', 'Philip Wicksteed', 'John Bates Clark',
            'Frédéric Bastiat', 'Richard Cantillon', 'Anne Robert Jacques Turgot',
            'Gustave de Molinari', 'David Hume', 'François Quesnay', 'Henry George'
        ],
        'Marxian': [
            'Karl Marx', 'Friedrich Engels', 'Rosa Luxemburg', 'Rudolf Hilferding',
            'Paul Sweezy', 'Ernest Mandel', 'Maurice Dobb', 'Paul Baran',
            'Piero Sraffa', 'Ian Steedman', 'Andrew Kliman', 'Anwar Shaikh',
            'Michael Hudson', 'David Harvey', 'Richard Wolff', 'Samuel Bowles',
            'Herbert Gintis', 'Duncan Foley', 'John Roemer', 'Gerald Cohen'
        ],
        'Institutional': [
            'Thorstein Veblen', 'John Commons', 'Wesley Mitchell', 'John Kenneth Galbraith',
            'Clarence Ayres', 'Gunnar Myrdal', 'Geoffrey Hodgson', 'Ha-Joon Chang',
            'Douglass North', 'Oliver Williamson', 'Elinor Ostrom', 'Daron Acemoglu',
            'Karl Polanyi', 'Albert Hirschman', 'Kenneth Boulding', 'Warren Samuels'
        ],
        'Behavioral': [
            'Daniel Kahneman', 'Amos Tversky', 'Richard Thaler', 'Robert Shiller',
            'George Akerlof', 'Colin Camerer', 'Dan Ariely', 'Sendhil Mullainathan',
            'Cass Sunstein', 'Matthew Rabin', 'Ernst Fehr', 'David Laibson',
            'Stefano DellaVigna', 'Ulrike Malmendier', 'Xavier Gabaix',
            # NOTE: Raj Chetty moved to Labor Economics — he is primarily a
            # labor/public economist; keeping him here contaminates the entire
            # Harvard labor cluster via Louvain community detection.
        ],
        'Welfare & Public Economics': [
            'Martin Feldstein',   # public finance — Wikipedia intro doesn't contain "public finance"
            'James Poterba',      # same: tax policy / public finance
            'Peter Diamond',      # pension/social security work; also Labor seed
        ],
        'Development': [
            'Theodore Schultz',   # Nobel 1979 — intro says "agricultural economist", not "development economics"
            'W. Arthur Lewis',    # Nobel 1979 — development economist
        ],
        'Game Theory': [
            'John von Neumann', 'John Nash', 'John Harsanyi', 'Reinhard Selten',
            'Robert Aumann', 'Thomas Schelling', 'Lloyd Shapley', 'Alvin Roth',
            'Jean Tirole', 'Eric Maskin', 'Roger Myerson', 'Drew Fudenberg',
            'Ariel Rubinstein', 'Ken Binmore', 'Ehud Kalai', 'David Kreps',
            'Robert Wilson', 'Paul Milgrom', 'Bengt Holmström', 'Oliver Hart'
        ],
        'Development': [
            'Amartya Sen', 'Abhijit Banerjee', 'Esther Duflo', 'Michael Kremer',
            'William Easterly', 'Jeffrey Sachs', 'Daron Acemoglu', 'James Robinson',
            'Arthur Lewis', 'Albert Hirschman', 'Raúl Prebisch', 'Hans Singer',
            'Paul Rosenstein-Rodan', 'Ragnar Nurkse', 'W. W. Rostow', 'Hernando de Soto',
            'Robert Barro', 'Xavier Sala-i-Martin', 'Partha Dasgupta', 'Angus Deaton'
        ],
        'Public Choice': [
            'James Buchanan', 'Gordon Tullock', 'Mancur Olson', 'William Niskanen',
            'Bryan Caplan', 'Anthony Downs', 'Dennis Mueller', 'Geoffrey Brennan',
            'Dwight Lee', 'Robert Tollison', 'Randall Holcombe', 'Peter Leeson'
        ],
        'Econometrics': [
            'Ragnar Frisch', 'Jan Tinbergen', 'Trygve Haavelmo', 'Lawrence Klein',
            'Clive Granger', 'Christopher Sims', 'James Heckman', 'Daniel McFadden',
            'Joshua Angrist', 'Guido Imbens', 'David Card', 'Robert Engle',
            'Halbert White', 'Jerry Hausman', 'Whitney Newey', 'Lars Peter Hansen',
            'Edward Leamer', 'Arnold Zellner', 'Takeshi Amemiya', 'Peter Phillips'
        ],
        'Finance': [
            'Harry Markowitz', 'William Sharpe', 'Fischer Black', 'Myron Scholes',
            'Robert Merton', 'Eugene Fama', 'Kenneth French', 'John Campbell',
            'Stephen Ross', 'Michael Jensen', 'Stewart Myers', 'John Lintner',
            'Franco Modigliani', 'Merton Miller', 'Andrew Lo', 'Robert Shiller'
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
            'Dani Rodrik', 'Douglas Irwin', 'Robert Baldwin', 'Ronald Jones'
        ],
    }

    # Build normalized lookup: normalized_name → pageid
    # Also keep the original lookup for exact matches (faster path)
    normalized_name_to_pageid = {normalize_name(name): pid for name, pid in name_to_pageid.items()}

    seed_assignments = {}
    unmatched_seeds = []
    for school, seed_names in SCHOOL_SEEDS.items():
        for seed_name in seed_names:
            # Try exact match first, then normalized
            pageid = name_to_pageid.get(seed_name) or normalized_name_to_pageid.get(normalize_name(seed_name))
            if pageid:
                seed_assignments[pageid] = school
            else:
                unmatched_seeds.append((school, seed_name))

    if unmatched_seeds:
        print(f"  ⚠ {len(unmatched_seeds)} seed names had no match in scraped data:")
        for school, name in unmatched_seeds:
            print(f"    [{school}] {name!r}")

    return seed_assignments


def assign_communities(graph, data, school_assignments):
    """
    Step 3 (fallback): Run Louvain community detection and label each community
    by its most common already-assigned school. Only fills economists not yet
    assigned (i.e. school_assignments[pageid] == 'Other' or missing).

    This runs AFTER Wikipedia NLP so it only covers economists whose Wikipedia
    page couldn't be matched to a field.
    """
    undirected = graph.to_undirected()
    try:
        communities = community.louvain_communities(undirected, seed=42)
    except Exception:
        communities = list(community.greedy_modularity_communities(undirected))

    # Label each community by the plurality school among already-assigned members
    community_labels = {}
    for i, comm in enumerate(communities):
        school_votes = defaultdict(int)
        for pageid in comm:
            s = school_assignments.get(pageid)
            if s and s != 'Other':
                school_votes[s] += 1
        community_labels[i] = max(school_votes.items(), key=lambda x: x[1])[0] if school_votes else 'Other'

    # Assign community label only to economists not yet classified
    result = dict(school_assignments)
    for i, comm in enumerate(communities):
        label = community_labels[i]
        for pageid in comm:
            if result.get(pageid, 'Other') == 'Other':
                result[pageid] = label

    return result


def inherit_from_network(data, name_to_pageid, school_assignments):
    """
    Step 4 (fallback): Assign remaining 'Other' economists based on their
    doctoral advisors (weight ×2) and influences. Students are also used
    to fill in advisors that are still 'Other'.
    """
    result = dict(school_assignments)

    for entry in data:
        pageid = entry['pageid']
        if result.get(pageid, 'Other') != 'Other':
            continue

        related = []
        for influence_name in entry.get('influences', []):
            inf_id = name_to_pageid.get(influence_name)
            s = result.get(inf_id, 'Other') if inf_id else 'Other'
            if s != 'Other':
                related.append(s)

        for advisor_name in entry.get('doctoral_advisors', []):
            adv_id = name_to_pageid.get(advisor_name)
            s = result.get(adv_id, 'Other') if adv_id else 'Other'
            if s != 'Other':
                related.extend([s, s])  # weight advisors ×2

        if related:
            counts = defaultdict(int)
            for s in related:
                counts[s] += 1
            result[pageid] = max(counts.items(), key=lambda x: x[1])[0]
        elif pageid not in result:
            result[pageid] = 'Other'

    # Reverse pass: propagate from students back to still-Other advisors
    for entry in data:
        pageid = entry['pageid']
        if result.get(pageid) != 'Other':
            continue
        student_schools = []
        for student_name in entry.get('doctoral_students', []):
            stu_id = name_to_pageid.get(student_name)
            s = result.get(stu_id, 'Other') if stu_id else 'Other'
            if s != 'Other':
                student_schools.append(s)
        if student_schools:
            counts = defaultdict(int)
            for s in student_schools:
                counts[s] += 1
            result[pageid] = max(counts.items(), key=lambda x: x[1])[0]

    return result


def classify_via_wikipedia(data, school_assignments, only_others=False):
    """
    Batch-fetch Wikipedia intro paragraphs and run keyword scoring to assign
    schools of thought.

    Parameters
    ----------
    only_others : bool
        If True, only process economists currently marked 'Other' (original
        behaviour for a cheap incremental pass).
        If False (default), process ALL non-seed economists with a URL so that
        Wikipedia NLP takes priority over community-detection assignments.
        Seed assignments (set before this call) are always preserved.

    Uses the Wikipedia Action API (up to 50 titles per request).
    """

    # Keyword taxonomy — phrases are matched as substrings in the lowercase text.
    # Longer / more specific phrases score higher implicitly because they are rarer.
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
        # Fields for economists who don't fit the existing schools
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
        'Health Economics': [
            'health economics', 'healthcare economics', 'medical economics',
            'pharmaceutical economics', 'health insurance',
        ],
        'Environmental Economics': [
            'environmental economics', 'resource economics', 'carbon tax',
            'climate economics', 'natural resource economics',
            'ecological economics', 'environmental policy',
        ],
    }

    # Determine which economists to classify.
    # Seed assignments (pageid present in school_assignments with a real school)
    # are always preserved — NLP never overrides a seed.
    seed_pageids = {pid for pid, s in school_assignments.items() if s != 'Other'}

    if only_others:
        candidates = [
            e for e in data
            if school_assignments.get(e['pageid']) == 'Other' and e.get('url')
        ]
    else:
        # Classify everyone with a URL who is not a direct seed
        candidates = [
            e for e in data
            if e['pageid'] not in seed_pageids and e.get('url')
        ]

    if not candidates:
        print("  No economists to classify via NLP.")
        return school_assignments

    print(f"  Classifying {len(candidates)} economists via Wikipedia abstracts...")

    result = dict(school_assignments)

    # Map URL title → pageid so we can match API results back
    title_to_pageid = {}
    for e in candidates:
        url = e.get('url', '')
        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            title_to_pageid[title] = e['pageid']

    titles = list(title_to_pageid.keys())
    classified = 0
    batch_size = 50

    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        titles_param = '|'.join(batch)
        api_url = (
            'https://en.wikipedia.org/w/api.php'
            '?action=query&prop=extracts&exintro=true&explaintext=true'
            f'&titles={titles_param}&format=json&origin=*'
        )
        try:
            resp = requests.get(
                api_url, timeout=30,
                headers={'User-Agent': 'EconographBot/1.0'}
            )
            resp.raise_for_status()
            pages = resp.json().get('query', {}).get('pages', {})

            for page in pages.values():
                raw_title = page.get('title', '')
                extract = page.get('extract', '')
                if not extract:
                    continue

                # Try both underscore and space variants to find the pageid
                pageid = (
                    title_to_pageid.get(raw_title.replace(' ', '_'))
                    or title_to_pageid.get(raw_title)
                )
                if not pageid:
                    continue

                # Score the extract against each field's keywords
                text = extract[:3000].lower()
                scores = {}
                for field, keywords in FIELD_KEYWORDS.items():
                    score = sum(1 for kw in keywords if kw in text)
                    if score > 0:
                        scores[field] = score

                if scores:
                    best = max(scores.items(), key=lambda x: x[1])[0]
                    result[pageid] = best
                    classified += 1
                else:
                    # NLP found nothing; leave as 'Other' for community fallback
                    result.setdefault(pageid, 'Other')

        except Exception as exc:
            print(f"    Batch {i // batch_size + 1} failed: {exc}")

        time.sleep(0.5)

    still_other = sum(1 for s in result.values() if s == 'Other')
    print(f"  ✓ Classified {classified} via NLP | {still_other} remain 'Other' (will use community fallback)")
    return result


def build_graph_json(data, pagerank_scores, school_assignments=None):
    """
    Build the final JSON structure for D3.js visualization.

    Format:
    {
      "nodes": [
        {"id": "pageid", "name": "...", "score": 0.001, "born": -123456, "img": "...", "school": "..."},
        ...
      ],
      "links": [
        {"source": "pageid1", "target": "pageid2", "value": 1},
        ...
      ],
      "schools": ["Austrian School", "Chicago School", ...]
    }
    """
    if school_assignments is None:
        school_assignments = {}

    # Build a pageid -> data lookup
    pageid_to_data = {entry['pageid']: entry for entry in data}

    # Build name -> pageid lookup for relationships
    name_to_pageid = build_name_lookup(data)

    # Collect all unique schools for the legend
    all_schools = sorted(set(school_assignments.values()))

    graph_json = {
        'nodes': [],
        'links': [],
        'schools': all_schools
    }

    # Build nodes
    for entry in data:
        pageid = entry['pageid']
        score = pagerank_scores.get(pageid, 0.0)
        school = school_assignments.get(pageid, 'Other')

        node = {
            'id': pageid,
            'name': entry['name'],
            'score': score,
            'born': entry['born'],
            'img': entry.get('img', ''),
            'url': entry.get('url', ''),
            'school': school
        }

        graph_json['nodes'].append(node)

    # Build links
    link_set = set()  # Avoid duplicate links

    for entry in data:
        source_pageid = entry['pageid']

        # Add influence links
        for influence_name in entry['influences']:
            target_pageid = name_to_pageid.get(influence_name)
            if target_pageid and target_pageid in pageid_to_data:
                link_key = (source_pageid, target_pageid)
                if link_key not in link_set:
                    link_set.add(link_key)
                    graph_json['links'].append({
                        'source': source_pageid,
                        'target': target_pageid,
                        'value': 1
                    })

        # Add doctoral advisor links
        for advisor_name in entry['doctoral_advisors']:
            target_pageid = name_to_pageid.get(advisor_name)
            if target_pageid and target_pageid in pageid_to_data:
                link_key = (source_pageid, target_pageid)
                if link_key not in link_set:
                    link_set.add(link_key)
                    graph_json['links'].append({
                        'source': source_pageid,
                        'target': target_pageid,
                        'value': 1
                    })

    return graph_json


if __name__ == '__main__':
    main()
