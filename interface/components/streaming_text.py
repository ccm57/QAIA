#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Streaming Text Display avec animation token-par-token
Format: (HH:MM) Speaker: texte
Espacement: 4px après chaque paire Q/R
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
# ]
# ///

import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StreamingTextDisplay(ctk.CTkTextbox):
    """
    Widget d'affichage de texte avec streaming token-par-token.
    Format aligné gauche avec timestamps et coloration.
    """
    
    # Couleurs selon le plan
    COLOR_TIMESTAMP = "#757575"  # Gris
    COLOR_USER = "#2196F3"       # Bleu
    COLOR_QAIA = "#4CAF50"       # Vert
    COLOR_TEXT = "#000000"       # Noir
    
    def __init__(self, master, **kwargs):
        """
        Initialise le StreamingTextDisplay.
        
        Args:
            master: Widget parent
            **kwargs: Arguments additionnels pour CTkTextbox
        """
        super().__init__(master, **kwargs)
        
        # Configuration du widget
        self.configure(
            wrap="word",
            state="disabled"  # Lecture seule par défaut
        )
        
        # État interne
        self._current_speaker: Optional[str] = None
        self._current_timestamp: Optional[str] = None
        self._is_streaming = False
        self._streamed_text = ""  # Texte accumulé pendant le streaming
        self._stream_start_index = "1.0"  # Index de début du message en cours
        self._previous_token = None  # Token précédent pour gestion espaces
        
        # Configuration des tags de couleur
        self._setup_tags()
        
        logger.debug("StreamingTextDisplay initialisé")
    
    def _setup_tags(self):
        """Configure les tags de coloration."""
        # Activer temporairement pour configurer les tags
        self.configure(state="normal")
        
        # Tags pour couleurs
        self.tag_config("timestamp", foreground=self.COLOR_TIMESTAMP)
        self.tag_config("user", foreground=self.COLOR_USER)
        self.tag_config("qaia", foreground=self.COLOR_QAIA)
        self.tag_config("text", foreground=self.COLOR_TEXT)
        
        # Désactiver à nouveau
        self.configure(state="disabled")
    
    def start_generation(self, speaker: str, timestamp: Optional[str] = None):
        """
        Démarre un nouveau bloc de génération.
        
        Args:
            speaker: 'Vous' ou 'QAIA'
            timestamp: Timestamp format (HH:MM), généré auto si None
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")
        
        self._current_speaker = speaker
        self._current_timestamp = timestamp
        self._is_streaming = True
        self._streamed_text = ""  # Réinitialiser le texte streamé
        self._stream_start_index = self.index("end")  # Mémoriser l'index de début
        self._previous_token = None  # Réinitialiser token précédent
        
        # Activer édition
        self.configure(state="normal")
        
        # Insérer timestamp + speaker
        # Format: (14:23) Vous: 
        self.insert("end", f"({timestamp}) ", "timestamp")
        
        speaker_tag = "user" if speaker == "Vous" else "qaia"
        self.insert("end", f"{speaker}: ", speaker_tag)
        
        # Désactiver édition
        self.configure(state="disabled")
        
        # Auto-scroll
        self.see("end")
        
        logger.debug(f"Génération démarrée: {speaker} à {timestamp}")
    
    def append_token(self, token: str, animate: bool = True):
        """
        Ajoute un token avec animation optionnelle.
        Gère automatiquement les espaces entre tokens si nécessaire.
        
        Args:
            token: Texte du token à ajouter
            animate: Si True, anime l'ajout (effet machine à écrire)
        """
        if not self._is_streaming:
            logger.warning("append_token appelé sans start_generation actif")
            return
        
        # CRITIQUE: Filtrer les préfixes indésirables AVANT affichage
        try:
            from utils.text_processor import filter_streaming_token
            filtered_token = filter_streaming_token(token)
            if not filtered_token:
                return  # Token filtré, ne pas afficher
            token = filtered_token
        except Exception as e:
            logger.warning(f"Erreur filtrage token: {e}, utilisation token brut")
        
        # Gérer les espaces entre tokens si nécessaire
        try:
            from utils.text_processor import should_add_space_before_token
            if should_add_space_before_token(token, self._previous_token):
                token = " " + token
        except Exception as e:
            logger.debug(f"Erreur gestion espaces: {e}")
        
        # Accumuler le texte streamé
        self._streamed_text += token
        
        # Mémoriser le token précédent
        self._previous_token = token
        
        # Activer édition
        self.configure(state="normal")
        
        # Insérer token
        self.insert("end", token, "text")
        
        # Désactiver édition
        self.configure(state="disabled")
        
        # Auto-scroll
        self.see("end")
        
        # Animation (pourrait être améliorée avec des delays)
        if animate:
            self.update_idletasks()
    
    def complete_generation(self):
        """Termine la génération en cours et ajoute une nouvelle ligne."""
        if not self._is_streaming:
            return
        
        self._is_streaming = False
        
        # Activer édition
        self.configure(state="normal")
        
        # Ajouter nouvelle ligne
        self.insert("end", "\n")
        
        # Désactiver édition
        self.configure(state="disabled")
        
        # Auto-scroll
        self.see("end")
        
        logger.debug(f"Génération terminée: {self._current_speaker}")
    
    def replace_current_message(self, new_text: str):
        """
        Remplace le contenu du message en cours (après le préfixe timestamp/QAIA)
        par un texte nettoyé globalement.
        
        Utilisé pour synchroniser le texte affiché avec le texte TTS (TODO-6).
        
        Args:
            new_text: Texte nettoyé à afficher
        """
        if not self._stream_start_index:
            logger.warning("replace_current_message appelé sans stream_start_index")
            return
        
        # CRITIQUE: Supprimer tout préfixe "(HH:MM) QAIA:" du texte (multi-pass) pour éviter doublon
        import re
        if new_text:
            prefix_re = re.compile(
                r"^\s*\(\d{1,2}:\d{2}\)\s*QAIA\s*:?\s*",
                re.IGNORECASE,
            )
            while prefix_re.match(new_text.strip()):
                new_text = prefix_re.sub("", new_text.strip(), count=1).strip()
            if not new_text:
                new_text = ""
        
        self.configure(state="normal")
        
        # Supprimer uniquement la partie texte après le préfixe "(HH:MM) QAIA: "
        # On garde le préfixe mais on remplace le contenu
        try:
            # Trouver la fin du préfixe "QAIA: " dans le texte actuel
            current_content = self.get(self._stream_start_index, "end")
            prefix_end = current_content.find(": ") + 2  # Après ": "
            
            if prefix_end > 0:
                # Supprimer tout après le préfixe
                delete_start = f"{self._stream_start_index}+{prefix_end}c"
                self.delete(delete_start, "end")
            else:
                # Fallback: supprimer depuis stream_start_index
                self.delete(self._stream_start_index, "end")
            
            # Réinsérer le texte nettoyé avec le tag "text"
            self.insert("end", new_text, "text")
        except Exception as e:
            logger.error(f"Erreur replace_current_message: {e}")
            # Fallback: remplacer tout le contenu depuis stream_start_index
            try:
                self.delete(self._stream_start_index, "end")
                self.insert("end", new_text, "text")
            except Exception as e2:
                logger.error(f"Erreur fallback replace_current_message: {e2}")
        
        self.configure(state="disabled")
        self.see("end")
        
        logger.debug(f"Message remplacé: {len(new_text)} caractères")
    
    def add_spacing(self, pixels: int = 4):
        """
        Ajoute espacement vertical après paire Q/R.
        
        Args:
            pixels: Nombre de pixels d'espacement (défaut: 4px)
        """
        # Activer édition
        self.configure(state="normal")
        
        # Calculer nombre de lignes pour approximer les pixels
        # (approximativement 1 ligne = 16-20px selon la police)
        lines_to_add = max(1, pixels // 16)
        
        # Ajouter les lignes vides
        for _ in range(lines_to_add):
            self.insert("end", "\n")
        
        # Désactiver édition
        self.configure(state="disabled")
        
        # Auto-scroll
        self.see("end")
    
    def add_message(self, speaker: str, text: str, timestamp: Optional[str] = None):
        """
        Ajoute un message complet (sans streaming).
        
        Args:
            speaker: 'Vous' ou 'QAIA'
            text: Texte complet du message
            timestamp: Timestamp optionnel
        """
        self.start_generation(speaker, timestamp)
        self.append_token(text, animate=False)
        self.complete_generation()
    
    def clear(self):
        """Efface tout le contenu."""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
        
        self._current_speaker = None
        self._current_timestamp = None
        self._is_streaming = False
        self._streamed_text = ""
        self._stream_start_index = "1.0"
        self._previous_token = None
        
        logger.debug("StreamingTextDisplay effacé")
    
    def get_text(self) -> str:
        """
        Retourne tout le texte.
        
        Returns:
            Contenu textuel complet
        """
        return self.get("1.0", "end-1c")
    
    def get_streamed_text(self) -> str:
        """
        Retourne le texte accumulé pendant le streaming en cours.
        
        Returns:
            Texte streamé du message en cours (sans timestamp ni speaker)
        """
        return self._streamed_text.strip() if self._streamed_text else ""

