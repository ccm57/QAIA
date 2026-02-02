#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Tests basiques du pipeline UI-control."""

# /// script
# dependencies = [
#   "pytest>=7.0.0"
# ]
# ///

from pathlib import Path

from ui_control.pipeline import UIControlPipeline


def test_ui_control_disabled(tmp_path: Path):
    """Vérifie le comportement lorsque UI-control est désactivé."""
    pipeline = UIControlPipeline(base_dir=tmp_path, config={"enabled": False, "dry_run": True})
    result = pipeline.handle_command("ouvre https://example.com", require_confirmation=True)
    assert result.status == "disabled"
    assert "désactivé" in (result.response or "").lower()


def test_ui_control_confirmation_required(tmp_path: Path):
    """Vérifie qu'une confirmation est demandée avant exécution."""
    pipeline = UIControlPipeline(base_dir=tmp_path, config={"enabled": True, "dry_run": True})
    result = pipeline.handle_command("ouvre https://example.com", require_confirmation=True)
    assert result.status == "confirmation_required"
    assert result.action_plan is not None
    assert result.action_plan.steps
