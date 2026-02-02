#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration centralisée des logs pour QAIA."""

# /// script
# dependencies = []
# ///

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path

# Configuration des chemins
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configuration des niveaux de log par catégorie
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Configuration des formats de log
LOG_FORMATS = {
    "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
}

# Force l'encodage UTF-8 pour la sortie standard et les fichiers
if sys.platform == 'win32':
    # Pour Windows, s'assurer que l'encodage est correct pour les logs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # Définir les variables d'environnement pour Python
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

def get_logger(name: str, category: str = "default", level: str = "info") -> logging.Logger:
    """
    Crée et configure un logger avec rotation de fichiers.
    
    Args:
        name: Nom du logger
        category: Catégorie du logger (détermine le nom du fichier)
        level: Niveau de log (debug, info, warning, error, critical)
        
    Returns:
        logging.Logger: Logger configuré
    """
    # Création du logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level.lower(), logging.INFO))
    
    # Vérification si le logger a déjà des handlers
    if logger.handlers:
        return logger
        
    # Configuration du fichier de log
    log_file = LOG_DIR / f"{category}.log"
    max_bytes = 10 * 1024 * 1024  # 10 MB
    backup_count = 5
    
    # Handler pour le fichier avec rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
        errors='replace'  # Utiliser 'replace' pour remplacer les caractères problématiques
    )
    file_handler.setLevel(LOG_LEVELS.get(level.lower(), logging.INFO))
    file_handler.setFormatter(logging.Formatter(LOG_FORMATS["detailed"]))
    
    # Handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVELS.get(level.lower(), logging.INFO))
    console_handler.setFormatter(logging.Formatter(LOG_FORMATS["default"]))
    
    # Ajout des handlers au logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def cleanup_logs():
    """
    Nettoie les anciens fichiers de log.
    """
    try:
        # Suppression des fichiers vides
        for log_file in LOG_DIR.glob("*.log"):
            if log_file.stat().st_size == 0:
                log_file.unlink()
                
        # Archivage des anciens fichiers
        for log_file in LOG_DIR.glob("*.log.*"):
            if log_file.suffix.isdigit():
                log_file.unlink()
                
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des logs: {e}") 