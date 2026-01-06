"""Tests for Iteration 2: Code Entity Fidelity."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def nested_python(temp_project):
    """Create a Python file with nested classes."""
    code = '''
class User:
    """User model."""

    class Profile:
        """Nested profile."""

        def update(self):
            pass

    def save(self):
        pass

def helper():
    pass
'''
    py_file = temp_project / "models.py"
    py_file.write_text(code)
    return py_file


class TestQualifiedNames:
    """Test qualified name computation."""

    def test_qualified_name_nested_class_method(self, temp_project, nested_python):
        """Nested method has fully qualified name."""
        from daem0nmcp.code_indexer import TreeSitterIndexer

        indexer = TreeSitterIndexer()
        if not indexer.available:
            pytest.skip("tree-sitter not available")

        entities = list(indexer.index_file(nested_python, temp_project))

        update_method = next((e for e in entities if e['name'] == 'update'), None)
        assert update_method is not None
        assert 'qualified_name' in update_method
        assert 'User' in update_method['qualified_name']
        assert 'Profile' in update_method['qualified_name']

    def test_qualified_name_top_level_function(self, temp_project, nested_python):
        """Top-level function has module-prefixed name."""
        from daem0nmcp.code_indexer import TreeSitterIndexer

        indexer = TreeSitterIndexer()
        if not indexer.available:
            pytest.skip("tree-sitter not available")

        entities = list(indexer.index_file(nested_python, temp_project))

        helper_func = next((e for e in entities if e['name'] == 'helper'), None)
        assert helper_func is not None
        assert 'qualified_name' in helper_func
        assert 'models' in helper_func['qualified_name']
