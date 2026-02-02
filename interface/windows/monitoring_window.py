#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Fenêtre Monitoring Système Temps Réel
Graphiques CPU, RAM, GPU, Température
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
from interface.components.realtime_chart import RealtimeChart
from interface.events.event_bus import event_bus
from interface.models.events import MetricsSnapshot
import logging

logger = logging.getLogger(__name__)


class MonitoringWindow(ctk.CTkToplevel):
    """
    Fenêtre dédiée au monitoring système temps réel.
    Abonnée aux événements 'metrics.update' via l'Event Bus.
    """
    
    def __init__(self, master):
        """
        Initialise la fenêtre monitoring.
        
        Args:
            master: Widget parent
        """
        super().__init__(master)
        
        # Configuration fenêtre
        self.title("QAIA - Monitoring Système")
        self.geometry("900x600")
        
        # Créer UI
        self._build_ui()
        
        # S'abonner aux métriques
        event_bus.subscribe('metrics.update', self._on_metrics_update)
        
        # Handler fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Fenêtre Monitoring ouverte")
    
    def _build_ui(self):
        """Construit l'interface."""
        # Titre
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="📊 Monitoring Système Temps Réel",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)
        
        # Bouton libérer mémoire
        ctk.CTkButton(
            title_frame,
            text="🧹 Libérer Mémoire",
            command=self._free_memory
        ).pack(side="right", padx=10)
        
        # Graphiques (2x2 grid)
        charts_frame = ctk.CTkFrame(self)
        charts_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configurer grid
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)
        charts_frame.grid_rowconfigure(0, weight=1)
        charts_frame.grid_rowconfigure(1, weight=1)
        
        # Graphique CPU
        self.cpu_chart = RealtimeChart(
            charts_frame,
            title="CPU (%)",
            ylabel="Utilisation",
            max_value=100,
            color="#2196F3"
        )
        self.cpu_chart.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Graphique RAM
        self.ram_chart = RealtimeChart(
            charts_frame,
            title="RAM (GB)",
            ylabel="Utilisée",
            max_value=40,  # 40GB max selon config
            color="#4CAF50"
        )
        self.ram_chart.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Graphique GPU (si disponible)
        self.gpu_chart = RealtimeChart(
            charts_frame,
            title="GPU (%)",
            ylabel="Utilisation",
            max_value=100,
            color="#FF9800"
        )
        self.gpu_chart.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Graphique Température (si disponible)
        self.temp_chart = RealtimeChart(
            charts_frame,
            title="Température (°C)",
            ylabel="Temp",
            max_value=100,
            color="#F44336"
        )
        self.temp_chart.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        # Status bar
        self.status_label = ctk.CTkLabel(
            self,
            text="En attente de métriques...",
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=10, pady=5)
    
    def _on_metrics_update(self, event_data: dict):
        """
        Callback événement metrics.update.
        
        Args:
            event_data: Données métriques (conforme à MetricsSnapshot)
        """
        try:
            # Extraire métriques
            cpu = event_data.get('cpu', 0)
            ram = event_data.get('ram', 0)
            gpu = event_data.get('gpu')
            timestamp = event_data.get('timestamp')
            additional = event_data.get('additional', {})
            
            # Mettre à jour graphiques
            self.cpu_chart.add_data_point(cpu, timestamp)
            self.ram_chart.add_data_point(ram, timestamp)
            
            if gpu is not None:
                self.gpu_chart.add_data_point(gpu, timestamp)
            
            # Température si disponible
            temp = additional.get('temperature')
            if temp is not None:
                self.temp_chart.add_data_point(temp, timestamp)
            
            # Mettre à jour status
            status_text = f"CPU: {cpu:.1f}% | RAM: {ram:.1f}GB"
            if gpu is not None:
                status_text += f" | GPU: {gpu:.1f}%"
            
            self.status_label.configure(text=status_text)
            
        except Exception as e:
            logger.error(f"Erreur mise à jour monitoring: {e}")
    
    def _free_memory(self):
        """Libère la mémoire (garbage collection)."""
        import gc
        gc.collect()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        
        logger.info("Mémoire libérée")
        self.status_label.configure(text="✅ Mémoire libérée")
    
    def _on_close(self):
        """Handler fermeture fenêtre."""
        # Se désabonner des événements
        event_bus.unsubscribe('metrics.update', self._on_metrics_update)
        
        logger.info("Fenêtre Monitoring fermée")
        self.destroy()

