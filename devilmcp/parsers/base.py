"""
Base parser interface for multi-language code analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Import:
    """Represents an import statement."""
    module: str
    names: List[str] = field(default_factory=list)
    line: int = 0
    is_relative: bool = False


@dataclass
class Function:
    """Represents a function definition."""
    name: str
    start_line: int
    end_line: int
    params: List[str] = field(default_factory=list)


@dataclass
class Class:
    """Represents a class definition."""
    name: str
    start_line: int
    end_line: int
    methods: List[str] = field(default_factory=list)


class CodeParser(ABC):
    """Abstract base class for language-specific code parsers."""

    @abstractmethod
    def parse_imports(self, source: str) -> List[Import]:
        """Extract all import statements from source code."""
        pass

    @abstractmethod
    def parse_functions(self, source: str) -> List[Function]:
        """Extract all function definitions from source code."""
        pass

    @abstractmethod
    def parse_classes(self, source: str) -> List[Class]:
        """Extract all class definitions from source code."""
        pass
