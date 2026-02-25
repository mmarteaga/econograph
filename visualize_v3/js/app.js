/* ================================================================
   app.js  —  Econograph · Timeline Browse + Detail Panel
   ================================================================ */

(function () {
  'use strict';

  /* ── 1. CONSTANTS ──────────────────────────────────────────────── */

  const ERAS = [
    { label: 'Pre-1700',                   min: -Infinity, max: 1700 },
    { label: '1700 – 1790',                min: 1700,      max: 1790 },
    { label: '1790 – 1870  ·  Classical',  min: 1790,      max: 1870 },
    { label: '1870 – 1920  ·  Neoclassical', min: 1870,    max: 1920 },
    { label: '1920 – 1950  ·  Interwar',   min: 1920,      max: 1950 },
    { label: '1950 – 1975  ·  Postwar',    min: 1950,      max: 1975 },
    { label: '1975+  ·  Contemporary',     min: 1975,      max: Infinity },
  ];

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

  /* ── 2. DATA PREP ──────────────────────────────────────────────── */

  const nodes = graph.nodes;   // loaded by graph_v3.js
  const links = graph.links;

  // id → node lookup
  const nodeById = {};
  nodes.forEach(n => { nodeById[n.id] = n; });

  // born (unix seconds) → birth year
  nodes.forEach(n => {
    n.birthYear = n.born ? Math.round(n.born / (365.25 * 86400) + 1970) : null;
  });

  // undirected adjacency sets
  const adj = {};
  nodes.forEach(n => { adj[n.id] = new Set(); });
  links.forEach(l => {
    const s = String(l.source), t = String(l.target);
    if (adj[s]) adj[s].add(t);
    if (adj[t]) adj[t].add(s);
  });

  /* ── 3. STATE ──────────────────────────────────────────────────── */

  let activeSchools = new Set();
  let activeEras    = new Set();
  let searchQuery   = '';
  let selectedNode  = null;

  /* ── 4. DOM REFS ───────────────────────────────────────────────── */

  const timelineList         = document.getElementById('timeline-list');
  const schoolFiltersEl      = document.getElementById('school-filters');
  const eraFiltersEl         = document.getElementById('era-filters');
  const mobileSchoolFilters  = document.getElementById('mobile-school-filters');
  const mobileEraFilters     = document.getElementById('mobile-era-filters');
  const searchInput          = document.getElementById('search');
  const mobileSearchInput    = document.getElementById('mobile-search');
  const countDisplay         = document.getElementById('count-display');
  const resetBtn             = document.getElementById('reset-btn');
  const mobileResetBtn       = document.getElementById('mobile-reset-btn');
  const detailPanel          = document.getElementById('detail-panel');
  const detailClose          = document.getElementById('detail-close');
  const mobileFilterBtn      = document.getElementById('mobile-filter-btn');
  const mobileFilterDrawer   = document.getElementById('mobile-filter-drawer');
  const mobileFilterOverlay  = document.getElementById('mobile-filter-overlay');

  /* ── 5. SCHOOL FILTER ITEMS ────────────────────────────────────── */

  const SCHOOLS_LIST = Object.keys(SCHOOL_COLORS);

  // Count economists per school (for labels)
  const schoolCounts = {};
  SCHOOLS_LIST.forEach(s => { schoolCounts[s] = 0; });
  nodes.forEach(n => { if (schoolCounts[n.school] !== undefined) schoolCounts[n.school]++; });

  function buildSchoolFilters(container) {
    container.innerHTML = '';
    SCHOOLS_LIST.forEach(s => {
      if (!schoolCounts[s]) return;
      const color = SCHOOL_COLORS[s];
      const item = document.createElement('div');
      item.className = 'school-filter-item';
      item.dataset.school = s;
      item.innerHTML =
        `<span class="school-dot" style="background:${color}"></span>` +
        `<span>${s}</span>` +
        `<span class="school-count">${schoolCounts[s]}</span>`;
      item.addEventListener('click', () => toggleSchool(s));
      container.appendChild(item);
    });
  }

  function toggleSchool(s) {
    if (activeSchools.has(s)) activeSchools.delete(s);
    else activeSchools.add(s);
    updateSchoolUI();
    renderTimeline();
  }

  function updateSchoolUI() {
    document.querySelectorAll('.school-filter-item').forEach(item => {
      item.classList.toggle('active', activeSchools.has(item.dataset.school));
    });
  }

  /* ── 6. ERA FILTER ITEMS ───────────────────────────────────────── */

  function buildEraFilters(container) {
    container.innerHTML = '';
    ERAS.forEach(era => {
      const item = document.createElement('div');
      item.className = 'era-filter-item';
      item.dataset.era = era.label;
      item.textContent = era.label;
      item.addEventListener('click', () => toggleEra(era.label));
      container.appendChild(item);
    });
  }

  function toggleEra(label) {
    if (activeEras.has(label)) activeEras.delete(label);
    else activeEras.add(label);
    updateEraUI();
    renderTimeline();
  }

  function updateEraUI() {
    document.querySelectorAll('.era-filter-item').forEach(item => {
      item.classList.toggle('active', activeEras.has(item.dataset.era));
    });
  }

  /* ── 7. FILTER HELPERS ─────────────────────────────────────────── */

  function getEraLabel(year) {
    if (year == null) return ERAS[ERAS.length - 1].label;
    for (const era of ERAS) {
      if (year >= era.min && year < era.max) return era.label;
    }
    return ERAS[ERAS.length - 1].label;
  }

  function nodeMatches(n) {
    if (activeSchools.size > 0 && !activeSchools.has(n.school)) return false;
    if (activeEras.size > 0 && !activeEras.has(getEraLabel(n.birthYear))) return false;
    if (searchQuery && !n.name.toLowerCase().includes(searchQuery)) return false;
    return true;
  }

  /* ── 8. TIMELINE RENDER ────────────────────────────────────────── */

  function renderTimeline() {
    const filtered = nodes.filter(nodeMatches);
    filtered.sort((a, b) => (a.birthYear || 9999) - (b.birthYear || 9999));

    // Group by era
    const eraGroups = {};
    ERAS.forEach(e => { eraGroups[e.label] = []; });
    filtered.forEach(n => { eraGroups[getEraLabel(n.birthYear)].push(n); });

    const frag = document.createDocumentFragment();
    let total = 0;

    ERAS.forEach(era => {
      const group = eraGroups[era.label];
      if (!group.length) return;
      total += group.length;

      // Era sticky header
      const header = document.createElement('div');
      header.className = 'era-header';
      header.textContent = era.label + '  ·  ' + group.length;
      frag.appendChild(header);

      // Economist rows
      group.forEach(n => {
        frag.appendChild(makeRow(n));
      });
    });

    timelineList.innerHTML = '';
    timelineList.appendChild(frag);
    countDisplay.textContent = total.toLocaleString() + ' economist' + (total !== 1 ? 's' : '');
  }

  function makeRow(n) {
    const color = SCHOOL_COLORS[n.school] || '#6b7280';
    const connCount = (adj[n.id] || new Set()).size;
    const row = document.createElement('div');
    row.className = 'economist-row' + (selectedNode && selectedNode.id === n.id ? ' selected' : '');
    row.dataset.id = n.id;

    // Photo element
    let photoHtml;
    if (n.img) {
      photoHtml = `<img class="economist-photo" src="${escapeAttr(n.img)}" alt="${escapeAttr(n.name)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">` +
                  `<div class="photo-placeholder" style="display:none;background:${color}20;color:${color}">${n.name.charAt(0)}</div>`;
    } else {
      photoHtml = `<div class="photo-placeholder" style="background:${color}20;color:${color}">${n.name.charAt(0)}</div>`;
    }

    row.innerHTML =
      photoHtml +
      `<div class="economist-info">` +
        `<div class="economist-name">${escapeHtml(n.name)}</div>` +
        `<div class="economist-meta">` +
          `<span class="school-pill" style="background:${color}18;color:${color};border:1px solid ${color}30">${escapeHtml(n.school)}</span>` +
          (n.birthYear ? `<span class="birth-year">b. ${n.birthYear}</span>` : '') +
          (connCount ? `<span class="birth-year">${connCount} link${connCount !== 1 ? 's' : ''}</span>` : '') +
        `</div>` +
      `</div>`;

    row.addEventListener('click', () => openDetail(n));
    return row;
  }

  /* ── 9. DETAIL PANEL ───────────────────────────────────────────── */

  function openDetail(n) {
    selectedNode = n;

    // Highlight selected row
    document.querySelectorAll('.economist-row').forEach(r => {
      r.classList.toggle('selected', r.dataset.id === n.id);
    });

    const color = SCHOOL_COLORS[n.school] || '#6b7280';

    // Photo
    const img         = document.getElementById('detail-img');
    const placeholder = document.getElementById('detail-img-placeholder');
    if (n.img) {
      img.src           = n.img;
      img.style.display = '';
      placeholder.style.display = 'none';
      img.onerror = () => {
        img.style.display = 'none';
        showPlaceholder(placeholder, n.name.charAt(0), color);
      };
    } else {
      img.style.display = 'none';
      showPlaceholder(placeholder, n.name.charAt(0), color);
    }

    // Text fields
    document.getElementById('detail-name').textContent  = n.name;
    document.getElementById('detail-dates').textContent = n.birthYear ? 'b. ' + n.birthYear : '';

    const schoolEl = document.getElementById('detail-school');
    schoolEl.textContent         = n.school;
    schoolEl.style.background    = color + '18';
    schoolEl.style.color         = color;
    schoolEl.style.borderColor   = color + '30';

    const linkEl = document.getElementById('detail-link');
    if (n.url) {
      linkEl.href          = n.url;
      linkEl.style.display = '';
    } else {
      linkEl.style.display = 'none';
    }

    // Reset async sections
    const bioEl = document.getElementById('detail-bio');
    bioEl.textContent = 'Loading…';
    bioEl.classList.add('loading');
    document.getElementById('mini-network').innerHTML              = '';
    document.getElementById('detail-connections-section').innerHTML = '';

    // Show panel
    detailPanel.classList.remove('detail-hidden');
    document.getElementById('detail-scroll').scrollTop = 0;

    // Async fills
    fetchBio(n);
    renderConnections(n);
    setTimeout(() => renderMiniNetwork(n), 50); // allow panel to paint first
  }

  function showPlaceholder(el, letter, color) {
    el.style.display         = 'grid';
    el.style.placeItems      = 'center';
    el.style.fontSize        = '28px';
    el.style.fontWeight      = '700';
    el.style.background      = color + '20';
    el.style.color           = color;
    el.textContent           = letter;
  }

  function closeDetail() {
    detailPanel.classList.add('detail-hidden');
    document.querySelectorAll('.economist-row.selected').forEach(r => r.classList.remove('selected'));
    selectedNode = null;
  }

  /* ── 10. WIKIPEDIA BIO ─────────────────────────────────────────── */

  function fetchBio(n) {
    const bioEl = document.getElementById('detail-bio');
    if (!n.url) {
      bioEl.textContent = 'No Wikipedia article available.';
      bioEl.classList.remove('loading');
      return;
    }

    let title;
    try {
      const parts = n.url.split('/wiki/');
      if (parts.length < 2) throw new Error();
      title = decodeURIComponent(parts[1].split('#')[0]);
    } catch (_) {
      bioEl.textContent = 'Biography unavailable.';
      bioEl.classList.remove('loading');
      return;
    }

    const apiUrl = 'https://en.wikipedia.org/api/rest_v1/page/summary/' +
                   encodeURIComponent(title);

    fetch(apiUrl)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (selectedNode && selectedNode.id !== n.id) return; // stale
        bioEl.classList.remove('loading');
        bioEl.textContent = (data && data.extract) ? data.extract : 'No summary available.';
      })
      .catch(() => {
        if (selectedNode && selectedNode.id !== n.id) return;
        bioEl.classList.remove('loading');
        bioEl.textContent = 'Could not load biography.';
      });
  }

  /* ── 11. CONNECTIONS LIST ──────────────────────────────────────── */

  function renderConnections(n) {
    const container = document.getElementById('detail-connections-section');
    const neighborIds = Array.from(adj[n.id] || []);
    if (!neighborIds.length) { container.innerHTML = ''; return; }

    const neighbors = neighborIds
      .map(id => nodeById[id])
      .filter(Boolean)
      .sort((a, b) => (b.score || 0) - (a.score || 0));

    const titleDiv = document.createElement('div');
    titleDiv.className   = 'section-title';
    titleDiv.textContent = 'Connections (' + neighbors.length + ')';
    container.innerHTML  = '';
    container.appendChild(titleDiv);

    neighbors.forEach(nb => {
      const c    = SCHOOL_COLORS[nb.school] || '#6b7280';
      const item = document.createElement('div');
      item.className = 'connection-item';
      item.dataset.id = nb.id;
      item.innerHTML  =
        `<span class="conn-dot" style="background:${c}"></span>` +
        `<span class="conn-name">${escapeHtml(nb.name)}</span>` +
        (nb.birthYear ? `<span class="conn-year">b. ${nb.birthYear}</span>` : '');
      item.addEventListener('click', () => openDetail(nb));
      container.appendChild(item);
    });
  }

  /* ── 12. MINI EGO-NETWORK (D3 v4) ─────────────────────────────── */

  function renderMiniNetwork(n) {
    const container = document.getElementById('mini-network');
    container.innerHTML = '';

    const neighborIds = Array.from(adj[n.id] || []);
    if (!neighborIds.length) {
      const msg = document.createElement('p');
      msg.className   = 'no-connections';
      msg.textContent = 'No network connections in this dataset.';
      container.appendChild(msg);
      return;
    }

    const W = container.offsetWidth || 300;
    const H = Math.min(280, W);

    // Build local graph: ego node + neighbors (cap at 30 for readability)
    const capNeighbors = neighborIds
      .map(id => nodeById[id]).filter(Boolean)
      .sort((a, b) => (b.score || 0) - (a.score || 0))
      .slice(0, 30);

    const localNodes = [
      Object.assign({}, n, { _ego: true }),
      ...capNeighbors.map(nb => Object.assign({}, nb, { _ego: false }))
    ];
    const localLinks = capNeighbors.map(nb => ({ source: n.id, target: nb.id }));

    const svg = d3.select(container).append('svg')
      .attr('width', W).attr('height', H);

    const sim = d3.forceSimulation(localNodes)
      .force('link',      d3.forceLink(localLinks).id(d => d.id).distance(65).strength(0.6))
      .force('charge',    d3.forceManyBody().strength(-100))
      .force('center',    d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(14));

    const linkSel = svg.append('g').attr('class', 'links')
      .selectAll('line').data(localLinks).enter()
      .append('line').attr('class', 'mini-link');

    const nodeSel = svg.append('g').attr('class', 'nodes')
      .selectAll('g').data(localNodes).enter()
      .append('g')
      .attr('class', d => d._ego ? 'mini-node-center' : 'mini-node')
      .on('click', function (d) {
        if (!d._ego) openDetail(nodeById[d.id]);
      });

    nodeSel.append('circle')
      .attr('r',            d => d._ego ? 13 : 8)
      .attr('fill',         d => SCHOOL_COLORS[d.school] || '#6b7280')
      .attr('fill-opacity', d => d._ego ? 1 : 0.72)
      .attr('stroke',       d => d._ego ? '#fff' : 'none')
      .attr('stroke-width', 2.5);

    nodeSel.append('text')
      .attr('class', 'mini-label')
      .attr('dy', d => -(d._ego ? 17 : 12))
      .attr('text-anchor', 'middle')
      .text(d => {
        // Show last name only, truncate if long
        const last = d.name.split(' ').slice(-1)[0];
        return last.length > 12 ? last.slice(0, 11) + '…' : last;
      });

    sim.on('tick', () => {
      linkSel
        .attr('x1', d => clamp(d.source.x, 12, W - 12))
        .attr('y1', d => clamp(d.source.y, 12, H - 12))
        .attr('x2', d => clamp(d.target.x, 12, W - 12))
        .attr('y2', d => clamp(d.target.y, 12, H - 12));

      nodeSel.attr('transform', d =>
        'translate(' + clamp(d.x, 12, W - 12) + ',' + clamp(d.y, 12, H - 12) + ')');
    });
  }

  /* ── 13. SEARCH ────────────────────────────────────────────────── */

  let searchTimer;
  function handleSearch(val) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = val.trim().toLowerCase();
      renderTimeline();
    }, 180);
  }

  searchInput.addEventListener('input', e => {
    if (mobileSearchInput) mobileSearchInput.value = e.target.value;
    handleSearch(e.target.value);
  });

  if (mobileSearchInput) {
    mobileSearchInput.addEventListener('input', e => {
      searchInput.value = e.target.value;
      handleSearch(e.target.value);
    });
  }

  /* ── 14. RESET ─────────────────────────────────────────────────── */

  function resetFilters() {
    activeSchools.clear();
    activeEras.clear();
    searchQuery = '';
    searchInput.value = '';
    if (mobileSearchInput) mobileSearchInput.value = '';
    updateSchoolUI();
    updateEraUI();
    renderTimeline();
  }

  resetBtn.addEventListener('click', resetFilters);
  if (mobileResetBtn) mobileResetBtn.addEventListener('click', resetFilters);

  /* ── 15. MOBILE FILTER DRAWER ──────────────────────────────────── */

  function openDrawer() {
    mobileFilterDrawer.classList.remove('hidden');
    mobileFilterOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    mobileFilterDrawer.classList.add('hidden');
    mobileFilterOverlay.classList.add('hidden');
    document.body.style.overflow = '';
  }

  if (mobileFilterBtn)     mobileFilterBtn.addEventListener('click', openDrawer);
  if (mobileFilterOverlay) mobileFilterOverlay.addEventListener('click', closeDrawer);

  /* ── 16. CLOSE DETAIL ──────────────────────────────────────────── */

  detailClose.addEventListener('click', closeDetail);

  // Close on Escape key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      if (!detailPanel.classList.contains('detail-hidden')) {
        closeDetail();
      } else if (!mobileFilterDrawer.classList.contains('hidden')) {
        closeDrawer();
      }
    }
  });

  /* ── 17. UTILITY ───────────────────────────────────────────────── */

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeAttr(str) {
    return String(str).replace(/"/g, '&quot;');
  }

  /* ── 18. INIT ──────────────────────────────────────────────────── */

  buildSchoolFilters(schoolFiltersEl);
  buildSchoolFilters(mobileSchoolFilters);
  buildEraFilters(eraFiltersEl);
  buildEraFilters(mobileEraFilters);
  renderTimeline();

  // Expose internals for research.js
  window.econograph = { openDetail, nodeById, adj };

})();
