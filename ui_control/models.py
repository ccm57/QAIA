#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Modèles de données pour UI-control."""

# /// script
# dependencies = []
# ///

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ScreenMetadata:
    """Métadonnées associées à une capture d'écran."""

    timestamp: float
    url: Optional[str] = None
    window_title: Optional[str] = None
    viewport: Optional[Tuple[int, int]] = None
    source: str = "local"


@dataclass
class ScreenElement:
    """Élément interactif détecté sur l'écran."""

    element_id: str
    role: str
    label: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenSchema:
    """Schéma d'écran structuré (DOM-like)."""

    schema_id: str
    screenshot_path: str
    metadata: ScreenMetadata
    elements: List[ScreenElement] = field(default_factory=list)


@dataclass
class ActionStep:
    """Étape d'action pour l'exécution UI."""

    action_type: str
    selector: Optional[str] = None
    coordinates: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    wait_for: Optional[str] = None
    retries: int = 0
    timeout_s: float = 10.0


@dataclass
class ActionPlan:
    """Plan d'actions séquencées."""

    plan_id: str
    steps: List[ActionStep]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    requires_confirmation: bool = True


@dataclass
class ActionResult:
    """Résultat d'exécution d'un plan d'action."""

    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Résultat global du pipeline UI-control."""

    status: str
    action_plan: Optional[ActionPlan] = None
    action_result: Optional[ActionResult] = None
    schema_id: Optional[str] = None
    error: Optional[str] = None
    response: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
