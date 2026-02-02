#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Moteur de sécurité et politiques d'exécution UI."""

# /// script
# dependencies = []
# ///

import logging
from typing import Dict, List, Tuple

from ui_control.models import ActionPlan


class SafetyPolicyEngine:
    """Vérifie les plans d'action selon allowlist/denylist."""

    def __init__(self, allowlist: List[str], denylist: List[str]):
        """
        Initialise le moteur de sécurité.

        Args:
            allowlist (List[str]): Actions autorisées
            denylist (List[str]): Actions interdites
        """
        self.allowlist = allowlist
        self.denylist = denylist
        self.logger = logging.getLogger(__name__)

    def validate(self, plan: ActionPlan) -> Tuple[bool, str]:
        """
        Valide un plan d'action.

        Args:
            plan (ActionPlan): Plan d'action

        Returns:
            Tuple[bool, str]: (autorisé, raison)
        """
        for step in plan.steps:
            if step.action_type in self.denylist:
                return False, f"Action interdite: {step.action_type}"
            if self.allowlist and step.action_type not in self.allowlist:
                return False, f"Action non autorisée: {step.action_type}"
        return True, "OK"
