"""
TypeScript parser using tree-sitter for accurate AST analysis.
"""

import logging
from typing import List, Set

from .base import CodeParser, Import, Function, Class

logger = logging.getLogger(__name__)


class TypeScriptParser(CodeParser):
    """TypeScript code parser using tree-sitter."""

    def __init__(self):
        self._parser = None
        self._language = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazily initialize tree-sitter parser."""
        if self._initialized:
            return True

        try:
            import tree_sitter_typescript as ts_ts
            from tree_sitter import Language, Parser

            # TypeScript has two languages: typescript and tsx
            self._language = Language(ts_ts.language_typescript())
            self._parser = Parser(self._language)
            self._initialized = True
            return True
        except ImportError:
            logger.warning("tree-sitter-typescript not installed")
            return False

    def _walk_tree(self, node, node_types: Set[str], results: list):
        """Recursively walk tree collecting nodes of specific types."""
        if node.type in node_types:
            results.append(node)
        for child in node.children:
            self._walk_tree(child, node_types, results)

    def parse_imports(self, source: str) -> List[Import]:
        """Extract all import statements from TypeScript source."""
        if not self._ensure_initialized():
            return []

        tree = self._parser.parse(bytes(source, 'utf8'))
        imports = []
        
        import_nodes = []
        self._walk_tree(tree.root_node, {'import_statement'}, import_nodes)
        
        for node in import_nodes:
            source_node = None
            names = []
            
            for child in node.children:
                if child.type == 'string':
                    source_node = child
                elif child.type == 'import_clause':
                    for clause_child in child.children:
                        if clause_child.type == 'identifier':
                            names.append(clause_child.text.decode())
                        elif clause_child.type == 'named_imports':
                            for import_spec in clause_child.children:
                                if import_spec.type == 'import_specifier':
                                    name = import_spec.child_by_field_name('name')
                                    if name:
                                        names.append(name.text.decode())
            
            if source_node:
                module = source_node.text.decode().strip('\'"')
                imports.append(Import(
                    module=module,
                    names=names,
                    line=node.start_point[0] + 1,
                    is_relative=module.startswith('.')
                ))
        
        return imports

    def parse_functions(self, source: str) -> List[Function]:
        """Extract all function definitions from TypeScript source."""
        if not self._ensure_initialized():
            return []

        tree = self._parser.parse(bytes(source, 'utf8'))
        functions = []
        
        func_nodes = []
        self._walk_tree(tree.root_node, {'function_declaration', 'method_definition'}, func_nodes)
        
        for node in func_nodes:
            name_node = node.child_by_field_name('name')
            params_node = node.child_by_field_name('parameters')
            
            params = self._extract_params(params_node)
            
            functions.append(Function(
                name=name_node.text.decode() if name_node else 'anonymous',
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                params=params
            ))
        
        return functions

    def _extract_params(self, params_node) -> List[str]:
        """Extract parameter names from a parameters node."""
        params = []
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    params.append(child.text.decode())
                elif child.type == 'required_parameter':
                    pattern = child.child_by_field_name('pattern')
                    if pattern and pattern.type == 'identifier':
                        params.append(pattern.text.decode())
                elif child.type == 'optional_parameter':
                    pattern = child.child_by_field_name('pattern')
                    if pattern and pattern.type == 'identifier':
                        params.append(pattern.text.decode())
        return params

    def parse_classes(self, source: str) -> List[Class]:
        """Extract all class definitions from TypeScript source."""
        if not self._ensure_initialized():
            return []

        tree = self._parser.parse(bytes(source, 'utf8'))
        classes = []
        
        class_nodes = []
        self._walk_tree(tree.root_node, {'class_declaration'}, class_nodes)
        
        for node in class_nodes:
            name_node = node.child_by_field_name('name')
            body_node = node.child_by_field_name('body')
            
            methods = []
            if body_node:
                for child in body_node.children:
                    if child.type in ('method_definition', 'public_field_definition'):
                        method_name = child.child_by_field_name('name')
                        if method_name:
                            methods.append(method_name.text.decode())
            
            classes.append(Class(
                name=name_node.text.decode() if name_node else 'unknown',
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                methods=methods
            ))
        
        return classes
