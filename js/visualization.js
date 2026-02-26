/**
 * Econograph V3 - Swimlane Constellation Layout
 *
 * Layout:
 *   X-axis  = school / field of thought (one column per school)
 *   Y-axis  = birth year (global timeline, top = oldest)
 *   Nodes   = individual economists, sized by PageRank
 *   Links   = doctoral lineage + influence, arcing across columns
 *   Colors  = school of thought
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COLUMN_WIDTH = 220;   // px per school column
const TOP_PADDING  = 80;    // px reserved for column headers
const BOT_PADDING  = 40;

// Canonical ordering of schools left → right (roughly chronological emergence)
const SCHOOL_ORDER = [
    'Classical/Neoclassical',
    'Marxian',
    'Austrian School',
    'Institutional',
    'Economic History',
    'Keynesian',
    'Welfare & Public Economics',
    'Chicago School',
    'Development',
    'Political Economy',
    'Public Choice',
    'International Trade',
    'Labor Economics',
    'Econometrics',
    'Game Theory',
    'Finance',
    'New Keynesian',
    'Behavioral',
    'Health Economics',
    'Environmental Economics',
    'Other',
];

const schoolColors = {
    'Austrian School':          '#e41a1c',
    'Chicago School':           '#377eb8',
    'Keynesian':                '#4daf4a',
    'New Keynesian':            '#984ea3',
    'Classical/Neoclassical':   '#ff7f00',
    'Marxian':                  '#a65628',
    'Institutional':            '#f781bf',
    'Behavioral':               '#17becf',
    'Game Theory':              '#66c2a5',
    'Development':              '#fc8d62',
    'Public Choice':            '#8da0cb',
    'Econometrics':             '#e78ac3',
    'Finance':                  '#a6d854',
    'Labor Economics':          '#ffd92f',
    'International Trade':      '#b15928',
    'Welfare & Public Economics':'#cab2d6',
    'Economic History':         '#6a3d9a',
    'Political Economy':        '#33a02c',
    'Health Economics':         '#fb9a99',
    'Environmental Economics':  '#b2df8a',
    'Other':                    '#bbbbbb',
};

function getSchoolColor(school) {
    return schoolColors[school] || schoolColors['Other'];
}

// ---------------------------------------------------------------------------
// Global state
// ---------------------------------------------------------------------------

const graphData   = graph;  // injected by graph_v3.js
let simulation;
let svg, g;
let nodeElements, linkElements;
let selectedNode    = null;
let searchMatches   = [];
let activeSchoolFilter = null;
let schoolColumns   = {};   // school → { x, index }
let globalYScale;           // d3 scale: birthYear → px

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

function init() {
    console.log(`Loaded ${graphData.nodes.length} nodes, ${graphData.links.length} links`);

    document.getElementById('node-count').textContent = `Economists: ${graphData.nodes.length}`;
    document.getElementById('link-count').textContent = `Connections: ${graphData.links.length}`;

    svg = d3.select('#graph-svg');

    // g must exist before zoom is set up — the zoom handler references it
    g = svg.append('g');

    // Build column map and Y scale before rendering anything
    processNodeData();

    // Fit all school columns into the initial viewport
    const numCols = Object.keys(schoolColumns).length;
    const totalW  = numCols * COLUMN_WIDTH;
    const initScale = totalW > 0 ? Math.min((window.innerWidth - 60) / totalW, 1) : 1;

    const zoom = d3.zoom()
        .scaleExtent([0.05, 6])
        .on('zoom', () => g.attr('transform', d3.event.transform));

    // Apply zoom AFTER g is defined so the handler doesn't throw
    svg.call(zoom)
       .call(zoom.transform,
             d3.zoomIdentity.translate(30, 20).scale(initScale));

    // Draw background column stripes (behind everything)
    renderColumnBackgrounds();

    // Draw links, then nodes, then labels
    renderGraph();

    // Y-axis timeline on the left edge
    createTimelineAxis();

    // Column headers (school names at top)
    renderColumnLabels();

    // Force simulation
    createSimulation();

    // UI wiring
    setupEventListeners();
    createLegend();

    console.log('Visualization ready.');
}

// ---------------------------------------------------------------------------
// Data processing
// ---------------------------------------------------------------------------

function processNodeData() {
    // Compute birth years from Unix timestamps
    graphData.nodes.forEach(node => {
        const clamped = Math.max(node.born, -20000000000);
        node.birthYear = new Date(clamped * 1000).getFullYear();
    });

    // Determine which schools actually appear in the data
    const presentSchools = new Set(graphData.nodes.map(n => n.school));

    // Build ordered list: SCHOOL_ORDER first, then any extras
    const ordered = SCHOOL_ORDER.filter(s => presentSchools.has(s));
    presentSchools.forEach(s => { if (!ordered.includes(s)) ordered.push(s); });

    ordered.forEach((school, i) => {
        schoolColumns[school] = { x: i * COLUMN_WIDTH + COLUMN_WIDTH / 2, index: i };
    });

    // Global Y scale: older economists near top
    const minYear = d3.min(graphData.nodes, d => d.birthYear);
    const maxYear = d3.max(graphData.nodes, d => d.birthYear);
    const h = window.innerHeight;

    globalYScale = d3.scaleLinear()
        .domain([minYear - 10, maxYear + 10])
        .range([h * 0.88, TOP_PADDING]);

    // Seed starting positions so the simulation converges quickly
    graphData.nodes.forEach(node => {
        const col = schoolColumns[node.school] || schoolColumns['Other'];
        node.x = (col ? col.x : COLUMN_WIDTH / 2) + (Math.random() - 0.5) * 40;
        node.y = globalYScale(node.birthYear);
    });
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderColumnBackgrounds() {
    Object.entries(schoolColumns).forEach(([school, col]) => {
        g.append('rect')
            .attr('class', 'column-bg')
            .attr('x', col.x - COLUMN_WIDTH / 2)
            .attr('y', TOP_PADDING - 10)
            .attr('width', COLUMN_WIDTH)
            .attr('height', window.innerHeight - TOP_PADDING - BOT_PADDING + 10)
            .attr('fill', getSchoolColor(school))
            .attr('opacity', 0.04)
            .attr('rx', 8);
    });
}

function renderColumnLabels() {
    Object.entries(schoolColumns).forEach(([school, col]) => {
        g.append('text')
            .attr('class', 'column-label')
            .attr('x', col.x)
            .attr('y', TOP_PADDING - 18)
            .attr('text-anchor', 'middle')
            .style('font-size', '11px')
            .style('font-weight', '600')
            .style('fill', getSchoolColor(school))
            .style('pointer-events', 'none')
            .text(school);
    });
}

function renderGraph() {
    // Links
    linkElements = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(graphData.links)
        .enter().append('line')
        .attr('class', 'link');

    // Node groups (circle + optional label)
    const nodeGroup = g.append('g').attr('class', 'nodes')
        .selectAll('.node-group')
        .data(graphData.nodes)
        .enter().append('g')
        .attr('class', 'node-group')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag',  dragging)
            .on('end',   dragEnded));

    nodeElements = nodeGroup.append('circle')
        .attr('class', 'node')
        .attr('r',    d => getNodeRadius(d))
        .attr('fill', d => getSchoolColor(d.school))
        .on('click',  onNodeClick);

    nodeElements.append('title')
        .text(d => `${d.name} (${d.birthYear})\n${d.school}`);

    // Labels for high-PageRank nodes only (top ~15%)
    const threshold = d3.quantile(
        graphData.nodes.map(n => n.score).sort((a, b) => b - a),
        0.15
    );
    nodeGroup.filter(d => d.score >= threshold)
        .append('text')
        .attr('class', 'node-label')
        .attr('dy', d => getNodeRadius(d) + 10)
        .attr('text-anchor', 'middle')
        .style('font-size', '9px')
        .style('pointer-events', 'none')
        .text(d => d.name.split(' ').pop());
}

function createTimelineAxis() {
    if (!globalYScale) return;
    const axis = d3.axisLeft(globalYScale)
        .ticks(14)
        .tickFormat(d => Math.round(d) + '');
    g.append('g')
        .attr('class', 'axis axis--y')
        .attr('transform', 'translate(28, 0)')
        .call(axis);
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

function createSimulation() {
    simulation = d3.forceSimulation(graphData.nodes)
        // Connections — kept weak so column forces dominate
        .force('link', d3.forceLink(graphData.links)
            .id(d => d.id)
            .distance(40)
            .strength(0.08))
        // Light repulsion to separate nodes within a column
        .force('charge', d3.forceManyBody()
            .strength(-25)
            .distanceMax(120))
        // Prevent overlap
        .force('collision', d3.forceCollide()
            .radius(d => getNodeRadius(d) + 3))
        // X: pull strongly to school column
        .force('x', d3.forceX(d => {
            const col = schoolColumns[d.school] || schoolColumns['Other'];
            return col ? col.x : COLUMN_WIDTH / 2;
        }).strength(0.7))
        // Y: pin to birth year on the global timeline
        .force('y', d3.forceY(d => globalYScale(d.birthYear)).strength(0.9))
        .on('tick', ticked);
}

function ticked() {
    linkElements
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

    d3.selectAll('.node-group')
        .attr('transform', d => `translate(${d.x},${d.y})`);
}

// ---------------------------------------------------------------------------
// Drag
// ---------------------------------------------------------------------------

function dragStarted(d) {
    if (!d3.event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}
function dragging(d) {
    d.fx = d3.event.x;
    d.fy = d3.event.y;
}
function dragEnded(d) {
    if (!d3.event.active) simulation.alphaTarget(0);
    d.fx = null;
    // Re-pin Y to birth year so node snaps back to its time position
    d.fy = null;
}

// ---------------------------------------------------------------------------
// Node sizing
// ---------------------------------------------------------------------------

function getNodeRadius(node) {
    return Math.max(3, Math.min(18, Math.sqrt(node.score * 5000)));
}

// ---------------------------------------------------------------------------
// Interaction
// ---------------------------------------------------------------------------

function onNodeClick(d) {
    selectedNode = d;
    updateNodeStyles();
    highlightConnections(d);
    showEconomistModal(d);
}

function updateNodeStyles() {
    nodeElements
        .classed('selected',     d => d === selectedNode)
        .classed('search-match', d => searchMatches.includes(d));
}

function highlightConnections(node) {
    linkElements.classed('highlighted',
        d => d.source.id === node.id || d.target.id === node.id);
}

function showEconomistModal(node) {
    document.getElementById('economist-name').textContent  = node.name;
    document.getElementById('economist-dates').textContent = `Born: ${node.birthYear}`;
    document.getElementById('economist-link').href =
        node.url ||
        `https://en.wikipedia.org/wiki/${encodeURIComponent(node.name.replace(/ /g, '_'))}`;

    const badge = document.getElementById('economist-school');
    if (badge) {
        badge.textContent       = node.school || 'Unknown';
        badge.style.backgroundColor = getSchoolColor(node.school);
        badge.style.color       = '#fff';
    }

    const img = document.getElementById('economist-img');
    if (node.img) { img.src = node.img; img.style.display = 'block'; }
    else          { img.style.display = 'none'; }

    fetchWikipediaExtract(node);
    displayConnections(node);

    M.Modal.getInstance(document.getElementById('economist-modal')).open();
}

function fetchWikipediaExtract(node) {
    let title = null;
    if (node.url) {
        const parts = node.url.split('/wiki/');
        if (parts.length > 1) title = parts[1];
    }
    if (!title) title = encodeURIComponent(node.name.replace(/ /g, '_'));

    const url = `https://en.wikipedia.org/w/api.php?` +
        `action=query&prop=extracts&exintro=true&explaintext=true` +
        `&titles=${title}&format=json&origin=*`;

    document.getElementById('economist-description').textContent = 'Loading…';

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const page    = Object.values(data.query.pages)[0];
            const extract = (page && page.extract) || 'No description available.';
            document.getElementById('economist-description').textContent = extract;
        })
        .catch(() => {
            document.getElementById('economist-description').textContent =
                'Could not load description.';
        });
}

function displayConnections(node) {
    const influencedBy = graphData.links
        .filter(l => l.source.id === node.id).map(l => l.target.name);
    const influences = graphData.links
        .filter(l => l.target.id === node.id).map(l => l.source.name);

    document.getElementById('influences-list').innerHTML =
        influences.length ? influences.map(n => `<li>${n}</li>`).join('') : '<li>None recorded</li>';
    document.getElementById('influenced-by-list').innerHTML =
        influencedBy.length ? influencedBy.map(n => `<li>${n}</li>`).join('') : '<li>None recorded</li>';
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

function createLegend() {
    const legend = document.getElementById('legend-container');
    legend.innerHTML = '<h6>Fields of Thought</h6><p class="legend-hint">Click to filter</p>';

    const counts = {};
    graphData.nodes.forEach(n => {
        counts[n.school] = (counts[n.school] || 0) + 1;
    });

    const ordered = SCHOOL_ORDER.filter(s => counts[s]);
    Object.keys(counts).forEach(s => { if (!ordered.includes(s)) ordered.push(s); });

    ordered.forEach(school => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = `
            <span class="legend-color" style="background:${getSchoolColor(school)}"></span>
            <span class="legend-label">${school}</span>
            <span class="legend-count">(${counts[school]})</span>`;
        item.addEventListener('click', () => toggleSchoolFilter(school));
        legend.appendChild(item);
    });

    const btn = document.createElement('button');
    btn.className = 'btn-small waves-effect waves-light';
    btn.id = 'show-all-btn';
    btn.textContent = 'Show All';
    btn.style.display = 'none';
    btn.addEventListener('click', clearSchoolFilter);
    legend.appendChild(btn);
}

function toggleSchoolFilter(school) {
    if (activeSchoolFilter === school) { clearSchoolFilter(); return; }
    activeSchoolFilter = school;

    nodeElements
        .style('opacity',        d => d.school === school ? 1 : 0.08)
        .style('pointer-events', d => d.school === school ? 'all' : 'none');
    linkElements
        .style('opacity', d =>
            (d.source.school === school || d.target.school === school) ? 0.7 : 0.03);

    document.querySelectorAll('.legend-item').forEach(el => {
        const label = el.querySelector('.legend-label').textContent;
        el.classList.toggle('active',   label === school);
        el.classList.toggle('inactive', label !== school);
    });
    document.getElementById('show-all-btn').style.display = 'block';
}

function clearSchoolFilter() {
    activeSchoolFilter = null;
    nodeElements.style('opacity', 1).style('pointer-events', 'all');
    linkElements.style('opacity', 0.5);
    document.querySelectorAll('.legend-item').forEach(el =>
        el.classList.remove('active', 'inactive'));
    document.getElementById('show-all-btn').style.display = 'none';
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

function setupEventListeners() {
    // Timeline toggle: pin/unpin Y to birth year
    document.getElementById('timeline-toggle').addEventListener('change', function () {
        simulation.force('y',
            this.checked
                ? d3.forceY(d => globalYScale(d.birthYear)).strength(0.9)
                : null
        );
        simulation.alpha(0.4).restart();
    });

    // Search
    document.getElementById('search-input').addEventListener('input', function () {
        const q = this.value.toLowerCase().trim();
        searchMatches = q ? graphData.nodes.filter(n => n.name.toLowerCase().includes(q)) : [];
        updateNodeStyles();
    });

    // Resize
    window.addEventListener('resize', () => {
        simulation.force('center', null);
        simulation.alpha(0.2).restart();
    });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

window.addEventListener('DOMContentLoaded', init);
