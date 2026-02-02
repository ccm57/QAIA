#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Fenêtre Métriques LLM
Affiche métriques de génération: latence, tokens/s, etc.
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
from interface.components.realtime_chart import RealtimeChart
from interface.events.event_bus import event_bus
from collections import deque
import logging

logger = logging.getLogger(__name__)


class MetricsWindow(ctk.CTkToplevel):
    """
    Fenêtre dédiée aux métriques LLM.
    Abonnée aux événements 'llm.complete' via l'Event Bus.
    """
    
    def __init__(self, master):
        """
        Initialise la fenêtre métriques.
        
        Args:
            master: Widget parent
        """
        super().__init__(master)
        
        # Configuration fenêtre
        self.title("QAIA - Métriques LLM")
        self.geometry("900x700")
        
        # Buffer historique (20 dernières requêtes)
        self._history_buffer = deque(maxlen=20)
        
        # Créer UI
        self._build_ui()
        
        # S'abonner aux événements LLM
        event_bus.subscribe('llm.complete', self._on_llm_complete)
        
        # Handler fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Fenêtre Métriques LLM ouverte")
    
    def _build_ui(self):
        """Construit l'interface."""
        # Titre
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="📈 Métriques LLM Temps Réel",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)
        
        # Métriques actuelles (cartes)
        metrics_frame = ctk.CTkFrame(self)
        metrics_frame.pack(fill="x", padx=10, pady=10)
        
        # Grille 2x2 de métriques
        metrics_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Latence
        self.latency_card = self._create_metric_card(
            metrics_frame, "⏱️ Latence", "0.0s"
        )
        self.latency_card.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Tokens/sec
        self.tokens_per_sec_card = self._create_metric_card(
            metrics_frame, "⚡ Tokens/sec", "0.0"
        )
        self.tokens_per_sec_card.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Total tokens session
        self.total_tokens_card = self._create_metric_card(
            metrics_frame, "📊 Total Tokens", "0"
        )
        self.total_tokens_card.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Config actuelle
        self.config_card = self._create_metric_card(
            metrics_frame, "⚙️ Config", "Temp: 0.6 | Top-p: 0.9"
        )
        self.config_card.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Graphique latence
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.latency_chart = RealtimeChart(
            chart_frame,
            title="Latence Génération (s)",
            ylabel="Secondes",
            max_value=60,
            color="#2196F3"
        )
        self.latency_chart.pack(fill="both", expand=True)
        
        # Tableau historique
        history_frame = ctk.CTkFrame(self)
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            history_frame,
            text="Historique (20 dernières requêtes)",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.history_textbox = ctk.CTkTextbox(
            history_frame,
            height=150,
            state="disabled"
        )
        self.history_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Métriques de session
        self._total_tokens = 0
        self._request_count = 0
    
    def _create_metric_card(self, parent, title: str, value: str) -> ctk.CTkFrame:
        """
        Crée une carte métrique.
        
        Args:
            parent: Widget parent
            title: Titre de la métrique
            value: Valeur initiale
            
        Returns:
            Frame contenant la carte
        """
        card = ctk.CTkFrame(parent)
        
        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 11)
        ).pack(pady=(10, 0))
        
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 20, "bold")
        )
        value_label.pack(pady=(5, 10))
        
        # Stocker référence au label pour mise à jour
        card.value_label = value_label
        
        return card
    
    def _on_llm_complete(self, event_data: dict):
        """
        Callback événement llm.complete.
        
        Args:
            event_data: Données de complétion (latency, tokens, etc.)
        """
        try:
            # Extraire métriques
            latency = event_data.get('latency', 0)
            tokens = event_data.get('tokens', 0)
            temperature = event_data.get('temperature', 0.6)
            top_p = event_data.get('top_p', 0.9)
            timestamp = event_data.get('timestamp')
            
            # Calculer tokens/sec
            tokens_per_sec = tokens / latency if latency > 0 else 0
            
            # Mettre à jour métriques session
            self._total_tokens += tokens
            self._request_count += 1
            
            # Mettre à jour cartes
            self.latency_card.value_label.configure(text=f"{latency:.2f}s")
            self.tokens_per_sec_card.value_label.configure(text=f"{tokens_per_sec:.1f}")
            self.total_tokens_card.value_label.configure(text=str(self._total_tokens))
            self.config_card.value_label.configure(
                text=f"Temp: {temperature} | Top-p: {top_p}"
            )
            
            # Ajouter au graphique
            self.latency_chart.add_data_point(latency, timestamp)
            
            # Ajouter à l'historique
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime('%H:%M:%S')
            
            history_entry = f"[{time_str}] Latence: {latency:.2f}s | Tokens: {tokens} | Tokens/s: {tokens_per_sec:.1f}"
            self._history_buffer.append(history_entry)
            
            # Mettre à jour textbox historique
            self.history_textbox.configure(state="normal")
            self.history_textbox.delete("1.0", "end")
            
            for entry in reversed(list(self._history_buffer)):
                self.history_textbox.insert("1.0", entry + "\n")
            
            self.history_textbox.configure(state="disabled")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour métriques LLM: {e}")
    
    def _on_close(self):
        """Handler fermeture fenêtre."""
        # Se désabonner des événements
        event_bus.unsubscribe('llm.complete', self._on_llm_complete)
        
        logger.info("Fenêtre Métriques LLM fermée")
        self.destroy()

