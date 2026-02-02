#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Gestionnaire Audio Centralisé pour QAIA
Singleton gérant tous les streams audio avec cleanup robuste et fallback automatique.
"""

# /// script
# dependencies = [
#   "numpy>=1.22.0",
#   "sounddevice>=0.4.5",
# ]
# ///

import os
import logging
import threading
import time
import numpy as np
import sounddevice as sd
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import traceback

try:
    from config.system_config import MODEL_CONFIG
except ImportError:
    MODEL_CONFIG = None

logger = logging.getLogger(__name__)

class RecordingStrategy(Enum):
    """Stratégies d'enregistrement disponibles."""
    INPUTSTREAM_VAD = "inputstream_vad"      # Optimal: InputStream + VAD
    INPUTSTREAM_FIXED = "inputstream_fixed"  # Fiable: InputStream + durée fixe
    REC_WAIT = "rec_wait"                    # Fallback: sd.rec() + sd.wait()
    PYAUDIO = "pyaudio"                      # Fallback ultime: PyAudio

@dataclass
class AudioData:
    """Données audio enregistrées."""
    samples: np.ndarray
    sample_rate: int
    duration: float
    rms: float
    clipping_percent: float
    strategy_used: RecordingStrategy

@dataclass
class DeviceInfo:
    """Informations périphérique audio."""
    name: str
    index: int
    channels: int
    sample_rate: int
    is_default: bool

class AudioManager:
    """
    Gestionnaire audio singleton avec cleanup robuste et fallback automatique.
    
    Responsabilités:
    - Gestion centralisée des streams audio
    - Cleanup automatique des ressources
    - Fallback multi-niveaux en cas d'échec
    - Monitoring qualité audio
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Pattern Singleton thread-safe."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le gestionnaire audio."""
        if self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialisation AudioManager...")
        
        # Configuration centralisée (system_config)
        if MODEL_CONFIG and "audio" in MODEL_CONFIG:
            audio_cfg = MODEL_CONFIG["audio"]
            self.sample_rate = int(audio_cfg.get("sampling_rate", 16000))
            self.channels = int(audio_cfg.get("channels", 1))
        else:
            self.sample_rate = 16000
            self.channels = 1
        self.dtype = 'float32'
        self._input_device_id = None
        if MODEL_CONFIG and "microphone" in MODEL_CONFIG:
            self._input_device_id = MODEL_CONFIG["microphone"].get("input_device_id")
        
        # État
        self._active_stream = None
        self._recording_in_progress = False
        self._stream_lock = threading.Lock()
        
        # Statistiques stratégies
        self._strategy_stats = {
            RecordingStrategy.INPUTSTREAM_VAD: {"success": 0, "failure": 0},
            RecordingStrategy.INPUTSTREAM_FIXED: {"success": 0, "failure": 0},
            RecordingStrategy.REC_WAIT: {"success": 0, "failure": 0},
            RecordingStrategy.PYAUDIO: {"success": 0, "failure": 0},
        }
        
        # Stratégie courante (auto-sélectionnée)
        self._current_strategy = RecordingStrategy.INPUTSTREAM_FIXED
        
        # Test périphérique audio (utilise input_device_id de la config si défini)
        try:
            self._device_info = self._detect_audio_device(self._input_device_id)
            self.logger.info(f"✅ Périphérique audio détecté: {self._device_info.name}")
        except Exception as e:
            self.logger.error(f"❌ Erreur détection périphérique: {e}")
            self._device_info = None
        
        self._initialized = True
        self.logger.info("✅ AudioManager initialisé")
    
    def _detect_audio_device(self, device_id: Optional[int] = None) -> DeviceInfo:
        """Détecte le périphérique audio (par défaut ou celui indiqué par device_id)."""
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            target_id = device_id if device_id is not None else default_input

            if isinstance(target_id, int) and 0 <= target_id < len(devices):
                device = devices[target_id]
                if device['max_input_channels'] > 0:
                    return DeviceInfo(
                        name=device['name'],
                        index=target_id,
                        channels=device['max_input_channels'],
                        sample_rate=int(device['default_samplerate']),
                        is_default=(target_id == default_input)
                    )
            # Fallback: périphérique par défaut ou premier entrée
            if isinstance(default_input, int):
                device = devices[default_input]
                return DeviceInfo(
                    name=device['name'],
                    index=default_input,
                    channels=device['max_input_channels'],
                    sample_rate=int(device['default_samplerate']),
                    is_default=True
                )
            for idx, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    return DeviceInfo(
                        name=device['name'],
                        index=idx,
                        channels=device['max_input_channels'],
                        sample_rate=int(device['default_samplerate']),
                        is_default=False
                    )
            raise RuntimeError("Aucun périphérique d'entrée audio trouvé")
                
        except Exception as e:
            self.logger.error(f"Erreur détection périphérique: {e}")
            raise
    
    def get_device_info(self) -> Optional[DeviceInfo]:
        """Retourne les informations du périphérique audio."""
        return self._device_info
    
    def test_microphone(self) -> Dict[str, Any]:
        """
        Test rapide du microphone.
        
        Returns:
            Dict avec métriques qualité
        """
        try:
            self.logger.info("Test microphone (1s)...")
            
            # Enregistrement test 1s
            test_duration = 1.0
            rec_kw = dict(
                frames=int(test_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
            )
            if self._input_device_id is not None:
                rec_kw["device"] = self._input_device_id
            audio_data = sd.rec(**rec_kw)
            sd.wait()
            
            # Analyse
            rms = float(np.sqrt(np.mean(audio_data**2)))
            peak = float(np.max(np.abs(audio_data)))
            clipping = int((np.abs(audio_data) > 0.99).sum())
            clipping_percent = (clipping / len(audio_data)) * 100
            
            # Évaluation qualité
            if rms < 0.001:
                quality = "❌ Trop faible (vérifier micro)"
            elif rms < 0.01:
                quality = "⚠️ Faible (parler plus fort)"
            elif rms < 0.1:
                quality = "✅ Bon"
            elif rms < 0.3:
                quality = "✅ Excellent"
            else:
                quality = "⚠️ Trop fort (risque saturation)"
            
            metrics = {
                "rms": rms,
                "peak": peak,
                "clipping_count": clipping,
                "clipping_percent": clipping_percent,
                "quality": quality,
                "status": "ok"
            }
            
            self.logger.info(f"Test micro: RMS={rms:.3f}, Quality={quality}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Erreur test microphone: {e}")
            return {"status": "error", "error": str(e)}
    
    def cleanup_stream(self, stream=None) -> bool:
        """
        Nettoie un stream audio avec méthodes robustes.
        
        Args:
            stream: Stream à nettoyer (None = stream actif)
            
        Returns:
            True si succès
        """
        if stream is None:
            stream = self._active_stream
        
        if stream is None:
            return True
        
        try:
            self.logger.debug("Cleanup stream...")
            
            # Méthode 1: Fermeture normale
            try:
                if hasattr(stream, 'active') and stream.active:
                    stream.stop()
                    time.sleep(0.05)
                stream.close()
                self.logger.debug("✅ Stream fermé (close)")
                return True
            except Exception as e1:
                self.logger.warning(f"close() échoué: {e1}")
            
            # Méthode 2: Abort forcé
            try:
                if hasattr(stream, 'abort'):
                    stream.abort()
                    self.logger.debug("✅ Stream fermé (abort)")
                    return True
            except Exception as e2:
                self.logger.warning(f"abort() échoué: {e2}")
            
            # Méthode 3: Suppression référence
            try:
                del stream
                self.logger.debug("✅ Stream supprimé (del)")
                return True
            except Exception as e3:
                self.logger.warning(f"del échoué: {e3}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur cleanup stream: {e}")
            return False
        finally:
            self._active_stream = None
    
    def _record_inputstream_fixed(self, duration: float) -> Optional[AudioData]:
        """
        Enregistrement avec InputStream + durée fixe.
        Stratégie fiable avec timeout garanti.
        
        Args:
            duration: Durée enregistrement (secondes)
            
        Returns:
            AudioData ou None
        """
        try:
            self.logger.info(f"🎤 Enregistrement InputStream (fixe {duration}s)...")
            
            # Buffer
            audio_buffer = []
            frames_to_record = int(duration * self.sample_rate)
            frames_recorded = [0]
            
            def callback(indata, frames, time_info, status):
                if status:
                    self.logger.warning(f"Status audio: {status}")
                if frames_recorded[0] < frames_to_record:
                    audio_buffer.append(indata.copy())
                    frames_recorded[0] += len(indata)
            
            # Enregistrement avec timeout
            timeout_timer = threading.Timer(duration + 2.0, lambda: self.logger.warning("⚠️ Timeout enregistrement"))
            timeout_timer.start()
            
            try:
                stream_kw = dict(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    callback=callback,
                    blocksize=int(self.sample_rate * 0.1),
                )
                if self._input_device_id is not None:
                    stream_kw["device"] = self._input_device_id
                with sd.InputStream(**stream_kw) as stream:
                    self._active_stream = stream
                    time.sleep(duration)
            finally:
                timeout_timer.cancel()
                self._active_stream = None
            
            # Validation
            if not audio_buffer:
                self.logger.error("Aucun audio capturé")
                return None
            
            # Assemblage
            audio_data = np.concatenate(audio_buffer, axis=0)[:frames_to_record].flatten()
            
            # Métriques
            rms = float(np.sqrt(np.mean(audio_data**2)))
            clipping = int((np.abs(audio_data) > 0.99).sum())
            clipping_percent = (clipping / len(audio_data)) * 100
            
            self.logger.info(f"✅ Audio capturé: {duration}s, RMS={rms:.3f}, Clipping={clipping_percent:.1f}%")
            
            return AudioData(
                samples=audio_data,
                sample_rate=self.sample_rate,
                duration=duration,
                rms=rms,
                clipping_percent=clipping_percent,
                strategy_used=RecordingStrategy.INPUTSTREAM_FIXED
            )
            
        except Exception as e:
            self.logger.error(f"Erreur InputStream fixe: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def _record_rec_wait(self, duration: float) -> Optional[AudioData]:
        """
        Enregistrement avec sd.rec() + sd.wait().
        Fallback basique.
        
        Args:
            duration: Durée enregistrement (secondes)
            
        Returns:
            AudioData ou None
        """
        try:
            self.logger.info(f"🎤 Enregistrement rec+wait ({duration}s)...")
            
            rec_kw = dict(
                frames=int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
            )
            if self._input_device_id is not None:
                rec_kw["device"] = self._input_device_id
            audio_data = sd.rec(**rec_kw)
            sd.wait()
            
            audio_data = audio_data.flatten()
            
            # Métriques
            rms = float(np.sqrt(np.mean(audio_data**2)))
            clipping = int((np.abs(audio_data) > 0.99).sum())
            clipping_percent = (clipping / len(audio_data)) * 100
            
            self.logger.info(f"✅ Audio capturé (rec+wait): RMS={rms:.3f}")
            
            return AudioData(
                samples=audio_data,
                sample_rate=self.sample_rate,
                duration=duration,
                rms=rms,
                clipping_percent=clipping_percent,
                strategy_used=RecordingStrategy.REC_WAIT
            )
            
        except Exception as e:
            self.logger.error(f"Erreur rec+wait: {e}")
            return None
    
    def record(
        self,
        duration: float = 5.0,
        strategy: Optional[RecordingStrategy] = None
    ) -> Optional[AudioData]:
        """
        Enregistre audio avec stratégie automatique ou spécifiée.
        
        Args:
            duration: Durée enregistrement (secondes)
            strategy: Stratégie à utiliser (None = auto)
            
        Returns:
            AudioData ou None
        """
        with self._stream_lock:
            if self._recording_in_progress:
                self.logger.warning("Enregistrement déjà en cours")
                return None
            
            self._recording_in_progress = True
        
        try:
            # Sélection stratégie
            if strategy is None:
                strategy = self._current_strategy
            
            self.logger.info(f"Enregistrement avec stratégie: {strategy.value}")
            
            # Tentative stratégie principale
            audio_data = None
            
            if strategy == RecordingStrategy.INPUTSTREAM_FIXED:
                audio_data = self._record_inputstream_fixed(duration)
            elif strategy == RecordingStrategy.REC_WAIT:
                audio_data = self._record_rec_wait(duration)
            
            # Mise à jour statistiques
            if audio_data:
                self._strategy_stats[strategy]["success"] += 1
                return audio_data
            else:
                self._strategy_stats[strategy]["failure"] += 1
                
                # Fallback automatique
                self.logger.warning(f"Échec {strategy.value}, tentative fallback...")
                
                if strategy != RecordingStrategy.REC_WAIT:
                    audio_data = self._record_rec_wait(duration)
                    if audio_data:
                        self._strategy_stats[RecordingStrategy.REC_WAIT]["success"] += 1
                        # Changer stratégie par défaut si échecs répétés
                        if self._strategy_stats[strategy]["failure"] >= 3:
                            self.logger.warning(f"Basculement stratégie: {strategy.value} → rec_wait")
                            self._current_strategy = RecordingStrategy.REC_WAIT
                        return audio_data
                
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur enregistrement: {e}")
            self.logger.error(traceback.format_exc())
            return None
        finally:
            self._recording_in_progress = False
            self.cleanup_stream()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques des stratégies."""
        return {
            "current_strategy": self._current_strategy.value,
            "stats": {
                strategy.value: {
                    "success": stats["success"],
                    "failure": stats["failure"],
                    "success_rate": (
                        stats["success"] / (stats["success"] + stats["failure"])
                        if (stats["success"] + stats["failure"]) > 0
                        else 0.0
                    )
                }
                for strategy, stats in self._strategy_stats.items()
            }
        }
    
    def cleanup(self):
        """Nettoie toutes les ressources."""
        try:
            self.logger.info("Nettoyage AudioManager...")
            self.cleanup_stream()
            self._recording_in_progress = False
            self.logger.info("✅ AudioManager nettoyé")
        except Exception as e:
            self.logger.error(f"Erreur cleanup AudioManager: {e}")

# Instance singleton globale
audio_manager = AudioManager()

