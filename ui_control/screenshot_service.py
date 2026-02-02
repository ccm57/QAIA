#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Service de capture d'écran (CPU-only, mode dégradé)."""

# /// script
# dependencies = []
# ///

from pathlib import Path
import time
import logging
from typing import Optional, Tuple

from ui_control.models import ScreenMetadata


class ScreenshotService:
    """Capture d'écran avec fallback texte (mode dégradé)."""

    def __init__(self, base_dir: Path, enabled: bool = False):
        """
        Initialise le service de capture.

        Args:
            base_dir (Path): Répertoire racine QAIA
            enabled (bool): Active la capture réelle (non implémentée ici)
        """
        self.base_dir = base_dir
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)
        self.screens_dir = self.base_dir / "data" / "ui_control" / "screenshots"
        self.screens_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen(
        self,
        url: Optional[str] = None,
        window_title: Optional[str] = None,
        viewport: Optional[Tuple[int, int]] = None,
    ) -> tuple[str, ScreenMetadata]:
        """
        Capture un écran ou produit un placeholder en mode dégradé.

        Args:
            url (Optional[str]): URL active
            window_title (Optional[str]): Titre fenêtre active
            viewport (Optional[Tuple[int, int]]): Taille viewport

        Returns:
            tuple[str, ScreenMetadata]: (chemin capture, métadonnées)
        """
        timestamp = time.time()
        metadata = ScreenMetadata(
            timestamp=timestamp,
            url=url,
            window_title=window_title,
            viewport=viewport,
            source="placeholder" if not self.enabled else "capture"
        )

        if not self.enabled:
            placeholder_path = self.screens_dir / f"screen_{int(timestamp * 1000)}.txt"
            placeholder_path.write_text(
                f"capture_placeholder={timestamp}\n"
                f"url={url or ''}\n"
                f"window_title={window_title or ''}\n"
                f"viewport={viewport or ''}\n",
                encoding="utf-8"
            )
            self.logger.info("Capture écran en mode dégradé (placeholder)")
            return str(placeholder_path), metadata

        # Capture réelle non implémentée dans ce module
        self.logger.warning("Capture écran réelle non implémentée (mode dégradé forcé)")
        return self.capture_screen(url=url, window_title=window_title, viewport=viewport)
