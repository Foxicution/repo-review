import networkx as nx
from copy import deepcopy


def fix_edges(graph_nodes: list[dict]) -> tuple[list[dict], tuple[str, str, float], list[str]]:
    edge_weight = 5.0
    file_names = [n['id'] for n in graph_nodes]
    graph_edges = []
    for graph_node in graph_nodes:
        for i, package in enumerate(graph_node['imports']):
            del graph_node['imports'][i]
            if package in file_names:
                graph_node['imports'].append(package)
                graph_edges.append((package, graph_node['id'], edge_weight))
            else:
                split_package = package.split('/')
                subpackage = "/".join(list(split_package[:-1]))
                base_package = split_package[0]
                if '*' in package:
                    for file_name in file_names:
                        if subpackage in file_name:
                            graph_node['imports'].append(file_name)
                            graph_edges.append((file_name, graph_node['id'], edge_weight))
                elif subpackage in file_names:
                    graph_node['imports'].append(subpackage)
                    graph_edges.append((subpackage, graph_node['id'], edge_weight))
                else:
                    graph_node['imports'].append(base_package)
                    graph_edges.append((base_package, graph_node['id'], 1.0))
    return graph_nodes, graph_edges, file_names


def without_keys(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


def get_graphs(edge_property_list: list[dict]) -> tuple[nx.Graph, nx.Graph]:
    nodes, edges, files = fix_edges(edge_property_list)
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(edges)
    for node in graph:
        if not any(file == node for file in files):
            graph.nodes[node]['color'] = '#ced7d8'
            graph.nodes[node]['shape'] = 'box'
            graph.nodes[node]['type'] = 'external'
    for node in nodes:
        graph.add_node(node['id'], **without_keys(node, {'id'}))
    return graph, deepcopy(graph).subgraph(files)
