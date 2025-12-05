"""
Code parser registry for multi-language AST analysis.

Provides tree-sitter based parsing for Python, JavaScript, and TypeScript
with fallback to regex/ast for when tree-sitter is not available.
"""

from pathlib import Path
from typing import Dict, Optional

from .base import CodeParser, Import, Function, Class
from .python_parser import PythonParser
from .javascript_parser import JavaScriptParser
from .typescript_parser import TypeScriptParser

# Lazily initialized parser instances
_parsers: Dict[str, CodeParser] = {}


def _get_parser_for_ext(ext: str) -> Optional[CodeParser]:
    """Get or create parser for file extension."""
    if ext in _parsers:
        return _parsers[ext]

    parser: Optional[CodeParser] = None
    if ext == '.py':
        parser = PythonParser()
    elif ext in ('.js', '.jsx', '.mjs'):
        parser = JavaScriptParser()
    elif ext in ('.ts', '.tsx'):
        parser = TypeScriptParser()

    if parser:
        _parsers[ext] = parser
    return parser


def get_parser(file_path: str) -> Optional[CodeParser]:
    """Get appropriate parser for a file path.

    Args:
        file_path: Path to the file to parse

    Returns:
        CodeParser instance for the file type, or None if unsupported
    """
    ext = Path(file_path).suffix.lower()
    return _get_parser_for_ext(ext)


def parse_file(file_path: str, source: str) -> Dict:
    """Parse a file and return all extracted information.

    Args:
        file_path: Path to the file (used to determine parser)
        source: Source code content

    Returns:
        Dictionary with 'imports', 'functions', and 'classes' keys
    """
    parser = get_parser(file_path)
    if not parser:
        return {'imports': [], 'functions': [], 'classes': []}

    return {
        'imports': parser.parse_imports(source),
        'functions': parser.parse_functions(source),
        'classes': parser.parse_classes(source),
    }


# Export public API
__all__ = [
    'CodeParser',
    'Import',
    'Function',
    'Class',
    'get_parser',
    'parse_file',
    'PythonParser',
    'JavaScriptParser',
    'TypeScriptParser',
]
