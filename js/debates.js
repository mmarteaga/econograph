/* ================================================================
   debates.js  —  Econograph · Intellectual Debates View
   ================================================================
   Six recurring tensions that have shaped economic thought, each
   shown as a horizontal thread through time with two "sides",
   clickable economists, and an expandable narrative.
   ================================================================ */

(function () {
  'use strict';

  /* ── 1. HELPERS ───────────────────────────────────────────────── */

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function birthYearOf(n) {
    // Use app.js-computed value if available; otherwise compute ourselves
    if (n.birthYear != null) return n.birthYear;
    if (!n.born) return null;
    return Math.round(n.born / (365.25 * 86400) + 1970);
  }

  /* ── 2. ECONOMIST LOOKUP ──────────────────────────────────────── */

  function normName(s) {
    return String(s).toLowerCase().replace(/[^a-z ]/g, '').trim();
  }

  let _lookup = null;

  function buildLookup() {
    if (_lookup) return _lookup;
    _lookup = {};
    (graph.nodes || []).forEach(function (n) {
      _lookup[normName(n.name)] = n;
    });
    return _lookup;
  }

  function findNode(name) {
    var lk = buildLookup();
    var norm = normName(name);
    if (lk[norm]) return lk[norm];
    // Fallback: first word + last word match
    var parts = norm.split(' ').filter(Boolean);
    if (parts.length >= 2) {
      var first = parts[0];
      var last  = parts[parts.length - 1];
      return (graph.nodes || []).find(function (n) {
        var np = normName(n.name).split(' ').filter(Boolean);
        return np.length >= 2 &&
          np[0] === first &&
          np[np.length - 1] === last;
      }) || null;
    }
    return null;
  }

  /* ── 3. DEBATE DEFINITIONS ────────────────────────────────────── */

  var DEBATES = [
    {
      id:       'rules-discretion',
      num:      '01',
      title:    'Rules vs. Discretion',
      sideA:    'Rules',
      sideB:    'Discretion',
      colorA:   '#60a5fa',
      colorB:   '#fb923c',
      question: 'Should economic policy follow fixed, pre-committed rules — or adapt flexibly to circumstances?',
      descA:    'Predictable, rule-based policy is credible. Discretion invites political manipulation and time-inconsistency: policymakers will always be tempted to over-stimulate.',
      descB:    'No rule anticipates every shock. Effective policymakers must exercise judgment; rigid rules can worsen crises by preventing necessary responses.',
      narrative:
        'The debate over rules versus discretion cuts to the heart of modern central banking. Classical economists assumed markets self-corrected, so policy hardly mattered. Keynes shattered this confidence: governments must actively stabilize demand during recessions. Yet Friedman countered that activist policy created more instability than it cured, proposing a fixed money-growth rule. The formal breakthrough came from Robert Lucas\'s 1976 critique: since rational agents anticipate policy, only rule-based, credible commitments achieve lasting effects — discretionary policy is neutralized before it acts. Kydland and Prescott formalized this as the time-inconsistency problem: even well-meaning policymakers, unconstrained by rules, consistently deliver too much inflation because they cannot credibly commit to restraint. The resolution that emerged in the 1990s — inflation targeting, pioneered in New Zealand — represents "constrained discretion": a clear numerical target that anchors expectations while preserving flexibility in how it is pursued. The 2021-22 inflation surge reignited the debate: did central banks exercise too much discretion by holding rates near zero while supply chains tightened?',
      today:
        'Modern central banks use inflation targeting — a transparent anchor that constrains discretion without eliminating it. The Taylor Rule remains a benchmark for judging whether policy is too loose or too tight.',
      namesA: [
        'Adam Smith', 'David Ricardo', 'Friedrich Hayek', 'Milton Friedman',
        'Thomas J. Sargent', 'Finn E. Kydland', 'Edward C. Prescott',
        'Henry Simons', 'Karl Brunner', 'Allan H. Meltzer', 'Knut Wicksell',
        'Robert Lucas'
      ],
      namesB: [
        'John Maynard Keynes', 'Paul Samuelson', 'James Tobin', 'Ben Bernanke',
        'Olivier Blanchard', 'Franco Modigliani', 'Alvin Hansen', 'Paul Krugman',
        'Lawrence Summers', 'Christina Romer', 'Stanley Fischer'
      ],
      schoolsA: ['Chicago School', 'Austrian School', 'Public Choice'],
      schoolsB: ['Keynesian', 'Post-Keynesian'],
      keywordsA: ['monetarism', 'gold standard', 'natural rate', 'quantity theory',
                  'time-inconsistency', 'rules-based', 'sound money'],
      keywordsB: ['fiscal stimulus', 'aggregate demand', 'countercyclical',
                  'discretionary', 'demand management'],
    },

    {
      id:       'markets-state',
      num:      '02',
      title:    'Markets vs. State',
      sideA:    'Markets',
      sideB:    'State Intervention',
      colorA:   '#34d399',
      colorB:   '#a78bfa',
      question: 'Do markets allocate resources efficiently on their own, or do pervasive failures require government correction?',
      descA:    'Prices aggregate dispersed knowledge that no central authority can replicate. Intervention creates distortions and attracts rent-seekers, making outcomes worse.',
      descB:    'Markets fail systematically through externalities, public goods, information asymmetry, and monopoly power. Corrective intervention improves aggregate welfare.',
      narrative:
        'Adam Smith\'s invisible hand established markets as the default engine of prosperity — a premise that dominated economic thinking for a century. The first serious challenge came from Arthur Pigou, who showed that private and social costs diverge wherever there are externalities: the market left alone produces too much pollution, too little education. The Great Depression seemed to vindicate Keynes: markets could collapse into persistent unemployment, requiring state intervention to restore demand. But the postwar welfare state produced its own pathologies. Hayek warned of the knowledge problem: central planners cannot know what millions of price signals convey; markets aggregate dispersed information through a mechanism no government can replicate. Stigler and the Chicago School documented regulatory capture — the agencies meant to discipline industries get captured by them. The synthesis that emerged by the 1990s was nuanced: markets work well for most goods, but systematic failures — information asymmetry (Akerlof, Stiglitz, Spence), network effects, and climate externalities — justify targeted intervention. The 2008 financial crisis pushed the pendulum back toward recognizing deeper market instabilities that rational-agent models had missed entirely.',
      today:
        'The mainstream consensus accepts regulated markets: failures in finance, climate, and healthcare justify intervention, but the design matters enormously. The "market vs. state" frame is increasingly seen as a false binary — the real question is institutional quality.',
      namesA: [
        'Adam Smith', 'David Ricardo', 'Friedrich Hayek', 'Milton Friedman',
        'George Stigler', 'Gary Becker', 'Ludwig von Mises', 'Frank H. Knight',
        'James M. Buchanan', 'Gordon Tullock', 'Armen A. Alchian', 'Harold Demsetz'
      ],
      namesB: [
        'John Maynard Keynes', 'John Kenneth Galbraith', 'Joseph E. Stiglitz',
        'Amartya Sen', 'Arthur Cecil Pigou', 'Gunnar Myrdal', 'Daron Acemoglu',
        'Paul Samuelson', 'James E. Meade', 'Abba P. Lerner', 'Nicholas Kaldor',
        'Anthony B. Atkinson'
      ],
      schoolsA: ['Chicago School', 'Austrian School', 'Public Choice'],
      schoolsB: ['Keynesian', 'Welfare & Public Economics', 'Institutional',
                 'Post-Keynesian', 'Marxian'],
      keywordsA: ['free market', 'deregulation', 'price mechanism', 'laissez-faire',
                  'spontaneous order', 'competition', 'privatization'],
      keywordsB: ['market failure', 'externalities', 'public goods', 'information asymmetry',
                  'welfare state', 'regulation', 'government intervention'],
    },

    {
      id:       'expectations',
      num:      '03',
      title:    'Rational vs. Behavioral Agents',
      sideA:    'Rational Expectations',
      sideB:    'Bounded Rationality',
      colorA:   '#fbbf24',
      colorB:   '#f472b6',
      question: 'Do economic agents form expectations efficiently — using all available information — or are they systematically biased and cognitively constrained?',
      descA:    'Agents form forecasts as efficiently as economists do, correcting errors quickly through market discipline. Policy that ignores this will be anticipated and neutralized.',
      descB:    'Humans use heuristics, exhibit loss aversion, and follow crowds. These deviations from rationality are predictable, consequential, and cannot be arbitraged away.',
      narrative:
        'The question of how expectations form has reshaped macroeconomics more than any other methodological debate. Before the 1960s, it was largely ignored — Keynesian models assumed mechanical adaptive expectations or simply left them as a residual "animal spirits." John Muth\'s 1961 paper introduced the radical claim that agents form forecasts as efficiently as economists do, using all available information. Robert Lucas weaponized this against Keynesian policy: if people anticipate fiscal stimulus, they raise prices immediately, leaving real output unchanged — the policy ineffectiveness proposition. Thomas Sargent showed empirically that inflation could be ended rapidly through credible commitment, without years of unemployment, if agents updated their expectations instantly. But rational expectations required cognitive capacities real humans demonstrably lack. Herbert Simon had long argued for "bounded rationality" — agents satisfice rather than globally optimize. Kahneman and Tversky provided systematic experimental evidence of predictable cognitive biases: loss aversion, anchoring, framing effects. Thaler and Sunstein translated these into behavioral economics and "nudge" policy design. Robert Shiller applied behavioral insights to finance, explaining persistent bubbles as collective departures from rationality. The current frontier is heterogeneous-agent models that let different agents form expectations in different ways, abandoning the single representative agent entirely.',
      today:
        'DSGE models still use rational expectations as a workhorse, but central bank communication strategy is now explicitly designed around behavioral insights — managing how non-rational agents update expectations matters as much as setting the right rate.',
      namesA: [
        'Robert Lucas', 'Thomas J. Sargent', 'Finn E. Kydland', 'Edward C. Prescott',
        'Robert J. Barro', 'Neil Wallace', 'Patrick Minford', 'Robert E. Hall'
      ],
      namesB: [
        'Daniel Kahneman', 'Richard H. Thaler', 'Amos Tversky',
        'Robert J. Shiller', 'George A. Akerlof', 'Matthew Rabin',
        'Herbert A. Simon', 'Colin F. Camerer', 'Andrei Shleifer',
        'Ernst Fehr', 'David Laibson'
      ],
      schoolsA: [],
      schoolsB: ['Behavioral'],
      keywordsA: ['rational expectations', 'policy ineffectiveness', 'efficient markets',
                  'representative agent', 'DSGE', 'microfoundations', 'perfect foresight'],
      keywordsB: ['behavioral economics', 'bounded rationality', 'prospect theory',
                  'loss aversion', 'cognitive bias', 'heuristics', 'nudge',
                  'animal spirits', 'irrational exuberance'],
    },

    {
      id:       'growth-inequality',
      num:      '04',
      title:    'Growth vs. Inequality',
      sideA:    'Efficiency & Growth',
      sideB:    'Distribution & Equality',
      colorA:   '#22d3ee',
      colorB:   '#fb7185',
      question: 'Should economics prioritize aggregate growth and efficiency — or are distribution and inequality central concerns in their own right?',
      descA:    'Economic growth lifts living standards for all. Distortionary redistribution shrinks the pie. Inequality reflects returns to talent, investment, and risk-taking.',
      descB:    'Growth without equity is unsustainable and unjust. Rising inequality undermines social mobility, political stability, and — through demand effects — growth itself.',
      narrative:
        'For classical economics, growth and distribution were inseparable — Ricardo\'s entire system was about how national income splits between landlords, capitalists, and workers. The neoclassical revolution bracketed distribution as a political, not economic, question, focusing instead on efficient allocation. Simon Kuznets proposed an optimistic resolution in 1955: the Kuznets curve predicted inequality would first rise, then fall as economies industrialize — growth would eventually cure its own distributional problems. This comforting narrative dominated development economics for decades. Amartya Sen challenged the framing entirely in the 1980s: development must be measured in human capabilities — freedom, health, education — not just income per capita. Arthur Lewis\'s dual-sector model showed how labor migration from subsistence agriculture to industry drives growth while compressing rural inequality. Then Thomas Piketty\'s Capital in the Twenty-First Century (2014) detonated a paradigm shift: his r>g thesis — returns to capital systematically exceed growth rates — predicts rising inequality as a structural feature of capitalism, not a transitional phase. The accompanying data, compiled with Emmanuel Saez and others, showed inequality in wealthy countries had returned to pre-war levels. The debate now shapes policy directly: is inequality a brake on growth through its effects on demand, human capital investment, and political economy — or is redistribution a tax on the very engine of growth?',
      today:
        'Post-Piketty, inequality is a central macroeconomic concern. The IMF and World Bank now publish research arguing excessive inequality harms growth — a near-reversal of the 1980s-90s Washington Consensus.',
      namesA: [
        'Robert Solow', 'Simon Kuznets', 'Theodore W. Schultz', 'Gary Becker',
        'Robert Lucas', 'Paul M. Romer', 'Philippe Aghion', 'Robert J. Barro',
        'Dale Jorgenson', 'Zvi Griliches'
      ],
      namesB: [
        'Thomas Piketty', 'Anthony B. Atkinson', 'Amartya Sen', 'Gunnar Myrdal',
        'Arthur Lewis', 'Raúl Prebisch', 'Joseph E. Stiglitz',
        'Daron Acemoglu', 'Emmanuel Saez', 'Branko Milanovic'
      ],
      schoolsA: ['Classical/Neoclassical', 'Chicago School'],
      schoolsB: ['Development', 'Welfare & Public Economics', 'Marxian',
                 'Institutional', 'Political Economy'],
      keywordsA: ['economic growth', 'human capital', 'total factor productivity',
                  'endogenous growth', 'Solow model', 'Kuznets curve', 'Pareto efficiency'],
      keywordsB: ['inequality', 'wealth distribution', 'Gini coefficient', 'poverty',
                  'redistribution', 'capital accumulation', 'capabilities approach'],
    },

    {
      id:       'money-endogeneity',
      num:      '05',
      title:    'Exogenous vs. Endogenous Money',
      sideA:    'Exogenous Money',
      sideB:    'Endogenous Money',
      colorA:   '#818cf8',
      colorB:   '#4ade80',
      question: 'Does the central bank control the money supply — driving prices and output — or does money respond passively to the economy\'s own credit demands?',
      descA:    'The central bank determines the stock of money. Excessive money growth causes inflation. Controlling the money supply is the primary lever of macroeconomic stabilization.',
      descB:    'Banks create money endogenously when they extend credit. Central banks set interest rates and accommodate demand — money supply is a consequence, not a cause, of economic activity.',
      narrative:
        'Irving Fisher\'s quantity theory — MV = PQ — established money as the prime mover of prices: more money means higher prices, proportionally, once velocity and output are given. Milton Friedman reinvigorated this as monetarism, famously arguing that "inflation is always and everywhere a monetary phenomenon." Paul Volcker\'s experiment with money-supply targeting in 1979-82 seemed to confirm the framework\'s power — squeezing the money supply brought inflation down dramatically, at the cost of a severe recession. But a persistent minority tradition, rooted in Wicksell\'s credit theory and developed by Post-Keynesian economists, always contested this picture. Banks do not lend out reserves — they create deposits when they make loans, expanding the money supply endogenously in response to creditworthy borrowers. Hyman Minsky showed how this credit endogeneity generates inherent financial instability: boom phases see an explosion of credit, asset prices, and leverage; busts see sudden, self-reinforcing deleveraging. The 2008 financial crisis was, almost precisely, the Minsky moment he had theorized: credit expansion fueling asset bubbles, followed by sudden collapse. Since then, the Bank of England has officially endorsed the endogenous view in a landmark 2014 bulletin. Modern Monetary Theory extends this framework further: since governments issue their own currency, their debt is fundamentally different from private debt, and "money financing" of deficits need not be inflationary below full employment.',
      today:
        'Post-2008, endogenous money has moved from heterodox fringe to mainstream acknowledgment. The debate has shifted: not whether money is endogenous, but whether the resulting credit dynamics create financial instability that monetary policy must lean against.',
      namesA: [
        'Irving Fisher', 'Milton Friedman', 'Karl Brunner', 'Allan H. Meltzer',
        'Henry Thornton', 'David Hume', 'John Stuart Mill', 'Anna Schwartz',
        'Henry Simons', 'David Laidler'
      ],
      namesB: [
        'Hyman Minsky', 'Knut Wicksell', 'Nicholas Kaldor', 'Wynne Godley',
        'Basil Moore', 'Marc Lavoie', 'Michał Kalecki', 'Perry Mehrling',
        'Steve Keen', 'Randall Wray'
      ],
      schoolsA: ['Chicago School'],
      schoolsB: ['Post-Keynesian', 'Keynesian', 'Institutional'],
      keywordsA: ['quantity theory', 'monetarism', 'money supply', 'velocity of money',
                  'monetary base', 'NAIRU', 'inflation targeting'],
      keywordsB: ['endogenous money', 'financial instability', 'Minsky moment',
                  'credit creation', 'financial fragility', 'MMT', 'circuit theory'],
    },

    {
      id:       'trade-development',
      num:      '06',
      title:    'Free Trade vs. Industrial Policy',
      sideA:    'Free Trade',
      sideB:    'Industrial Policy',
      colorA:   '#facc15',
      colorB:   '#2dd4bf',
      question: 'Does free trade maximize welfare for all nations — or do developing economies need strategic protection to build industries they don\'t yet have?',
      descA:    'Comparative advantage means all nations gain from specialization and free exchange. Protection raises consumer prices and shelters inefficient industries from competitive discipline.',
      descB:    'Comparative advantage is historically contingent, not fixed. Every nation that industrialized used active policy — tariffs, subsidies, directed credit — to build industries it didn\'t "naturally" have.',
      narrative:
        'David Ricardo\'s comparative advantage theorem (1817) became one of economics\' most powerful ideas: even a country worse at producing everything still benefits from trade by specializing in its relative strength. Heckscher and Ohlin extended this to factor endowments, and Samuelson\'s factor price equalization theorem showed trade could substitute for migration — a powerful case for free exchange. This framework undergirded the GATT/WTO system and dominated trade policy for 150 years. Yet Friedrich List had already challenged it in 1841: infant industries in less-developed nations needed temporary protection to compete with entrenched rivals in industrialized countries — not because free trade is wrong in theory, but because it locks in existing comparative advantages, which may be contingent on history and policy. The structuralist school — Prebisch, Myrdal — showed developing countries faced systematically deteriorating terms of trade for commodities versus manufactures, trapping them in a "development ceiling." Ha-Joon Chang\'s empirical broadside Kicking Away the Ladder (2002) documented that every currently rich country industrialized behind protective walls — then advocated free trade only after achieving dominance. Paul Krugman\'s new trade theory showed that economies of scale and "first mover" advantages could create comparative advantages through policy, not just natural endowments. The China shock — disruptive employment effects of China\'s WTO entry, documented by Autor, Dorn, and Hanson — cracked the free-trade consensus in mainstream economics. Post-2016, industrial policy has surged back into political favor across the ideological spectrum.',
      today:
        'Industrial policy is experiencing a dramatic comeback — the US CHIPS Act, EU Green Deal, and Inflation Reduction Act signal a bipartisan return to strategic intervention that would have been unthinkable in 1995. The intellectual debate has shifted from "should we?" to "how do we do it well?"',
      namesA: [
        'David Ricardo', 'Eli F. Heckscher', 'Bertil Ohlin', 'Paul Samuelson',
        'Jagdish Bhagwati', 'Anne O. Krueger', 'Arnold Harberger',
        'Alan V. Deardorff', 'Gene Grossman'
      ],
      namesB: [
        'Friedrich List', 'Raúl Prebisch', 'Ha-Joon Chang', 'Dani Rodrik',
        'Albert O. Hirschman', 'Gunnar Myrdal', 'Paul Krugman',
        'Joseph E. Stiglitz', 'Erik Reinert', 'Celso Furtado'
      ],
      schoolsA: ['International Trade', 'Classical/Neoclassical'],
      schoolsB: ['Development', 'Institutional', 'Political Economy'],
      keywordsA: ['comparative advantage', 'free trade', 'factor endowments',
                  'gains from trade', 'trade liberalization', 'globalization'],
      keywordsB: ['industrial policy', 'infant industry', 'import substitution',
                  'structuralism', 'dependency theory', 'terms of trade',
                  'development state', 'strategic trade'],
    },
  ];

  /* ── 4. TAG ECONOMISTS TO DEBATE SIDES ───────────────────────── */

  // Memoized: { debateId: { nodesA: [], nodesB: [] } }
  var _resolved = {};

  function resolveDebate(debate) {
    if (_resolved[debate.id]) return _resolved[debate.id];

    var seenA = {}, seenB = {};
    var nodesA = [], nodesB = [];

    function addA(n) {
      if (!n || seenA[n.id] || seenB[n.id]) return;
      seenA[n.id] = true;
      n._debYear = birthYearOf(n);
      nodesA.push(n);
    }
    function addB(n) {
      if (!n || seenA[n.id] || seenB[n.id]) return;
      seenB[n.id] = true;
      n._debYear = birthYearOf(n);
      nodesB.push(n);
    }

    // 1. Force-listed names (highest priority)
    (debate.namesA || []).forEach(function (nm) { addA(findNode(nm)); });
    (debate.namesB || []).forEach(function (nm) { addB(findNode(nm)); });

    // 2. School-based matching (broader coverage for the timeline)
    var sA = new Set(debate.schoolsA || []);
    var sB = new Set(debate.schoolsB || []);
    (graph.nodes || []).forEach(function (n) {
      if (seenA[n.id] || seenB[n.id]) return;
      var sc = n.school || '';
      if (sA.has(sc)) addA(n);
      else if (sB.has(sc)) addB(n);
    });

    // Sort by birth year
    nodesA.sort(function (a, b) { return (a._debYear || 9999) - (b._debYear || 9999); });
    nodesB.sort(function (a, b) { return (a._debYear || 9999) - (b._debYear || 9999); });

    _resolved[debate.id] = { nodesA: nodesA, nodesB: nodesB };
    return _resolved[debate.id];
  }

  /* ── 5. BUILD TIMELINE SVG ────────────────────────────────────── */

  function buildTimelineSVG(debate) {
    var res   = resolveDebate(debate);
    var YR_MIN = 1700, YR_MAX = 2010;
    var W = 720, H = 110;
    var L = 30, R = W - 16;
    var SPAN  = YR_MAX - YR_MIN;
    var xOf   = function (yr) {
      return L + Math.max(0, Math.min(1, (yr - YR_MIN) / SPAN)) * (R - L);
    };

    var AY = 22, AXIS_Y = 55, BY = 88;

    var s = [];
    s.push('<svg viewBox="0 0 ' + W + ' ' + H + '" class="dt-svg" data-debate="' +
      esc(debate.id) + '" preserveAspectRatio="xMidYMid meet">');

    // Subtle decade grid
    for (var yr = 1700; yr <= 2010; yr += 50) {
      var gx = xOf(yr).toFixed(1);
      s.push('<line x1="' + gx + '" y1="8" x2="' + gx + '" y2="' + (H - 14) +
        '" stroke="#27272a" stroke-width="1"/>');
    }

    // Axis
    s.push('<line x1="' + L + '" y1="' + AXIS_Y + '" x2="' + R + '" y2="' + AXIS_Y +
      '" stroke="#3f3f46" stroke-width="1.5"/>');

    // Year ticks + labels
    [1700, 1800, 1900, 1950, 2000].forEach(function (y) {
      var tx = xOf(y).toFixed(1);
      s.push('<line x1="' + tx + '" y1="' + (AXIS_Y - 4) + '" x2="' + tx + '" y2="' + (AXIS_Y + 4) +
        '" stroke="#52525b" stroke-width="1.5"/>');
      s.push('<text x="' + tx + '" y="' + (H - 2) + '" text-anchor="middle" fill="#52525b"' +
        ' font-size="9" font-family="ui-monospace,monospace">' + y + '</text>');
    });

    // Arrow cap on axis
    s.push('<polygon points="' + (R + 1) + ',' + AXIS_Y + ' ' + (R - 5) + ',' + (AXIS_Y - 3) +
      ' ' + (R - 5) + ',' + (AXIS_Y + 3) + '" fill="#3f3f46"/>');

    // Side labels (A / B)
    s.push('<text x="4" y="' + (AY + 4) + '" fill="' + debate.colorA +
      '" font-size="9" font-family="system-ui,sans-serif" font-weight="700" opacity="0.9">A</text>');
    s.push('<text x="4" y="' + (BY + 4) + '" fill="' + debate.colorB +
      '" font-size="9" font-family="system-ui,sans-serif" font-weight="700" opacity="0.9">B</text>');

    // Draw dots — only force-listed economists (cleaner visual)
    function drawDots(nodes, cy, color, forceNames) {
      // Filter to force-listed only for cleanliness
      var forceSet = new Set((forceNames || []).map(normName));
      var toShow = nodes.filter(function (n) {
        return n._debYear && forceSet.has(normName(n.name));
      });

      // Anti-collision: bucket economists by 15-year windows, stagger vertically
      var bucketed = {};
      toShow.forEach(function (n) {
        var bucket = Math.round(n._debYear / 15) * 15;
        if (!bucketed[bucket]) bucketed[bucket] = [];
        bucketed[bucket].push(n);
      });

      toShow.forEach(function (n) {
        var x = xOf(n._debYear).toFixed(1);
        var lastName = n.name.replace(/\b(Jr\.|Sr\.|II|III|IV)\b\.?/gi, '')
          .trim().split(' ').filter(Boolean).pop() || n.name;
        // Stagger: within a bucket, offset y slightly
        var bucket = Math.round(n._debYear / 15) * 15;
        var idx = bucketed[bucket].indexOf(n);
        var yOff = idx > 0 ? (idx % 2 === 1 ? -10 : 10) : 0;
        var dotY = cy + yOff;

        s.push(
          '<g class="dt-dot" data-id="' + esc(n.id) + '" tabindex="0" role="button">' +
          '<title>' + esc(n.name) + ' (b. ' + n._debYear + ')</title>' +
          // Larger invisible hit area
          '<circle cx="' + x + '" cy="' + dotY + '" r="12" fill="transparent"/>' +
          // Visible dot
          '<circle cx="' + x + '" cy="' + dotY + '" r="5" fill="' + color +
          '" stroke="' + color + '" stroke-width="1" opacity="0.88"/>' +
          // Label — last name only
          '<text x="' + x + '" y="' + (dotY - 8) + '" text-anchor="middle" fill="#d4d4d8"' +
          ' font-size="7.5" font-family="system-ui,sans-serif" pointer-events="none">' +
          esc(lastName) + '</text>' +
          '</g>'
        );
      });
    }

    drawDots(res.nodesA, AY, debate.colorA, debate.namesA);
    drawDots(res.nodesB, BY, debate.colorB, debate.namesB);

    s.push('</svg>');
    return s.join('');
  }

  /* ── 6. RENDER DEBATE CARD ────────────────────────────────────── */

  function chipFor(n, color) {
    var by = n._debYear || birthYearOf(n);
    return '<button class="dt-chip" data-id="' + esc(n.id) + '"' +
      ' style="--chip-col:' + color + '">' +
      esc(n.name) +
      (by ? '<span class="dt-chip-yr">b.' + by + '</span>' : '') +
      '</button>';
  }

  function renderDebateCard(debate) {
    var res = resolveDebate(debate);

    // Chips: force-listed names that exist in graph, ordered by birth year
    var forceANodes = (debate.namesA || []).map(findNode).filter(Boolean);
    var forceBNodes = (debate.namesB || []).map(findNode).filter(Boolean);
    forceANodes.sort(function (a, b) { return (birthYearOf(a) || 9999) - (birthYearOf(b) || 9999); });
    forceBNodes.sort(function (a, b) { return (birthYearOf(a) || 9999) - (birthYearOf(b) || 9999); });

    var totalA = res.nodesA.length;
    var totalB = res.nodesB.length;

    return (
      '<div class="dt-card" id="dt-card-' + debate.id + '">' +

      '<div class="dt-card-hd">' +
      '<span class="dt-num">' + esc(debate.num) + '</span>' +
      '<div class="dt-hd-text">' +
      '<h2 class="dt-title">' + esc(debate.title) + '</h2>' +
      '<p class="dt-question">' + esc(debate.question) + '</p>' +
      '</div>' +
      '</div>' +

      // Two-column sides
      '<div class="dt-sides">' +

      '<div class="dt-side" style="--sc:' + debate.colorA + '">' +
      '<div class="dt-side-lbl">' + esc(debate.sideA) + '</div>' +
      '<p class="dt-side-desc">' + esc(debate.descA) + '</p>' +
      '<div class="dt-chips">' +
      forceANodes.map(function (n) { return chipFor(n, debate.colorA); }).join('') +
      (totalA > forceANodes.length
        ? '<span class="dt-plus">+' + (totalA - forceANodes.length) + ' more</span>'
        : '') +
      '</div>' +
      '</div>' +

      '<div class="dt-vs">vs.</div>' +

      '<div class="dt-side" style="--sc:' + debate.colorB + '">' +
      '<div class="dt-side-lbl">' + esc(debate.sideB) + '</div>' +
      '<p class="dt-side-desc">' + esc(debate.descB) + '</p>' +
      '<div class="dt-chips">' +
      forceBNodes.map(function (n) { return chipFor(n, debate.colorB); }).join('') +
      (totalB > forceBNodes.length
        ? '<span class="dt-plus">+' + (totalB - forceBNodes.length) + ' more</span>'
        : '') +
      '</div>' +
      '</div>' +

      '</div>' + // .dt-sides

      // Timeline
      '<div class="dt-timeline-wrap">' +
      buildTimelineSVG(debate) +
      '</div>' +

      // Today
      '<div class="dt-today">' +
      '<span class="dt-today-badge">Today</span> ' +
      '<span>' + esc(debate.today) + '</span>' +
      '</div>' +

      // Narrative toggle
      '<button class="dt-narr-toggle" data-debate="' + esc(debate.id) + '">' +
      '<svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12" class="dt-narr-chevron">' +
      '<path d="M4 6l4 4 4-4"/></svg>' +
      'Read the full story' +
      '</button>' +

      '<div class="dt-narrative" id="dt-narr-' + esc(debate.id) + '" aria-hidden="true">' +
      '<p>' + esc(debate.narrative) + '</p>' +
      '</div>' +

      '</div>' // .dt-card
    );
  }

  /* ── 7. OPEN / CLOSE ──────────────────────────────────────────── */

  function openDebates() {
    var overlay = document.getElementById('debates-overlay');
    if (!overlay) return;

    // Lazy render
    if (!overlay.dataset.rendered) {
      var content = document.getElementById('debates-content');
      if (content) {
        content.innerHTML = DEBATES.map(renderDebateCard).join('');
      }
      overlay.dataset.rendered = '1';
    }

    overlay.classList.remove('dt-hidden');
    document.body.style.overflow = 'hidden';

    // Focus trap — put focus inside the panel
    var closeBtn = document.getElementById('debates-close-btn');
    if (closeBtn) closeBtn.focus();
  }

  function closeDebates() {
    var overlay = document.getElementById('debates-overlay');
    if (overlay) overlay.classList.add('dt-hidden');
    document.body.style.overflow = '';
  }

  /* ── 8. NARRATIVE TOGGLE ──────────────────────────────────────── */

  function toggleNarrative(debateId) {
    var narr = document.getElementById('dt-narr-' + debateId);
    var btn  = document.querySelector('.dt-narr-toggle[data-debate="' + debateId + '"]');
    if (!narr || !btn) return;

    var isOpen = narr.classList.contains('dt-narr-open');
    if (isOpen) {
      narr.classList.remove('dt-narr-open');
      narr.setAttribute('aria-hidden', 'true');
      btn.classList.remove('dt-narr-toggle--open');
    } else {
      narr.classList.add('dt-narr-open');
      narr.setAttribute('aria-hidden', 'false');
      btn.classList.add('dt-narr-toggle--open');
    }
  }

  /* ── 9. EVENT HANDLING ────────────────────────────────────────── */

  function handleOverlayClick(e) {
    // Economist dot (SVG)
    var dot = e.target.closest('.dt-dot');
    if (dot) {
      var id = dot.dataset.id;
      if (id && window.econograph) {
        var node = window.econograph.nodeById[id];
        if (node) {
          closeDebates();
          window.econograph.openDetail(node);
        }
      }
      return;
    }

    // Economist chip (HTML)
    var chip = e.target.closest('.dt-chip');
    if (chip) {
      var cid = chip.dataset.id;
      if (cid && window.econograph) {
        var cnode = window.econograph.nodeById[cid];
        if (cnode) {
          closeDebates();
          window.econograph.openDetail(cnode);
        }
      }
      return;
    }

    // Narrative toggle
    var toggle = e.target.closest('.dt-narr-toggle');
    if (toggle) {
      toggleNarrative(toggle.dataset.debate);
      return;
    }

    // Click on dark backdrop (outside panel) → close
    if (e.target === document.getElementById('debates-overlay')) {
      closeDebates();
    }
  }

  /* ── 10. INIT ─────────────────────────────────────────────────── */

  window.addEventListener('load', function () {
    // Resolve all debate nodes eagerly (while the page is idle) so
    // the first open is instant
    DEBATES.forEach(function (d) { resolveDebate(d); });

    var openBtn = document.getElementById('debates-open-btn');
    if (openBtn) openBtn.addEventListener('click', openDebates);

    var closeBtn = document.getElementById('debates-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', closeDebates);

    var overlay = document.getElementById('debates-overlay');
    if (overlay) overlay.addEventListener('click', handleOverlayClick);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var ov = document.getElementById('debates-overlay');
        if (ov && !ov.classList.contains('dt-hidden')) closeDebates();
      }
    });
  });

})();
