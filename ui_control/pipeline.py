#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Pipeline UI-control: capture → parse → plan → exécution."""

# /// script
# dependencies = []
# ///

from pathlib import Path
import logging
from typing import Optional

from ui_control.models import PipelineResult
from ui_control.screenshot_service import ScreenshotService
from ui_control.ui_parser import UIParser
from ui_control.schema_store import ScreenSchemaStore
from ui_control.vocal_action_mapper import VocalActionMapper
from ui_control.action_planner import ActionPlanner
from ui_control.action_executor import ActionExecutor
from ui_control.safety_engine import SafetyPolicyEngine
from ui_control.monitoring_replay import MonitoringReplay


class UIControlPipeline:
    """Orchestrateur UI-control."""

    def __init__(self, base_dir: Path, config: dict):
        """
        Initialise le pipeline UI-control.

        Args:
            base_dir (Path): Répertoire racine QAIA
            config (dict): Configuration UI-control
        """
        self.base_dir = base_dir
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enabled = bool(config.get("enabled", False))

        self.screenshot_service = ScreenshotService(base_dir=base_dir, enabled=self.enabled)
        self.ui_parser = UIParser()
        self.schema_store = ScreenSchemaStore(base_dir=base_dir)
        self.action_mapper = VocalActionMapper(
            confidence_threshold=float(config.get("confidence_threshold", 0.6))
        )
        self.action_planner = ActionPlanner()
        self.action_executor = ActionExecutor(dry_run=bool(config.get("dry_run", True)))
        self.safety_engine = SafetyPolicyEngine(
            allowlist=config.get("allowlist", []),
            denylist=config.get("denylist", ["download", "upload", "payment"])
        )
        self.monitoring = MonitoringReplay(base_dir=base_dir)

    def can_handle(self, text: str) -> bool:
        """Détermine si le pipeline doit traiter la commande."""
        return self.action_mapper.can_handle(text)

    def handle_command(self, text: str, require_confirmation: bool = True) -> PipelineResult:
        """
        Traite une commande UI de bout en bout.

        Args:
            text (str): Instruction utilisateur
            require_confirmation (bool): Confirmation avant exécution

        Returns:
            PipelineResult: Résultat du pipeline
        """
        if not self.enabled:
            return PipelineResult(
                status="disabled",
                error="UI-control désactivé",
                response="UI-control désactivé. Activez la configuration pour exécuter des actions."
            )

        steps = self.action_mapper.map_to_steps(text)
        if not steps:
            return PipelineResult(
                status="no_action",
                response="Aucune action UI détectée dans la commande."
            )

        plan = self.action_planner.plan_from_steps(steps, requires_confirmation=require_confirmation)
        allowed, reason = self.safety_engine.validate(plan)
        if not allowed:
            return PipelineResult(
                status="blocked",
                error=reason,
                response=f"Action bloquée par la politique de sécurité: {reason}"
            )

        if plan.requires_confirmation:
            return PipelineResult(
                status="confirmation_required",
                action_plan=plan,
                response="Confirmation requise avant exécution des actions UI."
            )

        screenshot_path, metadata = self.screenshot_service.capture_screen()
        schema = self.ui_parser.parse(screenshot_path, metadata)
        self.schema_store.save(schema)

        result = self.action_executor.execute(plan)
        self.monitoring.log_event(
            "ui_action",
            {"plan_id": plan.plan_id, "success": result.success, "details": result.details, "error": result.error}
        )

        return PipelineResult(
            status="executed" if result.success else "failed",
            action_plan=plan,
            action_result=result,
            schema_id=schema.schema_id,
            response="Action UI exécutée." if result.success else "Échec d'exécution UI.",
        )
