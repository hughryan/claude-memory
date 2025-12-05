"""
Python parser using tree-sitter for accurate AST analysis.
"""

import logging
from typing import List

from .base import CodeParser, Import, Function, Class

logger = logging.getLogger(__name__)


class PythonParser(CodeParser):
    """Python code parser using tree-sitter with ast fallback."""

    def __init__(self):
        self._parser = None
        self._language = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazily initialize tree-sitter parser."""
        if self._initialized:
            return True

        try:
            import tree_sitter_python as ts_python
            from tree_sitter import Language, Parser

            self._language = Language(ts_python.language())
            self._parser = Parser(self._language)
            self._initialized = True
            return True
        except ImportError:
            logger.warning("tree-sitter-python not installed, using fallback")
            return False

    def parse_imports(self, source: str) -> List[Import]:
        """Extract all import statements from Python source."""
        # Use ast fallback since it's always available and accurate for Python
        return self._parse_imports_fallback(source)

    def _parse_imports_fallback(self, source: str) -> List[Import]:
        """Fallback using Python's ast module."""
        import ast

        imports = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(Import(
                            module=alias.name,
                            names=[],
                            line=node.lineno
                        ))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    names = [alias.name for alias in node.names]
                    imports.append(Import(
                        module=module,
                        names=names,
                        line=node.lineno,
                        is_relative=node.level > 0
                    ))
        except SyntaxError:
            pass
        return imports

    def parse_functions(self, source: str) -> List[Function]:
        """Extract all function definitions from Python source."""
        return self._parse_functions_fallback(source)

    def _parse_functions_fallback(self, source: str) -> List[Function]:
        """Fallback using Python's ast module."""
        import ast

        functions = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    params = [arg.arg for arg in node.args.args]
                    functions.append(Function(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        params=params
                    ))
        except SyntaxError:
            pass
        return functions

    def parse_classes(self, source: str) -> List[Class]:
        """Extract all class definitions from Python source."""
        return self._parse_classes_fallback(source)

    def _parse_classes_fallback(self, source: str) -> List[Class]:
        """Fallback using Python's ast module."""
        import ast

        classes = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ]
                    classes.append(Class(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        methods=methods
                    ))
        except SyntaxError:
            pass
        return classes
