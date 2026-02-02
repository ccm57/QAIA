#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Event Bus Central pour QAIA
Architecture event-driven thread-safe pour communication inter-composants
"""

# /// script
# dependencies = []
# ///

import threading
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any
import queue
import time

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event Bus central thread-safe utilisant le pattern Observer.
    Permet la communication asynchrone entre composants sans couplage fort.
    """
    
    def __init__(self):
        """Initialise l'Event Bus."""
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._event_queue = queue.Queue(maxsize=1000)
        self._running = False
        self._worker_thread = None
        
        logger.info("Event Bus initialisé")
    
    def start(self):
        """Démarre le thread de traitement des événements."""
        if self._running:
            logger.warning("Event Bus déjà démarré")
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_events,
            name="EventBusWorker",
            daemon=True
        )
        self._worker_thread.start()
        logger.info("Event Bus worker thread démarré")
    
    def stop(self):
        """Arrête le thread de traitement des événements."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        logger.info("Event Bus arrêté")
    
    def emit(self, event_type: str, data: Dict[str, Any] = None):
        """
        Émet un événement de manière thread-safe.
        
        Args:
            event_type: Type d'événement (ex: 'llm.token', 'metrics.update')
            data: Données associées à l'événement
        """
        if data is None:
            data = {}
        
        try:
            # Ajouter timestamp si non présent
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Mettre en queue pour traitement asynchrone
            self._event_queue.put_nowait({
                'type': event_type,
                'data': data
            })
            
            logger.debug(f"Événement émis: {event_type}")
            
        except queue.Full:
            logger.error(f"Queue événements pleine, événement {event_type} perdu")
    
    def subscribe(self, event_type: str, callback: Callable):
        """
        Abonne un callback à un type d'événement.
        
        Args:
            event_type: Type d'événement à écouter
            callback: Fonction appelée lors de l'événement
                     Signature: callback(event_data: dict)
        """
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Abonnement à {event_type}: {callback.__name__}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """
        Désabonne un callback d'un type d'événement.
        
        Args:
            event_type: Type d'événement
            callback: Fonction à désabonner
        """
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Désabonnement de {event_type}: {callback.__name__}")
    
    def _process_events(self):
        """Thread worker qui traite les événements de la queue."""
        logger.info("Event Bus worker en cours d'exécution")
        
        while self._running:
            try:
                # Récupérer événement avec timeout
                event = self._event_queue.get(timeout=0.1)
                
                event_type = event['type']
                event_data = event['data']
                
                # Récupérer les callbacks thread-safe
                with self._lock:
                    callbacks = self._subscribers[event_type].copy()
                
                # Exécuter tous les callbacks abonnés
                for callback in callbacks:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logger.error(
                            f"Erreur callback {callback.__name__} "
                            f"pour événement {event_type}: {e}"
                        )
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erreur traitement événement: {e}")
    
    def get_subscriber_count(self, event_type: str = None) -> int:
        """
        Retourne le nombre d'abonnés.
        
        Args:
            event_type: Type d'événement spécifique, ou None pour tous
            
        Returns:
            Nombre d'abonnés
        """
        with self._lock:
            if event_type:
                return len(self._subscribers[event_type])
            else:
                return sum(len(callbacks) for callbacks in self._subscribers.values())


# Instance singleton globale
event_bus = EventBus()

# Démarrer automatiquement
event_bus.start()

