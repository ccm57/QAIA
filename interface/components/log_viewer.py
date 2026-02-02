#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Log Viewer avec filtrage et recherche temps réel
Affichage logs colorés par niveau
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
import tkinter as tk
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)


class LogViewer(ctk.CTkFrame):
    """
    Visualiseur de logs avec filtrage niveau et recherche.
    Coloration automatique par niveau, auto-scroll intelligent.
    """
    
    # Couleurs par niveau
    LEVEL_COLORS = {
        'DEBUG': '#9E9E9E',      # Gris
        'INFO': '#2196F3',       # Bleu
        'WARNING': '#FF9800',    # Orange
        'ERROR': '#F44336',      # Rouge
        'CRITICAL': '#D32F2F'    # Rouge foncé
    }
    
    def __init__(self, master, **kwargs):
        """
        Initialise le LogViewer.
        
        Args:
            master: Widget parent
            **kwargs: Arguments additionnels pour CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Frame contrôles (en haut)
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(fill="x", padx=5, pady=5)
        
        # Filtres niveau
        ctk.CTkLabel(self.control_frame, text="Niveau:").pack(side="left", padx=5)
        
        self.level_filter = ctk.CTkOptionMenu(
            self.control_frame,
            values=["TOUS", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            command=self._apply_filter
        )
        self.level_filter.set("TOUS")
        self.level_filter.pack(side="left", padx=5)
        
        # Recherche
        ctk.CTkLabel(self.control_frame, text="Recherche:").pack(side="left", padx=5)
        
        self.search_entry = ctk.CTkEntry(self.control_frame, width=200)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())
        
        # Boutons
        ctk.CTkButton(
            self.control_frame,
            text="Effacer",
            width=80,
            command=self.clear
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            self.control_frame,
            text="Export",
            width=80,
            command=self._export_logs
        ).pack(side="right", padx=5)
        
        # Auto-scroll toggle
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.control_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_var
        ).pack(side="right", padx=5)
        
        # Textbox logs
        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled"
        )
        self.textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configuration tags couleur
        self._setup_tags()
        
        # Buffer logs
        self._log_buffer: List[dict] = []
        self._max_buffer_size = 1000
        
        logger.debug("LogViewer créé")
    
    def _setup_tags(self):
        """Configure les tags de coloration."""
        self.textbox.configure(state="normal")
        
        for level, color in self.LEVEL_COLORS.items():
            self.textbox.tag_config(level, foreground=color)
        
        self.textbox.tag_config("timestamp", foreground="#757575")
        self.textbox.tag_config("source", foreground="#9C27B0")
        
        self.textbox.configure(state="disabled")
    
    def add_log(self, level: str, message: str, source: str = "", timestamp: str = ""):
        """
        Ajoute une entrée de log.
        
        Args:
            level: Niveau (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Message de log
            source: Source du log
            timestamp: Timestamp format (HH:MM:SS)
        """
        # Ajouter au buffer
        log_entry = {
            'level': level,
            'message': message,
            'source': source,
            'timestamp': timestamp
        }
        self._log_buffer.append(log_entry)
        
        # Limiter taille buffer
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer.pop(0)
        
        # Vérifier filtres
        if self._should_display(log_entry):
            self._display_log(log_entry)
    
    def _should_display(self, log_entry: dict) -> bool:
        """Vérifie si le log doit être affiché selon les filtres."""
        # Filtre niveau
        level_filter = self.level_filter.get()
        if level_filter != "TOUS" and log_entry['level'] != level_filter:
            return False
        
        # Filtre recherche
        search_text = self.search_entry.get().strip()
        if search_text:
            pattern = re.compile(search_text, re.IGNORECASE)
            full_text = f"{log_entry['timestamp']} {log_entry['level']} {log_entry['source']} {log_entry['message']}"
            if not pattern.search(full_text):
                return False
        
        return True
    
    def _display_log(self, log_entry: dict):
        """Affiche une entrée de log dans le textbox."""
        self.textbox.configure(state="normal")
        
        # Format: [14:23:15] INFO source: message
        if log_entry['timestamp']:
            self.textbox.insert("end", f"[{log_entry['timestamp']}] ", "timestamp")
        
        self.textbox.insert("end", f"{log_entry['level']} ", log_entry['level'])
        
        if log_entry['source']:
            self.textbox.insert("end", f"{log_entry['source']}: ", "source")
        
        self.textbox.insert("end", f"{log_entry['message']}\n")
        
        self.textbox.configure(state="disabled")
        
        # Auto-scroll
        if self.auto_scroll_var.get():
            self.textbox.see("end")
    
    def _apply_filter(self, *args):
        """Réapplique les filtres et rafraîchit l'affichage."""
        # Effacer affichage
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        
        # Réafficher logs filtrés
        for log_entry in self._log_buffer:
            if self._should_display(log_entry):
                self._display_log(log_entry)
    
    def clear(self):
        """Efface tous les logs."""
        self._log_buffer.clear()
        
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        
        logger.debug("LogViewer effacé")
    
    def _export_logs(self):
        """Exporte les logs vers un fichier."""
        from tkinter import filedialog
        from datetime import datetime
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"qaia_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for log_entry in self._log_buffer:
                        line = f"[{log_entry['timestamp']}] {log_entry['level']} {log_entry['source']}: {log_entry['message']}\n"
                        f.write(line)
                
                logger.info(f"Logs exportés vers {filename}")
            except Exception as e:
                logger.error(f"Erreur export logs: {e}")

