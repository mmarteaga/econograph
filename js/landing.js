/* ================================================================
   landing.js  —  Econograph animated network landing screen
   Runs AFTER app.js (window.econograph is available)
   ================================================================ */

(function () {
  'use strict';

  var SCHOOL_COLORS = {
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

  var SAMPLE_SIZE = window.innerWidth < 600 ? 16 : 26;

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function pickSample() {
    var sorted = graph.nodes
      .filter(function (n) { return n.url && n.name; })
      .sort(function (a, b) { return (b.score || 0) - (a.score || 0); });
    // Pool: top 120 by PageRank (recognisable names), sample randomly from it
    var pool = sorted.slice(0, 120).slice();
    var picks = [];
    while (picks.length < SAMPLE_SIZE && pool.length) {
      var i = Math.floor(Math.random() * pool.length);
      picks.push(pool.splice(i, 1)[0]);
    }
    return picks;
  }

  function runAnimation(container, picks, onNodeClick) {
    var W = container.offsetWidth  || window.innerWidth;
    var H = container.offsetHeight || window.innerHeight;

    // Clone nodes so D3 simulation doesn't mutate the real graph data
    var simNodes = picks.map(function (n) { return Object.assign({}, n); });
    var pickIds  = {};
    simNodes.forEach(function (n) { pickIds[n.id] = true; });

    var simLinks = graph.links
      .filter(function (l) {
        return pickIds[String(l.source)] && pickIds[String(l.target)];
      })
      .map(function (l) { return { source: String(l.source), target: String(l.target) }; });

    var svg = d3.select(container).append('svg')
      .attr('width', W).attr('height', H);

    var sim = d3.forceSimulation(simNodes)
      .force('link',      d3.forceLink(simLinks).id(function (d) { return d.id; }).distance(85).strength(0.35))
      .force('charge',    d3.forceManyBody().strength(-200))
      .force('center',    d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(32));

    // Edges — initially invisible, fade in after nodes start appearing
    var linkSel = svg.append('g')
      .selectAll('line').data(simLinks).enter()
      .append('line')
      .attr('stroke', 'rgba(148,163,184,0.18)')
      .attr('stroke-width', 1)
      .style('opacity', 0);

    // Node groups — staggered appearance
    var nodeSel = svg.append('g')
      .selectAll('g').data(simNodes).enter()
      .append('g')
      .style('opacity', 0)
      .style('cursor', 'pointer');

    // Circle radius scales gently with PageRank
    nodeSel.append('circle')
      .attr('r', function (d) { return 5 + Math.min((d.score || 0) * 2500, 6); })
      .attr('fill', function (d) { return SCHOOL_COLORS[d.school] || '#6b7280'; })
      .attr('fill-opacity', 0.88)
      .attr('stroke', 'rgba(255,255,255,0.15)')
      .attr('stroke-width', 1.5);

    // Last-name label
    nodeSel.append('text')
      .text(function (d) {
        var parts = d.name.split(' ');
        return parts[parts.length - 1];
      })
      .attr('dy', function (d) { return -(8 + Math.min((d.score || 0) * 2500, 6)); })
      .attr('text-anchor', 'middle')
      .attr('fill', 'rgba(203,213,225,0.8)')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .style('pointer-events', 'none');

    // Stagger node appearances
    simNodes.forEach(function (n, i) {
      var g = nodeSel.filter(function (d) { return d === n; });
      setTimeout(function () {
        g.transition().duration(400).style('opacity', 1);
      }, 100 + i * 115);
    });

    // Edges fade in after first nodes appear
    setTimeout(function () {
      linkSel.transition().duration(1200).style('opacity', 1);
    }, 350);

    // Tick
    sim.on('tick', function () {
      linkSel
        .attr('x1', function (d) { return clamp(d.source.x, 16, W - 16); })
        .attr('y1', function (d) { return clamp(d.source.y, 16, H - 16); })
        .attr('x2', function (d) { return clamp(d.target.x, 16, W - 16); })
        .attr('y2', function (d) { return clamp(d.target.y, 16, H - 16); });

      nodeSel.attr('transform', function (d) {
        return 'translate(' + clamp(d.x, 16, W - 16) + ',' + clamp(d.y, 16, H - 16) + ')';
      });
    });

    // Clicking a node dismisses landing and opens that economist
    nodeSel.on('click', function (d) {
      if (onNodeClick) onNodeClick(d);
    });

    return { sim: sim };
  }

  function initLanding() {
    var overlay = document.getElementById('landing-overlay');
    if (!overlay) return;

    var netContainer = overlay.querySelector('.landing-network');
    var animResult = null;

    if (netContainer && typeof d3 !== 'undefined' && typeof graph !== 'undefined') {
      var picks = pickSample();
      animResult = runAnimation(netContainer, picks, function (nodeData) {
        dismiss();
        var eg = window.econograph;
        if (eg && eg.openDetail) {
          var realNode = eg.nodeById[nodeData.id];
          if (realNode) setTimeout(function () { eg.openDetail(realNode); }, 480);
        }
      });
    }

    // Show the CTA buttons after the animation starts building out
    var actionsEl = document.getElementById('landing-actions');
    if (actionsEl) {
      setTimeout(function () {
        actionsEl.classList.add('landing-actions--visible');
      }, 2400);
    }

    // Reset the "seen" flag so the landing always shows on next visit too
    localStorage.removeItem('econograph-intro-seen');

    function dismiss() {
      if (animResult) animResult.sim.stop();
      overlay.classList.add('landing-hiding');
      setTimeout(function () { overlay.style.display = 'none'; }, 450);
      localStorage.setItem('econograph-intro-seen', '1');
    }

    var startBtn = document.getElementById('landing-start-btn');
    if (startBtn) startBtn.addEventListener('click', dismiss);
  }

  window.addEventListener('load', initLanding);

})();
