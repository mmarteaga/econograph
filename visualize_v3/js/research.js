/* ================================================================
   research.js  —  Econograph · Research Assistant (MiniSearch edition)
   ================================================================ */

(function () {
  'use strict';

  /* ── 1. SCHOOL COLORS ───────────────────────────────────────── */

  const SCHOOL_COLORS = {
    'Keynesian':                  '#2563eb',
    'New Keynesian':              '#60a5fa',
    'Austrian School':            '#d97706',
    'Chicago School':             '#dc2626',
    'Classical/Neoclassical':     '#7c3aed',
    'Marxian':                    '#16a34a',
    'Behavioral':                 '#db2777',
    'Game Theory':                '#0891b2',
    'Institutional':              '#92400e',
    'Econometrics':               '#4f46e5',
    'Development':                '#15803d',
    'Finance':                    '#b45309',
    'International Trade':        '#0e7490',
    'Labor Economics':            '#7e22ce',
    'Public Choice':              '#c2410c',
    'Welfare & Public Economics': '#047857',
    'Economic History':           '#78716c',
    'Environmental Economics':    '#059669',
    'Political Economy':          '#9333ea',
    'Other':                      '#6b7280',
  };

  /* ── 2. TOPIC RULES (keyword fallback only) ─────────────────── */
  /* Used when MiniSearch returns no results (e.g. very short query) */

  const TOPIC_RULES = [
    { keywords: ['keynesian', 'keynes', 'fiscal policy', 'aggregate demand', 'multiplier', 'depression', 'stimulus', 'deficit spending', 'liquidity trap'],
      schools: ['Keynesian', 'New Keynesian'] },
    { keywords: ['new keynesian', 'sticky price', 'sticky wage', 'dsge', 'new synthesis'],
      schools: ['New Keynesian', 'Keynesian'] },
    { keywords: ['monetary', 'inflation', 'central bank', 'federal reserve', 'money supply', 'quantitative easing', 'interest rate', 'monetarism', 'friedman'],
      schools: ['Chicago School', 'Keynesian', 'New Keynesian'] },
    { keywords: ['corporate governance', 'firm theory', 'transaction cost', 'property right', 'principal agent', 'contract theory', 'incomplete contract', 'coase'],
      schools: ['Institutional', 'Finance', 'Chicago School'] },
    { keywords: ['game theory', 'mechanism design', 'auction', 'nash equilibrium', 'strategy', 'signaling', 'bargaining', 'information asymmetry'],
      schools: ['Game Theory'] },
    { keywords: ['behavioral', 'psychology', 'nudge', 'heuristic', 'bias', 'prospect theory', 'bounded rationality', 'kahneman', 'thaler'],
      schools: ['Behavioral'] },
    { keywords: ['development', 'poverty', 'emerging market', 'growth model', 'underdevelopment', 'microfinance', 'foreign aid', 'inequality', 'human development'],
      schools: ['Development', 'Institutional'] },
    { keywords: ['international trade', 'globalization', 'comparative advantage', 'free trade', 'tariff', 'protectionism', 'exchange rate', 'balance of payment'],
      schools: ['International Trade', 'Classical/Neoclassical'] },
    { keywords: ['labor', 'wage', 'employment', 'unemployment', 'human capital', 'union', 'minimum wage', 'discrimination', 'migration', 'workforce'],
      schools: ['Labor Economics'] },
    { keywords: ['finance', 'capital market', 'banking', 'financial crisis', 'asset pricing', 'portfolio', 'derivative', 'risk', 'stock market', 'efficient market'],
      schools: ['Finance', 'Chicago School'] },
    { keywords: ['public choice', 'government failure', 'rent seeking', 'voting', 'bureaucracy', 'constitutional economics', 'buchanan'],
      schools: ['Public Choice', 'Political Economy'] },
    { keywords: ['classical', 'neoclassical', 'marginal utility', 'general equilibrium', 'walras', 'marshall', 'utility maximization', 'supply and demand'],
      schools: ['Classical/Neoclassical'] },
    { keywords: ['marxist', 'marxian', 'socialist', 'radical', 'class struggle', 'capitalism critique', 'surplus value', 'exploitation', 'marx', 'communist'],
      schools: ['Marxian'] },
    { keywords: ['economic history', 'industrial revolution', 'institutions', 'historical', 'cliometrics', 'north', 'path dependence'],
      schools: ['Economic History', 'Institutional'] },
    { keywords: ['welfare', 'externality', 'public good', 'market failure', 'pigou', 'social welfare', 'redistribution', 'taxation'],
      schools: ['Welfare & Public Economics'] },
    { keywords: ['environment', 'climate', 'carbon', 'pollution', 'sustainable', 'green', 'emissions trading', 'natural resource'],
      schools: ['Environmental Economics'] },
    { keywords: ['econometric', 'empirical', 'causal inference', 'regression', 'instrumental variable', 'natural experiment', 'difference in difference', 'panel data'],
      schools: ['Econometrics'] },
    { keywords: ['austrian', 'hayek', 'spontaneous order', 'knowledge problem', 'mises', 'praxeology', 'business cycle theory', 'calculation problem'],
      schools: ['Austrian School'] },
    { keywords: ['chicago', 'free market', 'deregulation', 'price theory', 'rational expectation', 'supply side', 'stigler', 'becker', 'posner'],
      schools: ['Chicago School'] },
    { keywords: ['institution', 'new institutional', 'transaction', 'property right', 'governance', 'organization', 'williamson'],
      schools: ['Institutional'] },
    { keywords: ['political economy', 'political', 'state', 'policy', 'regulation', 'lobbying', 'median voter'],
      schools: ['Political Economy', 'Public Choice'] },
    { keywords: ['growth', 'endogenous growth', 'solow', 'romer', 'technology', 'productivity', 'capital accumulation'],
      schools: ['Classical/Neoclassical', 'Development'] },
    { keywords: ['health economics', 'healthcare', 'insurance', 'pharmaceutical', 'hospital', 'medical'],
      schools: ['Welfare & Public Economics', 'Behavioral'] },
    { keywords: ['urban', 'housing', 'land', 'real estate', 'city', 'agglomeration', 'spatial'],
      schools: ['Labor Economics', 'Institutional'] },
    { keywords: ['industrial organization', 'monopoly', 'oligopoly', 'competition', 'antitrust', 'market structure', 'pricing strategy'],
      schools: ['Chicago School', 'Game Theory', 'Classical/Neoclassical'] },
  ];

  /* ── 3. MINISEARCH INDEX ────────────────────────────────────── */

  var msIndex = null;

  function ensureIndex() {
    if (msIndex) return true;
    if (!window.MiniSearch) return false;
    var eg = window.econograph;
    if (!eg || !eg.nodeById) return false;

    msIndex = new window.MiniSearch({
      idField: 'id',
      fields: ['name', 'school', 'bio'],
      storeFields: ['id'],
    });

    var docs = Object.values(eg.nodeById).map(function (n) {
      return {
        id:     n.id,
        name:   n.name   || '',
        school: n.school || '',
        bio:    n.bio    || '',
      };
    });
    msIndex.addAll(docs);
    return true;
  }

  /* ── 4. WIKIPEDIA QUERY ENRICHMENT ──────────────────────────── */

  function fetchQueryContext(query) {
    var url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' +
              encodeURIComponent(query.trim());
    return fetch(url)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || data.type === 'disambiguation' || !data.extract) return '';
        return data.extract.slice(0, 600);
      })
      .catch(function () { return ''; });
  }

  /* ── 5. KEYWORD FALLBACK ────────────────────────────────────── */

  function keywordFallback(q) {
    var lower    = q.toLowerCase();
    var schoolSet= new Set();
    var schools  = [];
    TOPIC_RULES.forEach(function (rule) {
      if (rule.keywords.some(function (kw) { return lower.includes(kw); })) {
        rule.schools.forEach(function (s) {
          if (!schoolSet.has(s)) { schoolSet.add(s); schools.push(s); }
        });
      }
    });
    Object.keys(SCHOOL_COLORS).forEach(function (s) {
      if (!schoolSet.has(s) && lower.includes(s.toLowerCase())) {
        schoolSet.add(s); schools.push(s);
      }
    });
    return schools;
  }

  /* ── 6. NAME HIT DETECTION ──────────────────────────────────── */

  function findNameHits(q) {
    var eg = window.econograph;
    if (!eg || !eg.nodeById) return [];
    var lower = q.toLowerCase();
    return Object.values(eg.nodeById).filter(function (n) {
      var parts = n.name.split(' ');
      var last  = parts[parts.length - 1];
      return last.length >= 4 && lower.includes(last.toLowerCase());
    });
  }

  /* ── 7. CORE SEARCH ─────────────────────────────────────────── */

  function searchNodes(query, wikiContext) {
    var eg = window.econograph;
    if (!eg || !eg.nodeById) return [];

    var scoreMap = {};
    var indexed  = ensureIndex();

    if (indexed && msIndex) {
      // Primary: original query
      msIndex.search(query, {
        boost:  { name: 4, school: 2, bio: 1 },
        fuzzy:  0.2,
        prefix: true,
      }).forEach(function (r) {
        scoreMap[r.id] = (scoreMap[r.id] || 0) + r.score * 2;
      });

      // Secondary: original query + Wikipedia context
      if (wikiContext) {
        var enriched = query + ' ' + wikiContext;
        msIndex.search(enriched, {
          boost:  { bio: 3, school: 1 },
          fuzzy:  0.15,
          prefix: true,
        }).forEach(function (r) {
          scoreMap[r.id] = (scoreMap[r.id] || 0) + r.score;
        });
      }
    }

    // Keyword fallback when MiniSearch returns nothing
    if (!Object.keys(scoreMap).length) {
      var fallbackSchools = keywordFallback(query);
      Object.values(eg.nodeById)
        .filter(function (n) { return fallbackSchools.includes(n.school); })
        .forEach(function (n) { scoreMap[n.id] = 0.5; });
    }

    // Rerank: MiniSearch score × (1 + normalised PageRank)
    return Object.entries(scoreMap)
      .map(function (entry) {
        var id        = entry[0];
        var textScore = entry[1];
        var node = eg.nodeById[id];
        if (!node) return null;
        var pr = Math.min((node.score || 0) * 500, 1);
        return { node: node, final: textScore * (1 + pr) };
      })
      .filter(Boolean)
      .sort(function (a, b) { return b.final - a.final; })
      .slice(0, 6)
      .map(function (x) { return x.node; });
  }

  /* ── 8. FETCH SUMMARY ───────────────────────────────────────── */

  function fetchSummary(node) {
    if (!node.url) return Promise.resolve('No Wikipedia article available.');
    var title;
    try {
      var parts = node.url.split('/wiki/');
      if (parts.length < 2) throw new Error('bad url');
      title = decodeURIComponent(parts[1].split('#')[0]);
    } catch (_) {
      return Promise.resolve('Biography unavailable.');
    }
    var apiUrl = 'https://en.wikipedia.org/api/rest_v1/page/summary/' +
                 encodeURIComponent(title);
    return fetch(apiUrl)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data && data.extract) {
          var txt = data.extract;
          return txt.length > 160 ? txt.slice(0, 160) + '…' : txt;
        }
        return 'No summary available.';
      })
      .catch(function () { return 'Could not load biography.'; });
  }

  /* ── 9. HTML ESCAPE ─────────────────────────────────────────── */

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── 10. RENDER RESULT CARD ─────────────────────────────────── */

  function renderCard(node, summaryText) {
    var eg       = window.econograph;
    var color    = SCHOOL_COLORS[node.school] || '#6b7280';
    var connCount= (eg && eg.adj && eg.adj[node.id]) ? eg.adj[node.id].size : 0;

    // Top 3 neighbours by PageRank
    var neighborChips = [];
    if (eg && eg.adj && eg.adj[node.id] && eg.nodeById) {
      Array.from(eg.adj[node.id])
        .map(function (id) { return eg.nodeById[id]; })
        .filter(Boolean)
        .sort(function (a, b) { return (b.score || 0) - (a.score || 0); })
        .slice(0, 3)
        .forEach(function (nb) {
          neighborChips.push({ id: nb.id, name: nb.name, node: nb });
        });
    }

    var card = document.createElement('div');
    card.className = 'research-card';

    // Photo / placeholder
    var photoHtml;
    if (node.img) {
      photoHtml =
        '<img class="research-card-photo" src="' + escHtml(node.img) + '" alt="' + escHtml(node.name) + '" loading="lazy" ' +
        'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'grid\'">' +
        '<div class="research-card-placeholder" style="display:none;background:' + color + '20;color:' + color + '">' + escHtml(node.name.charAt(0)) + '</div>';
    } else {
      photoHtml =
        '<div class="research-card-placeholder" style="background:' + color + '20;color:' + color + '">' + escHtml(node.name.charAt(0)) + '</div>';
    }

    var metaItems = [
      '<span class="research-card-pill" style="background:' + color + '18;color:' + color + ';border:1px solid ' + color + '30">' + escHtml(node.school) + '</span>',
    ];
    if (node.birthYear) metaItems.push('<span class="research-card-year">b. ' + node.birthYear + '</span>');
    if (connCount)       metaItems.push('<span class="research-card-year">' + connCount + ' connection' + (connCount !== 1 ? 's' : '') + '</span>');

    var excerptClass = 'research-card-excerpt' + (!summaryText ? ' loading' : '');
    var excerptText  = summaryText || 'Loading…';

    var chipsHtml = neighborChips
      .map(function (nb) {
        return '<button class="research-conn-chip" data-id="' + escHtml(nb.id) + '">' + escHtml(nb.name.split(' ').slice(-1)[0]) + '</button>';
      })
      .join('');

    card.innerHTML =
      '<div class="research-card-top">' +
        photoHtml +
        '<div class="research-card-info">' +
          '<div class="research-card-name">' + escHtml(node.name) + '</div>' +
          '<div class="research-card-meta">' + metaItems.join('') + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="' + excerptClass + '">' + escHtml(excerptText) + '</div>' +
      '<div class="research-card-footer">' +
        chipsHtml +
        '<button class="research-view-btn">View →</button>' +
      '</div>';

    // Click whole card → open detail
    card.addEventListener('click', function (e) {
      if (e.target.classList.contains('research-conn-chip') ||
          e.target.classList.contains('research-view-btn')) return;
      if (eg && eg.openDetail) eg.openDetail(node);
    });

    card.querySelector('.research-view-btn').addEventListener('click', function (e) {
      e.stopPropagation();
      if (eg && eg.openDetail) eg.openDetail(node);
    });

    card.querySelectorAll('.research-conn-chip').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var nbNode = eg && eg.nodeById && eg.nodeById[btn.dataset.id];
        if (nbNode && eg.openDetail) eg.openDetail(nbNode);
      });
    });

    return card;
  }

  /* ── 11. RUN SEARCH ─────────────────────────────────────────── */

  function runSearch(queryStr) {
    var resultsEl = document.getElementById('research-results');
    if (!queryStr.trim()) {
      resultsEl.innerHTML =
        '<div class="research-empty-state">' +
          '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40" opacity="0.3">' +
            '<circle cx="21" cy="21" r="13"/><path d="M34 34l8 8"/>' +
            '<path d="M21 15v12M15 21h12" stroke-width="2"/>' +
          '</svg>' +
          '<p>Ask about any topic in economics — schools of thought, key figures, or historical debates.</p>' +
        '</div>';
      return;
    }

    // Show loading state
    resultsEl.innerHTML =
      '<div class="research-loading">' +
        '<div class="research-spinner"></div>' +
        '<span>Finding economists…</span>' +
      '</div>';

    // Build index if not yet ready
    ensureIndex();

    // Fetch Wikipedia context and scan for name hits in parallel
    Promise.all([
      fetchQueryContext(queryStr),
      Promise.resolve(findNameHits(queryStr)),
    ]).then(function (results) {
      var wikiContext = results[0];
      var nameHits    = results[1];

      var searchResults = searchNodes(queryStr, wikiContext);

      // Name hits always first, then ranked MiniSearch results
      var seen     = new Set();
      var topNodes = [];
      nameHits.forEach(function (n) {
        if (!seen.has(n.id)) { seen.add(n.id); topNodes.push(n); }
      });
      searchResults.forEach(function (n) {
        if (!seen.has(n.id)) { seen.add(n.id); topNodes.push(n); }
      });
      var final = topNodes.slice(0, 6);

      if (!final.length) {
        resultsEl.innerHTML =
          '<div class="research-no-results">No economists found for that query. Try a different topic or economist name.</div>';
        return;
      }

      // Fetch summaries for all result cards in parallel
      Promise.allSettled(final.map(fetchSummary)).then(function (outcomes) {
        resultsEl.innerHTML = '';

        var label = document.createElement('div');
        label.className = 'research-result-label';
        label.appendChild(document.createTextNode(
          'Top ' + final.length + ' result' + (final.length !== 1 ? 's' : '')
        ));
        if (wikiContext) {
          var pill = document.createElement('span');
          pill.className = 'research-enriched-pill';
          pill.title = 'Query was enriched using Wikipedia context';
          pill.textContent = 'context expanded';
          label.appendChild(pill);
        }
        resultsEl.appendChild(label);

        final.forEach(function (node, i) {
          var summary = outcomes[i].status === 'fulfilled' ? outcomes[i].value : null;
          resultsEl.appendChild(renderCard(node, summary));
        });
      });
    });
  }

  /* ── 12. PANEL TOGGLE ───────────────────────────────────────── */

  function openPanel() {
    var panel = document.getElementById('research-panel');
    var fab   = document.getElementById('research-fab');
    panel.classList.remove('research-panel--hidden');
    fab.classList.add('research-fab--hidden');
    document.getElementById('research-input').focus();
    if (window.innerWidth <= 768) document.body.style.overflow = 'hidden';
    dismissTooltip(); // hide tooltip when panel opens
  }

  function closePanel() {
    var panel = document.getElementById('research-panel');
    var fab   = document.getElementById('research-fab');
    panel.classList.add('research-panel--hidden');
    fab.classList.remove('research-fab--hidden');
    document.body.style.overflow = '';
  }

  /* ── 13. ONBOARDING TOOLTIP ─────────────────────────────────── */

  function initTooltip() {
    if (localStorage.getItem('research-fab-seen')) return;
    var tooltip = document.getElementById('fab-tooltip');
    if (!tooltip) return;

    // Show after 1.5s
    setTimeout(function () {
      tooltip.classList.add('fab-tooltip--visible');
    }, 1500);

    // Auto-dismiss after 7.5s total (6s visible)
    setTimeout(dismissTooltip, 7500);

    // Dismiss on any click
    document.addEventListener('click', dismissTooltip, { once: true });
  }

  function dismissTooltip() {
    var tooltip = document.getElementById('fab-tooltip');
    if (tooltip) tooltip.classList.remove('fab-tooltip--visible');
    localStorage.setItem('research-fab-seen', '1');
  }

  /* ── 14. INIT ───────────────────────────────────────────────── */

  window.addEventListener('load', function () {
    var fab      = document.getElementById('research-fab');
    var closeBtn = document.getElementById('research-close');
    var submitBtn= document.getElementById('research-submit');
    var input    = document.getElementById('research-input');
    var chips    = document.querySelectorAll('.research-chip');
    var overlay  = document.getElementById('research-overlay');

    if (!fab) return;

    fab.addEventListener('click', openPanel);
    closeBtn.addEventListener('click', closePanel);
    submitBtn.addEventListener('click', function () { runSearch(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') runSearch(input.value);
    });
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        input.value = chip.dataset.query;
        runSearch(chip.dataset.query);
      });
    });
    if (overlay) overlay.addEventListener('click', closePanel);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var panel = document.getElementById('research-panel');
        if (panel && !panel.classList.contains('research-panel--hidden')) closePanel();
      }
    });

    // Build MiniSearch index in background, non-blocking
    setTimeout(ensureIndex, 50);

    // Show onboarding tooltip on first visit
    initTooltip();
  });

})();
