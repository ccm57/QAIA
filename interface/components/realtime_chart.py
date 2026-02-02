#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Real-Time Chart Widget avec matplotlib
Graphiques temps réel pour métriques système
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
#   "matplotlib>=3.5.0",
# ]
# ///

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from typing import List, Optional
import logging
import time

logger = logging.getLogger(__name__)


class RealtimeChart(ctk.CTkFrame):
    """
    Widget de graphique temps réel avec buffer circulaire.
    Optimisé pour 5 FPS sans blocage UI.
    """
    
    def __init__(
        self,
        master,
        title: str = "Métrique",
        ylabel: str = "Valeur",
        buffer_size: int = 300,  # 60s à 5 FPS
        max_value: float = 100.0,
        color: str = "#2196F3",
        **kwargs
    ):
        """
        Initialise le graphique temps réel.
        
        Args:
            master: Widget parent
            title: Titre du graphique
            ylabel: Label axe Y
            buffer_size: Taille buffer données (nombre de points)
            max_value: Valeur maximale axe Y
            color: Couleur de la courbe (hex)
            **kwargs: Arguments additionnels pour CTkFrame
        """
        super().__init__(master, **kwargs)
        
        self.title = title
        self.ylabel = ylabel
        self.buffer_size = buffer_size
        self.max_value = max_value
        self.color = color
        
        # Buffer circulaire pour données
        self._data_buffer = deque(maxlen=buffer_size)
        self._time_buffer = deque(maxlen=buffer_size)
        
        # Figure matplotlib
        self.figure = Figure(figsize=(6, 3), dpi=80, facecolor='#2B2B2B')
        self.ax = self.figure.add_subplot(111)
        
        # Configuration axes
        self.ax.set_facecolor('#1E1E1E')
        self.ax.set_title(title, color='white', fontsize=10)
        self.ax.set_ylabel(ylabel, color='white', fontsize=9)
        self.ax.set_ylim(0, max_value)
        self.ax.grid(True, alpha=0.3, color='gray')
        self.ax.tick_params(colors='white', labelsize=8)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Ligne de données
        self.line, = self.ax.plot([], [], color=color, linewidth=2)
        
        # État
        self._last_update = time.time()
        self._update_interval = 0.2  # 5 FPS
        
        logger.debug(f"RealtimeChart créé: {title}")
    
    def add_data_point(self, value: float, timestamp: Optional[float] = None):
        """
        Ajoute un point de données.
        
        Args:
            value: Valeur à ajouter
            timestamp: Timestamp Unix, généré auto si None
        """
        if timestamp is None:
            timestamp = time.time()
        
        self._data_buffer.append(value)
        self._time_buffer.append(timestamp)
        
        # Mise à jour graphique si intervalle écoulé
        now = time.time()
        if now - self._last_update >= self._update_interval:
            self._update_plot()
            self._last_update = now
    
    def _update_plot(self):
        """Met à jour le graphique."""
        if not self._data_buffer:
            return
        
        # Convertir timestamps en temps relatifs (secondes depuis premier point)
        if self._time_buffer:
            first_time = self._time_buffer[0]
            relative_times = [t - first_time for t in self._time_buffer]
        else:
            relative_times = []
        
        # Mettre à jour données ligne
        self.line.set_data(relative_times, list(self._data_buffer))
        
        # Ajuster limites axe X
        if relative_times:
            self.ax.set_xlim(max(0, relative_times[-1] - 60), relative_times[-1] + 1)
        
        # Redessiner
        try:
            self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Erreur mise à jour graphique: {e}")
    
    def clear(self):
        """Efface toutes les données."""
        self._data_buffer.clear()
        self._time_buffer.clear()
        self.line.set_data([], [])
        self.canvas.draw_idle()
        
        logger.debug(f"RealtimeChart effacé: {self.title}")
    
    def set_max_value(self, max_value: float):
        """
        Change la valeur maximale de l'axe Y.
        
        Args:
            max_value: Nouvelle valeur max
        """
        self.max_value = max_value
        self.ax.set_ylim(0, max_value)
        self.canvas.draw_idle()

