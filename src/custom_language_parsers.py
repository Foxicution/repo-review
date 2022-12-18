from collections import defaultdict
from dataclasses import dataclass, field

from tree_sitter_languages import get_language, get_parser


class ImportedModule:
    def __init__(
        self, module_base_name: str, alias: str = None, imported_objects: list = None
    ) -> None:
        self.module_base_name = module_base_name
        self.alias = alias
        self.imported_objects = imported_objects

    @classmethod
    def from_tree_node(cls, tree_node):
        module_base_name = None
        alias = None
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
                    alias = child.named_children[1].text.decode('ascii')
        return cls(module_base_name, alias, imported_objects)

    def __str__(self) -> str:
        if self.alias is None:
            return self.module_base_name
        return f'{self.module_base_name} as {self.alias}'


def match_function_call_to_imported_module(function_call, imported_modules):
    for imported_module in imported_modules:
        if function_call in imported_module.module_base_name.split('.'):
            return imported_module
        if imported_module.imported_objects is not None:
            for imported_object in imported_module.imported_objects:
                if function_call == imported_object:
                    return imported_module
    return None


@dataclass
class CustomLanguageSyntaxParser:
    name: str = 'python'
    extension: str = 'py'
    parser: object = get_parser('python')
    language: object = get_language('python')
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
        fun_def_query = self.language.query(
            """
            (function_definition
              name: (identifier) @function.def)

            """
        )
        fun_call_query = self.language.query(
            """
            (call
            function: (identifier) @function.call)
            """
        )

        fun_definitions = fun_def_query.captures(tree_node)
        call_map = defaultdict(list)

        for fun_definition in fun_definitions:
            calls = fun_call_query.captures(fun_definition[0])
            call_map[fun_definition[0].text.decode('ascii')] = [
                call[0].text.decode('ascii') for call in calls
            ]
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
    language: object = get_language('javascript')
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

    @staticmethod
    def clean_node_js_import_text(import_text):
        import_text = import_text.replace('./', '')
        return import_text

    def get_imports(self, root_node) -> list:
        # TODO: Add support for typical js import statements
        imports = self.get_node_imports(root_node)
        imports += self.get_bare_js_imports(root_node)
        return imports

    def get_bare_js_imports(self, root_node) -> list:
        imports = []
        # TODO
        return imports

    def get_node_imports(self, root_node) -> list:
        imports = []
        # Let's keep this in case we need it later
        # node_imported_module_single = self.language.query(
        #     """
        #     (variable_declarator
        #         (identifier) @import)
        #     """
        # )
        # TODO: We might not need inner imports, but let's keep them for now
        node_imported_modules = self.language.query(
            """
            (object_pattern
                (shorthand_property_identifier_pattern) @import)
            """
        )
        # use arguments to get the name of the module
        node_module_import_source_query = self.language.query(
            """
            (lexical_declaration
                (variable_declarator
                    (call_expression
                        (arguments
                            (string
                                (string_fragment) @import)))))
            """
        )

        for import_statement in node_module_import_source_query.captures(root_node):
            imported_module_name = import_statement[0].text.decode('ascii')
            imported_module_name = self.clean_node_js_import_text(imported_module_name)

            imported_inner_modules = node_imported_modules.captures(
                import_statement[0].parent.parent.parent.parent
            )
            imported_inner_modules = [
                imported_module[0].text.decode('ascii')
                for imported_module in imported_inner_modules
            ]

            imported_module = ImportedModule(
                module_base_name=imported_module_name,
                imported_objects=imported_inner_modules,
            )

            imports.append(imported_module)
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
    def get_imports(self, tree_node):
        imported_modules = {}
        query_import = self.language.query(
            """
            (import_from_statement
                (dotted_name) @import_from +
                (dotted_name
                    (identifier) @imported_from
                )
            )
            (import_statement
                (dotted_name) @import_base)
            (import_statement
                (aliased_import
                    (dotted_name) @import_base
                    (identifier) @import_alias
                )
            )
            """
        )
        import_captures = query_import.captures(tree_node)
        import_iter = iter(import_captures)
        last_key = ''
        while import_iter:
            import_obj = next(import_iter, None)
            if import_obj is None:
                break
            import_type = import_obj[1]
            if import_type == 'import_from':
                module_name = import_obj[0].text.decode('ascii')
                imported_module = ImportedModule(
                    module_base_name=module_name,
                    imported_objects=[],
                )
                last_key = module_name
                imported_modules[module_name] = imported_module

            elif import_type == 'imported_from':
                imported_object = import_obj[0].text.decode('ascii')
                imported_modules[last_key].imported_objects.append(imported_object)
            elif import_type == 'import_base':
                module_name = import_obj[0].text.decode('ascii')
                imported_module = ImportedModule(
                    module_base_name=module_name,
                    imported_objects=[],
                )
                last_key = module_name
                imported_modules[module_name] = imported_module
            elif import_type == 'import_alias':
                alias_name = import_obj[0].text.decode('ascii')
                imported_modules[last_key].alias = alias_name
        imported_modules = list(imported_modules.values())
        return imported_modules


PythonSyntaxParser = CustomPythonSyntaxParser(
    name='python',
    extension='py',
    parser=get_parser('python'),
    language=get_language('python'),
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
LANGUAGES = {
    'py': PythonSyntaxParser,
    'js': JavascriptSyntaxParser,
    'cs': CSharpSyntaxParser,
    'java': JavaSyntaxParser,
    'rs': RustSyntaxParser,
}
