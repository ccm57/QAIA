#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Mapper vocal → actions UI (règles + templates)."""

# /// script
# dependencies = []
# ///

import logging
import re
from typing import List, Optional

from ui_control.models import ActionStep


class VocalActionMapper:
    """Transforme une instruction vocale en étapes d'action."""

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialise le mapper.

        Args:
            confidence_threshold (float): Seuil de confiance minimal
        """
        self.logger = logging.getLogger(__name__)
        self.confidence_threshold = confidence_threshold

    def can_handle(self, text: str) -> bool:
        """Détermine si le texte ressemble à une commande UI."""
        patterns = [
            r"\bouvre\b",
            r"\baller sur\b",
            r"\bclique\b",
            r"\bclique sur\b",
            r"\btape\b",
            r"\bécris\b",
            r"\bscrolle\b",
            r"\bdescends\b",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def map_to_steps(self, text: str) -> List[ActionStep]:
        """
        Convertit une instruction en étapes d'action.

        Args:
            text (str): Instruction utilisateur

        Returns:
            List[ActionStep]: Liste d'étapes d'action
        """
        text_lower = text.lower().strip()
        steps: List[ActionStep] = []

        match_url = re.search(r"(https?://\S+)", text_lower)
        if "ouvre" in text_lower or "aller sur" in text_lower:
            if match_url:
                steps.append(ActionStep(action_type="open_url", text=match_url.group(1)))
                return steps

        match_click = re.search(r"clique sur\s+(.+)", text_lower)
        if match_click:
            steps.append(ActionStep(action_type="click", selector=match_click.group(1).strip()))
            return steps

        match_type = re.search(r"(tape|écris)\s+(.+)", text_lower)
        if match_type:
            steps.append(ActionStep(action_type="type", text=match_type.group(2).strip()))
            return steps

        if "scrolle" in text_lower or "descends" in text_lower:
            steps.append(ActionStep(action_type="scroll", text="down"))
            return steps

        return steps
