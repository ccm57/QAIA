#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compatibilité monitoring QAIA.
Module conservé pour compatibilité, centralisé via utils.metrics_collector.
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
# ]
# ///

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from utils.metrics_collector import metrics_collector, MetricsCollector

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Wrapper de compatibilité pour le monitoring de performance.

    S'appuie sur MetricsCollector pour centraliser la collecte.
    """

    def __init__(self, base_dir: Optional[Path] = None, max_history: int = 100):
        """
        Initialise le moniteur.

        Args:
            base_dir (Optional[Path]): Répertoire de base (conservé pour compatibilité).
            max_history (int): Taille max d'historique.
        """
        self.base_dir = base_dir or Path(__file__).parent.parent
        self._collector: MetricsCollector = metrics_collector
        # Harmoniser la taille d'historique si nécessaire
        try:
            self._collector.max_history = max_history
        except Exception:
            pass

    def start_monitoring(self, interval: float = 1.0) -> None:
        """Démarre le monitoring système en arrière-plan."""
        self._collector.start_monitoring(interval=interval)

    def stop_monitoring(self) -> None:
        """Arrête le monitoring système."""
        self._collector.stop_monitoring()

    def record_agent_metric(self, agent_name: str, operation: str, duration: float, **kwargs) -> None:
        """
        Enregistre une métrique agent (latence).

        Args:
            agent_name (str): Nom agent
            operation (str): Opération
            duration (float): Durée en secondes
            **kwargs: Ignoré (compatibilité)
        """
        self._collector.record_latency(agent_name, operation, duration)

    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """
        Retourne les stats d'un agent.

        Args:
            agent_name (str): Nom agent

        Returns:
            Dict[str, Any]: Statistiques filtrées
        """
        stats = self._collector.get_stats()
        prefix = f"{agent_name}."
        return {k: v for k, v in stats.items() if k.startswith(prefix)}

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Retourne un snapshot des métriques système.

        Returns:
            Dict[str, Any]: Snapshot CPU/RAM/GPU
        """
        try:
            self._collector.record_resource_usage()
        except Exception:
            pass

        stats = self._collector.get_stats()
        def _last(name: str, default: float = 0.0) -> float:
            return float(stats.get(name, {}).get("last", default))

        return {
            "cpu_percent": _last("system.cpu_percent"),
            "ram_percent": _last("system.ram_percent"),
            "ram_used_gb": _last("system.ram_used_gb"),
            "vram_allocated_gb": _last("system.vram_allocated_gb"),
            "vram_reserved_gb": _last("system.vram_reserved_gb"),
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de performance.

        Returns:
            Dict[str, Any]: Rapport complet
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_metrics(),
            "metrics": self._collector.get_stats(),
            "counters": self._collector.get_counters(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Évalue l'état de santé de base.

        Returns:
            Dict[str, Any]: Statut et alertes
        """
        system = self.get_system_metrics()
        status = "healthy"
        warnings = []

        if system["cpu_percent"] > 90:
            warnings.append(f"CPU élevé: {system['cpu_percent']:.1f}%")
            status = "warning"
        if system["ram_percent"] > 90:
            warnings.append(f"RAM élevée: {system['ram_percent']:.1f}%")
            status = "warning"

        return {
            "status": status,
            "warnings": warnings,
            "critical_issues": [],
        }

    def cleanup(self) -> None:
        """Nettoie les ressources du moniteur."""
        try:
            self.stop_monitoring()
            self._collector.clear()
        except Exception as e:
            logger.error(f"Erreur nettoyage moniteur: {e}")


# Instance globale (compatibilité)
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Retourne l'instance globale de PerformanceMonitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def start_performance_monitoring() -> PerformanceMonitor:
    """Démarre le monitoring de performance global."""
    monitor = get_performance_monitor()
    monitor.start_monitoring()
    return monitor


def stop_performance_monitoring() -> None:
    """Arrête le monitoring de performance global."""
    global _performance_monitor
    if _performance_monitor:
        _performance_monitor.stop_monitoring()

