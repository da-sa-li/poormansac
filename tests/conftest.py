"""Test configuration for the pure ``calc`` module.

``calc.py`` (and ``const.py``) depend only on the standard library, so the tests
import them directly from the integration directory. Going through the package
(``custom_components.poormansac``) would execute its ``__init__`` and pull in
Home Assistant, which is not needed here -- so we add the package directory to
``sys.path`` and import the modules by their bare names instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "poormansac"
sys.path.insert(0, str(PACKAGE_DIR))
