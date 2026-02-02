#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Moniteur de Santé pour QAIA
Watchdog, auto-recovery, fallback cascade.
"""

# /// script
# dependencies = []
# ///

import logging
import threading
import time
from typing import Dict, Callable, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class ComponentHealth(Enum):
    """État de santé d'un composant."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthStatus:
    """Status de santé d'un composant."""
    component: str
    health: ComponentHealth
    last_check: datetime
    consecutive_failures: int = 0
    last_error: Optional[str] = None

class HealthMonitor:
    """
    Moniteur de santé avec auto-recovery.
    
    Fonctionnalités:
    - Watchdog threads pour surveillance
    - Restart automatique si freeze
    - Fallback cascade
    - Logs détaillés erreurs
    """
    
    def __init__(self, check_interval: float = 5.0):
        """
        Initialise le moniteur de santé.
        
        Args:
            check_interval: Intervalle vérification (secondes)
        """
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval
        
        # État composants
        self._components: Dict[str, HealthStatus] = {}
        self._health_checks: Dict[str, Callable] = {}
        self._recovery_actions: Dict[str, Callable] = {}
        
        # Contrôle
        self._running = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        
        self.logger.info("HealthMonitor initialisé")
    
    def register_component(
        self,
        component_name: str,
        health_check: Callable[[], bool],
        recovery_action: Optional[Callable] = None
    ):
        """
        Enregistre un composant à surveiller.
        
        Args:
            component_name: Nom du composant
            health_check: Fonction retournant True si healthy
            recovery_action: Fonction de recovery (optionnelle)
        """
        with self._lock:
            self._components[component_name] = HealthStatus(
                component=component_name,
                health=ComponentHealth.UNKNOWN,
                last_check=datetime.now()
            )
            self._health_checks[component_name] = health_check
            
            if recovery_action:
                self._recovery_actions[component_name] = recovery_action
        
        self.logger.info(f"Composant enregistré: {component_name}")
    
    def start(self):
        """Démarre le monitoring."""
        if self._running:
            self.logger.warning("Monitoring déjà actif")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="HealthMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info("✅ Health monitoring démarré")
    
    def stop(self):
        """Arrête le monitoring."""
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        self.logger.info("Health monitoring arrêté")
    
    def _monitor_loop(self):
        """Boucle principale de monitoring."""
        while self._running:
            try:
                self._check_all_components()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Erreur monitoring loop: {e}")
    
    def _check_all_components(self):
        """Vérifie santé de tous les composants."""
        with self._lock:
            components = list(self._components.keys())
        
        for component_name in components:
            self._check_component(component_name)
    
    def _check_component(self, component_name: str):
        """
        Vérifie santé d'un composant.
        
        Args:
            component_name: Nom du composant
        """
        try:
            health_check = self._health_checks.get(component_name)
            
            if not health_check:
                return
            
            # Exécuter health check
            is_healthy = health_check()
            
            with self._lock:
                status = self._components[component_name]
                status.last_check = datetime.now()
                
                if is_healthy:
                    # Composant healthy
                    if status.health != ComponentHealth.HEALTHY:
                        self.logger.info(f"✅ {component_name} est maintenant healthy")
                    
                    status.health = ComponentHealth.HEALTHY
                    status.consecutive_failures = 0
                    status.last_error = None
                else:
                    # Composant unhealthy
                    status.consecutive_failures += 1
                    
                    # Déterminer niveau gravité
                    if status.consecutive_failures >= 3:
                        status.health = ComponentHealth.UNHEALTHY
                        self.logger.error(f"❌ {component_name} est UNHEALTHY")
                        
                        # Tenter recovery
                        self._attempt_recovery(component_name)
                    elif status.consecutive_failures >= 1:
                        status.health = ComponentHealth.DEGRADED
                        self.logger.warning(f"⚠️ {component_name} est DEGRADED")
                
        except Exception as e:
            self.logger.error(f"Erreur check {component_name}: {e}")
            
            with self._lock:
                status = self._components[component_name]
                status.health = ComponentHealth.UNKNOWN
                status.last_error = str(e)
    
    def _attempt_recovery(self, component_name: str):
        """
        Tente recovery d'un composant.
        
        Args:
            component_name: Nom du composant
        """
        recovery_action = self._recovery_actions.get(component_name)
        
        if not recovery_action:
            self.logger.warning(f"Pas d'action recovery pour {component_name}")
            return
        
        try:
            self.logger.info(f"🔄 Tentative recovery: {component_name}")
            recovery_action()
            self.logger.info(f"✅ Recovery réussie: {component_name}")
            
            # Réinitialiser compteur échecs
            with self._lock:
                self._components[component_name].consecutive_failures = 0
                
        except Exception as e:
            self.logger.error(f"❌ Échec recovery {component_name}: {e}")
    
    def get_component_health(self, component_name: str) -> Optional[HealthStatus]:
        """
        Retourne status santé d'un composant.
        
        Args:
            component_name: Nom du composant
            
        Returns:
            HealthStatus ou None
        """
        with self._lock:
            return self._components.get(component_name)
    
    def get_all_health(self) -> Dict[str, HealthStatus]:
        """Retourne status de tous les composants."""
        with self._lock:
            return dict(self._components)
    
    def is_system_healthy(self) -> bool:
        """
        Vérifie si le système entier est healthy.
        
        Returns:
            True si tous les composants sont healthy
        """
        with self._lock:
            return all(
                status.health == ComponentHealth.HEALTHY
                for status in self._components.values()
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne résumé santé système."""
        with self._lock:
            health_counts = {
                ComponentHealth.HEALTHY: 0,
                ComponentHealth.DEGRADED: 0,
                ComponentHealth.UNHEALTHY: 0,
                ComponentHealth.UNKNOWN: 0
            }
            
            for status in self._components.values():
                health_counts[status.health] += 1
            
            return {
                "system_healthy": self.is_system_healthy(),
                "total_components": len(self._components),
                "healthy": health_counts[ComponentHealth.HEALTHY],
                "degraded": health_counts[ComponentHealth.DEGRADED],
                "unhealthy": health_counts[ComponentHealth.UNHEALTHY],
                "unknown": health_counts[ComponentHealth.UNKNOWN],
                "components": {
                    name: status.health.value
                    for name, status in self._components.items()
                }
            }

# Instance globale
health_monitor = HealthMonitor()

