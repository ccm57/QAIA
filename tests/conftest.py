#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Configuration pytest commune."""

# /// script
# dependencies = [
#   "pytest>=7.0.0"
# ]
# ///

from pathlib import Path
import sys


def pytest_sessionstart(session):
    """Ajoute la racine projet au PYTHONPATH pour les imports."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
