#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Agent Circular Gauge - Jauge circulaire pour monitoring agents
Affiche charge CPU/activité + badge coloré statut
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
#   "Pillow>=9.0.0",
# ]
# ///

import customtkinter as ctk
import tkinter as tk
from typing import Optional
import math
import logging

logger = logging.getLogger(__name__)


class AgentGauge(ctk.CTkFrame):
    """
    Jauge circulaire style tableau de bord pour monitoring agent.
    Affiche pourcentage activité + badge statut coloré.
    """
    
    # Couleurs statuts
    STATUS_COLORS = {
        'ACTIF': '#4CAF50',      # Vert
        'EN_COURS': '#FFC107',   # Jaune
        'ERREUR': '#F44336',     # Rouge
        'IDLE': '#9E9E9E',       # Gris
        'STOPPED': '#424242'     # Gris foncé
    }
    
    # Emojis statuts
    STATUS_EMOJIS = {
        'ACTIF': '🟢',
        'EN_COURS': '🟡',
        'ERREUR': '🔴',
        'IDLE': '⚪',
        'STOPPED': '⚫'
    }
    
    def __init__(
        self,
        master,
        agent_name: str = "Agent",
        size: int = 120,
        **kwargs
    ):
        """
        Initialise la jauge agent.
        
        Args:
            master: Widget parent
            agent_name: Nom de l'agent (ex: 'LLM', 'STT', 'TTS')
            size: Taille de la jauge en pixels
            **kwargs: Arguments additionnels pour CTkFrame
        """
        super().__init__(master, width=size, height=size + 30, **kwargs)
        
        self.agent_name = agent_name
        self.size = size
        
        # État
        self._activity_percentage = 0.0  # 0-100
        self._status = 'IDLE'
        self._details = ""
        
        # Canvas pour dessin
        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg='#1E1E1E',
            highlightthickness=0
        )
        self.canvas.pack(padx=5, pady=5)
        
        # Label nom agent
        self.label = ctk.CTkLabel(
            self,
            text=agent_name,
            font=("Arial", 12, "bold")
        )
        self.label.pack()
        
        # Tooltip
        self._setup_tooltip()
        
        # Dessiner jauge initiale
        self._draw_gauge()
        
        logger.debug(f"AgentGauge créé: {agent_name}")
    
    def _setup_tooltip(self):
        """Configure le tooltip au survol."""
        self._tooltip = None
        self.canvas.bind("<Enter>", self._show_tooltip)
        self.canvas.bind("<Leave>", self._hide_tooltip)
    
    def _show_tooltip(self, event):
        """Affiche le tooltip avec détails."""
        if self._tooltip:
            return
        
        # Créer fenêtre tooltip
        self._tooltip = tk.Toplevel(self.canvas)
        self._tooltip.wm_overrideredirect(True)
        
        # Position
        x = event.x_root + 10
        y = event.y_root + 10
        self._tooltip.wm_geometry(f"+{x}+{y}")
        
        # Contenu
        tooltip_text = (
            f"Agent: {self.agent_name}\n"
            f"Statut: {self._status}\n"
            f"Activité: {self._activity_percentage:.1f}%\n"
        )
        if self._details:
            tooltip_text += f"Détails: {self._details}"
        
        label = tk.Label(
            self._tooltip,
            text=tooltip_text,
            background="#FFFFE0",
            foreground="#000000",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=5,
            font=("Arial", 9)
        )
        label.pack()
    
    def _hide_tooltip(self, event):
        """Masque le tooltip."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
    
    def update_state(
        self,
        activity_percentage: float,
        status: str = 'ACTIF',
        details: str = ""
    ):
        """
        Met à jour l'état de la jauge.
        
        Args:
            activity_percentage: Pourcentage activité (0-100)
            status: Statut ('ACTIF', 'EN_COURS', 'ERREUR', 'IDLE', 'STOPPED')
            details: Détails additionnels
        """
        self._activity_percentage = max(0, min(100, activity_percentage))
        self._status = status
        self._details = details
        
        # Redessiner
        self._draw_gauge()
    
    def _draw_gauge(self):
        """Dessine la jauge circulaire."""
        self.canvas.delete("all")
        
        center_x = self.size / 2
        center_y = self.size / 2
        radius = (self.size / 2) - 15
        
        # Arc de fond (gris)
        self.canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=0, extent=359.9,
            outline='#424242',
            width=8,
            style=tk.ARC
        )
        
        # Arc de progression (couleur statut)
        extent = (self._activity_percentage / 100) * 359.9
        color = self.STATUS_COLORS.get(self._status, '#9E9E9E')
        
        self.canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=90, extent=-extent,  # Commencer en haut, sens horaire
            outline=color,
            width=8,
            style=tk.ARC
        )
        
        # Badge statut au centre (cercle + emoji)
        badge_radius = radius * 0.4
        
        self.canvas.create_oval(
            center_x - badge_radius, center_y - badge_radius,
            center_x + badge_radius, center_y + badge_radius,
            fill=color,
            outline=""
        )
        
        # Emoji statut
        emoji = self.STATUS_EMOJIS.get(self._status, '⚪')
        self.canvas.create_text(
            center_x, center_y - 5,
            text=emoji,
            font=("Arial", 24),
            fill="white"
        )
        
        # Pourcentage
        self.canvas.create_text(
            center_x, center_y + 15,
            text=f"{self._activity_percentage:.0f}%",
            font=("Arial", 10, "bold"),
            fill="white"
        )

