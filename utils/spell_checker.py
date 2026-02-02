#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Correcteur orthographique français pour les réponses LLM
Corrige les erreurs courantes générées par Phi-3

# /// script
# dependencies = [
#   "pyspellchecker>=0.8.0",  # Correcteur orthographique
# ]
# ///
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Dictionnaire de corrections manuelles pour erreurs courantes Phi-3
CORRECTIONS_MANUELES = {
    "dran": "de",
    "lorsqueil": "lorsqu'il",
    "quest": "qu'est",
    "quest-ce": "qu'est-ce",
    "quest-ce que": "qu'est-ce que",
    "quest-ce qu": "qu'est-ce qu'",
    "quest-ce quil": "qu'est-ce qu'il",
    "quest-ce quun": "qu'est-ce qu'un",
    "quest-ce quune": "qu'est-ce qu'une",
    "quest-ce qui": "qu'est-ce qui",
    "cest": "c'est",
    "nest": "n'est",
    "nest pas": "n'est pas",
    "nest-ce": "n'est-ce",
    "nest-ce pas": "n'est-ce pas",
    "quil": "qu'il",
    "quun": "qu'un",
    "quune": "qu'une",
    "quon": "qu'on",
    "jusquà": "jusqu'à",
    "aujourdhui": "aujourd'hui",
    "prêt": "prêt",  # Garder tel quel
    "pret": "prêt",
    "près": "près",  # Garder tel quel
    "pres": "près",
    # Corrections spécifiques identifiées
    "dévelopression": "développer",
    "développression": "développer",
    "développement": "développement",  # Garder tel quel
}

# Dictionnaire de remplacement mots anglais → français
MOTS_ANGLAIS_FRANCAIS = {
    "privacy": "privacité",
    "privacy.": "privacité.",
    "privacy,": "privacité,",
    "privacy ": "privacité ",
}

try:
    from spellchecker import SpellChecker
    
    # Initialiser le correcteur français
    spell_fr = SpellChecker(language='fr')
    SPELLCHECKER_AVAILABLE = True
    logger.info("Correcteur orthographique français initialisé")
except ImportError:
    SPELLCHECKER_AVAILABLE = False
    logger.warning("pyspellchecker non disponible, utilisation uniquement des corrections manuelles")


def correct_spelling(text: str) -> str:
    """
    Corrige les erreurs d'orthographe dans un texte français.
    
    Applique d'abord les corrections manuelles (erreurs courantes Phi-3),
    puis remplace les mots anglais par leurs équivalents français,
    puis utilise pyspellchecker si disponible.
    
    Args:
        text: Texte à corriger
        
    Returns:
        Texte corrigé
    """
    if not text or not isinstance(text, str):
        return text
    
    # Étape 1: Corrections manuelles (erreurs courantes Phi-3)
    corrected = text
    for error, correction in CORRECTIONS_MANUELES.items():
        # Remplacer les occurrences (insensible à la casse, mais préserver la casse originale)
        pattern = re.compile(re.escape(error), re.IGNORECASE)
        corrected = pattern.sub(lambda m: _preserve_case(m.group(), correction), corrected)
    
    # Étape 2: Remplacer mots anglais par équivalents français
    for english_word, french_word in MOTS_ANGLAIS_FRANCAIS.items():
        # Remplacer en préservant la casse
        pattern = re.compile(re.escape(english_word), re.IGNORECASE)
        corrected = pattern.sub(lambda m: _preserve_case(m.group(), french_word), corrected)
    
    # Étape 3: Corrections avec pyspellchecker si disponible
    if SPELLCHECKER_AVAILABLE:
        try:
            # PROTÉGER les mots spéciaux (acronymes, noms propres) du correcteur
            PROTECTED_WORDS = ['QAIA', 'qaia', 'Qaia']  # Ne pas corriger QAIA
            
            # Séparer en mots ET espaces (préserver les espaces)
            parts = re.split(r'(\s+)', corrected)  # Split en gardant les séparateurs
            corrected_parts = []
            
            for part in parts:
                if re.match(r'^\s+$', part):  # C'est un espace/ponctuation
                    corrected_parts.append(part)  # Garder tel quel
                elif re.match(r'^\w+$', part):  # C'est un mot
                    # PROTÉGER QAIA et autres mots spéciaux
                    if part in PROTECTED_WORDS:
                        corrected_parts.append(part)  # Ne pas corriger
                    # Vérifier si le mot est mal orthographié
                    elif part.lower() in spell_fr:
                        corrected_parts.append(part)  # Mot correct
                    else:
                        # Chercher la correction la plus probable
                        candidates = spell_fr.candidates(part.lower())
                        if candidates:
                            best = spell_fr.correction(part.lower())
                            if best and best != part.lower():
                                # Préserver la casse originale
                                if part[0].isupper():
                                    corrected_parts.append(best.capitalize())
                                else:
                                    corrected_parts.append(best)
                            else:
                                corrected_parts.append(part)
                        else:
                            corrected_parts.append(part)
                else:
                    corrected_parts.append(part)  # Ponctuation, garder tel quel
            
            corrected = ''.join(corrected_parts)
        except Exception as e:
            logger.warning(f"Erreur correcteur orthographique: {e}, utilisation texte non corrigé")
    
    return corrected


def _preserve_case(original: str, replacement: str) -> str:
    """
    Préserve la casse de l'original dans le remplacement.
    
    Args:
        original: Texte original
        replacement: Texte de remplacement
        
    Returns:
        Remplacement avec casse préservée
    """
    if original.isupper():
        return replacement.upper()
    elif original.istitle():
        return replacement.capitalize()
    else:
        return replacement.lower()


def correct_common_errors(text: str) -> str:
    """
    Corrige uniquement les erreurs courantes (sans pyspellchecker).
    Plus rapide, utile si pyspellchecker n'est pas disponible.
    
    Args:
        text: Texte à corriger
        
    Returns:
        Texte corrigé
    """
    if not text or not isinstance(text, str):
        return text
    
    corrected = text
    for error, correction in CORRECTIONS_MANUELES.items():
        pattern = re.compile(re.escape(error), re.IGNORECASE)
        corrected = pattern.sub(lambda m: _preserve_case(m.group(), correction), corrected)
    
    return corrected

