#!/usr/bin/env node
// Phase 1 graph topology analyzer for tour-builder.
const fs = require('fs');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-tour-analyze.js <input.json> <output.json>');
  process.exit(1);
}

try {
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  const layers = data.layers || [];

  // Build node id set (file-level + non-code nodes only; function/class nodes excluded)
  const nodeById = new Map();
  for (const n of nodes) nodeById.set(n.id, n);
  const nodeIdSet = new Set(nodes.map((n) => n.id));

  // Only count edges whose BOTH endpoints are in the node set (file-level nodes).
  const relevantEdges = edges.filter(
    (e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target)
  );

  // ---- A. Fan-in ranking ----
  const fanIn = new Map();
  for (const n of nodes) fanIn.set(n.id, 0);
  for (const e of relevantEdges) fanIn.set(e.target, (fanIn.get(e.target) || 0) + 1);
  const fanInRanking = [...fanIn.entries()]
    .map(([id, fanIn]) => ({ id, fanIn, name: nodeById.get(id).name }))
    .sort((a, b) => b.fanIn - a.fanIn)
    .slice(0, 20);

  // ---- B. Fan-out ranking ----
  const fanOut = new Map();
  for (const n of nodes) fanOut.set(n.id, 0);
  for (const e of relevantEdges) fanOut.set(e.source, (fanOut.get(e.source) || 0) + 1);
  const fanOutRanking = [...fanOut.entries()]
    .map(([id, fanOut]) => ({ id, fanOut, name: nodeById.get(id).name }))
    .sort((a, b) => b.fanOut - a.fanOut)
    .slice(0, 20);

  // ---- C. Entry point candidates ----
  const ENTRY_NAMES = new Set([
    'index.ts','index.js','main.ts','main.js','app.ts','app.js','server.ts','server.js',
    'mod.rs','main.go','main.py','main.rs','manage.py','app.py','wsgi.py','asgi.py',
    'run.py','__main__.py','Application.java','Main.java','Program.cs','config.ru',
    'index.php','App.swift','Application.kt','main.cpp','main.c'
  ]);

  const fanOutValues = [...fanOut.values()];
  const fanOutSorted = [...fanOutValues].sort((a, b) => a - b);
  const fanOutTop10Threshold = fanOutSorted[Math.floor(fanOutSorted.length * 0.9)];
  const fanOutBottom25Threshold = fanOutSorted[Math.floor(fanOutSorted.length * 0.25)];

  function isCodeFile(n) { return n.type === 'file'; }
  function isRootOrOneDeep(filePath) {
    const parts = filePath.split('/').filter(Boolean);
    return parts.length <= 2;
  }

  const entryCandidates = [];
  for (const n of nodes) {
    let score = 0;
    if (isCodeFile(n)) {
      const base = n.name;
      if (ENTRY_NAMES.has(base)) score += 3;
      if (isRootOrOneDeep(n.filePath)) score += 1;
      const fo = fanOut.get(n.id) || 0;
      if (fo >= fanOutTop10Threshold && fo > 0) score += 1;
      if (fo <= fanOutBottom25Threshold) score += 1;
    }
    if (n.type === 'document') {
      if (n.name === 'README.md' && isRootOrOneDeep(n.filePath)) score += 5;
      else if (n.name.endsWith('.md') && isRootOrOneDeep(n.filePath)) score += 2;
    }
    if (score > 0) {
      entryCandidates.push({
        id: n.id, score, name: n.name, summary: n.summary || ''
      });
    }
  }
  entryCandidates.sort((a, b) => b.score - a.score);
  const entryCandidatesTop5 = entryCandidates.slice(0, 5);

  // ---- D. BFS from top CODE entry point (skip documents) ----
  const topCodeEntry = entryCandidates.find((c) => nodeById.get(c.id).type === 'file');

  // Build adjacency (forward) for imports + calls only, restricted to file-level nodes.
  const adj = new Map();
  for (const n of nodes) adj.set(n.id, []);
  for (const e of edges) {
    if ((e.type === 'imports' || e.type === 'calls') &&
        nodeIdSet.has(e.source) && nodeIdSet.has(e.target)) {
      adj.get(e.source).push(e.target);
    }
  }

  let bfsTraversal = { startNode: null, order: [], depthMap: {}, byDepth: {} };
  if (topCodeEntry) {
    const start = topCodeEntry.id;
    const depthMap = {};
    const visited = new Set();
    const queue = [{ id: start, depth: 0 }];
    visited.add(start);
    depthMap[start] = 0;
    const order = [];
    while (queue.length) {
      const { id, depth } = queue.shift();
      order.push(id);
      depthMap[id] = depth;
      const neighbors = adj.get(id) || [];
      for (const nb of neighbors) {
        if (!visited.has(nb)) {
          visited.add(nb);
          queue.push({ id: nb, depth: depth + 1 });
        }
      }
    }
    const byDepth = {};
    for (const [id, d] of Object.entries(depthMap)) {
      (byDepth[d] = byDepth[d] || []).push(id);
    }
    bfsTraversal = { startNode: start, order, depthMap, byDepth };
  }

  // ---- E. Non-code file inventory ----
  const nonCodeFiles = { documentation: [], infrastructure: [], data: [], config: [] };
  for (const n of nodes) {
    const item = { id: n.id, name: n.name, summary: n.summary || '' };
    if (n.type === 'document') nonCodeFiles.documentation.push(item);
    else if (n.type === 'service' || n.type === 'pipeline' || n.type === 'resource') nonCodeFiles.infrastructure.push(item);
    else if (n.type === 'table' || n.type === 'schema' || n.type === 'endpoint') nonCodeFiles.data.push(item);
    else if (n.type === 'config') nonCodeFiles.config.push(item);
  }

  // ---- F. Tightly coupled clusters ----
  const bidir = new Set();
  for (const e of relevantEdges) {
    const key = [e.source, e.target].sort().join('|');
    const rev = [e.target, e.source].sort().join('|');
    if (bidir.has(key)) continue;
    // check reverse edge exists
    const hasRev = relevantEdges.some(
      (e2) => e2.source === e.target && e2.target === e.source
    );
    if (hasRev) bidir.add(key);
  }
  // Group nodes connected by bidirectional edges into clusters (union-find on bidir pairs)
  const parent = new Map();
  function find(x) { if (!parent.has(x)) parent.set(x, x); if (parent.get(x) !== x) parent.set(x, find(parent.get(x))); return parent.get(x); }
  function union(a, b) { const ra = find(a), rb = find(b); if (ra !== rb) parent.set(ra, rb); }
  for (const key of bidir) {
    const [a, b] = key.split('|');
    union(a, b);
  }
  const groups = new Map();
  for (const key of bidir) {
    const [a] = key.split('|');
    const r = find(a);
    if (!groups.has(r)) groups.set(r, new Set());
    groups.get(r).add(a);
    groups.get(r).add(key.split('|')[1]);
  }
  const clusters = [...groups.values()]
    .map((s) => [...s])
    .filter((arr) => arr.length >= 2 && arr.length <= 5)
    .map((arr) => {
      // count edges within cluster
      let edgeCount = 0;
      const set = new Set(arr);
      for (const e of relevantEdges) {
        if (set.has(e.source) && set.has(e.target)) edgeCount++;
      }
      return { nodes: arr, edgeCount };
    })
    .sort((a, b) => b.edgeCount - a.edgeCount)
    .slice(0, 10);

  // ---- G. Layer list ----
  const layerList = layers.map((l) => ({ id: l.id, name: l.name, description: l.description }));

  // ---- H. Node summary index ----
  const nodeSummaryIndex = {};
  for (const n of nodes) {
    nodeSummaryIndex[n.id] = { name: n.name, type: n.type, summary: n.summary || '' };
  }

  const result = {
    scriptCompleted: true,
    entryPointCandidates: entryCandidatesTop5,
    fanInRanking,
    fanOutRanking,
    bfsTraversal,
    nonCodeFiles,
    clusters,
    layers: { count: layers.length, list: layerList },
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.error(`Wrote results to ${outputPath} (${nodes.length} nodes, ${edges.length} edges, ${relevantEdges.length} relevant edges)`);
  process.exit(0);
} catch (err) {
  console.error('Fatal error:', err.message);
  process.exit(1);
}
