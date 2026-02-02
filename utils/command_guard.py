#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Garde-fou des commandes système pour QAIA.
Évalue si une commande (verbe + cible) est autorisée, nécessite confirmation,
et journalise les tentatives. N'exécute aucune commande.
"""

# /// script
# dependencies = []
# ///

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CommandVerdict:
    """Verdict de sécurité pour une commande."""
    allowed: bool
    require_confirmation: bool
    risk_level: str  # "low" | "medium" | "high"
    reason: str
    raw_verb: Optional[str] = None
    raw_target: Optional[str] = None


# Paires (verbe, cible) autorisées sans confirmation (risque low)
WHITELIST_NO_CONFIRM: Set[Tuple[str, str]] = {
    ("arrete", "enregistrement"),
    ("arrete", "micro"),
    ("lance", "lecture"),
    ("desactive", "micro"),
    ("active", "micro"),
}


# Paires (verbe, cible) autorisées avec confirmation (risque medium)
WHITELIST_CONFIRM: Set[Tuple[str, str]] = {
    ("ferme", "application"),
    ("lance", "navigateur"),
    ("ouvre", "navigateur"),
    ("ferme", "interface"),
    ("redemarre", "assistant"),
}


def evaluate_command(
    command_verb: Optional[str],
    command_target: Optional[str],
    user_context: Optional[Dict[str, Any]] = None,
    raw_text: Optional[str] = None,
) -> CommandVerdict:
    """
    Évalue si une commande (verbe + cible) est autorisée et si une confirmation est requise.

    Args:
        command_verb: Verbe normalisé (ex. "arrete", "lance").
        command_target: Cible normalisée (ex. "enregistrement", "navigateur").
        user_context: Contexte optionnel (ex. user_id, rôle) pour politiques futures.
        raw_text: Texte brut de l'utilisateur (pour journalisation, sans secrets).

    Returns:
        CommandVerdict avec allowed, require_confirmation, risk_level, reason.
    """
    user_context = user_context or {}
    verb = (command_verb if isinstance(command_verb, str) else "").strip().lower() or None
    target = (command_target if isinstance(command_target, str) else "").strip().lower() or None

    verdict = CommandVerdict(
        allowed=False,
        require_confirmation=False,
        risk_level="high",
        reason="Commande non reconnue ou non autorisée.",
        raw_verb=command_verb,
        raw_target=command_target,
    )

    if not verb:
        verdict.reason = "Verbe de commande manquant."
        _log_attempt(verb, target, raw_text, verdict)
        return verdict

    if not target:
        verdict.reason = "Cible de commande manquante."
        verdict.risk_level = "medium"
        _log_attempt(verb, target, raw_text, verdict)
        return verdict

    key = (verb, target)
    if key in WHITELIST_NO_CONFIRM:
        verdict.allowed = True
        verdict.require_confirmation = False
        verdict.risk_level = "low"
        verdict.reason = "Commande autorisée (liste blanche)."
    elif key in WHITELIST_CONFIRM:
        verdict.allowed = True
        verdict.require_confirmation = True
        verdict.risk_level = "medium"
        verdict.reason = "Commande autorisée après confirmation."
    else:
        verdict.reason = f"Paire (verbe={verb}, cible={target}) non autorisée."
        verdict.risk_level = "high"

    _log_attempt(verb, target, raw_text, verdict)
    return verdict


def _log_attempt(
    verb: Optional[str],
    target: Optional[str],
    raw_text: Optional[str],
    verdict: CommandVerdict,
) -> None:
    """Journalise la tentative de commande (sans données sensibles)."""
    logger.info(
        "command_guard verdict | verb=%s target=%s allowed=%s require_confirmation=%s risk=%s reason=%s",
        verb,
        target,
        verdict.allowed,
        verdict.require_confirmation,
        verdict.risk_level,
        verdict.reason[:80] if verdict.reason else "",
    )
    if raw_text and len(raw_text) < 200:
        logger.debug("command_guard raw_text=%s", raw_text[:100])
