#!/usr/bin/env python3
"""
Phase 1 -- Structural Analysis Script
Analyzes file paths and import edges to compute structural patterns
that inform layer identification.
"""

import json
import sys
import os
import re

def compute_common_prefix(paths):
    if not paths:
        return ''
    normalized = [p.replace('\\', '/') for p in paths]
    prefix = normalized[0]
    for i in range(1, len(normalized)):
        while not normalized[i].startswith(prefix):
            idx = prefix.rfind('/')
            if idx == -1:
                return ''
            prefix = prefix[:idx + 1]
            if not prefix:
                return ''
    return prefix

def main():
    if len(sys.argv) < 3:
        print("Usage: python ua-arch-analyze.py <input.json> <output.json>", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        file_nodes = data['fileNodes']
        import_edges = data['importEdges']
        all_edges = data['allEdges']

        # ===== A. Directory Grouping =====
        dir_groups = {}
        all_paths = [n['filePath'] for n in file_nodes]

        # Compute common prefix
        common_prefix = compute_common_prefix(all_paths)

        for node in file_nodes:
            relative_path = node['filePath']
            if common_prefix:
                relative_path = relative_path[len(common_prefix):]
            parts = [p for p in relative_path.replace('\\', '/').split('/') if p]
            group = parts[0] if parts else 'root'
            if group not in dir_groups:
                dir_groups[group] = []
            dir_groups[group].append(node['id'])

        # ===== B. Node Type Grouping =====
        node_type_groups = {}
        for node in file_nodes:
            t = node.get('type', 'unknown')
            if t not in node_type_groups:
                node_type_groups[t] = []
            node_type_groups[t].append(node['id'])

        # ===== C. Import Adjacency Matrix =====
        fan_in = {}
        fan_out = {}
        adj_list = {}

        for node in file_nodes:
            fan_in[node['id']] = 0
            fan_out[node['id']] = 0
            adj_list[node['id']] = set()

        for edge in import_edges:
            src = edge['source']
            tgt = edge['target']
            if src in adj_list:
                adj_list[src].add(tgt)
            if tgt in fan_in:
                fan_in[tgt] += 1
            if src in fan_out:
                fan_out[src] += 1

        fan_out_counts = {k: len(v) for k, v in adj_list.items()}

        # Build file -> group map
        file_to_group = {}
        for group, ids in dir_groups.items():
            for fid in ids:
                file_to_group[fid] = group

        group_imports = {}
        group_internal_edges = {}
        group_total_edges = {}

        for edge in import_edges:
            src_group = file_to_group.get(edge['source'])
            tgt_group = file_to_group.get(edge['target'])
            if not src_group or not tgt_group:
                continue

            if src_group not in group_imports:
                group_imports[src_group] = {}
            if tgt_group not in group_imports[src_group]:
                group_imports[src_group][tgt_group] = 0
            group_imports[src_group][tgt_group] += 1

            group_total_edges[src_group] = group_total_edges.get(src_group, 0) + 1
            group_total_edges[tgt_group] = group_total_edges.get(tgt_group, 0) + 1

            if src_group == tgt_group:
                group_internal_edges[src_group] = group_internal_edges.get(src_group, 0) + 1

        # ===== D. Cross-Category Dependency Analysis =====
        node_type_map = {n['id']: n.get('type', 'unknown') for n in file_nodes}

        cross_category = {}
        for edge in all_edges:
            from_type = node_type_map.get(edge['source'], 'unknown')
            to_type = node_type_map.get(edge['target'], 'unknown')
            edge_type = edge.get('type', 'unknown')

            if from_type != to_type:
                key = f"{from_type}->{to_type}:{edge_type}"
                cross_category[key] = cross_category.get(key, 0) + 1

        cross_category_list = []
        for key, count in cross_category.items():
            match = re.match(r'^(.+?)->(.+?):(.+)$', key)
            if match:
                cross_category_list.append({
                    'fromType': match.group(1),
                    'toType': match.group(2),
                    'edgeType': match.group(3),
                    'count': count
                })
        cross_category_list.sort(key=lambda x: x['count'], reverse=True)

        # ===== E. Inter-Group Import Frequency =====
        inter_group_imports = []
        for from_g, targets in group_imports.items():
            for to_g, count in targets.items():
                if from_g != to_g:
                    inter_group_imports.append({'from': from_g, 'to': to_g, 'count': count})
        inter_group_imports.sort(key=lambda x: x['count'], reverse=True)

        # ===== F. Intra-Group Import Density =====
        intra_group_density = {}
        for group in dir_groups:
            internal = group_internal_edges.get(group, 0)
            total = group_total_edges.get(group, 0)
            density = internal / total if total > 0 else 0
            intra_group_density[group] = {
                'internalEdges': internal,
                'totalEdges': total,
                'density': density
            }

        # ===== G. Directory Pattern Matching =====
        pattern_map = {
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
        }

        pattern_matches = {}
        for group in dir_groups:
            lower = group.lower().replace('_', '').replace('-', '')
            pattern_matches[group] = pattern_map.get(lower) or pattern_map.get(group)

        # File-level pattern matching
        for node in file_nodes:
            name = node['name']
            group = file_to_group.get(node['id'])

            # Test files
            if re.search(r'\.(test|spec)\.', name) or re.match(r'^test_', name) or \
               re.search(r'_test\.\w+$', name) or re.search(r'Test\.\w+$', name) or \
               re.search(r'_spec\.\w+$', name) or re.search(r'Test\.php$', name) or \
               re.search(r'Tests\.cs$', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'test'

            if name == 'manage.py' or name == 'main.go' or name == 'main.rs' or \
               name == 'lib.rs' or name == 'Application.java' or name == 'Program.cs' or \
               name == 'config.ru':
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'entry'

            if name == 'wsgi.py' or name == 'asgi.py':
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'config'

            if name in ['Cargo.toml', 'go.mod', 'Gemfile', 'pom.xml', 'build.gradle', 'composer.json']:
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'config'

            if name == 'Dockerfile' or re.match(r'^docker-compose\.', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'infrastructure'

            if re.search(r'\.tf$', name) or re.search(r'\.tfvars$', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'infrastructure'

            if re.search(r'\.github/workflows/.+\.yml$', node['filePath'].replace('\\', '/')) or \
               name in ['.gitlab-ci.yml', 'Jenkinsfile']:
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'ci-cd'

            if re.search(r'\.sql$', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'data'

            if re.search(r'\.(graphql|gql|proto)$', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'types'

            if re.search(r'\.(md|rst)$', name):
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'documentation'

            if name == 'Makefile':
                if pattern_matches.get(group) is None:
                    pattern_matches[group] = 'infrastructure'

        # ===== H. Deployment Topology Detection =====
        deployment_topology = {
            'hasDockerfile': False,
            'hasCompose': False,
            'hasK8s': False,
            'hasTerraform': False,
            'hasCI': False,
            'infraFiles': []
        }

        for node in file_nodes:
            p = node['filePath'].replace('\\', '/')
            name = node['name']
            if name == 'Dockerfile' or re.match(r'^Dockerfile\.', name):
                deployment_topology['hasDockerfile'] = True
                deployment_topology['infraFiles'].append(node['filePath'])
            if re.match(r'^docker-compose\.', name):
                deployment_topology['hasCompose'] = True
                deployment_topology['infraFiles'].append(node['filePath'])
            if re.search(r'\.tf$', name) or re.search(r'\.tfvars$', name) or \
               p.startswith('k8s/') or p.startswith('kubernetes/'):
                deployment_topology['hasK8s'] = True
                deployment_topology['hasTerraform'] = True
                deployment_topology['infraFiles'].append(node['filePath'])
            if '.github/workflows/' in p or name in ['.gitlab-ci.yml', 'Jenkinsfile']:
                deployment_topology['hasCI'] = True
                deployment_topology['infraFiles'].append(node['filePath'])

        # ===== I. Data Pipeline Detection =====
        data_pipeline = {
            'schemaFiles': [],
            'migrationFiles': [],
            'dataModelFiles': [],
            'apiHandlerFiles': []
        }

        for node in file_nodes:
            p = node['filePath'].replace('\\', '/')
            name = node['name']
            if re.search(r'\.sql$', name) and not re.search(r'migration', p, re.IGNORECASE):
                data_pipeline['schemaFiles'].append(node['id'])
            if re.search(r'migration', p, re.IGNORECASE) and re.search(r'\.sql$', name):
                data_pipeline['migrationFiles'].append(node['id'])
            if re.search(r'model|entity|schema', p, re.IGNORECASE) and node.get('type') == 'file':
                data_pipeline['dataModelFiles'].append(node['id'])
            if re.search(r'route|api|controller|endpoint|handler', p, re.IGNORECASE) and node.get('type') == 'file':
                data_pipeline['apiHandlerFiles'].append(node['id'])

        # ===== J. Documentation Coverage =====
        groups_with_docs = set()
        doc_files = [n for n in file_nodes if n.get('type') == 'document' or re.search(r'\.(md|rst)$', n['name'])]

        for doc in doc_files:
            doc_group = file_to_group.get(doc['id'])
            if doc_group:
                groups_with_docs.add(doc_group)

        for node in file_nodes:
            if node['name'].lower() == 'readme.md':
                g = file_to_group.get(node['id'])
                if g:
                    groups_with_docs.add(g)

        total_groups = len(dir_groups)
        doc_coverage = {
            'groupsWithDocs': len(groups_with_docs),
            'totalGroups': total_groups,
            'coverageRatio': len(groups_with_docs) / total_groups if total_groups > 0 else 0,
            'undocumentedGroups': [g for g in dir_groups if g not in groups_with_docs]
        }

        # ===== K. Dependency Direction =====
        dependency_direction = []
        processed_pairs = set()

        for from_g, targets in group_imports.items():
            for to_g, count in targets.items():
                if from_g == to_g:
                    continue
                pair_key = tuple(sorted([from_g, to_g]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                a_to_b = count
                b_to_a = group_imports.get(to_g, {}).get(from_g, 0)

                if a_to_b > b_to_a:
                    dependency_direction.append({'dependent': from_g, 'dependsOn': to_g})
                elif b_to_a > a_to_b:
                    dependency_direction.append({'dependent': to_g, 'dependsOn': from_g})

        # ===== File Stats =====
        files_per_group = {g: len(ids) for g, ids in dir_groups.items()}
        node_type_counts = {t: len(ids) for t, ids in node_type_groups.items()}

        # ===== Output =====
        result = {
            'scriptCompleted': True,
            'directoryGroups': dir_groups,
            'nodeTypeGroups': node_type_groups,
            'crossCategoryEdges': cross_category_list,
            'interGroupImports': inter_group_imports,
            'intraGroupDensity': intra_group_density,
            'patternMatches': pattern_matches,
            'deploymentTopology': deployment_topology,
            'dataPipeline': data_pipeline,
            'docCoverage': doc_coverage,
            'dependencyDirection': dependency_direction,
            'fileStats': {
                'totalFileNodes': len(file_nodes),
                'filesPerGroup': files_per_group,
                'nodeTypeCounts': node_type_counts
            },
            'fileFanIn': fan_in,
            'fileFanOut': fan_out_counts
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Analysis complete. {len(file_nodes)} files, {len(import_edges)} imports, {len(all_edges)} total edges.")
        print(f"Directory groups: {len(dir_groups)}")
        print(f"Output written to {output_path}")
        sys.exit(0)

    except Exception as err:
        print(f"FATAL: {err}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()