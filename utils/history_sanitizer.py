#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sanitizer pour l'historique de conversation.
Valide et nettoie l'historique avant envoi au LLM pour éviter pollution.

# /// script
# dependencies = []
# ///
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Patterns de fragments suspects à détecter
SUSPICIOUS_PATTERNS = [
    r'---\s*##?\s*#?\s*',  # Markdown headers (--- ## #)
    r'Instruction\s+en\s+français',  # Fragments d'instructions
    r'Contraintes\s+supplémentaires',  # Fragments de contraintes
    r'Artemis',  # Nom d'exemple
    r'\bN\s+I\s+N\s+A\b',  # "N IN A" (BPE)
    r'\bNINA\b',  # "NINA"
    r'conseiller\s+numérique',  # Fragment de prompt
    r'personnage\s+de\s+fiction',  # Fragment de prompt
    r'opération\s+secrète',  # Fragment de prompt
    r'<\|user\|>',  # Balises Phi-3 mal placées
    r'<\|assistant\|>',  # Balises Phi-3 mal placées
    r'<\|system\|>',  # Balises Phi-3 mal placées
]

# Patterns de préfixes indésirables
PREFIX_PATTERNS = [
    r'^\(\d{1,2}:\d{2}\)\s*QAIA\s*:?\s*',  # "(HH:MM) QAIA:"
    r'^QAIA\s*:?\s*',  # "QAIA:"
]


def sanitize_conversation_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Nettoie l'historique de conversation des fragments suspects.
    
    Args:
        history: Historique de conversation brut
        
    Returns:
        Historique nettoyé
    """
    if not history:
        return []
    
    sanitized = []
    removed_count = 0
    
    for turn in history:
        if not isinstance(turn, dict):
            logger.warning(f"Tour invalide (pas un dict): {turn}")
            continue
        
        role = turn.get("role", "")
        content = turn.get("content", "")
        
        if not isinstance(content, str):
            logger.warning(f"Contenu invalide (pas une string): {content}")
            continue
        
        # Vérifier si le contenu contient des fragments suspects
        is_suspicious = False
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Fragment suspect détecté dans historique: {pattern} dans '{content[:50]}...'")
                is_suspicious = True
                removed_count += 1
                break
        
        # Vérifier les préfixes indésirables
        if not is_suspicious:
            for pattern in PREFIX_PATTERNS:
                if re.match(pattern, content.strip(), re.IGNORECASE):
                    # Supprimer le préfixe mais garder le reste
                    cleaned_content = re.sub(pattern, '', content.strip(), flags=re.IGNORECASE)
                    if cleaned_content:
                        turn = {"role": role, "content": cleaned_content}
                    else:
                        is_suspicious = True
                        removed_count += 1
                        break
        
        if not is_suspicious:
            sanitized.append(turn)
    
    if removed_count > 0:
        logger.info(f"Historique nettoyé: {removed_count} tours suspects supprimés sur {len(history)}")
    
    return sanitized


def sanitize_content(content: str) -> str:
    """
    Nettoie un contenu individuel des fragments suspects.
    
    Args:
        content: Contenu à nettoyer
        
    Returns:
        Contenu nettoyé
    """
    if not isinstance(content, str):
        return content
    
    cleaned = content
    
    # Supprimer les fragments suspects
    for pattern in SUSPICIOUS_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Supprimer les préfixes
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Normaliser les espaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def validate_prompt_format(prompt: str) -> bool:
    """
    Valide que le prompt est bien formaté (balises Phi-3 fermées).
    
    Args:
        prompt: Prompt à valider
        
    Returns:
        True si le prompt est valide
    """
    if not isinstance(prompt, str):
        return False
    
    # Compter les balises ouvrantes et fermantes
    open_tags = len(re.findall(r'<\|(system|user|assistant)\|>', prompt))
    close_tags = len(re.findall(r'<\|end\|>', prompt))
    
    # Le prompt peut se terminer par <|assistant|>\n sans <|end|> (c'est normal)
    # Donc on accepte si open_tags == close_tags OU si open_tags == close_tags + 1 et se termine par <|assistant|>
    ends_with_assistant = prompt.rstrip().endswith('<|assistant|>') or prompt.rstrip().endswith('<|assistant|>\n')
    
    if open_tags == close_tags:
        return True
    elif open_tags == close_tags + 1 and ends_with_assistant:
        return True  # Normal: prompt se termine par <|assistant|> sans <|end|>
    else:
        logger.warning(f"Prompt mal formaté: {open_tags} balises ouvrantes, {close_tags} balises fermantes")
        return False

