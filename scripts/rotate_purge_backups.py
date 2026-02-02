#!/usr/bin/env python
# -*- coding: utf-8 -*-
# F:\QAIA\
#
# /// script
# dependencies = [
#   "psutil>=5.9.0",
# ]
# ///
"""
Outil de rotation et purge des fichiers de backup et des logs QAIA.

Seuils par défaut :
- Backups et logs : 30 jours.

Options :
- --retention-jours : nombre de jours avant suppression (défaut 30)
- --dry-run : affiche ce qui serait supprimé sans agir
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple

RETENTION_JOURS_DEFAUT = 30

# Cibles à purger (chemin relatif, motif glob)
TARGETS: List[Tuple[str, str]] = [
    ("config", "system_config.py.backup*"),
    ("utils", "agent_manager.py.backup*"),
    ("backups/agents", "*.backup*"),
    ("logs/backup", "*"),
    (".", "backup.log"),
    (".", "*.backup"),
]


def configurer_logger() -> logging.Logger:
    """Configure un logger simple vers stdout."""
    logger = logging.getLogger("rotate_purge_backups")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def est_expire(path: Path, retention_secs: float) -> bool:
    """Vérifie si le fichier est plus vieux que la rétention."""
    try:
        age_secs = time.time() - path.stat().st_mtime
        return age_secs > retention_secs
    except FileNotFoundError:
        return False


def purger_cible(base_dir: Path, rel_path: str, pattern: str, retention_secs: float, dry_run: bool, logger: logging.Logger) -> int:
    """Purge les fichiers correspondant au motif si plus vieux que la rétention."""
    cible = base_dir / rel_path
    if not cible.exists():
        return 0

    supprimes = 0
    for fichier in cible.glob(pattern):
        if fichier.is_dir():
            # Ne pas supprimer les répertoires, on ne purge que les fichiers
            continue
        if est_expire(fichier, retention_secs):
            supprimes += 1
            if dry_run:
                logger.info(f"[DRY-RUN] Suppression prévue: {fichier}")
            else:
                try:
                    fichier.unlink()
                    logger.info(f"Supprimé: {fichier}")
                except Exception as e:
                    logger.warning(f"Échec suppression {fichier}: {e}")
    return supprimes


def main():
    parser = argparse.ArgumentParser(description="Rotation/purge des backups et logs QAIA.")
    parser.add_argument("--retention-jours", type=int, default=RETENTION_JOURS_DEFAUT, help="Nombre de jours avant suppression (défaut: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche ce qui serait supprimé sans supprimer")
    args = parser.parse_args()

    logger = configurer_logger()
    base_dir = Path(__file__).parent.parent
    retention_secs = args.retention_jours * 86400

    total_supprimes = 0
    for rel_path, pattern in TARGETS:
        total_supprimes += purger_cible(base_dir, rel_path, pattern, retention_secs, args.dry_run, logger)

    if args.dry_run:
        logger.info(f"[DRY-RUN] Fichiers qui seraient supprimés: {total_supprimes}")
    else:
        logger.info(f"Fichiers supprimés: {total_supprimes}")


if __name__ == "__main__":
    main()

