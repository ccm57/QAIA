#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Fenêtre Logs Temps Réel
Affiche tous les logs système avec filtrage
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
from interface.components.log_viewer import LogViewer
from interface.events.event_bus import event_bus
from interface.models.events import LogEntry
import logging

logger = logging.getLogger(__name__)


class LogsWindow(ctk.CTkToplevel):
    """
    Fenêtre dédiée à l'affichage des logs temps réel.
    Abonnée aux événements 'log.message' via l'Event Bus.
    """
    
    def __init__(self, master):
        """
        Initialise la fenêtre logs.
        
        Args:
            master: Widget parent
        """
        super().__init__(master)
        
        # Configuration fenêtre
        self.title("QAIA - Logs Temps Réel")
        self.geometry("800x600")
        
        # Créer UI
        self._build_ui()
        
        # S'abonner aux logs
        event_bus.subscribe('log.message', self._on_log_message)
        
        # Handler fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Fenêtre Logs ouverte")
    
    def _build_ui(self):
        """Construit l'interface."""
        # Titre
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="📋 Logs Système Temps Réel",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)
        
        # Log Viewer component
        self.log_viewer = LogViewer(self)
        self.log_viewer.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _on_log_message(self, event_data: dict):
        """
        Callback événement log.message.
        
        Args:
            event_data: Données log (conforme à LogEntry)
        """
        try:
            # Extraire données
            level = event_data.get('level', 'INFO')
            message = event_data.get('message', '')
            source = event_data.get('source', '')
            timestamp = event_data.get('timestamp', 0)
            
            # Formatter timestamp
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            timestamp_str = dt.strftime('%H:%M:%S')
            
            # Ajouter au log viewer
            self.log_viewer.add_log(level, message, source, timestamp_str)
            
        except Exception as e:
            logger.error(f"Erreur ajout log: {e}")
    
    def _on_close(self):
        """Handler fermeture fenêtre."""
        # Se désabonner des événements
        event_bus.unsubscribe('log.message', self._on_log_message)
        
        logger.info("Fenêtre Logs fermée")
        self.destroy()

