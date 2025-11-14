"""Project-wide Python path configuration.

This module is imported automatically by the Python runtime when it is
present on the import path.  We take advantage of this behaviour to ensure
that the test environment can always resolve the ``src`` package regardless
of how ``sys.path`` is manipulated inside individual test modules.

Some of the provided tests insert the ``src`` directory itself onto
``sys.path`` which inadvertently hides the project root from the module
resolver.  When that happens ``import src`` fails because Python looks for
``src`` inside ``/path/to/project/src`` (i.e. ``/path/to/project/src/src``),
which does not exist.  To make the import robust we explicitly add the
repository root to ``sys.path`` during interpreter start-up.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    """Ensure the repository root is available on ``sys.path``.

    The module file resides in the project root, so we can determine the
    correct directory relative to ``__file__``.  We then prepend the root to
    ``sys.path`` if it is not already present.  Prepending keeps the standard
    import precedence (project modules before site-packages) and avoids
    duplicating entries.
    """

    project_root = Path(__file__).resolve().parent

    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    src_dir = project_root / "src"
    src_str = str(src_dir)
    if src_dir.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_project_root_on_path()

