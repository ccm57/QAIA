#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration du système de logging."""

# /// script
# dependencies = []
# ///

import os
import sys
import logging
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure le système de logging avec rotation des fichiers.
    
    Args:
        log_dir: Répertoire où stocker les fichiers de log
        log_level: Niveau de log (logging.INFO, logging.DEBUG, etc.)
        max_bytes: Taille maximale d'un fichier de log avant rotation
        backup_count: Nombre de fichiers de backup à conserver
        console_output: Si True, affiche les logs dans la console
    
    Returns:
        logging.Logger: Logger configuré
    """
    try:
        # Créer le répertoire de logs s'il n'existe pas
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Créer le logger principal
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # Formatter pour les logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler pour les fichiers avec rotation
        log_file = log_path / f"qaia_{time.strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler pour la console si demandé
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # Handler pour les erreurs avec rotation temporelle
        error_log_file = log_path / "error.log"
        error_handler = TimedRotatingFileHandler(
            error_log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Logger de démarrage
        logger.info("Système de logging initialisé")
        logger.info(f"Logs stockés dans: {log_path.absolute()}")
        
        return logger
        
    except Exception as e:
        print(f"Erreur lors de la configuration du logging: {e}")
        # Fallback sur la configuration basique
        logging.basicConfig(level=log_level)
        return logging.getLogger()

def get_module_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour un module spécifique.
    
    Args:
        name: Nom du module (généralement __name__)
    
    Returns:
        logging.Logger: Logger configuré pour le module
    """
    return logging.getLogger(name)

if __name__ == "__main__":
    # Test de la configuration
    test_logger = setup_logging()
    test_logger.info("Test de log info")
    test_logger.debug("Test de log debug")
    test_logger.warning("Test de log warning")
    test_logger.error("Test de log error") 