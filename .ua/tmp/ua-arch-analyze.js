#!/usr/bin/env node
// Structural analysis for architecture layer detection.
const fs = require('fs');

function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    console.error('usage: node ua-arch-analyze.js <input.json> <output.json>');
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const fileNodes = data.fileNodes || [];
  const importEdges = data.importEdges || [];
  const allEdges = data.allEdges || [];

  const nodeById = {};
  for (const n of fileNodes) nodeById[n.id] = n;

  // ---- A. Directory grouping (common prefix, then first segment) ----
  const filePaths = fileNodes.map(n => n.filePath);
  const commonPrefix = commonPathPrefix(filePaths);
  function dirOf(p) {
    let rest = p;
    if (commonPrefix && rest.startsWith(commonPrefix)) rest = rest.slice(commonPrefix.length);
    rest = rest.replace(/^\/+/, '');
    const seg = rest.split('/')[0];
    if (!seg) return '(root)';
    return seg;
  }
  const directoryGroups = {};
  for (const n of fileNodes) {
    const g = dirOf(n.filePath);
    (directoryGroups[g] = directoryGroups[g] || []).push(n.id);
  }

  // ---- B. Node type grouping ----
  const nodeTypeGroups = {};
  for (const n of fileNodes) {
    (nodeTypeGroups[n.type] = nodeTypeGroups[n.type] || []).push(n.id);
  }

  // ---- C. Import adjacency, fan-in/fan-out ----
  const adj = {}; // source -> set(target)
  const fileFanOut = {};
  const fileFanIn = {};
  for (const n of fileNodes) { adj[n.id] = new Set(); fileFanOut[n.id] = 0; fileFanIn[n.id] = 0; }
  const idSet = new Set(Object.keys(nodeById));
  for (const e of importEdges) {
    if (idSet.has(e.source) && idSet.has(e.target)) {
      adj[e.source].add(e.target);
      fileFanOut[e.source]++;
      fileFanIn[e.target]++;
    }
  }

  // ---- D. Cross-category edge matrix (from allEdges) ----
  const typeOf = {};
  for (const n of fileNodes) typeOf[n.id] = n.type;
  const crossMap = {};
  for (const e of allEdges) {
    if (!idSet.has(e.source) || !idSet.has(e.target)) continue;
    const key = `${typeOf[e.source]}|${typeOf[e.target]}|${e.type}`;
    crossMap[key] = (crossMap[key] || 0) + 1;
  }
  const crossCategoryEdges = Object.entries(crossMap).map(([k, count]) => {
    const [fromType, toType, edgeType] = k.split('|');
    return { fromType, toType, edgeType, count };
  }).sort((a, b) => b.count - a.count);

  // ---- E/F. Inter-group import frequency & intra-group density ----
  const groupOf = {};
  for (const [g, ids] of Object.entries(directoryGroups)) for (const id of ids) groupOf[id] = g;
  const interMap = {};
  const intraEdges = {};
  const totalEdgesPerGroup = {};
  for (const [g] of Object.entries(directoryGroups)) { intraEdges[g] = 0; totalEdgesPerGroup[g] = 0; }
  for (const e of importEdges) {
    if (!idSet.has(e.source) || !idSet.has(e.target)) continue;
    const gs = groupOf[e.source], gt = groupOf[e.target];
    if (gs === gt) {
      intraEdges[gs]++;
      totalEdgesPerGroup[gs]++;
    } else {
      const key = `${gs}|${gt}`;
      interMap[key] = (interMap[key] || 0) + 1;
      totalEdgesPerGroup[gs]++;
      totalEdgesPerGroup[gt]++;
    }
  }
  const interGroupImports = Object.entries(interMap).map(([k, count]) => {
    const [from, to] = k.split('|');
    return { from, to, count };
  }).sort((a, b) => b.count - a.count);
  const intraGroupDensity = {};
  for (const [g] of Object.entries(directoryGroups)) {
    const total = totalEdgesPerGroup[g] || 0;
    intraGroupDensity[g] = {
      internalEdges: intraEdges[g] || 0,
      totalEdges: total,
      density: total ? (intraEdges[g] || 0) / total : 0,
    };
  }

  // ---- G. Directory pattern matching ----
  const dirPatterns = {
    routes: 'api', api: 'api', controllers: 'api', endpoints: 'api', handlers: 'api', serializers: 'api', blueprints: 'api', router: 'api', routers: 'api', controller: 'api',
    services: 'service', core: 'service', lib: 'service', domain: 'service', logic: 'service', signals: 'service', internal: 'service', composables: 'service', mailers: 'service', jobs: 'service', channels: 'service',
    models: 'data', db: 'data', data: 'data', persistence: 'data', repository: 'data', entities: 'data', migrations: 'data', entity: 'data', sql: 'data', database: 'data', schema: 'data',
    components: 'ui', views: 'ui', pages: 'ui', ui: 'ui', layouts: 'ui', screens: 'ui',
    middleware: 'middleware', plugins: 'middleware', interceptors: 'middleware', guards: 'middleware',
    utils: 'utility', helpers: 'utility', common: 'utility', shared: 'utility', tools: 'utility', templatetags: 'utility', pkg: 'utility',
    config: 'config', constants: 'config', env: 'config', settings: 'config', management: 'config', commands: 'config',
    test: 'test', tests: 'test', spec: 'test', specs: 'test', __tests__: 'test',
    types: 'types', interfaces: 'types', schemas: 'types', contracts: 'types', dtos: 'types', dto: 'types', request: 'types', response: 'types',
    hooks: 'hooks',
    store: 'state', state: 'state', reducers: 'state', actions: 'state', slices: 'state',
    assets: 'assets', static: 'assets', public: 'assets',
    cmd: 'entry', bin: 'entry',
    docs: 'documentation', documentation: 'documentation', wiki: 'documentation',
    deploy: 'infrastructure', deployment: 'infrastructure', infra: 'infrastructure', infrastructure: 'infrastructure',
    k8s: 'infrastructure', kubernetes: 'infrastructure', helm: 'infrastructure', charts: 'infrastructure',
    terraform: 'infrastructure', tf: 'infrastructure', docker: 'infrastructure',
  };
  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    patternMatches[g] = dirPatterns[g.toLowerCase()] || null;
  }

  // ---- H. Deployment topology ----
  const infraFiles = fileNodes.filter(n => {
    const p = n.filePath.toLowerCase();
    return /dockerfile|docker-compose|\.tf$|\.tfvars$|k8s|kubernetes|helm|\.github\/workflows|\.gitlab-ci|jenkinsfile|Makefile/.test(p);
  }).map(n => n.filePath);
  const hasDockerfile = infraFiles.some(p => /dockerfile/i.test(p));
  const hasCompose = infraFiles.some(p => /docker-compose/i.test(p));
  const hasK8s = infraFiles.some(p => /k8s|kubernetes|helm|charts/i.test(p));
  const hasTerraform = infraFiles.some(p => /\.tf$|\.tfvars$|terraform/i.test(p));
  const hasCI = infraFiles.some(p => /\.github\/workflows|\.gitlab-ci|jenkinsfile|\.circleci/i.test(p));
  const deploymentTopology = { hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI, infraFiles };

  // ---- I. Data pipeline ----
  const isSchema = p => /\.sql$|\.graphql$|\.gql$|\.proto$|\.prisma$/i.test(p);
  const schemaFiles = fileNodes.filter(n => isSchema(n.filePath)).map(n => n.filePath);
  const migrationFiles = fileNodes.filter(n => /migration/i.test(n.filePath)).map(n => n.filePath);
  const dataModelFiles = fileNodes.filter(n => /models?|entities|data-model|schema/i.test(n.filePath) && n.type === 'file').map(n => n.filePath);
  const apiHandlerFiles = fileNodes.filter(n => /routes?|controllers?|endpoints?|handlers?/i.test(n.filePath) && n.type === 'file').map(n => n.filePath);
  const dataPipeline = { schemaFiles, migrationFiles, dataModelFiles, apiHandlerFiles };

  // ---- J. Documentation coverage ----
  const docNodes = fileNodes.filter(n => n.type === 'document');
  const groupsWithDocsSet = new Set();
  for (const d of docNodes) {
    const g = dirOf(d.filePath);
    groupsWithDocsSet.add(g);
  }
  // A directory "has docs" if any .md under it, or a README at its root, or docs/ references
  const totalGroups = Object.keys(directoryGroups).length;
  const groupsWithDocs = groupsWithDocsSet.size;
  const undocumentedGroups = Object.keys(directoryGroups).filter(g => !groupsWithDocsSet.has(g));
  const docCoverage = {
    groupsWithDocs, totalGroups,
    coverageRatio: totalGroups ? groupsWithDocs / totalGroups : 0,
    undocumentedGroups,
  };

  // ---- K. Dependency direction ----
  const dependencyDirection = [];
  const seen = new Set();
  for (const e of interGroupImports) {
    const rev = interMap[`${e.to}|${e.from}`] || 0;
    if (e.count > rev && !seen.has(`${e.from}->${e.to}`)) {
      dependencyDirection.push({ dependent: e.from, dependsOn: e.to });
      seen.add(`${e.from}->${e.to}`);
    }
  }
  dependencyDirection.sort((a, b) => a.dependent.localeCompare(b.dependent));

  // ---- fileStats ----
  const filesPerGroup = {};
  for (const [g, ids] of Object.entries(directoryGroups)) filesPerGroup[g] = ids.length;
  const nodeTypeCounts = {};
  for (const [t, ids] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = ids.length;

  const result = {
    scriptCompleted: true,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
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
      nodeTypeCounts,
    },
    fileFanIn,
    fileFanOut,
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.log('Wrote', outputPath, '| total nodes:', fileNodes.length);
}

function commonPathPrefix(paths) {
  if (!paths.length) return '';
  const parts = paths.map(p => p.split('/'));
  let prefix = [];
  const minLen = Math.min(...parts.map(p => p.length));
  for (let i = 0; i < minLen; i++) {
    const seg = parts[0][i];
    if (parts.every(p => p[i] === seg)) prefix.push(seg);
    else break;
  }
  return prefix.join('/');
}

main();
