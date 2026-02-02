#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Parseur d'interface (OCR + détection éléments) en mode dégradé."""

# /// script
# dependencies = []
# ///

from typing import Optional
import logging
import time

from ui_control.models import ScreenSchema, ScreenMetadata


class UIParser:
    """Parseur d'interface pour produire un schéma d'écran structuré."""

    def __init__(self):
        """Initialise le parseur UI."""
        self.logger = logging.getLogger(__name__)

    def parse(self, screenshot_path: str, metadata: ScreenMetadata) -> ScreenSchema:
        """
        Produit un schéma d'écran structuré.

        Args:
            screenshot_path (str): Chemin capture
            metadata (ScreenMetadata): Métadonnées capture

        Returns:
            ScreenSchema: Schéma vide en mode dégradé
        """
        schema_id = f"schema_{int(time.time() * 1000)}"
        self.logger.info("UIParser: schéma d'écran généré (mode dégradé)")
        return ScreenSchema(
            schema_id=schema_id,
            screenshot_path=screenshot_path,
            metadata=metadata,
            elements=[]
        )
