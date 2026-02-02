#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Alert Popup - Pop-up automatique pour erreurs critiques agents
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class AlertPopup(ctk.CTkToplevel):
    """
    Fenêtre pop-up d'alerte pour erreurs critiques.
    Affiche message + options: Redémarrer, Ignorer, Voir logs.
    """
    
    def __init__(
        self,
        master,
        agent_name: str,
        error_message: str,
        on_restart: Optional[Callable] = None,
        on_ignore: Optional[Callable] = None,
        on_view_logs: Optional[Callable] = None
    ):
        """
        Initialise l'alerte pop-up.
        
        Args:
            master: Widget parent
            agent_name: Nom de l'agent en erreur
            error_message: Message d'erreur
            on_restart: Callback si bouton "Redémarrer" cliqué
            on_ignore: Callback si bouton "Ignorer" cliqué
            on_view_logs: Callback si bouton "Voir logs" cliqué
        """
        super().__init__(master)
        
        self.agent_name = agent_name
        self.error_message = error_message
        self.on_restart = on_restart
        self.on_ignore = on_ignore
        self.on_view_logs = on_view_logs
        
        # Configuration fenêtre
        self.title(f"QAIA - Erreur Agent {agent_name}")
        self.geometry("500x300")
        self.resizable(False, False)
        
        # Toujours au premier plan
        self.attributes("-topmost", True)
        
        # Centrer
        self._center_window()
        
        # Construire UI
        self._build_ui()
        
        logger.warning(f"AlertPopup affiché pour {agent_name}: {error_message}")
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = (screen_width - 500) // 2
        y = (screen_height - 300) // 2
        
        self.geometry(f"500x300+{x}+{y}")
    
    def _build_ui(self):
        """Construit l'interface de l'alerte."""
        # Icône erreur + titre
        header_frame = ctk.CTkFrame(self, fg_color="#F44336")
        header_frame.pack(fill="x", padx=0, pady=0)
        
        ctk.CTkLabel(
            header_frame,
            text="⚠️ ERREUR CRITIQUE",
            font=("Arial", 18, "bold"),
            text_color="white"
        ).pack(pady=15)
        
        # Contenu
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Agent concerné
        ctk.CTkLabel(
            content_frame,
            text=f"Agent: {self.agent_name}",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Message d'erreur
        ctk.CTkLabel(
            content_frame,
            text="Message d'erreur:",
            font=("Arial", 12)
        ).pack(anchor="w")
        
        error_textbox = ctk.CTkTextbox(
            content_frame,
            height=80,
            wrap="word",
            state="normal"
        )
        error_textbox.pack(fill="x", pady=5)
        error_textbox.insert("1.0", self.error_message)
        error_textbox.configure(state="disabled")
        
        # Boutons actions
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Bouton Redémarrer
        if self.on_restart:
            ctk.CTkButton(
                button_frame,
                text="🔄 Redémarrer Agent",
                fg_color="#4CAF50",
                hover_color="#45A049",
                command=self._handle_restart
            ).pack(side="left", padx=5)
        
        # Bouton Voir logs
        if self.on_view_logs:
            ctk.CTkButton(
                button_frame,
                text="📋 Voir Logs",
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=self._handle_view_logs
            ).pack(side="left", padx=5)
        
        # Bouton Ignorer
        ctk.CTkButton(
            button_frame,
            text="❌ Ignorer",
            fg_color="#9E9E9E",
            hover_color="#757575",
            command=self._handle_ignore
        ).pack(side="right", padx=5)
    
    def _handle_restart(self):
        """Gère clic bouton Redémarrer."""
        logger.info(f"Utilisateur a choisi de redémarrer {self.agent_name}")
        
        if self.on_restart:
            self.on_restart()
        
        self.destroy()
    
    def _handle_ignore(self):
        """Gère clic bouton Ignorer."""
        logger.info(f"Utilisateur a ignoré l'erreur de {self.agent_name}")
        
        if self.on_ignore:
            self.on_ignore()
        
        self.destroy()
    
    def _handle_view_logs(self):
        """Gère clic bouton Voir logs."""
        logger.info(f"Utilisateur veut voir logs de {self.agent_name}")
        
        if self.on_view_logs:
            self.on_view_logs()
        
        # Ne pas fermer la fenêtre, permettre de voir logs et revenir


def show_alert(
    parent,
    agent_name: str,
    error_message: str,
    on_restart: Optional[Callable] = None,
    on_ignore: Optional[Callable] = None,
    on_view_logs: Optional[Callable] = None
) -> AlertPopup:
    """
    Fonction helper pour afficher une alerte.
    
    Args:
        parent: Widget parent
        agent_name: Nom de l'agent
        error_message: Message d'erreur
        on_restart: Callback redémarrage
        on_ignore: Callback ignorer
        on_view_logs: Callback voir logs
        
    Returns:
        Instance AlertPopup
    """
    return AlertPopup(
        parent,
        agent_name,
        error_message,
        on_restart,
        on_ignore,
        on_view_logs
    )

