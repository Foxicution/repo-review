# import pickle
import logging
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from custom_language_parsers import LANGUAGES


@dataclass
class ParsedFile:
    filepath: Path
    language_name: str
    imported_modules: list
    function_definitions: list
    function_calls: list
    module_call_map: dict
    local_call_graph: nx.DiGraph
    project_connections: list = None  # on file level


def parse_file(filepath, file_bytes=None, module_name=None):
    # Get the language name from the file extension
    # TODO: Add error handling for unsupported languages
    custom_language_parser = LANGUAGES[filepath.suffix[1:]]
    if file_bytes is None:
        file_bytes = bytes(open(filepath, 'r').read(), 'utf-8')
    # Parse the file
    tree = custom_language_parser.parser.parse(file_bytes)
    local_call_graph = nx.DiGraph()
    # TODO: Traverse the tree only once
    module_call_map = custom_language_parser.build_node_call_map(tree.root_node)  # noqa
    function_definitions = custom_language_parser.get_function_definitions(tree.root_node)
    function_calls = custom_language_parser.get_calls_in_node(tree.root_node)
    imported_modules = custom_language_parser.get_imports(tree.root_node)
    custom_language_parser.build_call_graph(
        tree.root_node,
        local_call_graph,
        function_definitions,
        module_name,
        imported_modules,
    )

    parsed_file = ParsedFile(
        filepath=filepath,
        language_name=custom_language_parser.name,
        imported_modules=imported_modules,
        function_definitions=function_definitions,
        function_calls=function_calls,
        module_call_map=module_call_map,
        local_call_graph=local_call_graph,
    )
    return parsed_file


def parsed_file_is_imported(imported_modules, parsed_file):
    filepath_stem = parsed_file.filepath.stem
    for imported_module in imported_modules:
        imported_module_split = imported_module.module_base_name.split('.')
        if filepath_stem == imported_module_split or filepath_stem in imported_module_split:
            return True
    return False


def merge_graphs(graphs):
    merged_graph = nx.DiGraph()
    for graph in graphs:
        merged_graph = nx.compose(merged_graph, graph)
    return merged_graph


def build_file_level_graph(parsed_files):
    file_level_graph = nx.DiGraph()
    for filename, parsed_file in parsed_files.items():
        file_level_graph.add_node(filename)

    for filename, parsed_file in parsed_files.items():  # noqa
        for filename_b, parsed_file_b in parsed_files.items():
            if filename == filename_b:
                continue
            if parsed_file_is_imported(parsed_file.imported_modules, parsed_file_b):
                file_level_graph.add_edge(filename, filename_b)
    full_function_call_graph = merge_graphs(
        [parsed_file.local_call_graph for parsed_file in parsed_files.values()]
    )

    return file_level_graph, full_function_call_graph


def get_module_name_from_filepath(filepath, project_depth):
    module_name = '.'.join(filepath.parts[project_depth:]).replace(filepath.suffix, '')
    return module_name


def build_graphs_for_project(local_project_dir=None, github_filelist=None, max_depth=3):
    parsed_files = {}
    using_local = False
    assert (
        local_project_dir is not None or github_filelist is not None
    ), 'Must provide either local or github source'

    if local_project_dir is not None:
        filepaths = local_project_dir.glob('**/*')
        project_depth = len(local_project_dir.parts)
        using_local = True
    else:
        filepaths = github_filelist
        project_depth = 1

    for filepath_pre in filepaths:
        if using_local:
            filepath = filepath_pre
        else:
            filepath = Path(filepath_pre.path)

        if filepath.is_dir():
            continue

        if filepath.suffix[1:] not in LANGUAGES:
            continue

        current_depth = len(filepath.parts) - project_depth
        if current_depth > max_depth:
            continue

        file_contents = None
        if not using_local:
            file_contents = filepath_pre.decoded_content

        module_name = get_module_name_from_filepath(filepath, project_depth)
        parsed_file = parse_file(filepath, file_bytes=file_contents, module_name=module_name)
        if parsed_file is None:
            continue

        parsed_files['/'.join(filepath.parts[project_depth:])] = parsed_file

    file_level_graph, full_function_call_graph = build_file_level_graph(parsed_files)

    return file_level_graph, full_function_call_graph


def get_network_from_gh_filelist(github_filelist):
    file_level_graph, full_function_call_graph = build_graphs_for_project(
        github_filelist=github_filelist
    )
    nt_files = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_files.from_nx(file_level_graph)

    nt_all = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_all.from_nx(full_function_call_graph)

    return nt_all, nt_files


def get_filelist_from_gh_repo(repo, max_depth=4):
    repo_contents = repo.get_contents('')
    current_directory_depth = 0
    next_depth_dirs = []
    filelist = []

    while len(repo_contents) > 0 and current_directory_depth < max_depth:
        file_content = repo_contents.pop(0)
        if file_content.type == 'dir':
            next_depth_dirs.extend(repo.get_contents(file_content.path))
        else:
            filelist.append(file_content)
        # If reached current depth end
        if len(repo_contents) == 0:
            current_directory_depth += 1
            repo_contents = next_depth_dirs
            next_depth_dirs = []
    return filelist


def github_python_test():
    import os

    from github import Github

    g = Github(os.getenv('access_token'))

    repo = g.get_repo('Foxicution/repo-review')
    filelist = get_filelist_from_gh_repo(repo)
    logging.log(logging.DEBUG, f'Generating graph for {len(filelist)} files')
    file_level_graph, full_function_call_graph = get_network_from_gh_filelist(filelist)

    file_level_graph.show('python_files.html')

    full_function_call_graph.show('python_all.html')


def local_test():
    file_level_graph, full_function_call_graph = build_graphs_for_project(
        local_project_dir=Path('/home/mati/projects/repo-review'), max_depth=5
    )

    nt_files = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_files.from_nx(file_level_graph)

    nt_all = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_all.from_nx(full_function_call_graph)

    nt_files.show('local_files.html')

    nt_all.show('local_all.html')


def main():
    # github_python_test()
    local_test()


if __name__ == '__main__':
    # Get the graph for the file
    main()
