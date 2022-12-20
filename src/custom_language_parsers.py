from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from tree_sitter_languages import get_language, get_parser


@dataclass
class ImportedModule:
    module_base_name: str
    alias: str = None
    imported_objects: list = field(default_factory=list)

    def __str__(self) -> str:
        if self.alias is None:
            return self.module_base_name
        return f'{self.module_base_name} as {self.alias}'


def get_imported_module_for_function_call(
    function_call: str, imported_modules: list[ImportedModule]
) -> Optional[ImportedModule]:
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
    parser: object = Optional[object]
    language: object = Optional[object]

    def __post_init__(self):
        self.parser = get_parser(self.name)
        self.language = get_language(self.name)

    def get_function_definitions(self, tree_node) -> list:
        raise NotImplementedError

    def get_imports(self, tree_node) -> list:
        raise NotImplementedError

    def get_calls_in_node(self, tree_node) -> list:
        raise NotImplementedError

    def build_node_call_map(self, tree_node) -> dict:
        raise NotImplementedError

    @staticmethod
    def nodes_from_captures(captures):
        return [capture[0] for capture in captures]

    def build_call_graph(
        self,
        cur_graph: object,
        function_definitions: list = None,
        module_name: str = None,
        imported_modules: list = None,
    ) -> object:
        raise NotImplementedError

    def add_function_to_call_graph(
        self,
        function,
        full_graph,
        function_definition_names=None,
        module_name=None,
        imported_modules=None,
    ):
        function_name = self.get_function_name_from_node(function)
        function_calls = self.get_calls_in_node(function)

        function_name = module_name + '.' + function_name
        full_graph.add_node(function_name, content=function.text.decode('ascii'))
        for function_call in function_calls:
            function_call_name = self.function_call_to_text(function_call)
            if function_call_name in function_definition_names:
                function_call_name = module_name + '.' + function_call_name
            elif imported_modules is not None:
                matching_imported_module = get_imported_module_for_function_call(
                    function_call_name, imported_modules
                )
                if matching_imported_module is not None:
                    function_call_name = (
                        matching_imported_module.module_base_name + '.' + function_call_name
                    )
            full_graph.add_node(function_call_name)
            full_graph.add_edge(function_name, function_call_name)

    @staticmethod
    def get_function_name_from_node(node):
        raise NotImplementedError

    @staticmethod
    def function_call_to_text(function_call):
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

    @staticmethod
    def get_function_name_from_node(node):
        name = node.named_children[0].text.decode('ascii')
        return name

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

    def get_function_definitions(self, tree_node) -> list:
        query_function_definition = self.language.query(
            """
            (function_declaration) @function_definition
            """
        )
        function_definitions = self.nodes_from_captures(
            query_function_definition.captures(tree_node)
        )
        return function_definitions

    def build_call_graph(
        self,
        cur_graph,
        function_definitions=None,
        module_name=None,
        imported_modules=None,
    ):
        function_definition_names = [
            self.get_function_name_from_node(function_definition)
            for function_definition in function_definitions
        ]
        for function_definition in function_definitions:
            self.add_function_to_call_graph(
                function_definition,
                cur_graph,
                function_definition_names,
                module_name,
                imported_modules,
            )


@dataclass
class CustomPythonSyntaxParser(CustomLanguageSyntaxParser):
    def get_function_name_from_node(self, node):
        name = node.named_children[0].text.decode('ascii')
        return name

    def get_imports(self, tree_node) -> list[ImportedModule]:
        imported_modules = {}
        # TODO: Fix query to only match import_from once, remove dict fix
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
        for import_obj in import_iter:
            import_type = import_obj[1]
            obj_name = import_obj[0].text.decode('ascii')
            match import_type:
                case 'import_from' | 'import_base':
                    imported_module = ImportedModule(
                        module_base_name=obj_name,
                        imported_objects=[],
                    )
                    last_key = obj_name
                    imported_modules[obj_name] = imported_module
                case 'imported_from':
                    imported_modules[last_key].imported_objects.append(obj_name)
                case 'import_alias':
                    imported_modules[last_key].alias = obj_name

        imported_modules = list(imported_modules.values())
        return imported_modules

    def get_function_definitions(self, tree_node) -> list:
        query_function_definition = self.language.query(
            """
            (function_definition) @function_definition
            """
        )
        function_definitions = self.nodes_from_captures(
            query_function_definition.captures(tree_node)
        )
        return function_definitions

    def get_calls_in_node(self, tree_node) -> list:
        query_call = self.language.query(
            """
            (call) @call
            """
        )
        node_calls = self.nodes_from_captures(query_call.captures(tree_node))
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
        cur_graph,
        function_definitions=None,
        module_name=None,
        imported_modules=None,
    ):
        function_definition_names = [
            self.get_function_name_from_node(function_definition)
            for function_definition in function_definitions
        ]
        for function_definition in function_definitions:
            self.add_function_to_call_graph(
                function_definition,
                cur_graph,
                function_definition_names,
                module_name,
                imported_modules,
            )


PythonSyntaxParser = CustomPythonSyntaxParser(
    name='python',
    extension='py',
)

JavascriptSyntaxParser = CustomJavascriptSyntaxParser(
    name='javascript',
    extension='js',
)

CSharpSyntaxParser = CustomLanguageSyntaxParser(
    name='c_sharp',
    extension='cs',
)

JavaSyntaxParser = CustomLanguageSyntaxParser(
    name='java',
    extension='java',
)

RustSyntaxParser = CustomLanguageSyntaxParser(
    name='rust',
    extension='rs',
)

# Top 5 programming languages and their extensions
LANGUAGES = {
    'py': PythonSyntaxParser,
    'js': JavascriptSyntaxParser,
    'cs': CSharpSyntaxParser,
    'java': JavaSyntaxParser,
    'rs': RustSyntaxParser,
}
