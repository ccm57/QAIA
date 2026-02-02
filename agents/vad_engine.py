#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Moteur VAD (Voice Activity Detection) pour QAIA
Utilise WebRTC VAD pour détection robuste début/fin parole.
"""

# /// script
# dependencies = [
#   "numpy>=1.22.0",
#   "webrtcvad>=2.0.10",
# ]
# ///

import logging
import numpy as np
import webrtcvad
from collections import deque
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class VADMode(Enum):
    """Modes d'aggressivité VAD WebRTC."""
    QUALITY = 0      # Permissif (max qualité)
    LOW_BITRATE = 1  # Légèrement agressif
    AGGRESSIVE = 2   # Agressif (recommandé)
    VERY_AGGRESSIVE = 3  # Très agressif (usage spécifique)

@dataclass
class VADConfig:
    """Configuration VAD."""
    aggressiveness: int = 2        # Mode VAD (0-3)
    frame_duration_ms: int = 30    # Durée frame (10, 20 ou 30 ms)
    min_speech_duration_ms: int = 300      # Durée min parole (300ms)
    max_silence_duration_ms: int = 1500    # Silence max avant arrêt (1.5s)
    pre_speech_buffer_ms: int = 200        # Buffer avant parole (200ms)
    post_speech_buffer_ms: int = 400       # Buffer après parole (400ms)
    energy_threshold: float = 0.01         # Seuil RMS minimum
    
    def __post_init__(self):
        """Validation configuration."""
        if self.aggressiveness not in [0, 1, 2, 3]:
            raise ValueError("aggressiveness doit être 0-3")
        if self.frame_duration_ms not in [10, 20, 30]:
            raise ValueError("frame_duration_ms doit être 10, 20 ou 30")

class VADEngine:
    """
    Moteur VAD utilisant WebRTC pour détection parole robuste.
    
    Caractéristiques:
    - Détection temps réel frame-by-frame
    - Buffers pré/post parole
    - Gestion silence adaptatif
    - Filtrage bruit
    """
    
    def __init__(self, sample_rate: int = 16000, config: Optional[VADConfig] = None):
        """
        Initialise le moteur VAD.
        
        Args:
            sample_rate: Fréquence échantillonnage (8000, 16000, 32000 ou 48000)
            config: Configuration VAD (None = défaut)
        """
        self.logger = logging.getLogger(__name__)
        
        # Validation sample_rate
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"sample_rate {sample_rate} non supporté (8k, 16k, 32k, 48k)")
        
        self.sample_rate = sample_rate
        self.config = config or VADConfig()
        
        # Initialisation WebRTC VAD
        try:
            self.vad = webrtcvad.Vad(self.config.aggressiveness)
            self.logger.info(f"✅ WebRTC VAD initialisé (mode {self.config.aggressiveness})")
        except Exception as e:
            self.logger.error(f"❌ Erreur init WebRTC VAD: {e}")
            raise
        
        # Calcul tailles buffers
        self.frame_duration_s = self.config.frame_duration_ms / 1000.0
        self.frame_size = int(self.sample_rate * self.frame_duration_s)
        
        # Nombre frames pour détection
        self.min_speech_frames = int(
            self.config.min_speech_duration_ms / self.config.frame_duration_ms
        )
        self.max_silence_frames = int(
            self.config.max_silence_duration_ms / self.config.frame_duration_ms
        )
        self.pre_speech_frames = int(
            self.config.pre_speech_buffer_ms / self.config.frame_duration_ms
        )
        self.post_speech_frames = int(
            self.config.post_speech_buffer_ms / self.config.frame_duration_ms
        )
        
        # État
        self.reset()
        
        self.logger.info(
            f"VAD configuré: frame={self.config.frame_duration_ms}ms, "
            f"min_speech={self.config.min_speech_duration_ms}ms, "
            f"max_silence={self.config.max_silence_duration_ms}ms"
        )
    
    def reset(self):
        """Réinitialise l'état du VAD."""
        self.is_speech = False
        self.speech_started = False
        self.consecutive_speech_frames = 0
        self.consecutive_silence_frames = 0
        self.ring_buffer = deque(maxlen=self.pre_speech_frames)
        self.audio_buffer = []
    
    def _frame_to_bytes(self, frame: np.ndarray) -> bytes:
        """
        Convertit frame float32 en bytes int16 pour WebRTC VAD.
        
        Args:
            frame: Frame audio float32 [-1, 1]
            
        Returns:
            Bytes PCM int16
        """
        # Normaliser et convertir
        frame_int16 = (frame * 32767).astype(np.int16)
        return frame_int16.tobytes()
    
    def _check_energy(self, frame: np.ndarray) -> bool:
        """
        Vérifie si l'énergie de la frame dépasse le seuil minimum.
        
        Args:
            frame: Frame audio
            
        Returns:
            True si énergie suffisante
        """
        rms = np.sqrt(np.mean(frame**2))
        return rms >= self.config.energy_threshold
    
    def process_frame(self, frame: np.ndarray) -> Tuple[bool, bool]:
        """
        Traite une frame audio et détecte la parole.
        
        Args:
            frame: Frame audio float32 de taille frame_size
            
        Returns:
            Tuple (is_speech, speech_ended)
            - is_speech: True si parole détectée dans cette frame
            - speech_ended: True si fin de parole détectée
        """
        # Validation taille
        if len(frame) != self.frame_size:
            self.logger.warning(
                f"Frame size incorrecte: {len(frame)} vs {self.frame_size} attendu"
            )
            # Padding ou truncate
            if len(frame) < self.frame_size:
                frame = np.pad(frame, (0, self.frame_size - len(frame)))
            else:
                frame = frame[:self.frame_size]
        
        # Vérification énergie minimum
        if not self._check_energy(frame):
            is_speech_frame = False
        else:
            # Détection VAD WebRTC
            try:
                frame_bytes = self._frame_to_bytes(frame)
                is_speech_frame = self.vad.is_speech(frame_bytes, self.sample_rate)
            except Exception as e:
                self.logger.error(f"Erreur VAD: {e}")
                is_speech_frame = False
        
        speech_ended = False
        
        if is_speech_frame:
            # Parole détectée
            self.consecutive_speech_frames += 1
            self.consecutive_silence_frames = 0
            
            # Début parole détecté
            if not self.speech_started:
                if self.consecutive_speech_frames >= self.min_speech_frames:
                    self.speech_started = True
                    self.is_speech = True
                    # Ajouter buffer pré-parole
                    self.audio_buffer.extend(self.ring_buffer)
                    self.logger.debug("🎤 Début parole détecté")
            
            # Ajouter frame au buffer si parole active
            if self.speech_started:
                self.audio_buffer.append(frame)
            else:
                # Sinon, ajouter au ring buffer (pré-parole)
                self.ring_buffer.append(frame)
        else:
            # Silence détecté
            self.consecutive_silence_frames += 1
            self.consecutive_speech_frames = 0
            
            if self.speech_started:
                # En parole: accumuler silence post-parole
                self.audio_buffer.append(frame)
                
                # Fin parole détectée si silence prolongé
                if self.consecutive_silence_frames >= self.max_silence_frames:
                    speech_ended = True
                    self.is_speech = False
                    self.logger.debug("🔇 Fin parole détectée")
            else:
                # Pas encore en parole: ring buffer
                self.ring_buffer.append(frame)
        
        return is_speech_frame, speech_ended
    
    def process_audio(
        self,
        audio: np.ndarray,
        max_duration: Optional[float] = None
    ) -> Tuple[Optional[np.ndarray], float]:
        """
        Traite un flux audio complet et extrait les segments de parole.
        
        Args:
            audio: Signal audio complet
            max_duration: Durée max traitement (secondes, None = illimité)
            
        Returns:
            Tuple (audio_speech, duration)
            - audio_speech: Audio contenant uniquement parole (ou None si rien)
            - duration: Durée audio parole (secondes)
        """
        self.reset()
        
        # Découper en frames
        num_frames = len(audio) // self.frame_size
        max_frames = int(max_duration * self.sample_rate / self.frame_size) if max_duration else None
        
        frames_processed = 0
        
        for i in range(num_frames):
            if max_frames and frames_processed >= max_frames:
                break
            
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio[start:end]
            
            is_speech_frame, speech_ended = self.process_frame(frame)
            frames_processed += 1
            
            # Arrêt si fin parole détectée
            if speech_ended:
                break
        
        # Extraction audio parole
        if not self.audio_buffer:
            self.logger.debug("Aucune parole détectée")
            return None, 0.0
        
        audio_speech = np.concatenate(self.audio_buffer)
        duration = len(audio_speech) / self.sample_rate
        
        self.logger.info(f"✅ Parole extraite: {duration:.2f}s ({len(self.audio_buffer)} frames)")
        
        return audio_speech, duration
    
    def stream_process(
        self,
        frame_generator,
        max_duration: float = 10.0,
        callback: Optional[callable] = None
    ) -> Tuple[Optional[np.ndarray], float]:
        """
        Traite un flux audio en temps réel frame par frame.
        
        Args:
            frame_generator: Générateur de frames audio
            max_duration: Durée max enregistrement (secondes)
            callback: Fonction appelée à chaque frame (frame, is_speech, speech_ended)
            
        Returns:
            Tuple (audio_speech, duration)
        """
        self.reset()
        
        max_frames = int(max_duration * self.sample_rate / self.frame_size)
        frames_processed = 0
        
        try:
            for frame in frame_generator:
                if frames_processed >= max_frames:
                    self.logger.debug("Durée max atteinte")
                    break
                
                is_speech_frame, speech_ended = self.process_frame(frame)
                frames_processed += 1
                
                # Callback optionnel
                if callback:
                    callback(frame, is_speech_frame, speech_ended)
                
                # Arrêt si fin parole
                if speech_ended:
                    break
                    
        except Exception as e:
            self.logger.error(f"Erreur stream processing: {e}")
        
        # Extraction audio parole
        if not self.audio_buffer:
            return None, 0.0
        
        audio_speech = np.concatenate(self.audio_buffer)
        duration = len(audio_speech) / self.sample_rate
        
        return audio_speech, duration
    
    def get_stats(self) -> dict:
        """Retourne les statistiques courantes."""
        return {
            "speech_started": self.speech_started,
            "is_speech": self.is_speech,
            "consecutive_speech_frames": self.consecutive_speech_frames,
            "consecutive_silence_frames": self.consecutive_silence_frames,
            "audio_buffer_frames": len(self.audio_buffer),
            "audio_duration": len(self.audio_buffer) * self.frame_duration_s if self.audio_buffer else 0.0
        }

# Fonction utilitaire pour créer VAD avec profils prédéfinis
def create_vad(
    profile: str = "normal",
    sample_rate: int = 16000
) -> VADEngine:
    """
    Crée un VAD avec profil prédéfini.
    
    Args:
        profile: "rapide", "normal" ou "qualite"
        sample_rate: Fréquence échantillonnage
        
    Returns:
        VADEngine configuré
    """
    profiles = {
        "rapide": VADConfig(
            aggressiveness=3,
            frame_duration_ms=30,
            min_speech_duration_ms=200,
            max_silence_duration_ms=1000,
            pre_speech_buffer_ms=100,
            post_speech_buffer_ms=200
        ),
        "normal": VADConfig(
            aggressiveness=2,
            frame_duration_ms=30,
            min_speech_duration_ms=300,
            max_silence_duration_ms=1500,
            pre_speech_buffer_ms=200,
            post_speech_buffer_ms=400
        ),
        "qualite": VADConfig(
            aggressiveness=1,
            frame_duration_ms=30,
            min_speech_duration_ms=400,
            max_silence_duration_ms=2000,
            pre_speech_buffer_ms=300,
            post_speech_buffer_ms=500
        )
    }
    
    if profile not in profiles:
        logger.warning(f"Profil '{profile}' inconnu, utilisation 'normal'")
        profile = "normal"
    
    config = profiles[profile]
    logger.info(f"Création VAD avec profil '{profile}'")
    
    return VADEngine(sample_rate=sample_rate, config=config)

