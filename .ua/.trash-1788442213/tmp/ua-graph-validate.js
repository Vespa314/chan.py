#!/usr/bin/env node
/**
 * Knowledge Graph Validation Script
 * Reads assembled graph JSON, scan result, layers, and tour JSON.
 * Performs all deterministic validation checks and outputs results to a temp file.
 */

const fs = require('fs');
const path = require('path');

// --- Parse arguments ---
const graphFilePath = process.argv[2];
const outputFilePath = process.argv[3];
const scanResultPath = process.argv[4];
const layersPath = process.argv[5];
const tourPath = process.argv[6];

if (!graphFilePath || !outputFilePath) {
  console.error('Usage: node ua-graph-validate.js <graph.json> <output.json> [scan-result.json] [layers.json] [tour.json]');
  process.exit(1);
}

// --- Read input files ---
let graph, scanResult, layers, tour;
try {
  graph = JSON.parse(fs.readFileSync(graphFilePath, 'utf8'));
} catch (e) {
  console.error('Failed to read/parse graph file:', e.message);
  process.exit(1);
}

try {
  if (scanResultPath && fs.existsSync(scanResultPath)) {
    scanResult = JSON.parse(fs.readFileSync(scanResultPath, 'utf8'));
  }
} catch (e) {
  console.error('Failed to read/parse scan result file:', e.message);
  process.exit(1);
}

try {
  if (layersPath && fs.existsSync(layersPath)) {
    layers = JSON.parse(fs.readFileSync(layersPath, 'utf8'));
  }
} catch (e) {
  console.error('Failed to read/parse layers file:', e.message);
  process.exit(1);
}

try {
  if (tourPath && fs.existsSync(tourPath)) {
    tour = JSON.parse(fs.readFileSync(tourPath, 'utf8'));
  }
} catch (e) {
  console.error('Failed to read/parse tour file:', e.message);
  process.exit(1);
}

// --- Data structures ---
const nodes = graph.nodes || [];
const edges = graph.edges || [];
const issues = [];
const warnings = [];

// --- Valid type sets ---
const VALID_NODE_TYPES = new Set([
  'file', 'function', 'class', 'module', 'concept', 'config', 'document',
  'service', 'table', 'endpoint', 'pipeline', 'schema', 'resource',
  'domain', 'flow', 'step'
]);

const VALID_NODE_ID_PREFIXES = new Set([
  'file:', 'function:', 'class:', 'module:', 'concept:', 'config:', 'document:',
  'service:', 'table:', 'endpoint:', 'pipeline:', 'schema:', 'resource:',
  'domain:', 'flow:', 'step:'
]);

const VALID_EDGE_TYPES = new Set([
  'imports', 'exports', 'contains', 'inherits', 'implements', 'calls',
  'subscribes', 'publishes', 'middleware', 'reads_from', 'writes_to',
  'transforms', 'validates', 'depends_on', 'tested_by', 'configures',
  'related', 'similar_to', 'deploys', 'serves', 'migrates', 'documents',
  'provisions', 'routes', 'defines_schema', 'triggers', 'contains_flow',
  'flow_step', 'cross_domain'
]);

const VALID_EDGE_DIRECTIONS = new Set(['forward', 'backward', 'bidirectional']);
const VALID_COMPLEXITIES = new Set(['simple', 'moderate', 'complex']);

// File-level node types (for layer coverage check)
const FILE_LEVEL_TYPES = new Set([
  'file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint'
]);

// Domain graph detection
const DOMAIN_TYPES = new Set(['domain', 'flow', 'step']);

// --- Build lookup maps ---
const nodeIdSet = new Set();
const nodeMap = {};
const nodeIdToIndex = {};

for (let i = 0; i < nodes.length; i++) {
  const node = nodes[i];
  const id = node.id;
  nodeIdSet.add(id);
  nodeMap[id] = node;
  if (nodeIdToIndex[id] !== undefined) {
    // Duplicate ID found
    issues.push(`节点ID重复: '${id}' 出现在索引 ${nodeIdToIndex[id]} 和 ${i} 处`);
  }
  nodeIdToIndex[id] = i;
}

// --- Check 1: Schema Validation ---
for (let i = 0; i < nodes.length; i++) {
  const node = nodes[i];
  const id = node.id;

  // Check id
  if (typeof id !== 'string' || id.trim() === '') {
    issues.push(`节点索引 ${i}: 缺少有效的 'id' 字段`);
  } else {
    const hasValidPrefix = [...VALID_NODE_ID_PREFIXES].some(prefix => id.startsWith(prefix));
    if (!hasValidPrefix) {
      issues.push(`节点索引 ${i}: ID '${id}' 没有有效的前缀，有效前缀为: ${[...VALID_NODE_ID_PREFIXES].join(', ')}`);
    }
  }

  // Check type
  if (typeof node.type !== 'string' || !VALID_NODE_TYPES.has(node.type)) {
    issues.push(`节点索引 ${i} (${id}): 无效的 'type' 字段 '${node.type}'，有效类型为: ${[...VALID_NODE_TYPES].join(', ')}`);
  }

  // Check name
  if (typeof node.name !== 'string' || node.name.trim() === '') {
    issues.push(`节点索引 ${i} (${id}): 缺少有效的 'name' 字段`);
  }

  // Check summary
  if (typeof node.summary !== 'string' || node.summary.trim() === '') {
    issues.push(`节点索引 ${i} (${id}): 缺少有效的 'summary' 字段`);
  }

  // Check tags
  if (!Array.isArray(node.tags) || node.tags.length === 0) {
    issues.push(`节点索引 ${i} (${id}): 缺少有效的 'tags' 字段（至少需要一个元素）`);
  } else {
    for (let t = 0; t < node.tags.length; t++) {
      const tag = node.tags[t];
      if (typeof tag !== 'string' || tag !== tag.toLowerCase() || tag.includes(' ')) {
        issues.push(`节点索引 ${i} (${id}): tag '${tag}' 无效（必须全小写且使用连字符）`);
      }
    }
  }

  // Check complexity
  if (!VALID_COMPLEXITIES.has(node.complexity)) {
    issues.push(`节点索引 ${i} (${id}): 无效的 'complexity' 字段 '${node.complexity}'，有效值为: simple, moderate, complex`);
  }
}

// Edge schema validation
for (let i = 0; i < edges.length; i++) {
  const edge = edges[i];

  // Check source
  if (typeof edge.source !== 'string' || edge.source.trim() === '') {
    issues.push(`边索引 ${i}: 缺少有效的 'source' 字段`);
  }

  // Check target
  if (typeof edge.target !== 'string' || edge.target.trim() === '') {
    issues.push(`边索引 ${i}: 缺少有效的 'target' 字段`);
  }

  // Check type
  if (typeof edge.type !== 'string' || !VALID_EDGE_TYPES.has(edge.type)) {
    issues.push(`边索引 ${i}: 无效的边类型 '${edge.type}'，有效类型为: ${[...VALID_EDGE_TYPES].join(', ')}`);
  }

  // Check direction
  if (typeof edge.direction !== 'string' || !VALID_EDGE_DIRECTIONS.has(edge.direction)) {
    issues.push(`边索引 ${i}: 无效的边方向 '${edge.direction}'，有效值为: forward, backward, bidirectional`);
  }

  // Check weight
  if (typeof edge.weight !== 'number' || edge.weight < 0.0 || edge.weight > 1.0) {
    issues.push(`边索引 ${i}: 无效的边权重 '${edge.weight}'，必须在 0.0 到 1.0 之间`);
  }
}

// --- Check 2: Referential Integrity ---
for (let i = 0; i < edges.length; i++) {
  const edge = edges[i];
  if (edge.source && !nodeIdSet.has(edge.source)) {
    issues.push(`边索引 ${i}: source '${edge.source}' 引用了不存在的节点ID`);
  }
  if (edge.target && !nodeIdSet.has(edge.target)) {
    issues.push(`边索引 ${i}: target '${edge.target}' 引用了不存在的节点ID`);
  }
}

// Check layer nodeIds
if (layers && Array.isArray(layers)) {
  for (let l = 0; l < layers.length; l++) {
    const layer = layers[l];
    const nodeIds = layer.nodeIds || [];
    for (let n = 0; n < nodeIds.length; n++) {
      const nid = nodeIds[n];
      if (!nodeIdSet.has(nid)) {
        issues.push(`分层 '${layer.id || layer.name || l}' 中的 nodeIds[${n}] '${nid}' 引用了不存在的节点ID`);
      }
    }
  }
}

// Check tour step nodeIds
if (tour && Array.isArray(tour)) {
  for (let s = 0; s < tour.length; s++) {
    const step = tour[s];
    const nodeIds = step.nodeIds || [];
    for (let n = 0; n < nodeIds.length; n++) {
      const nid = nodeIds[n];
      if (!nodeIdSet.has(nid)) {
        issues.push(`导览步骤 ${step.order || s} 中的 nodeIds[${n}] '${nid}' 引用了不存在的节点ID`);
      }
    }
  }
}

// --- Check 3: Completeness ---
if (nodes.length === 0) {
  issues.push('图中没有节点');
}
if (edges.length === 0) {
  issues.push('图中没有边');
}

// Detect domain graph
const hasDomainNodes = nodes.some(n => DOMAIN_TYPES.has(n.type));
const isDomainGraph = hasDomainNodes;

if (!layers || !Array.isArray(layers) || layers.length === 0) {
  if (isDomainGraph) {
    warnings.push('域图没有分层定义（域图允许为空分层）');
  } else {
    issues.push('图中没有分层');
  }
}

if (!tour || !Array.isArray(tour) || tour.length === 0) {
  if (isDomainGraph) {
    warnings.push('域图没有导览步骤（域图允许为空导览）');
  } else {
    issues.push('图中没有导览步骤');
  }
}

// --- Check 4: Layer Coverage (only for structural graphs) ---
if (layers && Array.isArray(layers) && layers.length > 0 && !isDomainGraph) {
  const fileLevelNodeIds = new Set();
  for (const node of nodes) {
    if (FILE_LEVEL_TYPES.has(node.type)) {
      fileLevelNodeIds.add(node.id);
    }
  }

  const layerAssignment = {}; // nodeId -> [layerIndex, ...]
  for (let l = 0; l < layers.length; l++) {
    const layer = layers[l];
    const nodeIds = layer.nodeIds || [];

    if (nodeIds.length === 0) {
      issues.push(`分层 '${layer.id || layer.name || l}' 的 nodeIds 为空`);
    }

    for (const nid of nodeIds) {
      if (!layerAssignment[nid]) {
        layerAssignment[nid] = [];
      }
      layerAssignment[nid].push(l);
    }
  }

  // Check each file-level node appears in exactly one layer
  for (const nid of fileLevelNodeIds) {
    const assignments = layerAssignment[nid] || [];
    if (assignments.length === 0) {
      issues.push(`文件级节点 '${nid}' 未出现在任何分层中`);
    } else if (assignments.length > 1) {
      issues.push(`文件级节点 '${nid}' 出现在多个分层中: ${assignments.map(a => layers[a].id || layers[a].name).join(', ')}`);
    }
  }
} else if (isDomainGraph) {
  // Domain graph: skip layer coverage check
}

// --- Check 5: Uniqueness is already handled above ---

// --- Check 6: Tour Validation ---
if (tour && Array.isArray(tour) && tour.length > 0) {
  // Check step count
  if (tour.length < 5) {
    warnings.push(`导览步骤数量为 ${tour.length}，少于建议的 5-15 步范围`);
  } else if (tour.length > 15) {
    warnings.push(`导览步骤数量为 ${tour.length}，多于建议的 5-15 步范围`);
  }

  // Check sequential order
  const orders = tour.map(s => s.order);
  const sortedOrders = [...orders].sort((a, b) => a - b);
  const expectedOrders = [];
  for (let i = 1; i <= tour.length; i++) {
    expectedOrders.push(i);
  }

  const hasDuplicateOrders = new Set(orders).size !== orders.length;
  if (hasDuplicateOrders) {
    warnings.push('导览步骤中存在重复的 order 值');
  }

  const ordersSequential = sortedOrders.every((o, i) => o === i + 1);
  if (!ordersSequential) {
    warnings.push('导览步骤的 order 值不是从 1 开始的连续序列');
  }

  // Check each step has nodeIds
  for (let s = 0; s < tour.length; s++) {
    const step = tour[s];
    if (!step.nodeIds || step.nodeIds.length === 0) {
      warnings.push(`导览步骤 ${step.order || s} 没有 nodeIds（至少需要一个节点）`);
    }
  }
}

// --- Check 7: Quality Checks ---
// Empty or generic summaries
for (let i = 0; i < nodes.length; i++) {
  const node = nodes[i];
  const summary = (node.summary || '').trim();
  const name = (node.name || '').trim();

  if (summary === '') {
    warnings.push(`节点 '${node.id}' 的 summary 为空`);
  } else if (summary === name) {
    warnings.push(`节点 '${node.id}' 的 summary 与 name 完全相同`);
  } else if (summary.length < 10) {
    warnings.push(`节点 '${node.id}' 的 summary 过短（${summary.length} 字符）：'${summary}'`);
  }

  // Check if summary just restates the filename
  if (name && summary.includes(name) && summary.length <= name.length + 20) {
    // This is a heuristic - if summary is just the name plus a few words
    // We'll flag it if it's very short
    if (summary.length < 30) {
      warnings.push(`节点 '${node.id}' 的 summary 可能仅重复了文件名：'${summary}'`);
    }
  }
}

// Self-referencing edges
for (let i = 0; i < edges.length; i++) {
  const edge = edges[i];
  if (edge.source === edge.target) {
    warnings.push(`边索引 ${i}: 自引用边（source 和 target 均为 '${edge.source}'）`);
  }
}

// Orphan nodes
const nodeEdgeCount = {};
for (const node of nodes) {
  nodeEdgeCount[node.id] = 0;
}
for (const edge of edges) {
  if (nodeEdgeCount[edge.source] !== undefined) nodeEdgeCount[edge.source]++;
  if (nodeEdgeCount[edge.target] !== undefined) nodeEdgeCount[edge.target]++;
}

const orphanNodes = [];
for (const nodeId of Object.keys(nodeEdgeCount)) {
  if (nodeEdgeCount[nodeId] === 0) {
    orphanNodes.push(nodeId);
  }
}

if (orphanNodes.length > 0) {
  if (orphanNodes.length <= 10) {
    warnings.push(`${orphanNodes.length} 个节点没有任何边连接（孤立节点）: ${orphanNodes.join(', ')}`);
  } else {
    warnings.push(`${orphanNodes.length} 个节点没有任何边连接（孤立节点），前10个: ${orphanNodes.slice(0, 10).join(', ')}`);
  }
}

// --- Check 8: Non-Code Node Quality Checks ---
for (const node of nodes) {
  const nodeId = node.id;
  const nodeType = node.type;

  if (nodeType === 'document') {
    const hasDocumentsEdge = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && e.type === 'documents'
    );
    if (!hasDocumentsEdge) {
      warnings.push(`文档节点 '${nodeId}' 没有 'documents' 类型的边`);
    }
  }

  if (nodeType === 'service') {
    const hasDeploysOrDependsOn = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && (e.type === 'deploys' || e.type === 'depends_on')
    );
    if (!hasDeploysOrDependsOn) {
      warnings.push(`服务节点 '${nodeId}' 没有 'deploys' 或 'depends_on' 类型的边`);
    }
  }

  if (nodeType === 'pipeline') {
    const hasTriggers = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && e.type === 'triggers'
    );
    if (!hasTriggers) {
      warnings.push(`管道节点 '${nodeId}' 没有 'triggers' 类型的边`);
    }
  }

  if (nodeType === 'table') {
    const hasMigratesOrDefinesSchema = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && (e.type === 'migrates' || e.type === 'defines_schema')
    );
    if (!hasMigratesOrDefinesSchema) {
      warnings.push(`表节点 '${nodeId}' 没有 'migrates' 或 'defines_schema' 类型的边`);
    }
  }

  if (nodeType === 'schema') {
    const hasDefinesSchema = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && e.type === 'defines_schema'
    );
    if (!hasDefinesSchema) {
      warnings.push(`模式节点 '${nodeId}' 没有 'defines_schema' 类型的边`);
    }
  }

  if (nodeType === 'domain') {
    const hasContainsFlow = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && e.type === 'contains_flow'
    );
    if (!hasContainsFlow) {
      warnings.push(`域节点 '${nodeId}' 没有 'contains_flow' 类型的边`);
    }
  }

  if (nodeType === 'flow') {
    const hasFlowStep = edges.some(e =>
      (e.source === nodeId || e.target === nodeId) && e.type === 'flow_step'
    );
    if (!hasFlowStep) {
      warnings.push(`流节点 '${nodeId}' 没有 'flow_step' 类型的边`);
    }
  }
}

// --- Check 9: Node Type / ID Prefix Consistency ---
for (const node of nodes) {
  const id = node.id;
  const type = node.type;

  // Find the prefix that matches
  const matchingPrefix = [...VALID_NODE_ID_PREFIXES].find(p => id.startsWith(p));
  if (matchingPrefix) {
    const prefixType = matchingPrefix.replace(':', '');
    if (prefixType !== type) {
      warnings.push(`节点 '${id}' 的类型 '${type}' 与其ID前缀 '${matchingPrefix}' 不一致（期望类型为 '${prefixType}'）`);
    }
  }
}

// --- Additional Check: Scan result file coverage ---
if (scanResult && scanResult.files) {
  const scanFilePaths = scanResult.files.map(f => f.path);
  const graphFileNodeIds = nodes
    .filter(n => n.type === 'file' || n.type === 'document' || n.type === 'config')
    .map(n => {
      // Map graph node IDs to scan file paths
      // For file nodes, the ID is like "file:path/to/file.py"
      if (n.type === 'file' && n.id.startsWith('file:')) {
        return n.id.substring(5);
      }
      if (n.type === 'document' && n.id.startsWith('document:')) {
        return n.id.substring(9);
      }
      if (n.type === 'config' && n.id.startsWith('config:')) {
        return n.id.substring(7);
      }
      return null;
    })
    .filter(Boolean);

  const graphFileSet = new Set(graphFileNodeIds);

  for (const scanPath of scanFilePaths) {
    if (!graphFileSet.has(scanPath)) {
      // Check if it's a .ua/ internal file - those might be intentionally excluded
      if (scanPath.startsWith('.ua/')) {
        // .ua/ files are Understand Anything internal files, may not be in graph
        continue;
      }
      issues.push(`扫描结果中的文件 '${scanPath}' 未出现在知识图谱中`);
    }
  }
}

// --- Additional Check: Import map consistency ---
if (scanResult && scanResult.importMap) {
  const importMap = scanResult.importMap;

  // Build a set of (source, target) pairs from graph edges of type 'imports'
  const graphImportPairs = new Set();
  for (const edge of edges) {
    if (edge.type === 'imports' && edge.source.startsWith('file:') && edge.target.startsWith('file:')) {
      const src = edge.source.substring(5);
      const tgt = edge.target.substring(5);
      graphImportPairs.add(`${src}->${tgt}`);
    }
  }

  // Check import map entries against graph edges
  for (const [srcFile, imports] of Object.entries(importMap)) {
    for (const importedFile of imports) {
      const pair = `${srcFile}->${importedFile}`;
      if (!graphImportPairs.has(pair)) {
        warnings.push(`导入映射中 '${srcFile}' -> '${importedFile}' 的导入关系在知识图谱中未找到对应的 imports 边`);
      }
    }
  }
}

// --- Compute stats ---
const nodeTypes = {};
for (const node of nodes) {
  nodeTypes[node.type] = (nodeTypes[node.type] || 0) + 1;
}

const edgeTypes = {};
for (const edge of edges) {
  edgeTypes[edge.type] = (edgeTypes[edge.type] || 0) + 1;
}

const stats = {
  totalNodes: nodes.length,
  totalEdges: edges.length,
  totalLayers: (layers && Array.isArray(layers)) ? layers.length : 0,
  tourSteps: (tour && Array.isArray(tour)) ? tour.length : 0,
  nodeTypes: nodeTypes,
  edgeTypes: edgeTypes
};

// --- Output ---
const result = {
  scriptCompleted: true,
  issues: issues,
  warnings: warnings,
  stats: stats
};

fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2), 'utf8');
console.log(`Validation complete. ${issues.length} critical issues, ${warnings.length} warnings.`);
console.log(`Stats: ${stats.totalNodes} nodes, ${stats.totalEdges} edges, ${stats.totalLayers} layers, ${stats.tourSteps} tour steps.`);