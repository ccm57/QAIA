#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de reconnaissance vocale utilisant Wav2Vec2.

"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "sounddevice>=0.4.5",
#   "scipy>=1.9.0", # Pour scipy.io.wavfile
#   "transformers>=4.26.0",
#   "numpy>=1.22.0"
# ]
# ///

import os
import logging
import traceback
from pathlib import Path
import threading
import time
from typing import Optional, Tuple, Dict, List
import torch
import gc
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from utils.monitoring import record_timing

try:
    from config.system_config import MODEL_CONFIG
except ImportError:
    MODEL_CONFIG = None

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.propagate = True

def record_audio(duration: float = 5.0, sample_rate: int = 16000, output_dir: str = None) -> str:
    """
    Enregistre un court extrait audio via une fonction de module (compatibilité).

    Args:
        duration (float): Durée en secondes.
        sample_rate (int): Fréquence d'échantillonnage.
        output_dir (str): Dossier de sortie. Par défaut, data/audio.

    Returns:
        str: Chemin du fichier WAV créé, None en cas d'erreur.
    """
    try:
        base_dir = Path(__file__).parent.parent.absolute()
        audio_dir = Path(output_dir) if output_dir else (base_dir / "data" / "audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Enregistrement audio module-level: {duration}s @ {sample_rate}Hz")
        frames = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()

        timestamp = int(time.time())
        audio_file = audio_dir / f"recording_{timestamp}.wav"
        wav.write(str(audio_file), sample_rate, (frames * 32767).astype(np.int16))
        return str(audio_file) if audio_file.exists() else None
    except Exception as e:
        logger.error(f"Erreur record_audio (module): {e}")
        return None


def transcribe_audio(audio_path: str) -> str:
    """
    Fonction de compatibilité module-level: transcrit un fichier audio.

    Args:
        audio_path (str): Chemin du fichier audio.

    Returns:
        str: Transcription ou message d'erreur.
    """
    try:
        agent = Wav2VecVoiceAgent()
        text, _conf = agent.transcribe_audio(audio_path)
        return text
    except Exception as e:
        logger.error(f"Erreur transcribe_audio (module): {e}")
        return f"Erreur: {e}"

class Wav2VecVoiceAgent:
    """Agent de reconnaissance vocale simplifié pour QAIA."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Implémentation thread-safe du singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path="CONFIG.py", debug=False, enable_monitoring=True, preferred_model: str = "jonatasgrosman/wav2vec2-large-xlsr-53-french"):
        """
        Initialise l'agent de reconnaissance vocale.
        
        Args:
            config_path (str): Chemin vers le fichier de configuration
            debug (bool): Active le mode debug avec plus de logs
            enable_monitoring (bool): Active le monitoring des performances
        """
        if self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        
        # Configurer le niveau de log
        self.debug = debug
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        self.logger.info("Initialisation de l'agent vocal (version corrigée)")
        
        # Chemins
        self.base_dir = Path(__file__).parent.parent.absolute()
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION STT (centralisée via system_config)
        # ═══════════════════════════════════════════════════════════
        if MODEL_CONFIG and "speech" in MODEL_CONFIG:
            speech_cfg = MODEL_CONFIG["speech"]
            self.sample_rate = int(speech_cfg.get("sampling_rate", 16000))
            use_gpu_stt = False
            if MODEL_CONFIG.get("gpu_audio") and MODEL_CONFIG["gpu_audio"].get("USE_GPU_FOR_STT"):
                use_gpu_stt = torch.cuda.is_available()
            self.device = "cuda" if use_gpu_stt else str(speech_cfg.get("device", "cpu"))
        else:
            self.sample_rate = 16000
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Cache HuggingFace : s'assurer que le répertoire existe et est accessible
        self.hf_cache_dir = self.base_dir / "models" / "huggingface_cache"
        self.hf_cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ['HF_HOME'] = str(self.hf_cache_dir)
        os.environ['HUGGINGFACE_HUB_CACHE'] = str(self.hf_cache_dir)
        self.audio_dir = self.base_dir / "data" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # État
        self._model_loaded = False
        self._conversation_mode = False
        self._lazy_load = True
        self._last_load_error: Optional[str] = None
        self._load_lock = threading.Lock()
        
        # Modèle et processeur
        self.model = None
        self.processor = None
        self.preferred_model = preferred_model
        self.model_name = self.preferred_model  
        # Modèle de secours (base stable)
        self.fallback_model = "facebook/wav2vec2-base-960h"
        self.correction_dict = {}
        self.transcription_history = []
        self.max_history_size = 10
        self.AUDIO_DIR = self.audio_dir
        
        # Initialisation du monitoring simplifié
        self.enable_monitoring = enable_monitoring
        
        self._initialized = True
        self.logger.info(f"Agent vocal initialisé (GPU: {self.device})")
        # Désactiver torch.compile/dynamo pour éviter les tensors 'meta' avec chargement Flax
        try:
            import torch._dynamo as _dynamo  # type: ignore
            _dynamo.disable()
        except Exception:
            pass
        os.environ.setdefault("TORCH_COMPILE", "0")
    
    def _ensure_model_loaded(self, force_reload=False) -> bool:
        """
        S'assure que le modèle soit chargé avant une inférence.
        Thread-safe : un seul chargement à la fois.
        
        Args:
            force_reload (bool): Force le rechargement même si déjà chargé
            
        Returns:
            bool: True si le modèle est chargé avec succès, False sinon
        """
        if self._model_loaded and not force_reload:
            return True

        with self._load_lock:
            if self._model_loaded and not force_reload:
                return True
            self._last_load_error = None
            try:
                model_name = self.preferred_model
                self.logger.info(f"🔄 Chargement modèle STT: {model_name} (cache: {self.hf_cache_dir})")

                try:
                    self.processor = Wav2Vec2Processor.from_pretrained(model_name)
                    self.model = Wav2Vec2ForCTC.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                    )
                    self.logger.info(f"✅ Modèle STT chargé: {model_name}")
                except Exception as e:
                    self.logger.error(f"❌ Échec chargement {model_name}: {e}")
                    if self.fallback_model and self.fallback_model != model_name:
                        self.logger.warning(f"⚠️ Tentative fallback: {self.fallback_model}")
                        try:
                            self.processor = Wav2Vec2Processor.from_pretrained(self.fallback_model)
                            self.model = Wav2Vec2ForCTC.from_pretrained(
                                self.fallback_model,
                                torch_dtype=torch.float32,
                            )
                            model_name = self.fallback_model
                            self.model_name = self.fallback_model
                            self.logger.info(f"✅ Fallback actif: {self.fallback_model}")
                        except Exception as e2:
                            self.logger.error(f"❌ Fallback échoué: {e2}")
                            raise
                    else:
                        raise

                if self.device == "cuda":
                    self.model = self.model.to(self.device)
                self.model.eval()
                self._model_loaded = True
                return True

            except Exception as e:
                self._last_load_error = str(e)
                self.logger.error(f"Erreur lors du chargement du modèle STT: {e}")
                self.logger.error(traceback.format_exc())
                return False
            
    def _force_unload_model(self):
        """Force le déchargement du modèle et du processeur de la mémoire."""
        try:
            self.model = None
            self.processor = None
            self._model_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Modèle déchargé de la mémoire")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors du déchargement du modèle: {e}")
            return False
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Prétraite l'audio pour améliorer la qualité STT.
        Applique filtrage, normalisation et réduction bruit.
        
        Args:
            audio_data: Signal audio (numpy array float32)
            sample_rate: Fréquence d'échantillonnage
            
        Returns:
            Audio prétraité
        """
        from scipy.signal import butter, filtfilt
        
        # 1. Filtrage passe-haut (éliminer bruit basse fréquence < 100Hz, plus agressif)
        nyquist = sample_rate / 2
        cutoff = 100  # Hz (augmenté de 80 à 100 pour mieux éliminer le bruit)
        b, a = butter(4, cutoff / nyquist, btype='high')
        audio_data = filtfilt(b, a, audio_data)
        
        # 2. Normalisation RMS cible (augmentée pour meilleure intelligibilité)
        target_rms = 0.20  # Augmenté de 0.15 à 0.20 pour signal plus fort
        current_rms = np.sqrt(np.mean(audio_data**2))
        if current_rms > 1e-6:
            gain = target_rms / current_rms
            # Limiter le gain pour éviter amplification excessive du bruit
            gain = np.clip(gain, 0.5, 4.0)  # Augmenté de 3.0 à 4.0 pour permettre plus de gain
            audio_data = audio_data * gain
            self.logger.debug(f"Normalisation RMS: {current_rms:.3f} → {target_rms:.3f} (gain={gain:.2f})")
        
        # 3. Clipping soft (éviter distorsion dure)
        # Utilise tanh pour compression douce des pics
        audio_data = np.tanh(audio_data * 1.2) / 1.2
        
        # 4. Réduction de bruit simple (filtre médian pour éliminer les pics isolés)
        # Appliquer un filtre médian sur de très courtes fenêtres pour éliminer les clics
        if len(audio_data) > 10:
            from scipy.signal import medfilt
            audio_data = medfilt(audio_data, kernel_size=3)
        
        # 5. Normalisation finale pour éviter saturation
        max_val = np.abs(audio_data).max()
        if max_val > 0.95:  # Si proche de la saturation
            audio_data = audio_data * 0.95 / max_val
        
        return audio_data

    def transcribe_audio(self, audio_path: str, force_reload: bool = False) -> Tuple[str, float]:
        """
        Transcrit un fichier audio en texte.
        
        Args:
            audio_path (str): Chemin vers le fichier audio à transcrire
            force_reload (bool): Force le rechargement du modèle
            
        Returns:
            tuple: (texte transcrit, score de confiance)
        """
        try:
            # Mesurer le temps de transcription
            start_time = time.time()
            t_checkpoint = start_time
            
            # Charger le modèle si nécessaire
            if not self._ensure_model_loaded(force_reload):
                err = getattr(self, "_last_load_error", None) or ""
                hint = (" " + err.replace("\n", " ")[:80] + ("…" if len(err) > 80 else "")) if err else ""
                return f"Erreur: Modèle non disponible{hint}", 0.0
            else:
                record_timing("asr", "load_model", time.time() - t_checkpoint)
                t_checkpoint = time.time()
            
            # Vérifier le fichier
            if not audio_path or not os.path.isfile(audio_path):
                self.logger.error(f"Fichier audio introuvable: {audio_path}")
                return "Erreur: fichier audio introuvable", 0.0

            self.logger.info(f"Transcription de: {audio_path}")
            
            # Charger l'audio
            sample_rate, audio_data = wav.read(audio_path)
            record_timing("asr", "read_wav", time.time() - t_checkpoint)
            t_checkpoint = time.time()
            
            # Assurer mono
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                # Moyenne des canaux → mono
                audio_data = audio_data.mean(axis=1)

            # Conversion en float32 si nécessaire
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_data = (audio_data.astype(np.float32) / 2147483648.0)
            elif audio_data.dtype == np.float64:
                audio_data = audio_data.astype(np.float32)
            
            # Rééchantillonner si nécessaire
            if sample_rate != self.sample_rate:
                from scipy.signal import resample_poly
                # Utiliser un rééchantillonnage polyphasé plus rapide et précis
                audio_data = resample_poly(audio_data, self.sample_rate, sample_rate)
            record_timing("asr", "resample", time.time() - t_checkpoint)
            t_checkpoint = time.time()
            
            # NOUVEAU: Prétraitement audio pour améliorer qualité STT
            audio_data = self._preprocess_audio(audio_data, self.sample_rate)
            record_timing("asr", "preprocess_audio", time.time() - t_checkpoint)
            t_checkpoint = time.time()
            
            # Préprocesser avec le processor
            inputs = self.processor(
                audio_data,
                sampling_rate=self.sample_rate,
                return_tensors="pt",
                padding=True
            )
            record_timing("asr", "preprocess", time.time() - t_checkpoint)
            t_checkpoint = time.time()
            # Forcer CPU/float32 pour éviter 'meta' device issues
            inputs = {k: v.to("cpu", dtype=torch.float32) for k, v in inputs.items()}
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inférence
            with torch.no_grad():
                logits = self.model(**inputs).logits
            record_timing("asr", "inference", time.time() - t_checkpoint)
            t_checkpoint = time.time()
            
            # Décoder avec CTC
            predicted_ids = torch.argmax(logits, dim=-1)
            
            # CORRECTION: Utiliser decode au lieu de batch_decode pour CTC
            # batch_decode ne gère pas correctement les tokens CTC répétés
            transcription = self.processor.decode(predicted_ids[0])
            
            record_timing("asr", "decode", time.time() - t_checkpoint)
            
            # Calculer un score de confiance simple
            confidence = float(torch.max(torch.softmax(logits, dim=-1)).cpu())
            
            # Calculer le temps de transcription
            transcription_time = time.time() - start_time
            record_timing("asr", "transcription", transcription_time)
            
            # Ajouter à l'historique
            self.transcription_history.append((transcription, confidence))
            if len(self.transcription_history) > self.max_history_size:
                self.transcription_history.pop(0)
            
            # Log de statistiques
            self.logger.info(f"Transcription effectuée en {transcription_time:.2f}s avec confiance {confidence:.2f}")
            
            return transcription, confidence
            
        except Exception as e:
            self.logger.error(f"Erreur de transcription: {e}")
            self.logger.error(traceback.format_exc())
            return f"Erreur: {str(e)}", 0.0

    def transcribe_with_events(self, audio_path: str, force_reload: bool = False) -> Tuple[str, float]:
        """
        Transcrit un fichier audio en texte avec émission d'événements temps réel.
        
        Args:
            audio_path (str): Chemin vers le fichier audio à transcrire
            force_reload (bool): Force le rechargement du modèle
            
        Returns:
            tuple: (texte transcrit, score de confiance)
        """
        from interface.events.event_bus import event_bus
        
        try:
            # Émettre début transcription
            # Émettre événement agent.state_change pour STT (EN_COURS)
            event_data_start = {
                'name': 'STT',
                'status': 'EN_COURS',
                'activity_percentage': 50.0,
                'details': 'Transcription audio en cours...',
                'last_update': time.time()
            }
            event_bus.emit('agent.state_change', event_data_start)
            self.logger.info(f"Événement agent.state_change émis pour STT (EN_COURS): {event_data_start}")
            
            event_bus.emit('stt.start', {
                'timestamp': time.time(),
                'audio_path': audio_path
            })
            
            self.logger.info(f"Transcription avec événements: {audio_path}")
            
            # Émettre progression
            event_bus.emit('stt.transcribing', {
                'timestamp': time.time(),
                'status': 'Chargement du modèle...'
            })
            
            # Assurer modèle chargé
            if not self._ensure_model_loaded(force_reload):
                err = getattr(self, "_last_load_error", None) or ""
                hint = (" " + err.replace("\n", " ")[:80] + ("…" if len(err) > 80 else "")) if err else ""
                error_msg = f"Erreur: Modèle non disponible{hint}"
                event_bus.emit('stt.error', {
                    'timestamp': time.time(),
                    'error': error_msg
                })
                return error_msg, 0.0
            
            # Émettre progression
            event_bus.emit('stt.transcribing', {
                'timestamp': time.time(),
                'status': 'Analyse audio...'
            })
            
            # Effectuer transcription (réutilise la logique existante)
            transcription, confidence = self.transcribe_audio(audio_path, force_reload=False)
            
            # Émettre complétion
            # Émettre événement agent.state_change pour STT (ACTIF après transcription)
            # IMPORTANT: S'assurer que l'événement est bien émis même si transcription contient "Erreur"
            if transcription and not transcription.lower().startswith("erreur"):
                event_bus.emit('agent.state_change', {
                    'name': 'STT',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Transcription terminée: "{transcription[:50] if transcription else "N/A"}..."',
                    'last_update': time.time()
                })
            else:
                # En cas d'erreur, émettre statut ERREUR
                event_bus.emit('agent.state_change', {
                    'name': 'STT',
                    'status': 'ERREUR',
                    'activity_percentage': 0.0,
                    'details': f'Erreur transcription: {transcription}',
                    'last_update': time.time()
                })
            
            event_bus.emit('stt.complete', {
                'timestamp': time.time(),
                'transcription': transcription,
                'confidence': confidence
            })
            
            # Log pour debug
            self.logger.info(f"Événement agent.state_change émis pour STT: status=ACTIF, confiance={confidence:.2f}")
            
            return transcription, confidence
            
        except Exception as e:
            error_msg = f"Erreur: {str(e)}"
            event_bus.emit('stt.error', {
                'timestamp': time.time(),
                'error': error_msg
            })
            self.logger.error(f"Erreur transcription avec événements: {e}")
            return error_msg, 0.0
    
    def prepare_for_conversation(self):
        """
        Prépare l'agent pour le mode conversation en préchargeant le modèle.
        
        Returns:
            bool: True si la préparation a réussi, False sinon
        """
        try:
            self.logger.info("Préparation du mode conversation...")
            self._conversation_mode = True
            
            # Précharger le modèle
            if not self._ensure_model_loaded():
                return False
            
            # Optimiser la mémoire GPU si disponible
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.backends.cudnn.benchmark = True
            
            self.logger.info("Mode conversation prêt")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation du mode conversation: {e}")
            self._conversation_mode = False
            return False
    
    def exit_conversation_mode(self):
        """
        Quitte le mode conversation et libère les ressources réservées.
        
        Returns:
            bool: True si la sortie a réussi, False sinon
        """
        try:
            if not self._conversation_mode:
                return True
                
            self.logger.info("Sortie du mode conversation...")
            self._conversation_mode = False
            
            # Libérer la mémoire si nécessaire
            if self._model_loaded and not self._lazy_load:
                self._force_unload_model()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sortie du mode conversation: {e}")
            return False
    
    def record_audio_with_vad(
        self,
        max_duration: float = 10.0,
        silence_threshold: float = 0.015,
        silence_duration: float = 1.5,
        min_duration: float = 0.5
    ) -> Optional[str]:
        """
        Enregistre l'audio avec détection de fin de parole (VAD).
        Arrête automatiquement après silence prolongé.
        
        Args:
            max_duration: Durée maximale d'enregistrement (secondes)
            silence_threshold: Seuil RMS pour détecter le silence
            silence_duration: Durée de silence pour arrêter (secondes)
            min_duration: Durée minimale d'enregistrement (secondes)
            
        Returns:
            str: Chemin vers le fichier audio ou None
        """
        try:
            self.logger.info(f"Enregistrement avec VAD (max {max_duration}s)...")
            
            # Buffer pour accumuler l'audio
            audio_buffer = []
            silence_start = None
            recording_start = time.time()
            is_speaking = False
            
            # Callback pour traiter les chunks audio
            def audio_callback(indata, frames, time_info, status):
                nonlocal silence_start, is_speaking
                
                # Calculer RMS du chunk
                rms = np.sqrt(np.mean(indata**2))
                
                # Ajouter au buffer
                audio_buffer.append(indata.copy())
                
                # Détection parole/silence
                if rms > silence_threshold:
                    is_speaking = True
                    silence_start = None
                else:
                    # Silence détecté
                    if is_speaking and silence_start is None:
                        silence_start = time.time()
            
            # Stream audio
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms chunks
            ):
                while True:
                    elapsed = time.time() - recording_start
                    
                    # Vérifier durée max
                    if elapsed > max_duration:
                        self.logger.info(f"Durée max atteinte ({max_duration}s)")
                        break
                    
                    # Vérifier silence prolongé (après durée min)
                    if (elapsed > min_duration and 
                        silence_start and 
                        (time.time() - silence_start > silence_duration)):
                        self.logger.info(f"Fin de parole détectée ({elapsed:.1f}s)")
                        break
                    
                    time.sleep(0.05)
            
            # Concaténer buffer
            if not audio_buffer:
                self.logger.error("Aucun audio capturé")
                return None
            
            audio_data = np.concatenate(audio_buffer, axis=0)
            
            # Appliquer normalisation gain
            audio_data = audio_data * 0.3
            
            # Analyser qualité
            rms = np.sqrt(np.mean(audio_data**2))
            clipping = (np.abs(audio_data) > 0.99).sum()
            clipping_percent = clipping / len(audio_data) * 100
            duration = len(audio_data) / self.sample_rate
            
            self.logger.info(f"Audio capturé: {duration:.1f}s, RMS={rms:.3f}, Clipping={clipping_percent:.1f}%")
            
            # Sauvegarder
            timestamp = int(time.time())
            audio_file = self.audio_dir / f"recording_{timestamp}.wav"
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wav.write(str(audio_file), self.sample_rate, audio_int16)
            
            if audio_file.exists():
                self.logger.info(f"✅ Enregistré: {audio_file}")
                return str(audio_file)
            else:
                self.logger.error("Échec sauvegarde")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur enregistrement VAD: {e}")
            return None

    def record_audio(self, duration=None, max_duration=None, use_vad=False):
        """
        Enregistre l'audio depuis le microphone en utilisant AudioManager.
        
        Args:
            duration (float, optional): Durée fixe d'enregistrement en secondes (défaut: 5.0)
            max_duration (float, optional): Durée maximale avec VAD (ignoré si use_vad=False)
            use_vad (bool): Utiliser VAD pour détection fin parole (défaut: False)
            
        Returns:
            str: Chemin vers le fichier audio enregistré ou None en cas d'erreur
        """
        try:
            # Importer AudioManager et VAD
            from agents.audio_manager import audio_manager
            from agents.vad_engine import create_vad
            
            # Durée par défaut
            if duration is None:
                duration = 5.0
            
            if use_vad and max_duration:
                # Enregistrement avec VAD
                self.logger.info(f"🎤 Enregistrement avec VAD (max {max_duration}s)...")
                
                # Créer VAD
                vad = create_vad(profile="normal", sample_rate=self.sample_rate)
                
                # Enregistrer avec AudioManager
                audio_data_obj = audio_manager.record(duration=max_duration)
                
                if audio_data_obj is None:
                    self.logger.error("Échec enregistrement AudioManager")
                    return None
                
                # Appliquer VAD pour extraire parole
                audio_speech, speech_duration = vad.process_audio(
                    audio_data_obj.samples,
                    max_duration=max_duration
                )
                
                if audio_speech is None or len(audio_speech) == 0:
                    self.logger.warning("Aucune parole détectée par VAD")
                    # Fallback: utiliser audio complet
                    audio_data = audio_data_obj.samples
                else:
                    self.logger.info(f"✅ Parole extraite par VAD: {speech_duration:.2f}s")
                    audio_data = audio_speech
                
            else:
                # Enregistrement fixe avec AudioManager
                self.logger.info(f"🎤 Enregistrement fixe: {duration}s")
                
                audio_data_obj = audio_manager.record(duration=duration)
                
                if audio_data_obj is None:
                    self.logger.error("Échec enregistrement AudioManager")
                    return None
                
                audio_data = audio_data_obj.samples
            
            # Normalisation gain (AudioManager ne le fait pas)
            audio_data = audio_data * 0.3
            
            # Prétraitement audio pour améliorer qualité STT
            audio_data = self._preprocess_audio(audio_data, self.sample_rate)
            
            # Sauvegarder
            timestamp = int(time.time())
            audio_file = self.audio_dir / f"recording_{timestamp}.wav"
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wav.write(str(audio_file), self.sample_rate, audio_int16)
            
            if audio_file.exists():
                self.logger.info(f"✅ Audio enregistré: {audio_file}")
                return str(audio_file)
            else:
                self.logger.error("Fichier audio non créé")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur enregistrement: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def cleanup(self):
        """Nettoie les ressources de l'agent."""
        try:
            self.logger.info("Nettoyage des ressources de l'agent vocal...")
            
            # Sortir du mode conversation si actif
            if self._conversation_mode:
                self.exit_conversation_mode()
            
            # Décharger le modèle
            if self._model_loaded:
                self._force_unload_model()
            
            # Nettoyer la mémoire GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Nettoyage terminé")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage: {e}")
            self.logger.error(traceback.format_exc())
    
    def __del__(self):
        """Destructeur de l'agent."""
        try:
            self.cleanup()
        except:
            pass

# Pour les tests unitaires
if __name__ == "__main__":
    agent = Wav2VecVoiceAgent(debug=True)
    print(f"Agent initialisé sur {agent.device}")
    
    audio_path = input("Chemin vers un fichier audio à transcrire (ou appuyez sur Entrée pour enregistrer): ")
    
    if not audio_path:
        print("Enregistrement de 5 secondes...")
        audio_path = agent.record_audio(duration=5)
        if not audio_path:
            print("Erreur d'enregistrement")
            exit(1)
    
    transcription, confidence = agent.transcribe_audio(audio_path)
    print(f"Transcription: {transcription}")
    print(f"Confiance: {confidence:.3f}")
    
    agent.cleanup()