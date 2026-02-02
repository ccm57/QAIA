#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Normalisation phonétique pour transcriptions STT.
Corrige les erreurs de transcription courantes (français oral → texte écrit).

# /// script
# dependencies = []
# ///
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Dictionnaire de corrections phonétiques courantes
# Format: pattern_regex → correction
PHONETIC_CORRECTIONS: Dict[str, str] = {
    # Corrections phonétiques courantes
    r'\bboujeur\b': 'bouger',
    r'\bBoujeur\b': 'Bouger',
    r'\bast\b': 'est',  # "ast" → "est"
    r'\bAst\b': 'Est',
    r'\bqueyan\b': 'QAIA',
    r'\bQueyan\b': 'QAIA',
    r'\bcaya\b': 'QAIA',
    r'\bCaya\b': 'QAIA',
    r'\bkaia\b': 'QAIA',
    r'\bKaia\b': 'QAIA',
    r'\bjéclaude\b': 'je suis Claude',
    r'\bJéclaude\b': 'Je suis Claude',
    r'\baras-tu\b': 'vas-tu',
    r'\bAras-tu\b': 'Vas-tu',
    r'\baux\s+ourdhui\b': "aujourd'hui",
    r'\bAux\s+ourdhui\b': "Aujourd'hui",
    r'\bquell\b': 'quelle',
    r'\bQuell\b': 'Quelle',
    r'\best\s+octilisé\b': 'est utilisé',
    r'\bEst\s+octilisé\b': 'Est utilisé',
    r'\bpourier\b': 'peux-tu',
    r'\bPourier\b': 'Peux-tu',
    r'\bsefo\s+mation\b': 'ces informations',
    r'\bSefo\s+mation\b': 'Ces informations',
    r'\bne\s+boujeur\b': 'ne bouge pas',
    r'\bNe\s+boujeur\b': 'Ne bouge pas',
    r'\bjusquici\b': "jusqu'ici",
    r'\bJusquici\b': "Jusqu'ici",
    r'\bque\s+toi\b': 'que toi',
    r'\bQue\s+toi\b': 'Que toi',
}


def normalize_stt_text(text: str) -> str:
    """
    Normalise une transcription STT en corrigeant les erreurs phonétiques courantes.
    
    Args:
        text: Texte transcrit par STT (potentiellement bruité)
        
    Returns:
        Texte normalisé avec corrections phonétiques
    """
    if not text or not isinstance(text, str):
        return text
    
    normalized = text
    
    # Appliquer les corrections phonétiques
    for pattern, correction in PHONETIC_CORRECTIONS.items():
        normalized = re.sub(pattern, correction, normalized, flags=re.IGNORECASE)
    
    # Normaliser les espaces multiples
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Logger si des corrections ont été appliquées
    if normalized != text:
        logger.debug(f"STT normalisé: '{text[:50]}...' → '{normalized[:50]}...'")
    
    return normalized


def should_normalize(text: str) -> bool:
    """
    Détermine si un texte STT devrait être normalisé.
    
    Args:
        text: Texte à évaluer
        
    Returns:
        True si le texte contient des patterns suspects
    """
    if not text or not isinstance(text, str):
        return False
    
    # Vérifier si le texte contient des patterns suspects
    for pattern in PHONETIC_CORRECTIONS.keys():
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False

