#!/usr/bin/env python3
"""Phase 1 -- Structural Analysis Script (optimized)"""
import json, sys, os, re, time

t0 = time.time()
input_path = sys.argv[1]
output_path = sys.argv[2]

with open(input_path, 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'json loaded in {time.time()-t0:.1f}s', flush=True)

nodes = d['fileNodes']
imports = d['importEdges']
alledges = d['allEdges']

# A: Directory groups
dir_groups = {}
for node in nodes:
    parts = [p for p in node['filePath'].replace('\\', '/').split('/') if p]
    group = parts[0] if parts else 'root'
    dir_groups.setdefault(group, []).append(node['id'])
print(f'A: {len(dir_groups)} dir groups', flush=True)

# B: Node types
ntg = {}
for node in nodes:
    t = node.get('type', 'unknown')
    ntg.setdefault(t, []).append(node['id'])
print(f'B: {len(ntg)} node types', flush=True)

# C: Adjacency
adj = {}
fi = {}
fo = {}
for node in nodes:
    adj[node['id']] = set()
    fi[node['id']] = 0
    fo[node['id']] = 0
for edge in imports:
    s, t = edge['source'], edge['target']
    if s in adj:
        adj[s].add(t)
    if t in fi:
        fi[t] += 1
    if s in fo:
        fo[s] += 1
foc = {k: len(v) for k, v in adj.items()}
print(f'C: adj done', flush=True)

# File to group
f2g = {}
for g, ids in dir_groups.items():
    for fid in ids:
        f2g[fid] = g

# Group imports
gi = {}
gie = {}
gte = {}
for edge in imports:
    sg = f2g.get(edge['source'])
    tg = f2g.get(edge['target'])
    if not sg or not tg:
        continue
    gi.setdefault(sg, {}).setdefault(tg, 0)
    gi[sg][tg] += 1
    gte[sg] = gte.get(sg, 0) + 1
    gte[tg] = gte.get(tg, 0) + 1
    if sg == tg:
        gie[sg] = gie.get(sg, 0) + 1
print(f'C2: group imports done', flush=True)

# D: Cross category
ntm = {n['id']: n.get('type', 'unknown') for n in nodes}
cc = {}
for edge in alledges:
    ft = ntm.get(edge['source'], 'unknown')
    tt = ntm.get(edge['target'], 'unknown')
    et = edge.get('type', 'unknown')
    if ft != tt:
        k = f'{ft}->{tt}:{et}'
        cc[k] = cc.get(k, 0) + 1
print(f'D: cross cat done, {len(cc)} keys', flush=True)

ccl = []
for k, c in cc.items():
    m = re.match(r'^(.+?)->(.+?):(.+)$', k)
    if m:
        ccl.append({'fromType': m.group(1), 'toType': m.group(2), 'edgeType': m.group(3), 'count': c})
ccl.sort(key=lambda x: x['count'], reverse=True)

# E: Inter-group
igi = []
for fg, targets in gi.items():
    for tg, c in targets.items():
        if fg != tg:
            igi.append({'from': fg, 'to': tg, 'count': c})
igi.sort(key=lambda x: x['count'], reverse=True)
print(f'E: inter-group done', flush=True)

# F: Intra-group density
igd = {}
for g in dir_groups:
    internal = gie.get(g, 0)
    total = gte.get(g, 0)
    density = internal / total if total > 0 else 0
    igd[g] = {'internalEdges': internal, 'totalEdges': total, 'density': density}

# G: Pattern matching
pmap = {
    'routes': 'api', 'api': 'api', 'controllers': 'api', 'endpoints': 'api', 'handlers': 'api',
    'services': 'service', 'core': 'service', 'lib': 'service', 'domain': 'service', 'logic': 'service',
    'models': 'data', 'db': 'data', 'data': 'data', 'persistence': 'data', 'repository': 'data', 'entities': 'data',
    'components': 'ui', 'views': 'ui', 'pages': 'ui', 'ui': 'ui', 'layouts': 'ui', 'screens': 'ui',
    'middleware': 'middleware', 'plugins': 'middleware', 'interceptors': 'middleware', 'guards': 'middleware',
    'utils': 'utility', 'helpers': 'utility', 'common': 'utility', 'shared': 'utility', 'tools': 'utility',
    'config': 'config', 'constants': 'config', 'env': 'config', 'settings': 'config',
    'hooks': 'hooks', 'store': 'state', 'state': 'state', 'reducers': 'state', 'actions': 'state', 'slices': 'state',
    'assets': 'assets', 'static': 'assets', 'public': 'assets',
    'migrations': 'data', 'management': 'config', 'commands': 'config',
    'cmd': 'entry', 'internal': 'service', 'pkg': 'utility',
    'dto': 'types', 'request': 'types', 'response': 'types', 'entity': 'data', 'controller': 'api', 'routers': 'api',
    'bin': 'entry', 'docs': 'documentation', 'documentation': 'documentation', 'wiki': 'documentation',
    'deploy': 'infrastructure', 'infra': 'infrastructure', 'infrastructure': 'infrastructure',
    '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd',
    'docker': 'infrastructure', 'sql': 'data', 'database': 'data', 'schema': 'data',
}
pm = {}
for g in dir_groups:
    lower = g.lower().replace('_', '').replace('-', '')
    pm[g] = pmap.get(lower) or pmap.get(g)
print(f'G: patterns done', flush=True)

# H: Deployment
dt = {'hasDockerfile': False, 'hasCompose': False, 'hasK8s': False, 'hasTerraform': False, 'hasCI': False, 'infraFiles': []}
for node in nodes:
    n = node['name']
    if n == 'Dockerfile' or n.startswith('Dockerfile.'):
        dt['hasDockerfile'] = True
        dt['infraFiles'].append(node['filePath'])
    if n.startswith('docker-compose.'):
        dt['hasCompose'] = True
        dt['infraFiles'].append(node['filePath'])
    if '.github/workflows/' in node['filePath']:
        dt['hasCI'] = True
        dt['infraFiles'].append(node['filePath'])

# I: Data pipeline
dp = {'schemaFiles': [], 'migrationFiles': [], 'dataModelFiles': [], 'apiHandlerFiles': []}
for node in nodes:
    p = node['filePath'].replace('\\', '/')
    if node.get('type') == 'file':
        if re.search(r'model|entity|schema', p, re.I):
            dp['dataModelFiles'].append(node['id'])

# J: Doc coverage
gwd = set()
for node in nodes:
    if node.get('type') == 'document' or re.search(r'\.(md|rst)$', node['name']):
        g = f2g.get(node['id'])
        if g:
            gwd.add(g)
tg = len(dir_groups)
dc = {
    'groupsWithDocs': len(gwd),
    'totalGroups': tg,
    'coverageRatio': len(gwd) / tg if tg > 0 else 0,
    'undocumentedGroups': [g for g in dir_groups if g not in gwd]
}

# K: Dependency direction
dd = []
pp = set()
for fg, targets in gi.items():
    for tg2, c in targets.items():
        if fg == tg2:
            continue
        pk = tuple(sorted([fg, tg2]))
        if pk in pp:
            continue
        pp.add(pk)
        atob = c
        btoa = gi.get(tg2, {}).get(fg, 0)
        if atob > btoa:
            dd.append({'dependent': fg, 'dependsOn': tg2})
        elif btoa > atob:
            dd.append({'dependent': tg2, 'dependsOn': fg})
print(f'K: dep dir done', flush=True)

# Stats
fpg = {g: len(ids) for g, ids in dir_groups.items()}
ntc = {t: len(ids) for t, ids in ntg.items()}

result = {
    'scriptCompleted': True,
    'directoryGroups': dir_groups,
    'nodeTypeGroups': ntg,
    'crossCategoryEdges': ccl,
    'interGroupImports': igi,
    'intraGroupDensity': igd,
    'patternMatches': pm,
    'deploymentTopology': dt,
    'dataPipeline': dp,
    'docCoverage': dc,
    'dependencyDirection': dd,
    'fileStats': {'totalFileNodes': len(nodes), 'filesPerGroup': fpg, 'nodeTypeCounts': ntc},
    'fileFanIn': fi,
    'fileFanOut': foc
}

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'DONE in {time.time()-t0:.1f}s. {len(nodes)} nodes, {len(imports)} imports, {len(alledges)} allEdges.', flush=True)