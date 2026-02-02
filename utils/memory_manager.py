#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Module unifié pour la gestion de la mémoire (restauré)"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
#   "torch>=2.0.0",
# ]
# ///

import gc
import logging
import time
from typing import Optional, Dict

import psutil
import torch


class MemoryManager:
    """Gestionnaire de mémoire simple et fiable pour QAIA"""

    def __init__(self, memory_limit: Optional[int] = None) -> None:
        self.logger = logging.getLogger("MemoryManager")
        self.memory_limit_mb = memory_limit or (psutil.virtual_memory().total // (1024 * 1024))
        self.warning_threshold = 0.90  # 90%
        self.critical_threshold = 0.95  # 95%
        self._last_cleanup = 0.0
        self._cleanup_cooldown = 20.0  # secondes

    def should_cleanup(self) -> bool:
        now = time.time()
        if now - self._last_cleanup < self._cleanup_cooldown:
            return False
        mem = psutil.virtual_memory()
        return mem.percent >= self.warning_threshold * 100

    def check_memory_usage(self) -> bool:
        try:
            mem = psutil.virtual_memory()
            if mem.percent >= self.critical_threshold * 100:
                self.logger.error(f"Mémoire critique: {mem.percent:.1f}% utilisée")
                return False
            if mem.percent >= self.warning_threshold * 100:
                self.logger.warning(f"Mémoire élevée: {mem.percent:.1f}% utilisée")
            return True
        except Exception as e:
            self.logger.error(f"Erreur check_memory_usage: {e}")
            return True

    def optimize_memory(self) -> None:
        try:
            if not self.should_cleanup():
                return
            before = psutil.virtual_memory().percent

            # Collecte GC
            gc.collect()

            # Vider le cache CUDA si dispo
            if torch.cuda.is_available():
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

            after = psutil.virtual_memory().percent
            self._last_cleanup = time.time()
            self.logger.info(f"Mémoire optimisée: {before:.1f}% -> {after:.1f}%")
        except Exception as e:
            self.logger.error(f"Erreur optimize_memory: {e}")

    # Utilitaire simple
    def get_memory_stats(self) -> Dict[str, float]:
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "percent": mem.percent,
        }


