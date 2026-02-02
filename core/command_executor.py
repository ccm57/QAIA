#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Exécuteur de commandes système pour QAIA.
Exécute uniquement les commandes validées par command_guard.
Mapping (verbe, cible) vers actions internes ou callbacks ; pas de shell.
"""

# /// script
# dependencies = []
# ///

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecuteResult:
    """Résultat d'exécution d'une commande."""
    success: bool
    message: str
    error: Optional[str] = None


class CommandExecutor:
    """
    Exécuteur de commandes contrôlé.

    Utilise un registre d'actions (callbacks ou messages) pour (verbe, cible).
    Aucun subprocess avec shell ; seules des actions enregistrées sont exécutées.
    """

    def __init__(self) -> None:
        """Initialise l'exécuteur avec un registre d'actions vide."""
        self.logger = logging.getLogger(__name__)
        # Clé (verbe, cible) -> Callable[[], str] ou str (message de confirmation)
        self._actions: Dict[tuple, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Enregistre les actions par défaut (messages uniquement si pas de callback)."""
        # Actions sans callback : message uniquement (à remplacer par callback depuis qaia_core)
        defaults = [
            (("arrete", "enregistrement"), "J'ai arrêté l'enregistrement."),
            (("arrete", "micro"), "Micro désactivé."),
            (("lance", "lecture"), "Lecture activée."),
            (("desactive", "micro"), "Micro désactivé."),
            (("active", "micro"), "Micro activé."),
            (("ferme", "application"), "Application fermée."),
            (("lance", "navigateur"), "Navigateur ouvert."),
            (("ouvre", "navigateur"), "Navigateur ouvert."),
            (("ferme", "interface"), "Interface fermée."),
            (("redemarre", "assistant"), "Redémarrage de l'assistant demandé."),
        ]
        for key, msg in defaults:
            if key not in self._actions:
                self._actions[key] = msg

    def register_action(
        self,
        verb: str,
        target: str,
        action: Callable[[], str] | str,
    ) -> None:
        """
        Enregistre une action pour (verbe, cible).

        Args:
            verb: Verbe normalisé (ex. "arrete").
            target: Cible normalisée (ex. "enregistrement").
            action: Callable sans argument retournant un message, ou str (message fixe).
        """
        key = (verb.strip().lower(), target.strip().lower())
        self._actions[key] = action
        self.logger.debug("Commande enregistrée: %s -> %s", key, "callback" if callable(action) else "message")

    def execute_command(
        self,
        command_verb: str,
        command_target: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecuteResult:
        """
        Exécute une commande validée (verbe + cible).

        Args:
            command_verb: Verbe normalisé.
            command_target: Cible normalisée.
            context: Contexte optionnel (ignoré si l'action n'en a pas besoin).

        Returns:
            ExecuteResult avec success, message, error.
        """
        context = context or {}
        verb = (command_verb or "").strip().lower()
        target = (command_target or "").strip().lower()
        if not verb or not target:
            return ExecuteResult(
                success=False,
                message="",
                error="Verbe ou cible manquant.",
            )
        key = (verb, target)
        action = self._actions.get(key)
        if action is None:
            self.logger.warning("Aucune action enregistrée pour %s", key)
            return ExecuteResult(
                success=False,
                message="Cette commande n'est pas disponible.",
                error="action_not_registered",
            )
        try:
            if callable(action):
                message = action()
            else:
                message = str(action)
            self.logger.info("Commande exécutée: %s -> %s", key, message[:50])
            return ExecuteResult(success=True, message=message)
        except Exception as e:
            self.logger.exception("Erreur exécution commande %s: %s", key, e)
            return ExecuteResult(
                success=False,
                message="Une erreur s'est produite.",
                error=str(e),
            )


# Instance globale (optionnelle ; peut être créée par qaia_core et injectée)
_command_executor: Optional[CommandExecutor] = None


def get_command_executor() -> CommandExecutor:
    """Retourne l'instance globale de CommandExecutor (créée à la demande)."""
    global _command_executor
    if _command_executor is None:
        _command_executor = CommandExecutor()
    return _command_executor
