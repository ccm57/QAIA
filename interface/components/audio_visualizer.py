#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Audio Visualizer compact pour status bar
Forme d'onde temps réel + indicateurs VAD et RMS
"""

# /// script
# dependencies = [
#   "customtkinter>=5.2.0",
#   "numpy>=1.22.0",
# ]
# ///

import customtkinter as ctk
import tkinter as tk
from collections import deque
from typing import Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AudioVisualizer(ctk.CTkFrame):
    """
    Visualiseur audio compact intégré dans status bar.
    Affiche forme d'onde, niveau RMS, et détection VAD.
    """
    
    # Couleurs
    COLOR_WAVEFORM = "#4CAF50"      # Vert pour forme d'onde
    COLOR_RMS = "#FFC107"           # Jaune pour RMS
    COLOR_VAD_ACTIVE = "#F44336"    # Rouge quand VAD actif
    COLOR_BACKGROUND = "#1E1E1E"    # Fond sombre
    
    def __init__(
        self,
        master,
        width: int = 200,
        height: int = 60,
        **kwargs
    ):
        """
        Initialise l'AudioVisualizer.
        
        Args:
            master: Widget parent
            width: Largeur en pixels
            height: Hauteur en pixels (60px max pour status bar)
            **kwargs: Arguments additionnels pour CTkFrame
        """
        super().__init__(master, width=width, height=height, **kwargs)
        
        self.width = width
        self.height = height
        
        # Canvas pour dessin
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=self.COLOR_BACKGROUND,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Buffer données audio (100 derniers échantillons)
        self._audio_buffer = deque(maxlen=100)
        
        # État
        self._rms_level = 0.0
        self._vad_active = False
        self._is_visible = False
        
        # Masquer par défaut
        self.pack_forget()
        
        logger.debug("AudioVisualizer créé")
    
    def show(self):
        """Affiche le visualiseur."""
        if not self._is_visible:
            self.pack(side="left", padx=5)
            self._is_visible = True
    
    def hide(self):
        """Masque le visualiseur."""
        if self._is_visible:
            self.pack_forget()
            self._is_visible = False
    
    def update_audio(self, audio_data: np.ndarray):
        """
        Met à jour avec nouvelles données audio.
        
        Args:
            audio_data: Array numpy de samples audio (normalisé -1.0 à 1.0)
        """
        if len(audio_data) == 0:
            return
        
        # Downsampler pour visualisation (prendre 1 échantillon sur N)
        downsample_factor = max(1, len(audio_data) // 100)
        downsampled = audio_data[::downsample_factor]
        
        # Ajouter au buffer
        for sample in downsampled:
            self._audio_buffer.append(sample)
        
        # Calculer RMS
        self._rms_level = np.sqrt(np.mean(audio_data ** 2))
        
        # Redessiner
        self._draw_waveform()
    
    def set_vad_active(self, active: bool):
        """
        Définit l'état VAD (Voice Activity Detection).
        
        Args:
            active: True si voix détectée
        """
        self._vad_active = active
        self._draw_waveform()
    
    def _draw_waveform(self):
        """Dessine la forme d'onde et indicateurs."""
        # Effacer canvas
        self.canvas.delete("all")
        
        # Dessiner forme d'onde
        if self._audio_buffer:
            buffer_list = list(self._audio_buffer)
            num_samples = len(buffer_list)
            
            # Échelle X et Y
            x_scale = self.width / max(1, num_samples - 1)
            y_center = self.height / 2
            y_scale = (self.height / 2) * 0.8  # 80% de la hauteur
            
            # Dessiner ligne forme d'onde
            points = []
            for i, sample in enumerate(buffer_list):
                x = i * x_scale
                y = y_center - (sample * y_scale)
                points.append((x, y))
            
            if len(points) > 1:
                self.canvas.create_line(
                    points,
                    fill=self.COLOR_WAVEFORM,
                    width=2,
                    smooth=True
                )
        
        # Dessiner ligne RMS (niveau moyen)
        rms_y = self.height - (self._rms_level * self.height * 0.8)
        self.canvas.create_line(
            0, rms_y,
            self.width, rms_y,
            fill=self.COLOR_RMS,
            width=1,
            dash=(4, 4)
        )
        
        # Indicateur VAD (carré rouge en haut à droite)
        if self._vad_active:
            self.canvas.create_rectangle(
                self.width - 15, 5,
                self.width - 5, 15,
                fill=self.COLOR_VAD_ACTIVE,
                outline=""
            )
            self.canvas.create_text(
                self.width - 20, 10,
                text="REC",
                fill=self.COLOR_VAD_ACTIVE,
                anchor="e",
                font=("Arial", 8, "bold")
            )
    
    def clear(self):
        """Efface le buffer et réinitialise."""
        self._audio_buffer.clear()
        self._rms_level = 0.0
        self._vad_active = False
        self.canvas.delete("all")
        
        logger.debug("AudioVisualizer effacé")

