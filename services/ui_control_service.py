#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Service API UI-control (FastAPI)."""

# /// script
# dependencies = [
#   "fastapi>=0.104.1",
#   "uvicorn[standard]>=0.24.0"
# ]
# ///

import os
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from config.system_config import UI_CONTROL_CONFIG
from ui_control.pipeline import UIControlPipeline


class UICommandRequest(BaseModel):
    """Requête de commande UI."""

    text: str
    require_confirmation: bool = True


def _build_config() -> Dict[str, Any]:
    """Construit la configuration UI-control avec overrides d'environnement."""
    cfg = dict(UI_CONTROL_CONFIG)
    enabled = os.environ.get("QAIA_UI_CONTROL_ENABLED")
    if enabled is not None:
        cfg["enabled"] = enabled.strip().lower() in {"1", "true", "yes", "on"}
    dry_run = os.environ.get("QAIA_UI_CONTROL_DRY_RUN")
    if dry_run is not None:
        cfg["dry_run"] = dry_run.strip().lower() in {"1", "true", "yes", "on"}
    return cfg


app = FastAPI(title="QAIA UI-control", version="1.0.0")
logger = logging.getLogger("ui_control_service")

BASE_DIR = Path(__file__).parent.parent
PIPELINE = UIControlPipeline(base_dir=BASE_DIR, config=_build_config())


@app.get("/health")
def health() -> Dict[str, Any]:
    """Healthcheck service UI-control."""
    return {
        "status": "ok",
        "enabled": PIPELINE.enabled,
        "dry_run": PIPELINE.action_executor.dry_run,
    }


@app.post("/ui/command")
def ui_command(payload: UICommandRequest) -> Dict[str, Any]:
    """Exécute une commande UI."""
    result = PIPELINE.handle_command(
        text=payload.text,
        require_confirmation=payload.require_confirmation
    )
    return result.__dict__
