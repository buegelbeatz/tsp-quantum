"""Shared test utilities for board skill tests and other test suites.

Purpose:
    Centralize common test fixtures and module loading helpers.
    Reduce duplication across test files.

Security:
    No external execution; pure test utility functions.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(name: str, base_dir: Path | None = None) -> object:
    """Load and inject a module from a Python file in the test base directory.

    Args:
        name: Module name (without .py extension).
        base_dir: Optional base directory. Defaults to caller's parent directory.

    Returns:
        Loaded module object.

    Raises:
        AssertionError: If spec or loader cannot be created.
    """
    if base_dir is None:
        # Derive from caller's location (one level up from tests/)
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_file = Path(frame.f_back.f_code.co_filename)
            base_dir = caller_file.resolve().parents[1]
        else:
            base_dir = Path.cwd()

    spec = importlib.util.spec_from_file_location(name, base_dir / f"{name}.py")
    assert spec and spec.loader, f"Could not load module {name} from {base_dir}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_module_from_path(script_path: Path, module_name: str | None = None) -> object:
    """Load a module from a specific file path.

    Args:
        script_path: Full path to the Python file to load.
        module_name: Name to register module as. Defaults to file stem.

    Returns:
        Loaded module object.

    Raises:
        AssertionError: If spec or loader cannot be created.
    """
    if module_name is None:
        module_name = script_path.stem

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader, f"Could not load module from {script_path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
