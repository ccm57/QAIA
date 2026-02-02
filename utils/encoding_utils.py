#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaires d'encodage pour QAIA
Gère les problèmes d'encodage et de caractères spéciaux
"""

# /// script
# dependencies = [
#   "chardet>=5.0.0"
# ]
# ///

import os
import sys
import logging
import chardet
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def detect_encoding(file_path: str) -> str:
    """
    Détecte l'encodage d'un fichier.
    
    Args:
        file_path (str): Chemin vers le fichier
        
    Returns:
        str: Encodage détecté (par défaut 'utf-8')
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            if confidence < 0.7:
                logger.warning(f"Confiance faible pour l'encodage détecté: {encoding} ({confidence:.2f})")
                return 'utf-8'
            
            return encoding
    except Exception as e:
        logger.error(f"Erreur lors de la détection d'encodage: {e}")
        return 'utf-8'

def setup_encoding():
    """
    Configure l'encodage du système pour éviter les erreurs de caractères.
    """
    try:
        # Configurer l'encodage par défaut
        if sys.platform.startswith('win'):
            # Windows
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        else:
            # Linux/Mac
            os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Configurer stdout/stderr
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
            
        logger.info("Configuration d'encodage UTF-8 appliquée")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la configuration d'encodage: {e}")
        return False

def safe_read_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    Lit un fichier de manière sécurisée avec détection d'encodage.
    
    Args:
        file_path (str): Chemin vers le fichier
        encoding (Optional[str]): Encodage spécifique (si None, détection automatique)
        
    Returns:
        str: Contenu du fichier
    """
    try:
        if encoding is None:
            encoding = detect_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
            
        logger.debug(f"Fichier lu avec succès: {file_path} (encodage: {encoding})")
        return content
        
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return ""

def safe_write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Écrit un fichier de manière sécurisée avec encodage UTF-8.
    
    Args:
        file_path (str): Chemin vers le fichier
        content (str): Contenu à écrire
        encoding (str): Encodage à utiliser
        
    Returns:
        bool: True si succès, False sinon
    """
    try:
        # Créer le répertoire parent si nécessaire
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding, errors='replace') as f:
            f.write(content)
            
        logger.debug(f"Fichier écrit avec succès: {file_path} (encodage: {encoding})")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du fichier {file_path}: {e}")
        return False

def clean_text(text: str) -> str:
    """
    Nettoie un texte en supprimant les caractères problématiques.
    
    Args:
        text (str): Texte à nettoyer
        
    Returns:
        str: Texte nettoyé
    """
    try:
        if not text or not isinstance(text, str):
            return text if text else ""
        # Centraliser le nettoyage dans text_processor
        from utils.text_processor import clean_control_characters, normalize_spaces
        cleaned = clean_control_characters(text)
        cleaned = normalize_spaces(cleaned)
        return cleaned
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du texte: {e}")
        return text

def validate_utf8(text: str) -> bool:
    """
    Valide qu'un texte est en UTF-8 valide.
    
    Args:
        text (str): Texte à valider
        
    Returns:
        bool: True si UTF-8 valide, False sinon
    """
    try:
        text.encode('utf-8')
        return True
    except UnicodeEncodeError:
        return False

def fix_encoding_issues(file_path: str) -> bool:
    """
    Corrige les problèmes d'encodage d'un fichier.
    
    Args:
        file_path (str): Chemin vers le fichier
        
    Returns:
        bool: True si succès, False sinon
    """
    try:
        # Lire le fichier avec détection d'encodage
        content = safe_read_file(file_path)
        
        if not content:
            return False
        
        # Nettoyer le contenu
        cleaned_content = clean_text(content)
        
        # Réécrire en UTF-8
        success = safe_write_file(file_path, cleaned_content, 'utf-8')
        
        if success:
            logger.info(f"Problèmes d'encodage corrigés pour: {file_path}")
        
        return success
        
    except Exception as e:
        logger.error(f"Erreur lors de la correction d'encodage: {e}")
        return False

# Initialisation automatique
if __name__ == "__main__":
    setup_encoding()
