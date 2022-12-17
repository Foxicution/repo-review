# import pickle
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
from pyvis.network import Network
from tree_sitter_languages import get_parser

function_identifiers = ['function_definition', 'function_item']


@dataclass
class CustomLanguageSyntaxParser:
    name: str = 'python'
    extension: str = 'py'
    parser: object = get_parser('python')
    function_identifiers: list[str] = field(default_factory=list)
    import_identifiers: list[str] = field(default_factory=list)
    call_identifiers: list[str] = field(default_factory=list)

    def get_function_definitions(self, tree_node) -> list:
        functions = []
        for child in tree_node.children:
            if child.type in self.function_identifiers:
                functions.append(child)
            if child.children is not None:
                functions += self.get_function_definitions(child)
        return functions

    def get_imports(self, tree_node) -> list:
        imports = []
        return imports

    def get_calls_in_node(self, tree_node) -> list:
        node_calls = []
        for child in tree_node.children:
            if child.type in self.call_identifiers:
                node_calls.append(child)
            if child.children is not None:
                node_calls += self.get_calls_in_node(child)
        return node_calls

    def build_node_call_map(self, tree_node) -> dict:
        call_map = defaultdict(list)
        calls = self.get_calls_in_node(tree_node)
        for call in calls:
            if call.named_child_count >= 2 and call.named_children[0].named_child_count >= 2:
                module_name = call.named_children[0].named_children[0].text.decode('ascii')
                function_name = call.named_children[0].named_children[1].text.decode('ascii')
                call_map[module_name].append(function_name)
        return call_map

    def build_call_graph(
        self,
        tree_node,
        cur_graph,
        all_function_definitions=None,
        module_name=None,
        imported_modules=None,
    ):
        function_definitions = self.get_function_definitions(tree_node)
        function_definition_names = [
            self.get_fun_name(function_definition)
            for function_definition in function_definitions
        ]
        for function_definition in function_definitions:
            self.function_to_call_graph(
                function_definition,
                cur_graph,
                function_definition_names,
                module_name,
                imported_modules,
            )

    def function_to_call_graph(
        self,
        function,
        full_graph,
        function_definition_names=None,
        module_name=None,
        imported_modules=None,
    ):
        function_name = self.get_fun_name(function)
        function_calls = self.get_calls_in_node(function)
        add_module_name = function_definition_names is not None and module_name is not None
        if add_module_name:
            function_name = module_name + '.' + function_name
        full_graph.add_node(function_name, content=function.text.decode('ascii'))
        for function_call in function_calls:
            function_call_name = self.function_call_to_text(function_call)
            if add_module_name:
                if function_call_name in function_definition_names:
                    function_call_name = module_name + '.' + function_call_name
                elif imported_modules is not None:
                    matches_imported_module = match_function_call_to_imported_module(
                        function_call_name, imported_modules
                    )
                    if matches_imported_module is not None:
                        function_call_name = (
                            matches_imported_module.module_base_name
                            + '.'
                            + function_call_name
                        )
            full_graph.add_node(function_call_name)
            full_graph.add_edge(function_name, function_call_name)

    def get_fun_name(self, node):
        name = [ch.text.decode('ascii') for ch in node.children if ch.type == 'identifier'][0]
        return name

    def function_call_to_text(self, function_call):
        function_call_text = ''
        for child in function_call.children:
            if child.type == 'attribute':
                function_call_text += child.text.decode('ascii')
                break
            elif child.type == 'identifier':
                function_call_text += child.text.decode('ascii')
                break
        return function_call_text


@dataclass
class CustomJavascriptSyntaxParser(CustomLanguageSyntaxParser):
    name: str = 'javascript'
    extension: str = 'js'
    parser: object = get_parser('javascript')
    function_identifiers: list[str] = field(
        default_factory=lambda: ['function_definition', 'function_item']
    )
    import_identifiers: list[str] = field(
        default_factory=lambda: [
            'import_statement',
            'import_from_statement',
            'lexical_declaration',
            'require_call',
        ]
    )
    call_identifiers: list[str] = field(default_factory=lambda: ['call_expression'])

    def get_imports(self, root_node) -> list:
        imports = []
        for child in root_node.children:
            if child.type == 'lexical_declaration':  # require parsing
                try:

                    name = (
                        child.named_children[0]
                        .named_children[1]
                        .named_children[1]
                        .named_children[0]
                        .text.decode('ascii')
                    )
                    imported_module = ImportedModule(module_base_name=name)
                    imports.append(imported_module)
                except IndexError:
                    # Is not an import
                    pass
            if child.children is not None:
                imports += self.get_imports(child)
        return imports

    def get_calls_in_node(self, tree_node) -> list:
        node_calls = []
        for child in tree_node.children:
            if child.type in self.call_identifiers:
                call_node = child.named_children[0]
                if call_node.type == 'member_expression':
                    node_calls.append(call_node)
            if child.children is not None:
                node_calls += self.get_calls_in_node(child)
        return node_calls

    def build_node_call_map(self, tree_node) -> dict:
        call_map = defaultdict(list)
        calls = self.get_calls_in_node(tree_node)
        for call in calls:
            if call.named_child_count >= 2 and call.named_children[0].named_child_count >= 2:
                module_name = call.named_children[0].named_children[0].text.decode('ascii')
                function_name = call.named_children[0].named_children[1].text.decode('ascii')
                call_map[module_name].append(function_name)
        return call_map


@dataclass
class CustomPythonSyntaxParser(CustomLanguageSyntaxParser):
    def get_imported_modules(self, tree_node):
        used_modules = []
        for child in tree_node.children:
            if child.type == 'import_statement':
                used_modules.append(ImportedModule.from_tree_node(child))
            if child.type == 'import_from_statement':
                used_modules.append(ImportedModule.from_tree_node(child))
            if child.children is not None:
                used_modules += self.get_imported_modules(child)
        return used_modules


PythonSyntaxParser = CustomPythonSyntaxParser(
    name='python',
    extension='py',
    parser=get_parser('python'),
    function_identifiers=['function_definition', 'function_item'],
    import_identifiers=['import_statement', 'import_from_statement'],
    call_identifiers=['call'],
)

JavascriptSyntaxParser = CustomJavascriptSyntaxParser()

CSharpSyntaxParser = CustomLanguageSyntaxParser(
    name='c-sharp',
    extension='cs',
    parser=get_parser('c_sharp'),
    function_identifiers=['function_definition', 'function_item'],
    import_identifiers=['import_statement', 'import_from_statement'],
    call_identifiers=['call'],
)

JavaSyntaxParser = CustomLanguageSyntaxParser(
    name='java',
    extension='java',
    parser=get_parser('java'),
    function_identifiers=['function_definition', 'function_item'],
    import_identifiers=['import_statement', 'import_from_statement'],
    call_identifiers=['call'],
)

RustSyntaxParser = CustomLanguageSyntaxParser(
    name='rust',
    extension='rs',
    parser=get_parser('rust'),
    function_identifiers=['function_definition', 'function_item'],
    import_identifiers=['import_statement', 'import_from_statement'],
    call_identifiers=['call'],
)

# Top 20 programming languages and their extensions
languages = {
    'py': PythonSyntaxParser,
    'js': JavascriptSyntaxParser,
    'cs': CSharpSyntaxParser,
    'java': JavaSyntaxParser,
    'rs': RustSyntaxParser,
}


class ParsedFile:
    def __init__(
        self,
        filepath: Path,
        language_name: str,
        imported_modules: list,
        function_definitions: list,
        function_calls: list,
        module_call_map: dict,
        local_call_graph: nx.DiGraph,
        project_connections: list = None,
    ) -> None:
        self.filepath = filepath
        self.language_name = language_name
        self.imported_modules = imported_modules
        self.function_definitions = function_definitions
        self.function_calls = function_calls
        self.node_call_map = module_call_map
        self.local_call_graph = local_call_graph
        self.project_connections = project_connections  # on file level
        # TODO: Make it on function call level too


class ImportedModule:
    def __init__(
        self, module_base_name: str, module_name_as: str = None, imported_objects: list = None
    ) -> None:
        self.module_base_name = module_base_name
        self.module_name_as = module_name_as
        self.imported_objects = imported_objects

    @classmethod
    def from_tree_node(cls, tree_node):
        module_base_name = None
        module_name_as = None
        imported_objects = None
        if tree_node.type == 'import_from_statement':
            module_base_name = tree_node.named_children[0].text.decode('ascii')
            imported_objects = [
                ch.text.decode('ascii') for ch in tree_node.named_children[1:]
            ]

        elif tree_node.type == 'import_statement':
            for child in tree_node.children:
                if child.type == 'dotted_name':
                    module_base_name = child.text.decode('ascii')
                elif child.type == 'aliased_import':
                    module_base_name = child.named_children[0].text.decode('ascii')
                    module_name_as = child.named_children[1].text.decode('ascii')
        return cls(module_base_name, module_name_as, imported_objects)

    def __str__(self) -> str:
        if self.module_name_as is None:
            return self.module_base_name
        return f'{self.module_base_name} as {self.module_name_as}'


def parse_file(filepath, file_bytes=None, module_name=None):
    # Get the language name from the file extension
    # TODO: Add error handling for unsupported languages
    custom_language_parser = languages[filepath.suffix[1:]]
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

    # renamed_call_graph = rename_call_graph_nodes(local_call_graph, filepath.stem)

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
    for imported_module in imported_modules:
        if parsed_file.filepath.stem in imported_module.module_base_name.split('.'):
            return True
    return False


def match_function_call_to_imported_module(function_call, imported_modules):
    for imported_module in imported_modules:
        if function_call in imported_module.module_base_name.split('.'):
            return imported_module
        if imported_module.imported_objects is not None:
            for imported_object in imported_module.imported_objects:
                if function_call == imported_object:
                    return imported_module
    return None


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


def make_node_call_graph_for_project(
    local_project_dir=None, github_filelist=None, max_depth=3
):
    parsed_files = {}
    using_github = False
    using_local = False
    if local_project_dir is not None:
        filepaths = local_project_dir.glob('**/*')
        project_depth = len(local_project_dir.parts)
        using_local = True
    elif github_filelist is not None:
        filepaths = github_filelist
        project_depth = 1
        using_github = True
    else:
        Exception('Must provide either a local project directory or a github filelist')

    for filepath_pre in filepaths:
        if using_local:
            filepath = filepath_pre
        elif using_github:
            filepath = Path(filepath_pre.path)

        if filepath.is_dir():
            continue
        depth = len(filepath.parts)
        if depth - project_depth > max_depth:
            continue
        if filepath.suffix[1:] in languages:
            module_name = '.'.join(filepath.parts[project_depth:]).replace(
                filepath.suffix, ''
            )
            if using_local:
                parsed_file = parse_file(filepath, file_bytes=None, module_name=module_name)
            elif using_github:
                parsed_file = parse_file(
                    filepath, file_bytes=filepath_pre.decoded_content, module_name=module_name
                )
            parsed_files['/'.join(filepath.parts[project_depth:])] = parsed_file

    file_level_graph, full_function_call_graph = build_file_level_graph(parsed_files)

    return file_level_graph, full_function_call_graph


def get_network_from_gh_filelist(github_filelist):
    file_level_graph, full_function_call_graph = make_node_call_graph_for_project(
        github_filelist=github_filelist
    )
    nt_files = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_files.from_nx(file_level_graph)

    nt_all = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_all.from_nx(full_function_call_graph)

    return nt_all, nt_files


def get_filelist_from_gh_repo(repo, max_depth=3):
    contents = repo.get_contents('')
    cur_dir_depth = 0
    next_dirs = []
    filelist = []

    while len(contents) > 0 and cur_dir_depth < max_depth:
        file_content = contents.pop(0)
        if file_content.type == 'dir':
            next_dirs.extend(repo.get_contents(file_content.path))
        else:
            filelist.append(file_content)
        if len(contents) == 0:
            cur_dir_depth += 1
            contents = next_dirs
            next_dirs = []
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


def javascript_test():
    file_level_graph, full_function_call_graph = make_node_call_graph_for_project(
        local_project_dir=Path('/home/mati/projects/atom')
    )

    nt_files = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_files.from_nx(file_level_graph)

    nt_all = Network(directed=True, bgcolor='#f2f3f4', height=1080, width=1080)
    nt_all.from_nx(full_function_call_graph)

    nt_files.show('javascript_files.html')

    nt_all.show('javascript_all.html')


def main():
    github_python_test()
    javascript_test()


if __name__ == '__main__':
    # Get the graph for the file
    main()
