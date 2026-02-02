#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Module de sécurité minimal (restauré)
Fournit des fonctions stubs utilisées par qaia_core pour éviter les erreurs d'import.
"""

# /// script
# dependencies = [
# ]
# ///

import os
from pathlib import Path
from typing import Optional, Dict, Any


def validate_user_input(text: Optional[str], max_length: int = 4000) -> Dict[str, Any]:
    """
    Valide et nettoie une entrée utilisateur.

    Args:
        text (Optional[str]): Texte utilisateur à valider.
        max_length (int): Longueur maximale autorisée après nettoyage.

    Returns:
        Dict[str, Any]:
            - is_valid (bool): Indique si l'input est acceptable.
            - cleaned_input (str): Texte nettoyé (ou chaîne vide si invalide).
            - warnings (list[str]): Motifs suspects détectés.
            - blocked_reason (str|None): Raison du blocage si invalide.
    """
    result: Dict[str, Any] = {
        "is_valid": False,
        "cleaned_input": "",
        "warnings": [],
        "blocked_reason": None,
    }

    if text is None:
        result["blocked_reason"] = "Input manquant"
        return result
    if not isinstance(text, str):
        result["blocked_reason"] = "Type invalide"
        return result

    cleaned = text.strip()
    if len(cleaned) == 0:
        result["blocked_reason"] = "Input vide"
        return result

    # Sanitation minimale
    import re
    injection_patterns = [
        r"<script[\s\S]*?</script>",
        r"javascript:\s*",
        r"eval\s*\(",
        r"import\s+os",
        r"subprocess\s*\.\s*",
    ]
    for pat in injection_patterns:
        if re.search(pat, cleaned, flags=re.IGNORECASE):
            result["warnings"].append(f"pattern_detected:{pat}")
            # Neutraliser basiquement le motif
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Filtrer les caractères de contrôle dangereux (sauf \n, \r, \t)
    cleaned = "".join(
        ch for ch in cleaned
        if (31 < ord(ch) < 0xD800) or ch in ("\n", "\r", "\t", " ")
    )

    # Contrôle de longueur
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
        result["warnings"].append("truncated_to_max_length")

    result["is_valid"] = True
    result["cleaned_input"] = cleaned
    return result


def validate_file_path(path: str, must_exist: bool = True) -> bool:
    """Validation simple de chemin de fichier."""
    try:
        p = Path(path)
        if must_exist:
            return p.exists()
        # Chemin non existant autorisé: vérifier que le parent existe
        return p.parent.exists()
    except Exception:
        return False
