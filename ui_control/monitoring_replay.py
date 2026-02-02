#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Journalisation et replay pour UI-control."""

# /// script
# dependencies = []
# ///

from pathlib import Path
import json
import time
import logging
from typing import Any, Dict


class MonitoringReplay:
    """Gère les journaux d'actions et traces UI-control."""

    def __init__(self, base_dir: Path):
        """
        Initialise le module de replay.

        Args:
            base_dir (Path): Répertoire racine QAIA
        """
        self.base_dir = base_dir
        self.logs_dir = self.base_dir / "logs" / "ui_control"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def log_event(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Enregistre un événement UI-control.

        Args:
            event_type (str): Type d'événement
            payload (Dict[str, Any]): Données associées

        Returns:
            str: Chemin du log
        """
        timestamp = int(time.time() * 1000)
        path = self.logs_dir / f"{event_type}_{timestamp}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.logger.info(f"UI-control log: {path}")
        return str(path)
