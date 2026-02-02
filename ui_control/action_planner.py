#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Planificateur d'actions UI (templates + règles)."""

# /// script
# dependencies = []
# ///

import logging
import time
from typing import List, Optional

from ui_control.models import ActionPlan, ActionStep, ScreenSchema


class ActionPlanner:
    """Construit un plan d'action à partir d'un schéma et d'une intention."""

    def __init__(self):
        """Initialise le planificateur."""
        self.logger = logging.getLogger(__name__)

    def plan_from_steps(self, steps: List[ActionStep], requires_confirmation: bool = True) -> ActionPlan:
        """
        Construit un plan à partir d'étapes pré-définies.

        Args:
            steps (List[ActionStep]): Étapes d'action
            requires_confirmation (bool): Confirmation requise

        Returns:
            ActionPlan: Plan structuré
        """
        plan_id = f"plan_{int(time.time() * 1000)}"
        return ActionPlan(plan_id=plan_id, steps=steps, requires_confirmation=requires_confirmation)

    def plan(self, schema: ScreenSchema, intent_payload: Optional[dict] = None) -> ActionPlan:
        """
        Produit un plan d'action à partir d'un schéma UI.

        Args:
            schema (ScreenSchema): Schéma UI
            intent_payload (Optional[dict]): Données issues du mapper vocal

        Returns:
            ActionPlan: Plan d'action (mode dégradé)
        """
        self.logger.info("ActionPlanner: plan en mode dégradé (aucune action)")
        return self.plan_from_steps([], requires_confirmation=False)
