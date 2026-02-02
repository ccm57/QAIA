#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Exécuteur d'actions UI (sandbox, mode dégradé)."""

# /// script
# dependencies = []
# ///

import logging
from typing import List

from ui_control.models import ActionPlan, ActionResult


class ActionExecutor:
    """Exécute un plan d'action en sandbox (placeholder)."""

    def __init__(self, dry_run: bool = True):
        """
        Initialise l'exécuteur.

        Args:
            dry_run (bool): Mode simulation sans exécution réelle
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def execute(self, plan: ActionPlan) -> ActionResult:
        """
        Exécute un plan d'action.

        Args:
            plan (ActionPlan): Plan d'action

        Returns:
            ActionResult: Résultat d'exécution
        """
        if self.dry_run:
            self.logger.info("ActionExecutor: exécution simulée (dry_run)")
            return ActionResult(success=True, details={"steps": len(plan.steps), "mode": "dry_run"})

        # Exécution réelle non implémentée
        self.logger.warning("ActionExecutor: exécution réelle non implémentée")
        return ActionResult(success=False, error="Exécution UI non configurée")
