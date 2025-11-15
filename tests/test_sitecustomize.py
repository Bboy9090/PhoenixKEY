"""
Comprehensive unit tests for sitecustomize.py
Tests the project-wide Python path configuration module
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import pytest


class TestSitecustomizePathConfiguration:
    """Test sitecustomize.py path configuration functionality"""
    
    def test_sitecustomize_module_exists(self):
        """Test that sitecustomize.py exists in the expected location"""
        # sitecustomize.py should be at project root
        project_root = Path(__file__).parent.parent
        sitecustomize_path = project_root / "sitecustomize.py"
        
        assert sitecustomize_path.exists(), "sitecustomize.py should exist at project root"
        assert sitecustomize_path.is_file(), "sitecustomize.py should be a file"
    
    def test_sitecustomize_has_required_function(self):
        """Test that sitecustomize.py contains the required function"""
        project_root = Path(__file__).parent.parent
        sitecustomize_path = project_root / "sitecustomize.py"
        
        with open(sitecustomize_path, 'r') as f:
            content = f.read()
        
        # Check for function definition
        assert "_ensure_project_root_on_path" in content
        assert "def _ensure_project_root_on_path()" in content
    
    def test_sitecustomize_imports(self):
        """Test that sitecustomize.py imports can be resolved"""
        # Import sitecustomize should not raise errors
        import sitecustomize
        
        # Verify it has the expected function
        assert hasattr(sitecustomize, '_ensure_project_root_on_path')
    
    def test_project_root_detection(self):
        """Test that sitecustomize correctly identifies project root"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        
        # Project root should exist
        assert project_root.exists()
        assert project_root.is_dir()
        
        # Should contain expected project files
        assert (project_root / "src").exists()
        assert (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists()
    
    def test_project_root_in_sys_path(self):
        """Test that project root is added to sys.path"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        root_str = str(project_root)
        
        # Project root should be in sys.path
        assert root_str in sys.path, "Project root should be in sys.path"
    
    def test_src_directory_in_sys_path(self):
        """Test that src directory is added to sys.path"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        src_dir = project_root / "src"
        src_str = str(src_dir)
        
        if src_dir.exists():
            # src directory should be in sys.path
            assert src_str in sys.path, "src directory should be in sys.path"
    
    def test_path_order_precedence(self):
        """Test that project paths are prepended to sys.path for proper precedence"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        root_str = str(project_root)
        
        # Project root should be near the beginning of sys.path
        if root_str in sys.path:
            root_index = sys.path.index(root_str)
            # Should be in first 10 entries for proper precedence
            assert root_index < 10, "Project root should be early in sys.path for precedence"
    
    def test_no_duplicate_paths(self):
        """Test that paths are not duplicated in sys.path"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        root_str = str(project_root)
        
        # Count occurrences in sys.path
        occurrences = sys.path.count(root_str)
        
        # Should appear only once (no duplicates)
        assert occurrences <= 1, "Project root should not be duplicated in sys.path"
    
    def test_src_import_resolution(self):
        """Test that 'import src' works correctly after sitecustomize"""
        try:
            import src
            # Should not raise ImportError
            assert src is not None
            
            # Should be a package
            assert hasattr(src, '__path__')
        except ImportError as e:
            pytest.fail(f"Failed to import src package: {e}")
    
    def test_src_submodule_imports(self):
        """Test that src submodules can be imported"""
        try:
            from src.core import config
            assert config is not None
            
            from src.core import win_patch_engine
            assert win_patch_engine is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src submodules: {e}")


class TestSitecustomizeRobustness:
    """Test robustness and edge cases of sitecustomize"""
    
    def test_multiple_imports_idempotent(self):
        """Test that multiple imports of sitecustomize are idempotent"""
        # Record initial sys.path length
        initial_length = len(sys.path)
        
        # Import sitecustomize multiple times
        import sitecustomize
        import importlib
        importlib.reload(sitecustomize)
        importlib.reload(sitecustomize)
        
        # Path length should not grow significantly
        final_length = len(sys.path)
        # Allow small growth but not proportional to reload count
        assert final_length - initial_length < 5, "Multiple sitecustomize loads should not duplicate paths"
    
    def test_works_with_modified_sys_path(self):
        """Test that sitecustomize works even if sys.path is modified"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        root_str = str(project_root)
        
        # Temporarily modify sys.path
        original_path = sys.path.copy()
        try:
            # Add some noise to sys.path
            sys.path.append("/fake/path/1")
            sys.path.append("/fake/path/2")
            
            # Reload sitecustomize
            import importlib
            importlib.reload(sitecustomize)
            
            # Project root should still be accessible
            assert root_str in sys.path
        finally:
            # Restore original path
            sys.path = original_path
    
    def test_handles_missing_src_directory(self):
        """Test that sitecustomize handles missing src directory gracefully"""
        # This test verifies the code doesn't crash if src doesn't exist
        # Since we can't easily remove src, we just verify the check exists
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        src_dir = project_root / "src"
        
        # If src exists in the actual project, we can't test the missing case
        # But we can verify the exists() check is in the code
        with open(project_root / "sitecustomize.py", 'r') as f:
            content = f.read()
        
        assert "src_dir.exists()" in content, "Should check if src directory exists"


class TestSitecustomizeDocumentation:
    """Test documentation and code quality of sitecustomize"""
    
    def test_module_has_docstring(self):
        """Test that sitecustomize.py has a module docstring"""
        import sitecustomize
        
        assert sitecustomize.__doc__ is not None
        assert len(sitecustomize.__doc__) > 0
        assert "path configuration" in sitecustomize.__doc__.lower()
    
    def test_function_has_docstring(self):
        """Test that _ensure_project_root_on_path has a docstring"""
        import sitecustomize
        
        func = sitecustomize._ensure_project_root_on_path
        assert func.__doc__ is not None
        assert len(func.__doc__) > 0
        assert "sys.path" in func.__doc__
    
    def test_uses_pathlib(self):
        """Test that sitecustomize uses pathlib for path handling"""
        project_root = Path(__file__).parent.parent
        sitecustomize_path = project_root / "sitecustomize.py"
        
        with open(sitecustomize_path, 'r') as f:
            content = f.read()
        
        # Should import and use Path
        assert "from pathlib import Path" in content
        assert "Path(__file__)" in content
    
    def test_future_annotations(self):
        """Test that sitecustomize uses future annotations"""
        project_root = Path(__file__).parent.parent
        sitecustomize_path = project_root / "sitecustomize.py"
        
        with open(sitecustomize_path, 'r') as f:
            content = f.read()
        
        # Should use future annotations for better type hints
        assert "from __future__ import annotations" in content


class TestSitecustomizeTestCompatibility:
    """Test that sitecustomize solves the test import problem it was designed for"""
    
    def test_src_imports_work_from_tests(self):
        """Test that src imports work correctly from test context"""
        # This simulates the issue sitecustomize was designed to solve
        try:
            # Both absolute and relative to src should work
            import src.core.config
            from src.core import config
            
            assert src.core.config is config
        except ImportError as e:
            pytest.fail(f"Import failed - sitecustomize not working: {e}")
    
    def test_mixed_import_styles_work(self):
        """Test that different import styles all work"""
        try:
            # Style 1: import src
            import src
            assert src is not None
            
            # Style 2: from src import module
            from src.core import config
            assert config is not None
            
            # Style 3: import src.module directly
            import src.core.win_patch_engine
            assert src.core.win_patch_engine is not None
            
            # All should refer to the same package
            assert src.core.config is config
        except ImportError as e:
            pytest.fail(f"Mixed import styles failed: {e}")
    
    def test_no_src_src_path_issue(self):
        """Test that the src/src path issue is resolved"""
        import sitecustomize
        
        project_root = Path(sitecustomize.__file__).resolve().parent
        
        # Verify no paths like /path/to/project/src/src exist in sys.path
        for path_str in sys.path:
            path = Path(path_str)
            # Check if path ends with src/src
            if path.exists() and path.name == "src":
                parent = path.parent
                assert parent.name != "src", "Should not have src/src in sys.path"


class TestPyprojectTomlPytestConfiguration:
    """Test pytest configuration in pyproject.toml"""
    
    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists"""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"
        
        assert pyproject_path.exists(), "pyproject.toml should exist"
    
    def test_pytest_config_in_pyproject(self):
        """Test that pytest configuration is present in pyproject.toml"""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Should contain pytest configuration
        assert "[tool.pytest.ini_options]" in content
        assert "pythonpath" in content
    
    def test_pytest_pythonpath_includes_required_dirs(self):
        """Test that pytest pythonpath includes required directories"""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Should include both . and src
        assert '"."' in content or "'.'".lower() in content.lower()
        assert '"src"' in content or "'src'".lower() in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])