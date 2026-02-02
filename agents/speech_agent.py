#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de synthèse vocale (text-to-speech) pour QAIA
Utilise pyttsx3 pour la synthèse vocale locale
"""

# /// script
# dependencies = [
#   "pyttsx3>=2.90",
#   "pycaw>=20230102; platform_system == \"Windows\"", # Optionnel, pour contrôle volume
#   "pygame>=2.1.2", # Optionnel, pour alternative gTTS
#   "gTTS>=2.3.1"    # Optionnel, pour alternative gTTS
# ]
# ///

import os
import logging
import pyttsx3
import threading
import queue
import time
import sys
import traceback
import re
from pathlib import Path
import platform

# Importer la configuration depuis system_config
from config.system_config import (
    DATA_DIR as QAIA_DATA_DIR,
    LOGS_DIR as QAIA_LOGS_DIR, # MODELS_DIR n'est pas utilisé directement ici
    TTS_CONFIG as QAIA_TTS_CONFIG,
)

# Configuration des chemins (utilise system_config)

AUDIO_DIR = QAIA_DATA_DIR / "audio" # Conserve la structure locale pour les fichiers audio générés
# LOGS_DIR = DATA_DIR / "logs" # Supprimé, utilise QAIA_LOGS_DIR

# Création des répertoires nécessaires
# QAIA_DATA_DIR et QAIA_LOGS_DIR sont créés par system_config.py
# AUDIO_DIR est un sous-dossier de QAIA_DATA_DIR
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.propagate = True

# Import pycaw de manière conditionnelle
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    logging.warning("Module pycaw non disponible. L'ajustement de volume ne sera pas disponible.")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("Module pygame non disponible. L'alternative gTTS ne sera pas disponible.")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logging.warning("Module gTTS non disponible. L'alternative gTTS ne sera pas disponible.")

try:
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False
    SynthesisConfig = None
    logging.warning("Module Piper TTS non disponible. Voix neuronale haute qualité non disponible.")

class SpeechAgent:
    """Agent gérant la synthèse vocale."""
    
    def __init__(self):
        """Initialise le moteur de synthèse vocale."""
        try:
            # Détection et initialisation moteur TTS
            self.use_piper = False
            self.piper_voice = None
            
            # Essayer d'initialiser Piper en priorité (qualité supérieure)
            if PIPER_AVAILABLE and self._init_piper():
                logger.info("✅ Piper TTS initialisé (qualité professionnelle)")
                self.use_piper = True
            else:
                logger.info("Utilisation pyttsx3 (fallback)")
            
            # Initialisation du moteur pyttsx3 (toujours nécessaire pour fallback)
            self.engine = pyttsx3.init()
            
            # Configuration optimisée (centralisée)
            try:
                self.engine.setProperty('rate', int(QAIA_TTS_CONFIG.get('rate', 195)))
            except Exception:
                self.engine.setProperty('rate', 195)
            try:
                self.engine.setProperty('volume', float(QAIA_TTS_CONFIG.get('volume', 1.0)))
            except Exception:
                self.engine.setProperty('volume', 1.0)
            
            # File d'attente pour gérer les messages
            self.speech_queue = queue.Queue()
            self.is_speaking = False
            self.speech_thread = None
            
            # Tenter de configurer une voix française (pyttsx3)
            if not self.use_piper:
                self._setup_french_voice()
            
            # Démarrer la boucle d'attente pour les messages vocaux
            self._start_speech_worker()
            
            # Vérifier si le moteur est disponible
            self.is_available = True
            
            # Configurer les options de synthèse
            # Permettre le choix du backend via variable d'environnement
            preferred_backend = os.environ.get("QAIA_TTS_BACKEND", str(QAIA_TTS_CONFIG.get('backend', 'pyttsx3'))).lower()
            self.use_pyttsx3 = (preferred_backend != "gtts")
            # Mode par défaut FIABLE: lecture directe via pyttsx3
            self.force_engine_mode = True
            
            # Activer l'ajustement de volume pour garantir une sortie audible sous Windows
            self.volume_adjustment = True
            
            # Initialiser pygame si disponible pour l'alternative gTTS
            if PYGAME_AVAILABLE:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                # Régler volume général pygame (utilise config)
                try:
                    volume = float(QAIA_TTS_CONFIG.get('volume', 0.5))
                    pygame.mixer.music.set_volume(volume)
                    logger.info(f"🔊 Volume pygame défini à {volume*100:.0f}%")
                except Exception:
                    pygame.mixer.music.set_volume(0.5)
                if GTTS_AVAILABLE:
                    logger.info("Alternative gTTS disponible")
            
            logger.info("Moteur de synthèse vocale initialisé avec succès")
            
            # Cache des textes fréquents
            self._speech_cache = {}
            self._max_cache_size = 50
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du moteur de synthèse vocale: {e}")
            logger.error(traceback.format_exc())
            self.is_available = False
    
    def _init_piper(self):
        """Initialise Piper TTS avec voix féminine française."""
        try:
            # Chemin vers le modèle Piper
            base_dir = Path(__file__).parent.parent
            piper_model_path = base_dir / "models" / "piper" / "fr_FR-siwis-medium.onnx"
            
            if not piper_model_path.exists():
                logger.warning(f"Modèle Piper non trouvé: {piper_model_path}")
                return False
            
            # Charger le modèle
            logger.info(f"Chargement modèle Piper: {piper_model_path}")
            self.piper_voice = PiperVoice.load(str(piper_model_path))
            
            # Configurer les paramètres
            self.piper_sample_rate = 22050  # Sample rate du modèle siwis
            
            logger.info("✅ Piper TTS chargé: fr_FR-siwis-medium (voix féminine)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation Piper: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _speak_piper(self, text, save_to_file=None, wait=True):
        """
        Synthétise avec Piper TTS (qualité professionnelle).
        
        Args:
            text (str): Texte à synthétiser
            save_to_file (str): Chemin fichier de sortie (optionnel)
            wait (bool): Attend la fin de la lecture
            
        Returns:
            bool: True si succès
        """
        try:
            import wave
            
            # Générer l'audio
            logger.info(f"Piper: Génération audio '{text[:50]}...'")
            t_start = time.time()
            
            # Déterminer fichier de sortie
            if save_to_file:
                output_file = save_to_file
            else:
                output_file = AUDIO_DIR / f"piper_temp_{int(time.time())}.wav"
            
            # Synthétiser avec Piper (CORRECTION: utiliser wave.open)
            # Configurer la vitesse via length_scale (1.3 = 25% plus lent pour vitesse naturelle)
            syn_config = SynthesisConfig(length_scale=1.2) if SynthesisConfig else None
            
            with wave.open(str(output_file), 'wb') as wav_file:
                if syn_config:
                    self.piper_voice.synthesize_wav(text, wav_file, syn_config=syn_config)
                else:
                    self.piper_voice.synthesize_wav(text, wav_file)
            
            t_synth = time.time() - t_start
            logger.info(f"Piper: Audio généré en {t_synth:.2f}s")
            
            # Si sauvegarde uniquement, retourner
            if save_to_file:
                logger.info(f"Piper: Audio sauvegardé dans {save_to_file}")
                return True
            
            # Lire l'audio avec pygame
            if PYGAME_AVAILABLE:
                try:
                    # Initialiser pygame mixer si nécessaire
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=self.piper_sample_rate)
                    
                    # Lire avec volume configuré
                    logger.info("Piper: Lecture audio...")
                    pygame.mixer.music.load(str(output_file))
                    volume = float(QAIA_TTS_CONFIG.get('volume', 0.5))
                    pygame.mixer.music.set_volume(volume)
                    pygame.mixer.music.play()
                    
                    if wait:
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                    
                    # Nettoyer fichier temporaire
                    try:
                        Path(output_file).unlink()
                    except Exception as e_clean:
                        logger.warning(f"Impossible de supprimer fichier temp: {e_clean}")
                    
                    logger.info("✅ Piper: Synthèse terminée")
                    
                    # Émettre événement agent.state_change pour TTS (ACTIF après synthèse Piper)
                    try:
                        from interface.events.event_bus import event_bus
                        event_bus.emit('agent.state_change', {
                            'name': 'TTS',
                            'status': 'ACTIF',
                            'activity_percentage': 100.0,
                            'details': f'Synthèse vocale terminée (Piper, {len(text)} caractères, {t_synth:.2f}s)',
                            'last_update': time.time()
                        })
                    except Exception:
                        pass
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Erreur lecture audio Piper: {e}")
                    logger.error(traceback.format_exc())
                    return False
            else:
                logger.warning("Pygame non disponible, impossible de lire l'audio Piper")
                return False
                
        except Exception as e:
            logger.error(f"Erreur synthèse Piper: {e}")
            logger.error(traceback.format_exc())
            # Fallback sur pyttsx3
            logger.info("Fallback sur pyttsx3...")
            self.use_piper = False
            return self._speak_sync(text)
    
    def _setup_french_voice(self):
        """Configure une voix française féminine si disponible."""
        try:
            voices = self.engine.getProperty('voices')
            french_voice = None
            female_voice = None
            
            # Recherche prioritaire: voix française féminine
            for voice in voices:
                voice_id_lower = voice.id.lower()
                voice_name_lower = voice.name.lower()
                is_french = "french" in voice_name_lower or "fr" in voice_id_lower or voice_id_lower.startswith("roa/fr")
                
                if is_french:
                    # Vérifier si c'est une voix féminine
                    is_female = False
                    if hasattr(voice, 'gender'):
                        is_female = voice.gender and 'female' in str(voice.gender).lower()
                    
                    # Chercher indices de voix féminine dans le nom
                    female_keywords = ['female', 'femme', 'woman', 'f+', 'feminine']
                    for keyword in female_keywords:
                        if keyword in voice_name_lower or keyword in voice_id_lower:
                            is_female = True
                            break
                    
                    if is_female:
                        female_voice = voice.id
                        logger.info(f"Voix française féminine trouvée: {voice.name} ({voice.id})")
                        break
                    elif not french_voice:
                        # Garder la première voix française comme fallback
                        french_voice = voice.id
            
            # Configurer la voix
            if female_voice:
                self.engine.setProperty('voice', female_voice)
                logger.info(f"✅ Voix féminine configurée: {female_voice}")
            elif french_voice:
                self.engine.setProperty('voice', french_voice)
                logger.info(f"Voix française configurée (masculin par défaut): {french_voice}")
                logger.info("💡 Ajustement pitch pour simuler voix féminine...")
                
                # ASTUCE: Augmenter le pitch pour simuler une voix féminine
                # espeak-ng ne supporte pas directement le pitch via pyttsx3,
                # mais on peut l'ajuster via la propriété 'rate' et d'autres paramètres
                # NOTE: L'augmentation automatique de rate a été supprimée pour éviter une diction trop rapide
                # Le rate est maintenant uniquement défini par TTS_CONFIG['rate']
            else:
                logger.warning("Aucune voix française trouvée, utilisation de la voix par défaut")
                
        except Exception as e:
            logger.error(f"Erreur lors de la configuration de la voix: {e}")
    
    def _start_speech_worker(self):
        """Démarre un thread de travail pour gérer la file d'attente des messages vocaux."""
        def speech_worker():
            try:
                logger.info("Thread de synthèse vocale démarré")
                while True:
                    # Attendre un message dans la file
                    message = self.speech_queue.get()
                    
                    # None signifie arrêt du thread
                    if message is None:
                        logger.info("Thread de synthèse vocale arrêté")
                        break
                    
                    logger.info(f"Traitement du message de synthèse: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                    self.is_speaking = True
                    try:
                        # Vérifier que le moteur est disponible
                        if not self.engine:
                            logger.error("Moteur de synthèse vocale non disponible")
                            continue
                            
                    
                            
                        # Tentative de parole avec gestion d'erreur
                        logger.info("Début de la synthèse avec backend TTS")
                        original_volume = None
                        volume = None
                        # Ajustement de volume système (Windows) si activé
                        if self.volume_adjustment and sys.platform == 'win32' and PYCAW_AVAILABLE:
                            try:
                                devices = AudioUtilities.GetSpeakers()
                                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                                volume = cast(interface, POINTER(IAudioEndpointVolume))
                                original_volume = volume.GetMasterVolumeLevelScalar()
                                target_volume = 1.0 if original_volume < 0.6 else original_volume
                                volume.SetMasterVolumeLevelScalar(target_volume, None)
                            except Exception as vol_err:
                                logger.warning(f"Ajustement volume impossible: {vol_err}")

                        if self.use_pyttsx3:
                            # Stratégie fiable: générer un WAV puis le jouer (pygame > winsound)
                            try:
                                tmp_path = AUDIO_DIR / f"tts_{int(time.time()*1000)}.wav"
                                try:
                                    if tmp_path.exists():
                                        tmp_path.unlink(missing_ok=True)
                                except Exception:
                                    pass
                                # Forcer paramètres sûrs
                                try:
                                    self.engine.setProperty('volume', 1.0)
                                except Exception:
                                    pass
                                logger.info(f"TTS: pyttsx3 -> WAV {tmp_path}")
                                # Génération avec timeout de sécurité
                                self.engine.save_to_file(message, str(tmp_path))
                                gen_start = time.time()
                                self.engine.runAndWait()
                                if (time.time() - gen_start) > 5.0:
                                    logger.warning("TTS: runAndWait a dépassé 5s pour la génération WAV")
                                size_ok = tmp_path.exists() and tmp_path.stat().st_size > 0
                                logger.info(f"TTS: WAV prêt size={tmp_path.stat().st_size if tmp_path.exists() else 0} bytes")
                                if size_ok:
                                    # Priorité à pygame (lecture bloquante fiable), puis winsound en secours
                                    played = False
                                    if PYGAME_AVAILABLE:
                                        try:
                                            logger.info(f"TTS: Lecture WAV (pygame) {tmp_path}")
                                            self._play_wav_file(str(tmp_path))
                                            played = True
                                        except Exception as pe:
                                            logger.warning(f"TTS: pygame échoué: {pe}")
                                    if not played and sys.platform == 'win32':
                                        try:
                                            import winsound  # type: ignore
                                            logger.info(f"TTS: Lecture WAV (winsound) {tmp_path}")
                                            try:
                                                flags = getattr(winsound, 'SND_FILENAME', 0) | getattr(winsound, 'SND_SYNC', 0)
                                                winsound.PlaySound(str(tmp_path), flags)
                                            except AttributeError:
                                                winsound.PlaySound(str(tmp_path), getattr(winsound, 'SND_FILENAME', 0))
                                            played = True
                                        except Exception as we:
                                            logger.warning(f"TTS: winsound échoué: {we}")
                                    if played:
                                        logger.info("TTS: lecture WAV terminée")
                                    # Nettoyage best-effort
                                    try:
                                        tmp_path.unlink(missing_ok=True)
                                    except Exception:
                                        pass
                                else:
                                    # Si le fichier n'est pas créé, fallback gTTS si dispo
                                    if GTTS_AVAILABLE and PYGAME_AVAILABLE:
                                        try:
                                            mp3_path = AUDIO_DIR / f"tts_{int(time.time()*1000)}.mp3"
                                            tts = gTTS(text=message, lang='fr', slow=False)
                                            tts.save(str(mp3_path))
                                            pygame.mixer.music.load(str(mp3_path))
                                            pygame.mixer.music.play()
                                            while pygame.mixer.music.get_busy():
                                                pygame.time.wait(50)
                                        finally:
                                            try:
                                                mp3_path.unlink(missing_ok=True)
                                            except Exception:
                                                pass
                                    else:
                                        logger.warning("TTS: fichier WAV non créé, tentative lecture directe engine")
                                        self.engine.say(message)
                                        self.engine.runAndWait()
                            except Exception as play_err:
                                logger.error(f"TTS WAV/engine échoué: {play_err}")
                        elif PYGAME_AVAILABLE and GTTS_AVAILABLE:
                            # Écrire un MP3 temporaire puis jouer via pygame
                            mp3_path = AUDIO_DIR / f"tts_{int(time.time()*1000)}.mp3"
                            try:
                                tts = gTTS(text=message, lang='fr', slow=False)
                                tts.save(str(mp3_path))
                                pygame.mixer.music.load(str(mp3_path))
                                pygame.mixer.music.play()
                                while pygame.mixer.music.get_busy():
                                    pygame.time.wait(50)
                            finally:
                                try:
                                    mp3_path.unlink(missing_ok=True)
                                except Exception:
                                    pass
                        else:
                            # Fallback minimal pyttsx3 si gTTS indisponible
                            self.engine.say(message)
                            self.engine.runAndWait()

                        # Restaurer volume
                        if original_volume is not None and sys.platform == 'win32' and PYCAW_AVAILABLE and volume is not None:
                            try:
                                volume.SetMasterVolumeLevelScalar(original_volume, None)
                            except Exception as vol_err:
                                logger.warning(f"Restauration volume impossible: {vol_err}")
                        logger.info("Synthèse vocale terminée avec succès")
                        
                    except RuntimeError as e:
                        if "run loop already started" in str(e):
                            # Recréer le moteur en cas d'erreur de boucle
                            logger.warning("Redémarrage du moteur de synthèse vocale après erreur de boucle")
                            self._recreate_engine()
                            # Retenter avec le nouveau moteur
                            try:
                                if self.engine:
                                    self.engine.say(message)
                                    self.engine.runAndWait()
                                    logger.info("Synthèse vocale réussie après redémarrage")
                                else:
                                    logger.error("Impossible de recréer le moteur")
                            except Exception as retry_e:
                                logger.error(f"Échec de la seconde tentative: {retry_e}")
                        else:
                            logger.error(f"Erreur RuntimeError lors de la synthèse vocale: {e}")
                    except Exception as e:
                        logger.error(f"Erreur inattendue lors de la synthèse vocale: {e}")
                        logger.error(traceback.format_exc())
                    finally:
                        self.is_speaking = False
                        self.speech_queue.task_done()
                        # Petit délai pour éviter des problèmes de contention
                        time.sleep(0.05)  # Réduit pour diminuer la latence
            except Exception as e:
                logger.error(f"Erreur dans le thread de synthèse vocale: {e}")
                logger.error(traceback.format_exc())
        
        # Démarrer le thread de travail
        self.speech_thread = threading.Thread(target=speech_worker, daemon=True)
        self.speech_thread.start()
    
    def _play_wav_file(self, file_path: str, wait_ms: int | None = None) -> None:
        """Lit un WAV via pygame si dispo, sinon essaie via simpleaudio.

        Args:
            file_path (str): chemin du fichier WAV
            wait_ms (int|None): temps d'attente minimal après démarrage
        """
        try:
            if PYGAME_AVAILABLE:
                # (Ré)initialiser le mixer si nécessaire et s'assurer qu'aucune lecture ne bloque
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                except Exception:
                    pass
                try:
                    if hasattr(pygame.mixer, 'music') and pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                except Exception:
                    pass
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                if wait_ms is not None:
                    pygame.time.wait(int(wait_ms))
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(50)
                return
        except Exception as e:
            logger.warning(f"Lecture via pygame échouée: {e}")
        # Fallback optionnel si simpleaudio dispo (non listé en dépendance)
        try:
            import simpleaudio as sa  # type: ignore
            wave_obj = sa.WaveObject.from_wave_file(file_path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
        except Exception as e:
            logger.error(f"Impossible de jouer le fichier WAV: {e}")
    
    def _recreate_engine(self):
        """Recrée le moteur de synthèse vocale en cas de problème."""
        try:
            # Arrêter proprement l'ancien moteur si possible
            try:
                self.engine.stop()
            except:
                pass
            
            # Créer un nouveau moteur
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 190)
            self.engine.setProperty('volume', 0.9)
            self._setup_french_voice()
            logger.info("Moteur de synthèse vocale recréé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la recréation du moteur: {e}")
    
    def speak(self, text, wait=False, block=None, save_to_file=None):
        """
        Synthétise et prononce le texte.
        
        Émet des événements agent.state_change pour TTS.
        """
        # Émettre événement agent.state_change pour TTS (EN_COURS)
        try:
            from interface.events.event_bus import event_bus
            import time
            event_bus.emit('agent.state_change', {
                'name': 'TTS',
                'status': 'EN_COURS',
                'activity_percentage': 50.0,
                'details': f'Synthèse vocale en cours: "{text[:50]}..."',
                'last_update': time.time()
            })
        except Exception:
            pass  # Ne pas bloquer si Event Bus indisponible
        """
        Synthétise et joue un texte.
        
        Args:
            text (str): Texte à synthétiser
            wait (bool): Si True, attend la fin de la synthèse
            block (bool): Alias de wait pour compatibilité avec l'ancien code
            save_to_file (str): Si fourni, sauvegarde l'audio dans ce fichier
            
        Returns:
            bool: True si réussi, False sinon
        """
        # Utiliser block comme alias de wait si fourni
        if block is not None:
            wait = block
        
        # Vérifier si le texte est valide
        if not text or not isinstance(text, str):
            logger.warning(f"Tentative de synthèse d'un texte invalide: {text}")
            return False
            
        # Nettoyer le texte
        text = self._clean_text(text)
        
        # Si Piper est disponible, l'utiliser en priorité
        if self.use_piper and self.piper_voice:
            logger.info(f"TTS Piper: synthèse '{text[:50]}...' (len={len(text)})")
            return self._speak_piper(text, save_to_file=save_to_file, wait=wait)
        
        # Sinon, utiliser pyttsx3 (fallback)
        logger.info(f"TTS pyttsx3: speak() appelé wait={wait} len={len(text)} is_available={self.is_available} is_speaking={self.is_speaking}")
            
        # Détecter si une synthèse est en cours pour éviter les chevauchements
        if self.is_speaking:
            logger.info("Synthèse vocale déjà en cours, arrêt de la précédente")
            self.stop()
            
        # Pause pour éviter les problèmes de superposition
        time.sleep(0.1)
            
        # Vérifier l'agent de synthèse vocale
        if not self.is_available:
            logger.warning("Synthèse vocale non disponible (is_available=False)")
            return False
        
        try:
            # Protéger les premières secondes contre un stop() intempestif
            try:
                import time as _time
                protect_ms = int(QAIA_TTS_CONFIG.get('protection_window_ms', 1200))
                self._protected_until = _time.time() + (protect_ms / 1000.0)
            except Exception:
                self._protected_until = 0
            if wait:
                logger.info("TTS: chemin synchronisé (_speak_sync)")
                return self._speak_sync(text)
            else:
                logger.info("TTS: chemin asynchrone (_speak_async)")
                return self._speak_async(text)
        except Exception as e:
            logger.error(f"Erreur lors de la synthèse vocale: {e}")
            return False
            
    def _clean_text(self, text):
        """
        Nettoie le texte avant synthèse pour éviter les problèmes.
        Utilise le module centralisé text_processor pour cohérence.
        """
        if not text:
            return ""
        
        try:
            # Utiliser le module centralisé pour cohérence avec l'affichage
            from utils.text_processor import process_text_for_tts
            return process_text_for_tts(text)
        except Exception as e:
            logger.warning(f"Erreur post-traitement TTS: {e}, nettoyage basique")
            # Fallback: nettoyage basique si module centralisé indisponible
            text = re.sub(r'[^\w\s.,!?;:()\'"-]', '', text)
            return text
    
    def _split_text(self, text):
        """Découpe un texte long en segments plus petits."""
        # Découper aux points, aux virgules ou aux espaces selon la longueur
        try:
            max_segment = int(QAIA_TTS_CONFIG.get('segment_max_chars', 280))
        except Exception:
            max_segment = 280
        segments = []
        
        remaining = text
        while len(remaining) > max_segment:
            # Trouver un bon point de coupure (point, virgule, espace)
            cut_point = max_segment
            
            # Chercher un point dans la zone de recherche
            period_pos = remaining[:cut_point].rfind('. ')
            if period_pos > max_segment * 0.6:  # Au moins 60% de la longueur max
                cut_point = period_pos + 1  # Inclure le point
            else:
                # Chercher une virgule
                comma_pos = remaining[:cut_point].rfind(', ')
                if comma_pos > max_segment * 0.7:  # Au moins 70% de la longueur max
                    cut_point = comma_pos + 1  # Inclure la virgule
                else:
                    # Chercher un espace
                    space_pos = remaining[:cut_point].rfind(' ')
                    if space_pos > 0:
                        cut_point = space_pos
            
            segments.append(remaining[:cut_point].strip())
            remaining = remaining[cut_point:].strip()
        
        if remaining:
            segments.append(remaining)
            
        return segments
    
    def _speak_segments(self, segments):
        """Traite plusieurs segments de texte en séquence."""
        for segment in segments:
            self._speak_sync(segment)
    
    def _speak_async(self, text):
        """
        Méthode interne pour la synthèse vocale asynchrone.
        
        Args:
            text (str): Texte à synthétiser
            
        Returns:
            bool: True si réussi, False sinon
        """
        # Vérification supplémentaire
        if text is None or not isinstance(text, str) or text.strip() == "":
            logger.warning("Tentative de synthèse vocale asynchrone avec un texte invalide")
            return False
            
        try:
            # Log pour diagnostiquer
            logger.info(f"Début synthèse vocale asynchrone: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Ajouter à la cache si pas trop long
            if len(text) < 100 and text not in self._speech_cache:
                # Gérer la taille du cache
                if len(self._speech_cache) >= self._max_cache_size:
                    # Supprimer une entrée aléatoire (simple)
                    if self._speech_cache:
                        self._speech_cache.pop(next(iter(self._speech_cache)))
                self._speech_cache[text] = True
            
            # Vérifier si le thread de synthèse vocale est actif
            if not self.speech_thread or not self.speech_thread.is_alive():
                logger.warning("Thread de synthèse vocale inactif, redémarrage...")
                self._start_speech_worker()
            
            # Mettre le texte dans la file d'attente pour traitement asynchrone
            self.speech_queue.put(text)
            logger.info("Texte ajouté à la file de synthèse vocale")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la synthèse vocale asynchrone: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    def _speak_sync(self, text):
        """
        Méthode interne pour la synthèse vocale synchrone.
        
        Args:
            text (str): Texte à synthétiser
            
        Returns:
            bool: True si réussi, False sinon
        """
        # Vérification supplémentaire
        if text is None or not isinstance(text, str) or text.strip() == "":
            logger.warning("Tentative de synthèse vocale synchrone avec un texte invalide")
            return False
            
        try:
            # Segmentation pour fiabiliser les longues réponses
            try:
                max_seg = int(QAIA_TTS_CONFIG.get('segment_max_chars', 280))
            except Exception:
                max_seg = 280
            if len(text) > max_seg:
                segments = self._split_text(text)
                for seg in segments:
                    ok = self._speak_sync(seg)
                    if not ok:
                        return False
                    try:
                        pause_s = float(QAIA_TTS_CONFIG.get('segment_pause_ms', 120)) / 1000.0
                    except Exception:
                        pause_s = 0.12
                    time.sleep(pause_s)
                return True
            # Ajouter à la cache si pas trop long
            if len(text) < 100 and text not in self._speech_cache:
                # Gérer la taille du cache
                if len(self._speech_cache) >= self._max_cache_size:
                    # Supprimer une entrée aléatoire (simple)
                    if self._speech_cache:
                        self._speech_cache.pop(next(iter(self._speech_cache)))
                self._speech_cache[text] = True
            
            # Ajuster le volume de sortie si une modification a été demandée
            original_volume = None
            if self.volume_adjustment and sys.platform == 'win32' and PYCAW_AVAILABLE:
                # Sauvegarder le volume original
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    original_volume = volume.GetMasterVolumeLevelScalar()
                    
                    # Ajuster le volume pour la synthèse vocale
                    target_volume = min(1.0, original_volume * 1.5)  # Augmenter de 50%, max 100%
                    volume.SetMasterVolumeLevelScalar(target_volume, None)
                except Exception as vol_err:
                    logger.error(f"Erreur lors de l'ajustement du volume: {vol_err}")
                    original_volume = None  # Réinitialiser pour éviter d'essayer de restaurer
            
            # Effectuer la synthèse vocale
            if self.use_pyttsx3:
                # Utiliser la stratégie WAV fiable comme en asynchrone (nom unique)
                from time import time as _t
                tmp_path = AUDIO_DIR / f"tts_{int(_t()*1000)}.wav"
                try:
                    if tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    self.engine.setProperty('volume', 1.0)
                except Exception:
                    pass
                logger.info(f"TTS: pyttsx3 -> WAV {tmp_path}")
                self.engine.save_to_file(text, str(tmp_path))
                self.engine.runAndWait()
                # Attendre explicitement la création du fichier (timeout 2s)
                _start_wait = time.time()
                while (not tmp_path.exists() or tmp_path.stat().st_size == 0) and (time.time() - _start_wait) < 2.0:
                    time.sleep(0.05)
                size_ok = tmp_path.exists() and tmp_path.stat().st_size > 0
                logger.info(f"TTS: WAV prêt size={tmp_path.stat().st_size if tmp_path.exists() else 0} bytes")
                if size_ok:
                    played = False
                    if PYGAME_AVAILABLE:
                        try:
                            logger.info(f"TTS: Lecture WAV (pygame) {tmp_path}")
                            self._play_wav_file(str(tmp_path))
                            played = True
                        except Exception as pe:
                            logger.warning(f"TTS: pygame échoué: {pe}")
                    if not played and sys.platform == 'win32':
                        try:
                            import winsound  # type: ignore
                            logger.info(f"TTS: Lecture WAV (winsound) {tmp_path}")
                            try:
                                flags = getattr(winsound, 'SND_FILENAME', 0) | getattr(winsound, 'SND_SYNC', 0)
                                winsound.PlaySound(str(tmp_path), flags)
                            except AttributeError:
                                winsound.PlaySound(str(tmp_path), getattr(winsound, 'SND_FILENAME', 0))
                            played = True
                        except Exception as we:
                            logger.warning(f"TTS: winsound échoué: {we}")
                    if played:
                        logger.info("TTS: lecture WAV terminée")
                        
                        # Émettre événement agent.state_change pour TTS (ACTIF après synthèse)
                        try:
                            from interface.events.event_bus import event_bus
                            event_bus.emit('agent.state_change', {
                                'name': 'TTS',
                                'status': 'ACTIF',
                                'activity_percentage': 100.0,
                                'details': f'Synthèse vocale terminée ({len(text)} caractères)',
                                'last_update': time.time()
                            })
                        except Exception:
                            pass
                    # Nettoyage best-effort
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                else:
                    logger.warning("TTS: Fichier WAV non créé, tentative engine.runAndWait directe")
                self.engine.say(text)
                self.engine.runAndWait()
            elif PYGAME_AVAILABLE and GTTS_AVAILABLE:
                from io import BytesIO
                
                # Génération de l'audio avec gTTS
                mp3_fp = BytesIO()
                tts = gTTS(text=text, lang='fr', slow=False)
                tts.write_to_fp(mp3_fp)
                mp3_fp.seek(0)
                
                # Lecture de l'audio
                pygame.mixer.music.load(mp3_fp)
                pygame.mixer.music.play()
                
                # Attendre la fin de la lecture
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(50)  # Réduit pour diminuer la latence
            else:
                logger.warning("Aucune méthode de synthèse vocale disponible")
                return False
            
            # Restaurer le volume d'origine si nécessaire
            if original_volume is not None and sys.platform == 'win32' and PYCAW_AVAILABLE:
                try:
                    volume.SetMasterVolumeLevelScalar(original_volume, None)
                except Exception as vol_err:
                    logger.error(f"Erreur lors de la restauration du volume: {vol_err}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la synthèse vocale synchrone: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def stop(self):
        """Arrête la synthèse vocale en cours."""
        try:
            # Ne pas interrompre si on est dans la fenêtre protégée de lancement
            try:
                import time as _time
                if getattr(self, '_protected_until', 0) and _time.time() < self._protected_until:
                    logger.info("Stop ignoré (fenêtre protégée)")
                    return True
            except Exception:
                pass
            # Vider la file d'attente pour stopper les messages en attente
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except queue.Empty:
                    break
            
            # Arrêter le moteur en cours
            try:
                self.engine.stop()
            except Exception as e:
                logger.warning(f"Erreur lors de l'arrêt du moteur pyttsx3: {e}")
            
            # Si un fichier est en cours de lecture avec pygame
            if PYGAME_AVAILABLE and hasattr(pygame.mixer, 'music') and pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.stop()
                    logger.info("Lecture audio pygame arrêtée")
                except Exception as e:
                    logger.warning(f"Erreur lors de l'arrêt de pygame: {e}")
            
            # Réinitialiser l'état de parole
            self.is_speaking = False
            
            # Éviter la recréation systématique du moteur pour ne pas interrompre les lectures
            logger.info("Synthèse vocale arrêtée avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la synthèse vocale: {e}")
            return False
    
    def cleanup(self):
        """Nettoie les ressources de l'agent de synthèse vocale."""
        try:
            logger.info("Nettoyage de l'agent de synthèse vocale...")
            
            # Arrêter la synthèse en cours
            self.stop()
            
            # Arrêter le thread de synthèse vocale
            if hasattr(self, 'speech_thread') and self.speech_thread and self.speech_thread.is_alive():
                # Envoyer un signal de fin au thread
                self.speech_queue.put(None)
                # Attendre la fin du thread (avec timeout)
                self.speech_thread.join(timeout=2)
                logger.info("Thread de synthèse vocale arrêté")
            
            # Nettoyer le moteur pyttsx3
            if hasattr(self, 'engine') and self.engine:
                try:
                    self.engine.stop()
                    del self.engine
                    self.engine = None
                except Exception as e:
                    logger.warning(f"Erreur lors du nettoyage du moteur pyttsx3: {e}")
            
            # Nettoyer pygame si utilisé
            if PYGAME_AVAILABLE and hasattr(pygame.mixer, 'music'):
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                except Exception as e:
                    logger.warning(f"Erreur lors du nettoyage pygame: {e}")
            
            # Vider les caches
            if hasattr(self, '_speech_cache'):
                self._speech_cache.clear()
            
            logger.info("Nettoyage de l'agent de synthèse vocale terminé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de l'agent de synthèse vocale: {e}")
            return False
    
    def __del__(self):
        """Nettoyage à la destruction de l'instance."""
        if hasattr(self, 'speech_queue') and hasattr(self, 'speech_thread'):
            try:
                # Envoyer un signal de fin au thread
                self.speech_queue.put(None)
                # Attendre la fin du thread (avec timeout)
                if self.speech_thread:
                    self.speech_thread.join(timeout=1)
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture de l'agent de synthèse vocale: {e}")


def is_available() -> bool:
    """
    Indique si la synthèse vocale est disponible sur ce système.

    Returns:
        bool: True si pyttsx3 est utilisable, False sinon.
    """
    try:
        engine = pyttsx3.init()
        try:
            engine.stop()
        except Exception:
            pass
        return True
    except Exception:
        return False


def speak(text: str, wait: bool = False) -> bool:
    """
    Fonction de compatibilité au niveau module pour déclencher la synthèse vocale.

    Args:
        text (str): Texte à prononcer.
        wait (bool): Si True, bloque jusqu'à la fin de la synthèse.

    Returns:
        bool: True si la synthèse a été déclenchée avec succès, False sinon.
    """
    try:
        agent = SpeechAgent()
        return agent.speak(text, wait=wait)
    except Exception as e:
        logger.error(f"Erreur speak(module): {e}")
        return False

# Test unitaire
if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(level=logging.INFO)
    
    # Créer l'agent
    speech_agent = SpeechAgent()
    
    # Test de synthèse vocale
    print("Test de synthèse vocale...")
    speech_agent.speak("Ceci est un test de synthèse vocale en français.")
    
    # Test de synthèse vocale asynchrone
    print("Test de synthèse vocale asynchrone...")
    speech_agent.speak("Ceci est un test de synthèse vocale asynchrone.", wait=False)
    print("Continue immédiatement sans attendre la fin de la parole.")
    
    # Laisser le temps à la parole de se terminer
    time.sleep(5)
    
    print("Test terminé.") 