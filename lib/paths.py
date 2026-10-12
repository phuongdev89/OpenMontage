"""Canonical repository paths — single source of truth.

The projects root is the most load-bearing path in the system: checkpoints
are written under it, tool events are attributed against it, and the Backlot
board watches it. Define it once.
"""

from __future__ import annotations

import os
from pathlib import Path

from lib.env_loader import load_env

REPO_ROOT = Path(__file__).resolve().parent.parent

load_env(REPO_ROOT)

# Overridable for staging/screenshots/tests. Everything — checkpoint writes,
# event attribution, the Backlot board — follows the same root.
_override = os.environ.get("OPENMONTAGE_PROJECTS_DIR")
if _override:
    PROJECTS_DIR = Path(_override)
else:
    _default = REPO_ROOT / "projects"
    try:
        # Verify access; corrupted directory entries (e.g. exFAT) raise PermissionError/OSError
        next(_default.iterdir(), None)
        PROJECTS_DIR = _default
    except (PermissionError, OSError):
        PROJECTS_DIR = REPO_ROOT / "projects_work"
