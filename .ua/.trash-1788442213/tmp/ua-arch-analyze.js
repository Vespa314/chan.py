#!/usr/bin/env node
/**
 * Phase 1 — Structural Analysis Script
 * Analyzes file paths and import edges to compute structural patterns
 * that inform layer identification.
 */

const fs = require('fs');
const path = require('path');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-arch-analyze.js <input.json> <output.json>');
  process.exit(1);
}

try {
  const raw = fs.readFileSync(inputPath, 'utf8');
  const data = JSON.parse(raw);
  const { fileNodes, importEdges, allEdges } = data;

  // ===== A. Directory Grouping =====
  const dirGroups = {};
  const allPaths = fileNodes.map(n => n.filePath);

  // Compute common prefix
  const commonPrefix = computeCommonPrefix(allPaths);

  for (const node of fileNodes) {
    let relativePath = node.filePath;
    if (commonPrefix) {
      relativePath = relativePath.slice(commonPrefix.length);
    }
    const parts = relativePath.replace(/\\/g, '/').split('/').filter(Boolean);
    let group;
    if (parts.length === 0) {
      group = 'root';
    } else {
      group = parts[0];
    }
    if (!dirGroups[group]) dirGroups[group] = [];
    dirGroups[group].push(node.id);
  }

  // ===== B. Node Type Grouping =====
  const nodeTypeGroups = {};
  for (const node of fileNodes) {
    const t = node.type || 'unknown';
    if (!nodeTypeGroups[t]) nodeTypeGroups[t] = [];
    nodeTypeGroups[t].push(node.id);
  }

  // ===== C. Import Adjacency Matrix =====
  const fanIn = {};
  const fanOut = {};
  const adjList = {}; // source -> Set of targets

  for (const node of fileNodes) {
    fanIn[node.id] = 0;
    fanOut[node.id] = 0;
    adjList[node.id] = new Set();
  }

  for (const edge of importEdges) {
    const src = edge.source;
    const tgt = edge.target;
    if (adjList[src]) {
      adjList[src].add(tgt);
    }
    if (fanIn[tgt] !== undefined) fanIn[tgt]++;
    if (fanOut[src] !== undefined) fanOut[src]++;
  }

  // Convert sets to counts for output
  const fanOutCounts = {};
  for (const [id, s] of Object.entries(adjList)) {
    fanOutCounts[id] = s.size;
  }

  // Group-level import analysis
  // Build a map: file id -> group name
  const fileToGroup = {};
  for (const [group, ids] of Object.entries(dirGroups)) {
    for (const id of ids) {
      fileToGroup[id] = group;
    }
  }

  const groupImports = {}; // fromGroup -> { toGroup: count }
  const groupInternalEdges = {}; // group -> internal count
  const groupTotalEdges = {}; // group -> total edges involving the group

  for (const edge of importEdges) {
    const srcGroup = fileToGroup[edge.source];
    const tgtGroup = fileToGroup[edge.target];
    if (!srcGroup || !tgtGroup) continue;

    if (!groupImports[srcGroup]) groupImports[srcGroup] = {};
    if (!groupImports[srcGroup][tgtGroup]) groupImports[srcGroup][tgtGroup] = 0;
    groupImports[srcGroup][tgtGroup]++;

    // Track total edges per group
    if (!groupTotalEdges[srcGroup]) groupTotalEdges[srcGroup] = 0;
    groupTotalEdges[srcGroup]++;
    if (!groupTotalEdges[tgtGroup]) groupTotalEdges[tgtGroup] = 0;
    groupTotalEdges[tgtGroup]++;

    // Track internal edges
    if (srcGroup === tgtGroup) {
      if (!groupInternalEdges[srcGroup]) groupInternalEdges[srcGroup] = 0;
      groupInternalEdges[srcGroup]++;
    }
  }

  // ===== D. Cross-Category Dependency Analysis =====
  // Build a fast lookup: nodeId -> nodeType
  const nodeTypeMap = {};
  for (const node of fileNodes) {
    nodeTypeMap[node.id] = node.type || 'unknown';
  }

  const crossCategoryEdges = {}; // "fromType->toType:edgeType" -> count
  for (const edge of allEdges) {
    const fromType = nodeTypeMap[edge.source] || 'unknown';
    const toType = nodeTypeMap[edge.target] || 'unknown';
    const edgeType = edge.type || 'unknown';

    // Only count cross-category (different types)
    if (fromType !== toType) {
      const key = `${fromType}->${toType}:${edgeType}`;
      if (!crossCategoryEdges[key]) crossCategoryEdges[key] = 0;
      crossCategoryEdges[key]++;
    }
  }

  const crossCategoryList = [];
  for (const [key, count] of Object.entries(crossCategoryEdges)) {
    const match = key.match(/^(.+?)->(.+?):(.+)$/);
    if (match) {
      crossCategoryList.push({
        fromType: match[1],
        toType: match[2],
        edgeType: match[3],
        count
      });
    }
  }
  crossCategoryList.sort((a, b) => b.count - a.count);

  // ===== E. Inter-Group Import Frequency =====
  const interGroupImports = [];
  for (const [from, targets] of Object.entries(groupImports)) {
    for (const [to, count] of Object.entries(targets)) {
      if (from !== to) {
        interGroupImports.push({ from, to, count });
      }
    }
  }
  interGroupImports.sort((a, b) => b.count - a.count);

  // ===== F. Intra-Group Import Density =====
  const intraGroupDensity = {};
  for (const group of Object.keys(dirGroups)) {
    const internal = groupInternalEdges[group] || 0;
    const total = groupTotalEdges[group] || 0;
    const density = total > 0 ? internal / total : 0;
    intraGroupDensity[group] = { internalEdges: internal, totalEdges: total, density };
  }

  // ===== G. Directory Pattern Matching =====
  const patternMap = {
    'routes': 'api', 'api': 'api', 'controllers': 'api', 'endpoints': 'api', 'handlers': 'api',
    'services': 'service', 'core': 'service', 'lib': 'service', 'domain': 'service', 'logic': 'service',
    'models': 'data', 'db': 'data', 'data': 'data', 'persistence': 'data', 'repository': 'data', 'entities': 'data',
    'components': 'ui', 'views': 'ui', 'pages': 'ui', 'ui': 'ui', 'layouts': 'ui', 'screens': 'ui',
    'middleware': 'middleware', 'plugins': 'middleware', 'interceptors': 'middleware', 'guards': 'middleware',
    'utils': 'utility', 'helpers': 'utility', 'common': 'utility', 'shared': 'utility', 'tools': 'utility',
    'config': 'config', 'constants': 'config', 'env': 'config', 'settings': 'config',
    '__tests__': 'test', 'test': 'test', 'tests': 'test', 'spec': 'test', 'specs': 'test',
    'types': 'types', 'interfaces': 'types', 'schemas': 'types', 'contracts': 'types', 'dtos': 'types',
    'hooks': 'hooks', 'store': 'state', 'state': 'state', 'reducers': 'state', 'actions': 'state', 'slices': 'state',
    'assets': 'assets', 'static': 'assets', 'public': 'assets',
    'migrations': 'data', 'management': 'config', 'commands': 'config',
    'templatetags': 'utility', 'signals': 'service', 'serializers': 'api',
    'cmd': 'entry', 'internal': 'service', 'pkg': 'utility',
    'dto': 'types', 'request': 'types', 'response': 'types',
    'entity': 'data', 'controller': 'api', 'routers': 'api',
    'composables': 'service', 'blueprints': 'api',
    'mailers': 'service', 'jobs': 'service', 'channels': 'service',
    'bin': 'entry', 'docs': 'documentation', 'documentation': 'documentation', 'wiki': 'documentation',
    'deploy': 'infrastructure', 'deployment': 'infrastructure', 'infra': 'infrastructure', 'infrastructure': 'infrastructure',
    '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd',
    'k8s': 'infrastructure', 'kubernetes': 'infrastructure', 'helm': 'infrastructure', 'charts': 'infrastructure',
    'terraform': 'infrastructure', 'tf': 'infrastructure', 'docker': 'infrastructure',
    'sql': 'data', 'database': 'data', 'schema': 'data',
  };

  const patternMatches = {};
  for (const group of Object.keys(dirGroups)) {
    const lower = group.toLowerCase().replace(/[_-]/g, '');
    patternMatches[group] = patternMap[lower] || patternMap[group] || null;
  }

  // File-level pattern matching
  for (const node of fileNodes) {
    const name = node.name;
    const group = fileToGroup[node.id];

    // Test files
    if (/\.(test|spec)\./.test(name) || /^test_/.test(name) || /_test\.\w+$/.test(name) ||
        /Test\.\w+$/.test(name) || /_spec\.\w+$/.test(name) || /Test\.php$/.test(name) ||
        /Tests\.cs$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'test';
    }
    // TypeScript declaration files
    if (/\.d\.ts$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'types';
    }
    // Entry points
    if (name === 'index.ts' || name === 'index.js' || name === '__init__.py') {
      // Only mark as entry if at a package root — skip for now, pattern matching on dir name is better
    }
    if (name === 'manage.py' || name === 'main.go' || name === 'main.rs' || name === 'lib.rs' ||
        name === 'Application.java' || name === 'Program.cs' || name === 'config.ru') {
      patternMatches[group] = patternMatches[group] || 'entry';
    }
    if (name === 'wsgi.py' || name === 'asgi.py') {
      patternMatches[group] = patternMatches[group] || 'config';
    }
    // Config files
    if (['Cargo.toml', 'go.mod', 'Gemfile', 'pom.xml', 'build.gradle', 'composer.json'].includes(name)) {
      patternMatches[group] = patternMatches[group] || 'config';
    }
    // Infrastructure
    if (name === 'Dockerfile' || /^docker-compose\./.test(name)) {
      patternMatches[group] = patternMatches[group] || 'infrastructure';
    }
    if (/\.tf$/.test(name) || /\.tfvars$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'infrastructure';
    }
    if (/\.github\/workflows\/.+\.yml$/.test(node.filePath) || name === '.gitlab-ci.yml' || name === 'Jenkinsfile') {
      patternMatches[group] = patternMatches[group] || 'ci-cd';
    }
    if (/\.sql$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'data';
    }
    if (/\.(graphql|gql|proto)$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'types';
    }
    if (/\.(md|rst)$/.test(name)) {
      patternMatches[group] = patternMatches[group] || 'documentation';
    }
    if (name === 'Makefile') {
      patternMatches[group] = patternMatches[group] || 'infrastructure';
    }
  }

  // ===== H. Deployment Topology Detection =====
  const deploymentTopology = {
    hasDockerfile: false,
    hasCompose: false,
    hasK8s: false,
    hasTerraform: false,
    hasCI: false,
    infraFiles: []
  };

  for (const node of fileNodes) {
    const p = node.filePath.replace(/\\/g, '/');
    const name = node.name;
    if (name === 'Dockerfile' || /^Dockerfile\./.test(name)) {
      deploymentTopology.hasDockerfile = true;
      deploymentTopology.infraFiles.push(node.filePath);
    }
    if (/^docker-compose\./.test(name)) {
      deploymentTopology.hasCompose = true;
      deploymentTopology.infraFiles.push(node.filePath);
    }
    if (/\.tf$/.test(name) || /\.tfvars$/.test(name) || /^k8s\//.test(p) || /^kubernetes\//.test(p)) {
      deploymentTopology.hasK8s = true;
      deploymentTopology.hasTerraform = true;
      deploymentTopology.infraFiles.push(node.filePath);
    }
    if (/\.github\/workflows\//.test(p) || name === '.gitlab-ci.yml' || name === 'Jenkinsfile') {
      deploymentTopology.hasCI = true;
      deploymentTopology.infraFiles.push(node.filePath);
    }
  }

  // ===== I. Data Pipeline Detection =====
  const dataPipeline = {
    schemaFiles: [],
    migrationFiles: [],
    dataModelFiles: [],
    apiHandlerFiles: []
  };

  for (const node of fileNodes) {
    const p = node.filePath.replace(/\\/g, '/');
    const name = node.name;
    if (/\.sql$/.test(name) && !/migration/i.test(p)) {
      dataPipeline.schemaFiles.push(node.id);
    }
    if (/migration/i.test(p) && /\.sql$/.test(name)) {
      dataPipeline.migrationFiles.push(node.id);
    }
    if (/model|entity|schema/i.test(p) && node.type === 'file') {
      dataPipeline.dataModelFiles.push(node.id);
    }
    if (/route|api|controller|endpoint|handler/i.test(p) && node.type === 'file') {
      dataPipeline.apiHandlerFiles.push(node.id);
    }
  }

  // ===== J. Documentation Coverage =====
  const groupsWithDocs = new Set();
  const docFiles = fileNodes.filter(n => n.type === 'document' || /\.(md|rst)$/.test(n.name));

  for (const doc of docFiles) {
    const docGroup = fileToGroup[doc.id];
    if (docGroup) groupsWithDocs.add(docGroup);
  }

  // Also check for README in each group
  for (const node of fileNodes) {
    if (node.name.toLowerCase() === 'readme.md') {
      const g = fileToGroup[node.id];
      if (g) groupsWithDocs.add(g);
    }
  }

  const totalGroups = Object.keys(dirGroups).length;
  const docCoverage = {
    groupsWithDocs: groupsWithDocs.size,
    totalGroups,
    coverageRatio: totalGroups > 0 ? groupsWithDocs.size / totalGroups : 0,
    undocumentedGroups: Object.keys(dirGroups).filter(g => !groupsWithDocs.has(g))
  };

  // ===== K. Dependency Direction =====
  const dependencyDirection = [];
  const processedPairs = new Set();

  for (const [from, targets] of Object.entries(groupImports)) {
    for (const [to, count] of Object.entries(targets)) {
      if (from === to) continue;
      const pairKey = [from, to].sort().join('::');
      if (processedPairs.has(pairKey)) continue;
      processedPairs.add(pairKey);

      const aToB = count || 0;
      const bToA = (groupImports[to] && groupImports[to][from]) ? groupImports[to][from] : 0;

      if (aToB > bToA) {
        dependencyDirection.push({ dependent: from, dependsOn: to });
      } else if (bToA > aToB) {
        dependencyDirection.push({ dependent: to, dependsOn: from });
      }
      // Equal counts = no dominant direction, skip
    }
  }

  // ===== File Stats =====
  const filesPerGroup = {};
  for (const [group, ids] of Object.entries(dirGroups)) {
    filesPerGroup[group] = ids.length;
  }

  const nodeTypeCounts = {};
  for (const [t, ids] of Object.entries(nodeTypeGroups)) {
    nodeTypeCounts[t] = ids.length;
  }

  // ===== Output =====
  const result = {
    scriptCompleted: true,
    directoryGroups: dirGroups,
    nodeTypeGroups,
    crossCategoryEdges: crossCategoryList,
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    deploymentTopology,
    dataPipeline,
    docCoverage,
    dependencyDirection,
    fileStats: {
      totalFileNodes: fileNodes.length,
      filesPerGroup,
      nodeTypeCounts
    },
    fileFanIn: fanIn,
    fileFanOut: fanOutCounts
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf8');
  console.log(`Analysis complete. ${fileNodes.length} files, ${importEdges.length} imports, ${allEdges.length} total edges.`);
  console.log(`Directory groups: ${Object.keys(dirGroups).length}`);
  console.log(`Output written to ${outputPath}`);
  process.exit(0);

} catch (err) {
  console.error('FATAL:', err.message);
  console.error(err.stack);
  process.exit(1);
}

function computeCommonPrefix(paths) {
  if (paths.length === 0) return '';
  const normalized = paths.map(p => p.replace(/\\/g, '/'));
  let prefix = normalized[0];
  for (let i = 1; i < normalized.length; i++) {
    while (!normalized[i].startsWith(prefix)) {
      prefix = prefix.substring(0, prefix.lastIndexOf('/') + 1);
      if (!prefix) return '';
    }
  }
  return prefix;
}