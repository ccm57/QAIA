#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Fenêtre États Agents
Affiche jauges circulaires pour chaque agent + détails
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
from interface.components.agent_gauge import AgentGauge
from interface.events.event_bus import event_bus
from interface.models.events import AgentState
import logging

logger = logging.getLogger(__name__)


class AgentsWindow(ctk.CTkToplevel):
    """
    Fenêtre dédiée à la surveillance des agents.
    Affiche grille de jauges circulaires + détails agent sélectionné.
    """
    
    # Liste des agents à surveiller
    AGENTS = ['LLM', 'STT', 'TTS', 'RAG']
    
    def __init__(self, master):
        """
        Initialise la fenêtre agents.
        
        Args:
            master: Widget parent
        """
        super().__init__(master)
        
        # Configuration fenêtre
        self.title("QAIA - États Agents")
        self.geometry("700x600")
        
        # État
        self._gauges = {}
        self._selected_agent = None
        self._agent_states = {agent: None for agent in self.AGENTS}
        
        # Créer UI
        self._build_ui()
        
        # S'abonner aux changements d'état
        event_bus.subscribe('agent.state_change', self._on_agent_state_change)
        
        # Handler fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Fenêtre États Agents ouverte")
    
    def _build_ui(self):
        """Construit l'interface."""
        # Titre
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="🤖 États des Agents QAIA",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)
        
        # Grille de jauges
        gauges_frame = ctk.CTkFrame(self, height=180)
        gauges_frame.pack(fill="x", padx=10, pady=10)
        gauges_frame.pack_propagate(False)
        
        # Créer jauges horizontalement
        for agent_name in self.AGENTS:
            gauge = AgentGauge(gauges_frame, agent_name=agent_name, size=120)
            gauge.pack(side="left", padx=10, pady=10)
            
            # Bind click pour sélection
            gauge.canvas.bind("<Button-1>", lambda e, a=agent_name: self._select_agent(a))
            
            self._gauges[agent_name] = gauge
        
        # Panneau détails agent sélectionné
        details_frame = ctk.CTkFrame(self)
        details_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            details_frame,
            text="Détails Agent",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Nom agent
        self.details_name_label = ctk.CTkLabel(
            details_frame,
            text="Agent sélectionné: Aucun",
            font=("Arial", 12)
        )
        self.details_name_label.pack(anchor="w", padx=10, pady=5)
        
        # Status
        self.details_status_label = ctk.CTkLabel(
            details_frame,
            text="Status: -",
            font=("Arial", 12)
        )
        self.details_status_label.pack(anchor="w", padx=10, pady=5)
        
        # Métriques
        self.details_metrics_label = ctk.CTkLabel(
            details_frame,
            text="Métriques: -",
            font=("Arial", 12)
        )
        self.details_metrics_label.pack(anchor="w", padx=10, pady=5)
        
        # Détails additionnels
        ctk.CTkLabel(
            details_frame,
            text="Détails:",
            font=("Arial", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.details_textbox = ctk.CTkTextbox(
            details_frame,
            height=150,
            state="disabled"
        )
        self.details_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Boutons actions
        button_frame = ctk.CTkFrame(details_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.restart_button = ctk.CTkButton(
            button_frame,
            text="🔄 Redémarrer Agent",
            command=self._restart_agent,
            state="disabled"
        )
        self.restart_button.pack(side="left", padx=5)
        
        self.logs_button = ctk.CTkButton(
            button_frame,
            text="📋 Voir Logs",
            command=self._view_logs,
            state="disabled"
        )
        self.logs_button.pack(side="left", padx=5)
    
    def _on_agent_state_change(self, event_data: dict):
        """
        Callback événement agent.state_change.
        
        Args:
            event_data: Données état agent (conforme à AgentState)
        """
        try:
            # Extraire données
            name = event_data.get('name', '')
            status = event_data.get('status', 'IDLE')
            activity_percentage = event_data.get('activity_percentage', 0.0)
            details = event_data.get('details', '')
            
            # Log pour debug
            logger.debug(f"AgentsWindow: Événement reçu pour {name}: status={status}, activity={activity_percentage}%")
            
            # Vérifier si agent connu
            if name not in self.AGENTS:
                logger.debug(f"AgentsWindow: Agent {name} ignoré (non dans AGENTS)")
                return
            
            # Stocker état
            self._agent_states[name] = event_data
            
            # Mettre à jour jauge
            gauge = self._gauges.get(name)
            if gauge:
                logger.debug(f"AgentsWindow: Mise à jour jauge pour {name}")
                gauge.update_state(activity_percentage, status, details)
            else:
                logger.warning(f"AgentsWindow: Jauge introuvable pour {name}")
            
            # Mettre à jour détails si agent sélectionné
            if self._selected_agent == name:
                self._update_details_panel()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour état agent: {e}", exc_info=True)
    
    def _select_agent(self, agent_name: str):
        """
        Sélectionne un agent pour afficher ses détails.
        
        Args:
            agent_name: Nom de l'agent
        """
        self._selected_agent = agent_name
        self._update_details_panel()
        
        # Activer boutons
        self.restart_button.configure(state="normal")
        self.logs_button.configure(state="normal")
        
        logger.debug(f"Agent sélectionné: {agent_name}")
    
    def _update_details_panel(self):
        """Met à jour le panneau de détails avec l'agent sélectionné."""
        if not self._selected_agent:
            return
        
        agent_state = self._agent_states.get(self._selected_agent)
        if not agent_state:
            return
        
        # Nom + status
        self.details_name_label.configure(
            text=f"Agent sélectionné: {self._selected_agent}"
        )
        
        status = agent_state.get('status', 'IDLE')
        last_update = agent_state.get('last_update', 0)
        
        from datetime import datetime
        dt = datetime.fromtimestamp(last_update)
        time_str = dt.strftime('%H:%M:%S')
        
        self.details_status_label.configure(
            text=f"Status: {status} (MAJ: {time_str})"
        )
        
        # Métriques
        activity = agent_state.get('activity_percentage', 0)
        self.details_metrics_label.configure(
            text=f"Activité: {activity:.1f}%"
        )
        
        # Détails
        details = agent_state.get('details', 'Aucun détail disponible')
        
        self.details_textbox.configure(state="normal")
        self.details_textbox.delete("1.0", "end")
        self.details_textbox.insert("1.0", details)
        self.details_textbox.configure(state="disabled")
    
    def _restart_agent(self):
        """Redémarre l'agent sélectionné."""
        if not self._selected_agent:
            return
        
        # Émettre événement de redémarrage
        event_bus.emit('agent.restart', {'name': self._selected_agent})
        
        logger.info(f"Demande redémarrage agent: {self._selected_agent}")
        
        # Notification
        from interface.components.alert_popup import show_alert
        # Note: Besoin d'accès au parent principal pour afficher popup
        # Pour l'instant, juste logger
    
    def _view_logs(self):
        """Ouvre la fenêtre logs filtrée sur l'agent sélectionné."""
        if not self._selected_agent:
            return
        
        # Émettre événement pour ouvrir fenêtre logs
        event_bus.emit('ui.open_logs', {'filter_source': self._selected_agent})
        
        logger.info(f"Demande ouverture logs agent: {self._selected_agent}")
    
    def _on_close(self):
        """Handler fermeture fenêtre."""
        # Se désabonner des événements
        event_bus.unsubscribe('agent.state_change', self._on_agent_state_change)
        
        logger.info("Fenêtre États Agents fermée")
        self.destroy()

