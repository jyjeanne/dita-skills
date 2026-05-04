"""
conftest.py — shared pytest fixtures and path helpers for the dita-skills test suite.

Each skill's scripts/ directory is added to sys.path here so tests can
import the modules directly without packaging.
"""
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent

# Register every scripts/ subdirectory on sys.path once
_SCRIPT_DIRS = [
    "validate-dita-topic/scripts",
    "validate-ditamap/scripts",
    "validate-bookmap/scripts",
    "generate-dita-topic/scripts",
    "generate-ditamap/scripts",
    "generate-bookmap/scripts",
    "dita-best-practices/scripts",
    "ditaval-helper/scripts",
    "review-dita-guide/scripts",
]

for _rel in _SCRIPT_DIRS:
    _path = str(ROOT / _rel)
    if _path not in sys.path:
        sys.path.insert(0, _path)
