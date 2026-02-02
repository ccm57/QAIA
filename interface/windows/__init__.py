#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Fenêtres modulaires pour l'interface QAIA."""

# /// script
# dependencies = []
# ///

from .monitoring_window import MonitoringWindow
from .logs_window import LogsWindow
from .metrics_window import MetricsWindow
from .agents_window import AgentsWindow

__all__ = ['MonitoringWindow', 'LogsWindow', 'MetricsWindow', 'AgentsWindow']

