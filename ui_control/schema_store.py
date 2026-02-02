#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Stockage des schémas d'écran (JSON)."""

# /// script
# dependencies = []
# ///

from pathlib import Path
import json
import logging
from dataclasses import asdict

from ui_control.models import ScreenSchema


class ScreenSchemaStore:
    """Stocke et charge des schémas d'écran."""

    def __init__(self, base_dir: Path):
        """
        Initialise le stockage.

        Args:
            base_dir (Path): Répertoire racine QAIA
        """
        self.base_dir = base_dir
        self.schemas_dir = self.base_dir / "data" / "ui_control" / "schemas"
        self.schemas_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def save(self, schema: ScreenSchema) -> str:
        """
        Sauvegarde un schéma au format JSON.

        Args:
            schema (ScreenSchema): Schéma à sauvegarder

        Returns:
            str: Chemin du fichier
        """
        path = self.schemas_dir / f"{schema.schema_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(schema), f, ensure_ascii=False, indent=2)
        self.logger.info(f"Schéma UI sauvegardé: {path}")
        return str(path)
