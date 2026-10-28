/**
 * Phase 1: Graph Topology Analysis Script
 *
 * Analyzes a codebase knowledge graph to compute:
 * A. Fan-In Ranking (importance)
 * B. Fan-Out Ranking (scope)
 * C. Entry Point Candidates
 * D. BFS Traversal from entry point
 * E. Non-Code File Inventory
 * F. Tightly Coupled Clusters
 * G. Layer List
 * H. Node Summary Index
 */

const fs = require('fs');

// Read input
const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
    console.error('Usage: node ua-tour-analyze.js <input.json> <output.json>');
    process.exit(1);
}

let input;
try {
    input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
} catch (e) {
    console.error('Failed to read input file:', e.message);
    process.exit(1);
}

const { nodes, edges, layers } = input;

if (!nodes || !edges || !layers) {
    console.error('Input must contain nodes, edges, and layers');
    process.exit(1);
}

// ────────────────────────────────────────────────────────────
// H. Node Summary Index
// ────────────────────────────────────────────────────────────
const nodeSummaryIndex = {};
for (const node of nodes) {
    nodeSummaryIndex[node.id] = {
        name: node.name,
        type: node.type,
        summary: node.summary || ''
    };
}

// Build adjacency maps
const fanIn = {};    // nodeId -> count of edges pointing TO it
const fanOut = {};   // nodeId -> count of edges pointing FROM it
const incomingEdges = {}; // nodeId -> set of source nodeIds
const outgoingEdges = {}; // nodeId -> set of target nodeIds

// Initialize all nodes
for (const node of nodes) {
    fanIn[node.id] = 0;
    fanOut[node.id] = 0;
    incomingEdges[node.id] = new Set();
    outgoingEdges[node.id] = new Set();
}

const nodeIdSet = new Set(nodes.map(n => n.id));

for (const edge of edges) {
    const src = edge.source;
    const tgt = edge.target;

    // Only count edges where both source and target are known nodes
    if (nodeIdSet.has(src)) {
        fanOut[src] = (fanOut[src] || 0) + 1;
        if (outgoingEdges[src]) {
            outgoingEdges[src].add(tgt);
        }
    }
    if (nodeIdSet.has(tgt)) {
        fanIn[tgt] = (fanIn[tgt] || 0) + 1;
        if (incomingEdges[tgt]) {
            incomingEdges[tgt].add(src);
        }
    }
}

// ────────────────────────────────────────────────────────────
// A. Fan-In Ranking (Importance)
// ────────────────────────────────────────────────────────────
const fanInRanking = nodes
    .map(n => ({ id: n.id, fanIn: fanIn[n.id] || 0, name: n.name }))
    .sort((a, b) => b.fanIn - a.fanIn)
    .slice(0, 20);

// ────────────────────────────────────────────────────────────
// B. Fan-Out Ranking (Scope)
// ────────────────────────────────────────────────────────────
const fanOutRanking = nodes
    .map(n => ({ id: n.id, fanOut: fanOut[n.id] || 0, name: n.name }))
    .sort((a, b) => b.fanOut - a.fanOut)
    .slice(0, 20);

// ────────────────────────────────────────────────────────────
// C. Entry Point Candidates
// ────────────────────────────────────────────────────────────
const entryPointPatterns = [
    'index.ts', 'index.js', 'main.ts', 'main.js', 'app.ts', 'app.js',
    'server.ts', 'server.js', 'mod.rs', 'main.go', 'main.py', 'main.rs',
    'manage.py', 'app.py', 'wsgi.py', 'asgi.py', 'run.py', '__main__.py',
    'Application.java', 'Main.java', 'Program.cs', 'config.ru', 'index.php',
    'App.swift', 'Application.kt', 'main.cpp', 'main.c'
];

// Compute fan-in thresholds
const fanInValues = Object.values(fanIn).filter(v => v > 0).sort((a, b) => a - b);
const top10FanOutThreshold = (() => {
    const fanOutValues = Object.values(fanOut).sort((a, b) => b - a);
    if (fanOutValues.length === 0) return 0;
    const idx = Math.max(0, Math.floor(fanOutValues.length * 0.1) - 1);
    return fanOutValues[idx] || 0;
})();
const bottom25FanInThreshold = (() => {
    const sorted = fanInValues;
    if (sorted.length === 0) return Infinity;
    const idx = Math.floor(sorted.length * 0.25);
    return sorted[idx] || sorted[0];
})();

function scoreEntryPoint(node) {
    let score = 0;
    const name = node.name || '';
    const filePath = node.filePath || node.id || '';

    if (node.type === 'document') {
        if (name === 'README.md' && (filePath === 'README.md' || filePath === 'README.md')) {
            score += 5;
        } else if (name.endsWith('.md') && !filePath.includes('/')) {
            score += 2;
        }
        return score;
    }

    // Filename match
    for (const pattern of entryPointPatterns) {
        if (name === pattern || name.endsWith('/' + pattern)) {
            score += 3;
            break;
        }
    }

    // Check if file is at project root or one level deep
    if (filePath && !filePath.includes('/')) {
        score += 1; // root level
    } else if (filePath && filePath.split('/').length === 2) {
        score += 1; // one level deep
    }

    // High fan-out (top 10%)
    if ((fanOut[node.id] || 0) >= top10FanOutThreshold && fanOut[node.id] > 0) {
        score += 1;
    }

    // Low fan-in (bottom 25%)
    if ((fanIn[node.id] || 0) <= bottom25FanInThreshold) {
        score += 1;
    }

    return score;
}

const entryPointCandidates = nodes
    .map(n => ({ id: n.id, score: scoreEntryPoint(n), name: n.name, summary: n.summary || '' }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

// ────────────────────────────────────────────────────────────
// D. BFS Traversal from Entry Point
// ────────────────────────────────────────────────────────────

// Find the top code entry point (skip documents for BFS)
const topCodeEntry = entryPointCandidates.find(c => {
    const nodeInfo = nodeSummaryIndex[c.id];
    return nodeInfo && nodeInfo.type !== 'document';
});

let bfsResult = {
    startNode: null,
    order: [],
    depthMap: {},
    byDepth: {}
};

if (topCodeEntry) {
    const startNodeId = topCodeEntry.id;
    const visited = new Set();
    const depthMap = {};
    const byDepth = {};
    const queue = [];

    // BFS initialization
    visited.add(startNodeId);
    depthMap[startNodeId] = 0;
    byDepth['0'] = [startNodeId];
    queue.push({ id: startNodeId, depth: 0 });

    while (queue.length > 0) {
        const { id, depth } = queue.shift();

        // Follow 'imports' and 'calls' edges forward
        const neighbors = outgoingEdges[id] || new Set();
        for (const neighbor of neighbors) {
            if (!visited.has(neighbor) && nodeIdSet.has(neighbor)) {
                // Check if there's an imports or calls edge from id to neighbor
                const hasRelevantEdge = edges.some(e =>
                    e.source === id && e.target === neighbor &&
                    (e.type === 'imports' || e.type === 'calls')
                );
                if (hasRelevantEdge) {
                    visited.add(neighbor);
                    const newDepth = depth + 1;
                    depthMap[neighbor] = newDepth;
                    if (!byDepth[String(newDepth)]) {
                        byDepth[String(newDepth)] = [];
                    }
                    byDepth[String(newDepth)].push(neighbor);
                    queue.push({ id: neighbor, depth: newDepth });
                }
            }
        }
    }

    bfsResult = {
        startNode: startNodeId,
        order: [...visited],
        depthMap: depthMap,
        byDepth: byDepth
    };
}

// ────────────────────────────────────────────────────────────
// E. Non-Code File Inventory
// ────────────────────────────────────────────────────────────
const nonCodeFiles = {
    documentation: [],
    infrastructure: [],
    data: [],
    config: []
};

for (const node of nodes) {
    const entry = { id: node.id, name: node.name, summary: node.summary || '' };

    if (node.type === 'document') {
        nonCodeFiles.documentation.push(entry);
    } else if (node.type === 'service' || node.type === 'pipeline' || node.type === 'resource') {
        nonCodeFiles.infrastructure.push(entry);
    } else if (node.type === 'table' || node.type === 'schema' || node.type === 'endpoint') {
        nonCodeFiles.data.push(entry);
    } else if (node.type === 'config') {
        nonCodeFiles.config.push(entry);
    }
}

// ────────────────────────────────────────────────────────────
// F. Tightly Coupled Clusters
// ────────────────────────────────────────────────────────────

// Build an undirected edge map: for each pair (a,b) count edges in both directions
const pairEdgeCount = {}; // "a|b" -> count
function pairKey(a, b) {
    return a < b ? `${a}|${b}` : `${b}|${a}`;
}

// Only consider certain edge types for clustering
const clusterEdgeTypes = new Set(['imports', 'calls', 'depends_on', 'inherits']);

for (const edge of edges) {
    if (!clusterEdgeTypes.has(edge.type)) continue;
    if (!nodeIdSet.has(edge.source) || !nodeIdSet.has(edge.target)) continue;
    const key = pairKey(edge.source, edge.target);
    pairEdgeCount[key] = (pairEdgeCount[key] || 0) + 1;
}

// Find bidirectional pairs (at least 2 edges between them)
const bidirectionalPairs = [];
for (const [key, count] of Object.entries(pairEdgeCount)) {
    if (count >= 2) {
        const [a, b] = key.split('|');
        // Check if there's at least one edge in each direction
        const aToB = edges.filter(e => e.source === a && e.target === b && clusterEdgeTypes.has(e.type)).length;
        const bToA = edges.filter(e => e.source === b && e.target === a && clusterEdgeTypes.has(e.type)).length;
        if (aToB >= 1 && bToA >= 1) {
            bidirectionalPairs.push({ a, b, count });
        }
    }
}

// Build clusters from bidirectional pairs
const parent = {};
const rank = {};

function find(x) {
    if (parent[x] === undefined) {
        parent[x] = x;
        rank[x] = 0;
    }
    if (parent[x] !== x) {
        parent[x] = find(parent[x]);
    }
    return parent[x];
}

function union(x, y) {
    const rx = find(x);
    const ry = find(y);
    if (rx === ry) return;
    if (rank[rx] < rank[ry]) {
        parent[rx] = ry;
    } else if (rank[rx] > rank[ry]) {
        parent[ry] = rx;
    } else {
        parent[ry] = rx;
        rank[rx]++;
    }
}

// Union bidirectional pairs
for (const pair of bidirectionalPairs) {
    union(pair.a, pair.b);
}

// Group by root
const clusterGroups = {};
for (const node of nodes) {
    const root = find(node.id);
    if (!clusterGroups[root]) clusterGroups[root] = [];
    clusterGroups[root].push(node.id);
}

// Expand clusters: add nodes that connect to 2+ existing cluster members
function expandCluster(clusterNodes) {
    const clusterSet = new Set(clusterNodes);
    let changed = true;
    while (changed) {
        changed = false;
        for (const node of nodes) {
            if (clusterSet.has(node.id)) continue;
            let connections = 0;
            const neighbors = new Set([
                ...(outgoingEdges[node.id] || []),
                ...(incomingEdges[node.id] || [])
            ]);
            for (const neighbor of neighbors) {
                if (clusterSet.has(neighbor)) connections++;
            }
            if (connections >= 2) {
                clusterSet.add(node.id);
                changed = true;
            }
        }
    }
    return [...clusterSet];
}

// Build final clusters (2-5 nodes)
const clusters = [];
for (const [root, members] of Object.entries(clusterGroups)) {
    if (members.length < 2) continue;
    const expanded = expandCluster(members);
    if (expanded.length >= 2 && expanded.length <= 5) {
        // Calculate edge count within cluster
        let edgeCount = 0;
        for (const key of Object.keys(pairEdgeCount)) {
            const [a, b] = key.split('|');
            if (expanded.includes(a) && expanded.includes(b)) {
                edgeCount += pairEdgeCount[key];
            }
        }
        clusters.push({ nodes: expanded, edgeCount });
    }
}

// Sort by edge count descending, take top 10
clusters.sort((a, b) => b.edgeCount - a.edgeCount);
const topClusters = clusters.slice(0, 10);

// ────────────────────────────────────────────────────────────
// G. Layer List
// ────────────────────────────────────────────────────────────
const layerList = layers.map(l => ({
    id: l.id,
    name: l.name,
    description: l.description
}));

// ────────────────────────────────────────────────────────────
// Build output
// ────────────────────────────────────────────────────────────
const result = {
    scriptCompleted: true,
    entryPointCandidates,
    fanInRanking,
    fanOutRanking,
    bfsTraversal: bfsResult,
    nonCodeFiles,
    clusters: topClusters,
    layers: {
        count: layers.length,
        list: layerList
    },
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length
};

// Write output
try {
    fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
} catch (e) {
    console.error('Failed to write output file:', e.message);
    process.exit(1);
}

console.log(`Analysis complete: ${nodes.length} nodes, ${edges.length} edges`);
console.log(`Top entry point: ${entryPointCandidates[0]?.name || 'none'} (score: ${entryPointCandidates[0]?.score || 0})`);
console.log(`BFS traversed: ${bfsResult.order.length} nodes from ${bfsResult.startNode || 'none'}`);
console.log(`Clusters found: ${topClusters.length}`);
console.log(`Output written to: ${outputPath}`);

process.exit(0);