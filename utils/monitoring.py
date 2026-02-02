#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Monitoring unifié (centralisé)
Point d'entrée unique pour les métriques et le suivi des agents.
"""

# /// script
# dependencies = [
# ]
# ///

from typing import Dict, Any
from utils.metrics_collector import metrics_collector


def start_monitoring(interval: float = 1.0) -> None:
    """
    Démarre le monitoring système via le collecteur centralisé.

    Args:
        interval (float): Intervalle de collecte (secondes)
    """
    metrics_collector.start_monitoring(interval=interval)
    return None


def stop_monitoring() -> None:
    """Arrête le monitoring système."""
    metrics_collector.stop_monitoring()
    return None


def performance_monitor() -> Any:
    """
    Retourne le collecteur de métriques centralisé.

    Returns:
        Any: Instance globale de MetricsCollector
    """
    return metrics_collector


def record_timing(component: str, metric: str, value: float) -> None:
    """
    Enregistre une latence au format centralisé.

    Args:
        component (str): Nom du composant (ex: "llm", "asr")
        metric (str): Nom de la métrique (ex: "response", "inference")
        value (float): Valeur de latence en secondes
    """
    try:
        metrics_collector.record_latency(component, metric, value)
    except Exception:
        # Ne jamais casser un flux de traitement pour une métrique
        pass


def get_timings() -> Dict[str, Dict[str, Any]]:
    """
    Retourne un aperçu des métriques enregistrées.

    Returns:
        Dict[str, Dict[str, Any]]: Statistiques par métrique
    """
    try:
        return metrics_collector.get_stats()
    except Exception:
        return {}


def update_active_agents(agent_names):
    """
    Met à jour les états des agents et émet des événements agent.state_change.
    
    Args:
        agent_names: Liste des noms d'agents actifs
    """
    try:
        from interface.events.event_bus import event_bus
        import time
        
        # Mapping des noms d'agents internes vers les noms UI
        agent_mapping = {
            'llm': 'LLM',
            'voice': 'STT',
            'speech': 'TTS',
            'rag': 'RAG',
        }
        
        # Agents connus dans l'UI
        known_agents = ['LLM', 'STT', 'TTS', 'RAG']
        
        # Émettre événement pour chaque agent connu
        for ui_name in known_agents:
            # Vérifier si l'agent est actif
            is_active = False
            activity_percentage = 0.0
            status = 'IDLE'
            details = ''
            
            # Chercher dans la liste des agents actifs
            for internal_name, mapped_name in agent_mapping.items():
                if mapped_name == ui_name and internal_name in agent_names:
                    is_active = True
                    activity_percentage = 50.0  # Par défaut, activité moyenne si actif
                    status = 'ACTIF'
                    details = f'Agent {ui_name} initialisé et disponible'
                    break
            
            # Émettre événement état agent
            event_bus.emit('agent.state_change', {
                'name': ui_name,
                'status': status,
                'activity_percentage': activity_percentage,
                'details': details,
                'last_update': time.time(),
                'is_active': is_active
            })
            
    except Exception as e:
        # Ne pas faire échouer si Event Bus n'est pas disponible
        import logging
        logging.getLogger(__name__).debug(f"Impossible d'émettre événements agents: {e}")
