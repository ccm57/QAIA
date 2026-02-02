#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Interface utilisateur de QAIA."""

# /// script
# dependencies = [
#   "customtkinter",
#   "pillow>=10.0.0",
# ]
# ///

import os
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from qaia_core import QAIACore
import customtkinter as ctk
from PIL import Image, ImageTk
from config.logging_config import get_logger
from config.system_config import (
    DATA_DIR as QAIA_DATA_DIR,
    LOGS_DIR as QAIA_LOGS_DIR,
    MODEL_CONFIG,
)
import numpy as np
try:
    import sounddevice as sd
    SD_AVAILABLE = True
except Exception:
    SD_AVAILABLE = False
import wave
from data.database import Database

# Nouveaux imports pour interface restructurée
from interface.events.event_bus import event_bus
from interface.components.streaming_text import StreamingTextDisplay
from interface.components.audio_visualizer import AudioVisualizer
from interface.windows.monitoring_window import MonitoringWindow
from interface.windows.logs_window import LogsWindow
from interface.windows.metrics_window import MetricsWindow
from interface.windows.agents_window import AgentsWindow
from utils.monitoring import metrics_collector
from agents.audio_manager import AudioManager, RecordingStrategy

# Configuration des chemins (utilise system_config pour garantir la cohérence F:)
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = QAIA_DATA_DIR
AUDIO_DIR = DATA_DIR / "audio"
LOGS_DIR = QAIA_LOGS_DIR

# S'assurer que le dossier de logs existe
os.makedirs(LOGS_DIR, exist_ok=True)

# Désactivation des logs des bibliothèques tierces
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

class LightweightTextArea(tk.Canvas):
    """Implémentation légère d'une zone de texte, plus efficace que le widget Text standard."""
    
    def __init__(self, master, **kwargs):
        bg_color = kwargs.pop('bg', 'white')
        self.width = kwargs.pop('width', 400)
        self.height = kwargs.pop('height', 300)
        super().__init__(master, bg=bg_color, width=self.width, height=self.height, **kwargs)
        self.lines = []
        self.text_font = kwargs.pop('font', ('Arial', 10))
        self.line_height = 20  # Hauteur approx. d'une ligne
        self.left_margin = 10
        self.top_margin = 10
        self.visible_lines = self.height // self.line_height
        self.scroll_position = 0
        
        # Scrollbar optimisée
        self.scrollbar = ttk.Scrollbar(master, orient=tk.VERTICAL, command=self.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.configure(yscrollcommand=self.scrollbar.set)
        
        # Gestionnaire d'événements
        self.bind("<Configure>", self._on_configure)
        self.bind("<MouseWheel>", self._on_mousewheel)
        
        # Buffer de rendu pour réduire le clignotement
        self.double_buffer = True
    
    def insert(self, position, text):
        """Insère du texte dans la zone."""
        lines_to_add = text.split('\n')
        for line in lines_to_add:
            self.lines.append(line)
        
        # Mise à jour automatique de la position de défilement
        if len(self.lines) > self.visible_lines:
            self.scroll_position = max(0, len(self.lines) - self.visible_lines)
        
        self._redraw()
    
    def clear(self):
        """Efface tout le contenu."""
        self.lines = []
        self.scroll_position = 0
        self._redraw()
    
    def yview(self, *args):
        """Gère le défilement vertical."""
        if args[0] == 'moveto':
            # Convertir la fraction en position de ligne
            fraction = float(args[1])
            total_lines = max(1, len(self.lines))
            self.scroll_position = int(fraction * total_lines)
        elif args[0] == 'scroll':
            amount = int(args[1])
            unit = args[2]
            if unit == 'units':
                # Défilement ligne par ligne
                self.scroll_position += amount
            elif unit == 'pages':
                # Défilement page par page
                self.scroll_position += amount * self.visible_lines
                
        # Limiter la position de défilement
        self.scroll_position = max(0, min(len(self.lines) - self.visible_lines, self.scroll_position))
        if self.scroll_position < 0:
            self.scroll_position = 0
            
        self._redraw()
        self._update_scrollbar()
    
    def _on_mousewheel(self, event):
        """Gère le défilement avec la molette de la souris."""
        # Direction de défilement (dépend du système)
        delta = -1 if event.delta > 0 else 1
        self.yview('scroll', delta, 'units')
    
    def _on_configure(self, event):
        """Gère le redimensionnement de la zone."""
        self.width = event.width
        self.height = event.height
        self.visible_lines = self.height // self.line_height
        self._redraw()
        self._update_scrollbar()
    
    def _update_scrollbar(self):
        """Met à jour la position de la scrollbar."""
        total_lines = max(1, len(self.lines))
        if total_lines <= self.visible_lines:
            # Pas besoin de scrollbar
            self.scrollbar.set(0, 1)
        else:
            # Calculer les fractions pour la scrollbar
            top_fraction = self.scroll_position / total_lines
            bottom_fraction = min(1, (self.scroll_position + self.visible_lines) / total_lines)
            self.scrollbar.set(top_fraction, bottom_fraction)
    
    def _redraw(self):
        """Redessine le contenu."""
        self.delete("all")  # Effacer le canvas
        
        # Dessiner les lignes visibles
        y = self.top_margin
        for i in range(self.scroll_position, min(len(self.lines), self.scroll_position + self.visible_lines)):
            line = self.lines[i]
            # Utiliser différentes couleurs selon l'émetteur
            if line.startswith("Vous:"):
                text_color = "blue"
            elif line.startswith("QAIA:"):
                text_color = "green"
            else:
                text_color = "black"
                
            self.create_text(
                self.left_margin, y, 
                text=line, 
                anchor="nw", 
                font=self.text_font,
                fill=text_color
            )
            y += self.line_height
        
        self._update_scrollbar()

class QAIAInterface:
    def __init__(self, qaia_core=None):
        """Initialise l'interface utilisateur."""
        self.logger = get_logger("qaia_interface", "interface")
        self.logger.info("Initialisation de l'interface")
        # État interne: suivi du streaming LLM pour éviter les doublons d'affichage
        self._llm_streaming_active = False
        # Commande en attente de confirmation (pipeline commandes système)
        self._pending_command = None
        # CRITIQUE: Thread-safety pour TTS (TODO-11)
        import threading
        self._tts_lock = threading.Lock()
        # État interne unifié pour les messages d'état UI
        self._status_state = {
            "code": "initialisation",
            "label": "Initialisation…",
            "severity": "info",
        }

        # Table de correspondance des statuts d'interface.
        # Tous les messages utilisateurs doivent passer par ces clés.
        self._status_definitions = {
            "initialisation": {
                "label": "Initialisation…",
                "background": "#fff3cd",
                "severity": "info",
            },
            "ready": {
                "label": "Système prêt",
                "background": "#e6ffe6",
                "severity": "success",
            },
            "core_initializing": {
                "label": "Noyau QAIA en cours d'initialisation…",
                "background": "#fff3cd",
                "severity": "info",
            },
            "llm_typing": {
                "label": "QAIA écrit…",
                "background": "#e6f6ff",
                "severity": "info",
            },
            "ptt_recording": {
                "label": "Enregistrement…",
                "background": "#fff3cd",
                "severity": "info",
            },
            "stt_transcribing": {
                "label": "Transcription…",
                "background": "#e6f6ff",
                "severity": "info",
            },
            "tts_stopped": {
                "label": "Voix interrompue",
                "background": "#fff3cd",
                "severity": "info",
            },
            "llm_ready": {
                "label": "LLM prêt",
                "background": "#e6ffe6",
                "severity": "success",
            },
            "error_micro": {
                "label": "Erreur micro",
                "background": "#ffe6e6",
                "severity": "error",
            },
            "error_ptt": {
                "label": "Erreur PTT",
                "background": "#ffe6e6",
                "severity": "error",
            },
            "error_core": {
                "label": "Erreur noyau",
                "background": "#ffe6e6",
                "severity": "error",
            },
            "error_llm": {
                "label": "Erreur LLM",
                "background": "#ffe6e6",
                "severity": "error",
            },
            "error_generic": {
                "label": "Erreur",
                "background": "#ffe6e6",
                "severity": "error",
            },
        }

        # Initialiser la base de données pour journaliser les conversations
        try:
            self.db = Database()
        except Exception as e:
            self.logger.error(f"Base de données indisponible: {e}")
            self.db = None
        
        # Initialiser le service d'identité vocale (optionnel, ne bloque pas si indisponible)
        self.voice_identity_service = None
        try:
            from agents.voice_identity import VoiceIdentityService
            self.voice_identity_service = VoiceIdentityService()
            self.logger.info("Service d'identité vocale initialisé")
        except Exception as e:
            self.logger.warning(f"Service d'identité vocale non disponible: {e}")

        # Utiliser l'instance QAIACore fournie ou en créer une nouvelle si nécessaire
        self.qaia = qaia_core

        try:
            self.root = ctk.CTk()
            self.setup_ui()
            self.logger.info("Interface initialisée avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'interface: {e}")
            raise

    def _set_status(self, code: str) -> None:
        """
        Met à jour de manière unifiée le message d'état de l'interface.

        Args:
            code (str): Code de statut logique (voir _status_definitions).
        """
        try:
            definition = self._status_definitions.get(code) or self._status_definitions.get("error_generic")
            self._status_state.update(
                {
                    "code": code,
                    "label": definition["label"],
                    "severity": definition["severity"],
                }
            )
            if hasattr(self, "status_label"):
                # Protection contre les appels hors thread UI
                def _apply():
                    self.status_label.configure(
                        text=self._status_state["label"],
                        background=definition["background"],
                    )

                try:
                    self.root.after(0, _apply)
                except Exception:
                    _apply()
        except Exception as e:
            # Ne jamais faire crasher l'UI sur un simple changement de statut
            self.logger.error(f"Erreur mise à jour statut UI ({code}): {e}")

    def setup_ui(self):
        """Configure l'interface utilisateur."""
        # Configuration de la fenêtre
        self.root.title("QAIA - Quality Assistant Intelligent Agent")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configurer l'icône fenêtre + barre des tâches
        try:
            logo_path = BASE_DIR / "assets" / "icons" / "QAIA2.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                logo_photo = ImageTk.PhotoImage(logo_img)
                self.root.iconphoto(True, logo_photo)  # True = applique aussi à la barre des tâches
                self.logger.info("Icône fenêtre configurée")
            else:
                self.logger.warning(f"Icône non trouvée: {logo_path}")
        except Exception as e:
            self.logger.error(f"Erreur configuration icône: {e}")
        
        # Fenêtres modulaires (références)
        self.monitoring_window = None
        self.logs_window = None
        self.metrics_window = None
        self.agents_window = None
        
        # Créer menu bar
        self._create_menu_bar()
        
        # Configuration pour réduire la charge CPU de l'interface
        self.update_interval = 50  # ms, fréquence de mise à jour UI
        
        # Créer une instance de QAIACore si aucune n'a été fournie, en arrière-plan pour éviter l'écran noir
        if self.qaia is None:
            def _init_core_bg():
                try:
                    from qaia_core import QAIACore
                    qaia = QAIACore()
                    self.qaia = qaia
                    self.logger.info("Instance QAIACore créée en arrière-plan")
                    # Mettre à jour l'état UI
                    try:
                        self.root.after(0, lambda: self._set_status("ready"))
                        # Déclencher la voix de bienvenue si pas encore parlée
                        self.root.after(0, lambda: self._attempt_welcome_speak())
                    except Exception:
                        pass
                except Exception as e:
                    self.logger.error(f"Erreur initialisation QAIACore (bg): {e}")
                    try:
                        self.root.after(0, lambda: self._set_status("error_core"))
                    except Exception:
                        pass
            threading.Thread(target=_init_core_bg, daemon=True).start()
        else:
            self.logger.info("Utilisation de l'instance QAIACore fournie")
        
        # Initialisation des composants
        self._setup_ui()
        
        # Création des dossiers nécessaires
        os.makedirs(AUDIO_DIR, exist_ok=True)

        # Planifier les mises à jour UI via Tkinter (thread principal uniquement)
        self._ui_tick_id = None
        self._schedule_ui_tick()

        # Préparation du LLM en arrière-plan (si disponible)
        threading.Thread(target=self._preheat_llm_safe, daemon=True).start()

        # État de traitement pour éviter les doublons
        self.is_processing = False
        # Drapeau pour éviter de répéter la voix de bienvenue
        self.welcome_spoken = False

        # Message de bienvenue
        try:
            self._show_welcome_message()
        except Exception:
            pass
        
        # S'abonner aux événements Event Bus
        self._subscribe_to_events()
        
        # Démarrer monitoring métriques système
        metrics_collector.start_monitoring(interval=1.0)
        self.logger.info("Monitoring métriques système démarré")
        
        # Lier la fermeture de l'application
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_menu_bar(self):
        """Crée la barre de menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu QAIA
        qaia_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="QAIA", menu=qaia_menu)
        qaia_menu.add_command(label="À propos", command=self._show_about)
        qaia_menu.add_separator()
        qaia_menu.add_command(label="Quitter", command=self._on_closing)
        
        # Menu Vue
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Vue", menu=view_menu)
        view_menu.add_command(label="Monitoring (Ctrl+M)", command=self._open_monitoring)
        view_menu.add_command(label="Logs (Ctrl+L)", command=self._open_logs)
        view_menu.add_command(label="Métriques LLM (Ctrl+K)", command=self._open_metrics)
        view_menu.add_command(label="États Agents (Ctrl+A)", command=self._open_agents)
        
        # Raccourcis clavier
        self.root.bind('<Control-m>', lambda e: self._open_monitoring())
        self.root.bind('<Control-l>', lambda e: self._open_logs())
        self.root.bind('<Control-k>', lambda e: self._open_metrics())
        self.root.bind('<Control-a>', lambda e: self._open_agents())
    
    def _show_about(self):
        """Affiche la fenêtre À propos."""
        about_window = ctk.CTkToplevel(self.root)
        about_window.title("À propos de QAIA")
        about_window.geometry("400x350")
        about_window.resizable(False, False)
        
        # Centrer
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() - 400) // 2
        y = (about_window.winfo_screenheight() - 350) // 2
        about_window.geometry(f"400x350+{x}+{y}")
        
        # Contenu
        try:
            logo_path = BASE_DIR / "assets" / "icons" / "QAIA2.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((100, 100), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(about_window, image=logo_photo)
                logo_label.image = logo_photo
                logo_label.pack(pady=20)
        except Exception as e:
            self.logger.error(f"Erreur chargement logo: {e}")
        
        ctk.CTkLabel(about_window, text="QAIA v2.1.0", font=("Arial", 16, "bold")).pack(pady=5)
        ctk.CTkLabel(about_window, text="Quality Assistant", font=("Arial", 12)).pack()
        ctk.CTkLabel(about_window, text="Intelligent Agent", font=("Arial", 12)).pack(pady=5)
        ctk.CTkLabel(about_window, text="", font=("Arial", 10)).pack(pady=10)  # Spacer
        ctk.CTkLabel(about_window, text="Modèle: Phi-3-mini-4k", font=("Arial", 10)).pack()
        ctk.CTkLabel(about_window, text="Python: 3.11.9", font=("Arial", 10)).pack()
        
        ctk.CTkButton(about_window, text="Fermer", command=about_window.destroy).pack(pady=20)
    
    def _open_monitoring(self):
        """Ouvre la fenêtre Monitoring."""
        if self.monitoring_window is None or not self.monitoring_window.winfo_exists():
            self.monitoring_window = MonitoringWindow(self.root)
        else:
            self.monitoring_window.lift()
    
    def _open_logs(self):
        """Ouvre la fenêtre Logs."""
        if self.logs_window is None or not self.logs_window.winfo_exists():
            self.logs_window = LogsWindow(self.root)
        else:
            self.logs_window.lift()
    
    def _open_metrics(self):
        """Ouvre la fenêtre Métriques LLM."""
        if self.metrics_window is None or not self.metrics_window.winfo_exists():
            self.metrics_window = MetricsWindow(self.root)
        else:
            self.metrics_window.lift()
    
    def _open_agents(self):
        """Ouvre la fenêtre États Agents."""
        if self.agents_window is None or not self.agents_window.winfo_exists():
            self.agents_window = AgentsWindow(self.root)
        else:
            self.agents_window.lift()
    
    def _schedule_ui_tick(self):
        """Planifie une mise à jour légère de l'UI dans le thread principal."""
        try:
            self.root.update_idletasks()
        except Exception as e:
            self.logger.error(f"Erreur update_idletasks: {e}")
        finally:
            self._ui_tick_id = self.root.after(self.update_interval, self._schedule_ui_tick)
    
    def _subscribe_to_events(self):
        """S'abonne aux événements de l'Event Bus."""
        # Événements LLM
        event_bus.subscribe('llm.token', self._on_llm_token)
        event_bus.subscribe('llm.start', self._on_llm_start)
        event_bus.subscribe('llm.complete', self._on_llm_complete)
        event_bus.subscribe('llm.error', self._on_llm_error)
        
        # Événements STT
        event_bus.subscribe('stt.transcribing', self._on_stt_transcribing)
        event_bus.subscribe('stt.complete', self._on_stt_complete)
        event_bus.subscribe('stt.error', self._on_stt_error)
        # Commande vocale : arrêt enregistrement (pipeline commandes)
        event_bus.subscribe('command.stop_recording', self._on_command_stop_recording)
        
        self.logger.info("Abonnement aux événements Event Bus OK")
    
    def _on_command_stop_recording(self, event_data: dict):
        """Callback pour commande vocale « arrête l'enregistrement ». Arrête le PTT sans lancer la transcription."""
        finalize = event_data.get('finalize', False)
        self.root.after(0, lambda f=finalize: self._stop_ptt_recording(finalize=f))

    def _on_llm_token(self, event_data: dict):
        """Callback pour événement llm.token."""
        token = event_data.get('token', '')
        
        # Si on a un StreamingTextDisplay, ajouter le token
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            self.root.after(0, lambda: self.conversation_area.append_token(token))
    
    def _on_llm_start(self, event_data: dict):
        """Callback pour événement llm.start."""
        # Marquer le début d'une génération en streaming
        self._llm_streaming_active = True
        # Mettre à jour le statut pour refléter que QAIA génère une réponse
        self._set_status("llm_typing")
        # Démarrer une nouvelle génération QAIA
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            self.root.after(0, lambda: self.conversation_area.start_generation("QAIA"))
    
    def _on_llm_complete(self, event_data: dict):
        """Callback pour événement llm.complete."""
        # CRITIQUE: Thread-safety pour empêcher les appels TTS multiples (TODO-11)
        with getattr(self, '_tts_lock', threading.Lock()):
            if getattr(self, '_tts_already_triggered', False):
                self.logger.warning("TTS déjà déclenché, ignorer appel multiple")
                return
            
            # Marquer TTS comme déclenché AVANT traitement
            self._tts_already_triggered = True
        
        # Terminer la génération
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            # Récupérer le texte complet streamé AVANT de terminer la génération
            streamed_text = self.conversation_area.get_streamed_text()
            
            # Post-traitement complet du texte streamé (nettoyage + correction orthographique)
            if streamed_text:
                try:
                    from utils.text_processor import process_streamed_text
                    cleaned_streamed = process_streamed_text(streamed_text)
                    
                    if cleaned_streamed:
                        qaia = getattr(self, "qaia", None)
                        # Déclencher le TTS immédiatement (avant mise à jour UI) pour réduire le décalage voix/texte
                        if qaia and hasattr(qaia, "speak"):
                            def _speak_streamed(txt: str):
                                try:
                                    self.logger.info(f"TTS UI (streaming): déclenchement, longueur={len(txt)}")
                                    if hasattr(qaia.speech_agent, "speak"):
                                        self.qaia.speech_agent.speak(txt, wait=False)
                                    else:
                                        try:
                                            qaia.speak(txt, wait=False)
                                        except TypeError:
                                            qaia.speak(txt)
                                    self.logger.info("TTS UI (streaming): lancé (non bloquant)")
                                except Exception as e:
                                    self.logger.error(f"TTS UI (streaming): échec {e}")
                                finally:
                                    with getattr(self, "_tts_lock", threading.Lock()):
                                        self._tts_already_triggered = False
                            threading.Thread(target=_speak_streamed, args=(cleaned_streamed,), daemon=True).start()
                            self.logger.debug(f"TTS déclenché avec texte streamé traité: {len(cleaned_streamed)} caractères")
                        # CRITIQUE: Remplacer le message PUIS terminer la génération dans le même callback
                        # pour garantir l'ordre (évite complete_generation avant replace → doublon préfixe)
                        def _replace_then_complete(txt: str):
                            self.conversation_area.replace_current_message(txt)
                            self.conversation_area.complete_generation()
                            self.conversation_area.add_spacing(4)
                        self.root.after(0, lambda t=cleaned_streamed: _replace_then_complete(t))
                    else:
                        # Texte streamé mais vide après nettoyage : terminer quand même
                        self.root.after(0, lambda: self.conversation_area.complete_generation())
                        self.root.after(0, lambda: self.conversation_area.add_spacing(4))
                except Exception as e:
                    self.logger.error(f"Erreur post-traitement texte streamé: {e}")
                    with getattr(self, '_tts_lock', threading.Lock()):
                        self._tts_already_triggered = False
                    self.root.after(0, lambda: self.conversation_area.complete_generation())
                    self.root.after(0, lambda: self.conversation_area.add_spacing(4))
            
            if not streamed_text:
                self.root.after(0, lambda: self.conversation_area.complete_generation())
                self.root.after(0, lambda: self.conversation_area.add_spacing(4))
        # Streaming terminé
        self._llm_streaming_active = False
        # Repasser l'interface en état prêt si aucun autre traitement n'est en cours
        if not getattr(self, "is_processing", False):
            self._set_status("ready")

    def _on_llm_error(self, event_data: dict):
        """Callback pour événement llm.error (erreurs de génération LLM)."""
        error_msg = event_data.get("error", "Erreur LLM inconnue.")
        self.logger.error(f"Erreur LLM (event): {error_msg}")
        # S'assurer que le flag de streaming est réinitialisé en cas d'erreur
        self._llm_streaming_active = False
        self._set_status("error_llm")
        if hasattr(self, "conversation_area") and isinstance(self.conversation_area, StreamingTextDisplay):
            # Si un bloc QAIA en streaming est déjà ouvert, remplacer son contenu par l'erreur
            # pour éviter le doublon "(HH:MM) QAIA: (HH:MM) QAIA: Erreur..."
            if getattr(self.conversation_area, "_is_streaming", False):
                full_msg = f"Erreur lors de la génération de réponse: {error_msg}"
                self.root.after(
                    0,
                    lambda msg=full_msg: (
                        self.conversation_area.replace_current_message(msg),
                        self.conversation_area.complete_generation(),
                        self.conversation_area.add_spacing(4),
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda msg=error_msg: self.conversation_area.add_message(
                        "QAIA",
                        f"Erreur lors de la génération de réponse: {msg}",
                    ),
                )
    
    def _on_stt_transcribing(self, event_data: dict):
        """Callback pour événement stt.transcribing."""
        # Mettre à jour la barre d'état en mode transcription vocale
        # On ne prend pas le texte brut pour garantir l'uniformité des messages.
        self.root.after(0, lambda: self._set_status("stt_transcribing"))
    
    def _on_stt_complete(self, event_data: dict):
        """Callback pour événement stt.complete."""
        # NOTE: L'affichage du message utilisateur est géré par _after_transcription()
        # dans _stop_ptt_recording() pour éviter les doublons.
        # Ce callback est conservé pour compatibilité mais n'affiche plus le message.
        transcription = event_data.get('transcription', '')
        self.logger.debug(f"STT complété (événement): {transcription[:50]}...")

    def _on_stt_error(self, event_data: dict):
        """Callback pour événement stt.error (erreurs de transcription)."""
        error_msg = event_data.get("error", "Erreur de transcription.")
        self.logger.error(f"Erreur STT (event): {error_msg}")
        # Utiliser le même statut que les erreurs micro/PTT pour cohérence UX
        self._set_status("error_micro")
        if hasattr(self, "conversation_area") and isinstance(self.conversation_area, StreamingTextDisplay):
            self.root.after(
                0,
                lambda: self.conversation_area.add_message(
                    "QAIA",
                    f"Erreur transcription vocale: {error_msg}",
                ),
            )
    
    def _on_closing(self):
        """Gère la fermeture propre de l'application."""
        try:
            # Arrêter monitoring
            metrics_collector.stop_monitoring()
            
            # Arrêter Event Bus
            event_bus.stop()

            # Nettoyer le noyau et les agents si disponibles
            try:
                qaia = getattr(self, "qaia", None)
                if qaia is not None:
                    # CRITIQUE: Réinitialiser l'état de conversation
                    try:
                        qaia.clear_conversation()
                        qaia._first_interaction = True  # Pour prochaine session
                        self.logger.info("État de conversation réinitialisé")
                    except Exception as e_conv:
                        self.logger.error(f"Erreur réinitialisation conversation: {e_conv}")
                    
                    # Arrêter la synthèse vocale
                    try:
                        if hasattr(qaia, "stop_speech"):
                            qaia.stop_speech()
                    except Exception:
                        pass
                    
                    # Nettoyer le noyau
                    try:
                        if hasattr(qaia, "cleanup"):
                            qaia.cleanup()
                    except Exception:
                        pass
                    
                    # Demander au gestionnaire d'agents de nettoyer
                    try:
                        from utils.agent_manager import agent_manager
                        agent_manager.cleanup_agents()
                    except Exception:
                        pass
            except Exception as e_agents:
                self.logger.error(f"Erreur lors du nettoyage des agents: {e_agents}")

            # Fermer proprement la base de données si initialisée
            try:
                if hasattr(self, "db") and self.db and hasattr(self.db, "conn"):
                    self.db.conn.close()
                    self.logger.info("Connexion base de données fermée proprement")
            except Exception as e_db:
                self.logger.error(f"Erreur lors de la fermeture de la base de données: {e_db}")
            
            if hasattr(self, '_ui_tick_id') and self._ui_tick_id is not None:
                self.root.after_cancel(self._ui_tick_id)
                self._ui_tick_id = None
        except Exception as e:
            self.logger.error(f"Erreur lors de l'annulation du scheduler UI: {e}")
        self.root.destroy()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        # Frame principal avec un style plus moderne
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style personnalisé pour les boutons
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.map("TButton",
                 foreground=[('pressed', 'blue'), ('active', 'blue')],
                 background=[('pressed', '!disabled', '#ddd'), ('active', '#ddd')])
        
        # Zone de conversation principale (streaming LLM + historique complet)
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Utiliser StreamingTextDisplay comme zone unique de conversation
        # pour profiter du streaming token-par-token et des messages complets.
        self.conversation_area = StreamingTextDisplay(
            text_frame,
            width=800,
            height=400
        )
        self.conversation_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame pour la saisie de texte
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Champ de saisie de texte
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.input_field.bind("<Return>", self.process_text_input)
        
        # Bouton d'envoi
        self.send_button = ttk.Button(
            input_frame,
            text="Envoyer",
            command=self.process_text_input
        )
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        # Frame pour les boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Bouton de nettoyage
        self.clear_button = ttk.Button(
            button_frame,
            text="🗑️ Effacer",
            command=self.clear_text
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Bouton Push-To-Talk (PTT)
        self.ptt_button = ttk.Button(
            button_frame,
            text="🎙 Parler",
            command=self.toggle_ptt
        )
        self.ptt_button.pack(side=tk.LEFT, padx=5)

        # Bouton pour interrompre la synthèse vocale
        self.stop_tts_button = ttk.Button(
            button_frame,
            text="⏸ Interrompre la voix",
            command=self.stop_tts
        )
        self.stop_tts_button.pack(side=tk.LEFT, padx=5)

        # Bouton Diagnostic
        self.health_button = ttk.Button(
            button_frame,
            text="🩺 Diagnostic",
            command=self.open_health_window
        )
        self.health_button.pack(side=tk.LEFT, padx=5)

        # Bouton Monitoring (utilise la fenêtre modulaire)
        self.monitor_button = ttk.Button(
            button_frame,
            text="📊 Monitoring",
            command=self._open_monitoring
        )
        self.monitor_button.pack(side=tk.LEFT, padx=5)

        # Indicateur d'état du système (messages unifiés)
        self.status_label = ttk.Label(button_frame)
        self.status_label.pack(side=tk.RIGHT, padx=10)
        # Appliquer l'état initial cohérent
        self._set_status("ready")

        # État PTT (centralisé via system_config)
        self.ptt_active = False
        self.ptt_stream = None
        self.ptt_frames = []
        if MODEL_CONFIG and "audio" in MODEL_CONFIG:
            self.ptt_sample_rate = int(MODEL_CONFIG["audio"].get("sampling_rate", 16000))
        else:
            self.ptt_sample_rate = 16000
        if MODEL_CONFIG and "microphone" in MODEL_CONFIG:
            self.ptt_max_duration_ms = int(MODEL_CONFIG["microphone"].get("ptt_max_duration_ms", 7000))
            self.ptt_input_device_id = MODEL_CONFIG["microphone"].get("input_device_id")
        else:
            self.ptt_max_duration_ms = 7000
            self.ptt_input_device_id = None
        self.ptt_timeout_after_id = None
        
        # AudioManager pour gestion robuste et cleanup
        try:
            self.audio_manager = AudioManager()
            # Diagnostics périphérique + micro natif pour calibrage STT
            try:
                info = self.audio_manager.get_device_info()
                if info:
                    self.logger.info(f"Périphérique audio détecté: {info.name} ({info.sample_rate}Hz)")
                mic_metrics = self.audio_manager.test_microphone()
                self.logger.info(f"Diagnostics micro natif: {mic_metrics}")
            except Exception as e_mic:
                self.logger.warning(f"Impossible de diagnostiquer le micro: {e_mic}")
            self.logger.info("✅ AudioManager initialisé")
        except Exception as e:
            self.logger.warning(f"⚠️ AudioManager non disponible: {e}, utilisation fallback directe")
            self.audio_manager = None

        # Raccourci clavier pour le diagnostic (F9)
        try:
            self.root.bind("<F9>", lambda _e=None: self.open_health_window())
        except Exception:
            pass
    
    def process_text_input(self, event=None):
        """
        Traite l'entrée texte saisie par l'utilisateur depuis le champ principal.

        Cette méthode valide l'état du noyau, empêche les doubles envois,
        met à jour l'UI (statut, bouton, historique) puis délègue le traitement
        au thread `_process_text_thread`.

        Args:
            event: Éventuel événement Tkinter (ex: pression de la touche Entrée).

        Returns:
            str | None: La chaîne spéciale \"break\" pour stopper la propagation
            de l'événement clavier, ou None dans les autres cas.
        """
        # Anti-doublon si un traitement est déjà en cours
        if getattr(self, 'is_processing', False):
            return "break" if event is not None else None

        # Vérifier que le noyau est prêt
        if not getattr(self, "qaia", None):
            # Noyau en cours d'initialisation ou indisponible
            self._set_status("core_initializing")
            if hasattr(self, "conversation_area") and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message(
                    "QAIA",
                    "Noyau non prêt, merci de patienter quelques secondes puis de réessayer."
                )
            return "break" if event is not None else None

        self.is_processing = True
        # Récupérer le texte
        text = self.input_field.get()
        if not text:
            self.is_processing = False
            return "break" if event is not None else None
            
        # Interruption de la synthèse vocale en cours (barge-in) uniquement si parlant
        try:
            if hasattr(self.qaia, 'speech_agent') and getattr(self.qaia.speech_agent, 'is_speaking', False):
                if hasattr(self.qaia, 'stop_speech'):
                    self.qaia.stop_speech()
        except Exception:
            pass

        # Effacer le champ de saisie
        self.input_field.delete(0, tk.END)
        
        # Désactiver le bouton pendant le traitement
        self.send_button.configure(state="disabled")
        self._set_status("llm_typing")
        
        # Afficher le texte dans la zone de texte
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            self.conversation_area.add_message("Vous", text)
        
        # Lancer le traitement dans un thread séparé
        threading.Thread(target=self._process_text_thread, args=(text,), daemon=True).start()
        # Empêcher la propagation de l'événement <Return> pour éviter un double envoi
        if event is not None:
            return "break"
    
    def _process_text_thread(self, text, media_info: dict | None = None):
        """Traite l'entrée texte dans un thread séparé et journalise la conversation.

        Args:
            text (str): Texte utilisateur
            media_info (dict|None): Informations médias optionnelles, clés supportées:
                - 'user_audio_path' (str)
                - 'user_audio_duration_ms' (int)
                - 'speaker_id' (str): Identifiant du locuteur (si identifié via PTT)
        """
        try:
            # Vérifier que le noyau est disponible avant tout traitement
            qaia = getattr(self, "qaia", None)
            if qaia is None:
                # Noyau indisponible (échec ou non-initialisation) : ne pas appeler process_message
                self.root.after(
                    0,
                    lambda: self.conversation_area.add_message(
                        "QAIA",
                        "Noyau indisponible, merci de redémarrer QAIA ou de vérifier les logs système."
                    )
                )
                self.root.after(0, lambda: self._set_status("error_core"))
                return

            # Mettre à jour l'interface
            def _set_typing():
                try:
                    self._set_status("llm_typing")
                except Exception:
                    pass
            self.root.after(100, _set_typing)
            
            # Appeler le modèle (avec speaker_id si identifié ; confirmation commande si en attente)
            speaker_id = media_info.get('speaker_id') if media_info else None
            confirmation_pending = getattr(self, "_pending_command", None)
            if confirmation_pending:
                self._pending_command = None
            result = qaia.process_message(
                text, speaker_id=speaker_id, confirmation_pending=confirmation_pending
            )
            # Mémoriser une commande en attente de confirmation (oui/non)
            if result.get("intent") == "command_confirmation_pending":
                self._pending_command = {
                    "command_verb": result.get("command_verb"),
                    "command_target": result.get("command_target"),
                }
            response = result.get('response', '')
            
            if response and isinstance(response, str) and response.strip():
                # Affichage de la réponse
                # Si le streaming LLM est actif, l'affichage token-par-token
                # a déjà été géré par les événements llm.start/token/complete.
                # Dans ce cas, on n'ajoute pas de message complet pour éviter le doublon.
                if not getattr(self, "_llm_streaming_active", False):
                    # Post-traitement complet via module centralisé
                    try:
                        from utils.text_processor import process_text_for_display
                        text_for_display_and_tts = process_text_for_display(response)
                    except Exception as e:
                        self.logger.warning(f"Erreur post-traitement texte: {e}, utilisation texte brut")
                        text_for_display_and_tts = response.strip()

                    # IMPORTANT: Utiliser exactement le même texte traité pour affichage ET TTS
                    if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                        self.root.after(
                            100,
                            lambda txt=text_for_display_and_tts: self.conversation_area.add_message("QAIA", txt)
                        )

                    # Synthèse vocale (thread dédié, wait=True, hors thread UI)
                    if hasattr(qaia, 'speak'):
                        def _speak_worker(txt: str):
                            try:
                                self.logger.info(f"TTS UI: déclenchement, longueur={len(txt)}")
                                if hasattr(qaia.speech_agent, 'speak'):
                                    # Ne pas bloquer l'UI
                                    self.qaia.speech_agent.speak(txt, wait=False)
                                else:
                                    try:
                                        qaia.speak(txt, wait=False)
                                    except TypeError:
                                        qaia.speak(txt)
                                self.logger.info("TTS UI: lancé (non bloquant)")
                            except Exception as e:
                                if hasattr(self.logger, 'error'):
                                    self.logger.error(f"TTS UI: échec {e}")
                                if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                                    self.root.after(
                                        0,
                                        lambda: self.conversation_area.add_message(
                                            "QAIA",
                                            f"Erreur TTS: {e}"
                                        )
                                    )
                        # Utiliser text_for_display_and_tts (même texte que l'affichage) pour synchronisation parfaite
                        threading.Thread(target=_speak_worker, args=(text_for_display_and_tts,), daemon=True).start()
                else:
                    # Streaming actif: le TTS sera déclenché dans _on_llm_complete() avec le texte streamé complet
                    self.logger.debug("Streaming actif: TTS sera déclenché après complétion avec texte streamé")
            else:
                # Gérer les erreurs ou réponses vides
                err_msg = None
                if isinstance(result, dict):
                    err_msg = result.get('error')
                fallback = err_msg or "Désolé, je n'ai pas pu générer de réponse. Réessayez ou reformulez."
                if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                    self.root.after(
                        100,
                        lambda: self.conversation_area.add_message("QAIA", fallback)
                    )

                # Journaliser la conversation en base (avec speaker_id si identifié)
                def _log_conv():
                    try:
                        if self.db:
                            speaker_id = media_info.get('speaker_id') if media_info else None
                            if media_info and (media_info.get('user_audio_path') or media_info.get('qaia_audio_path')):
                                self.db.add_conversation_detailed(
                                    user_input=text,
                                    qaia_response=response,
                                    user_audio_path=media_info.get('user_audio_path'),
                                    qaia_audio_path=media_info.get('qaia_audio_path'),
                                    user_audio_duration_ms=media_info.get('user_audio_duration_ms'),
                                    qaia_audio_duration_ms=media_info.get('qaia_audio_duration_ms'),
                                    speaker_id=speaker_id,
                                )
                            else:
                                self.db.add_conversation(user_input=text, qaia_response=response, speaker_id=speaker_id)
                    except Exception as e:
                        self.logger.error(f"Erreur de journalisation conversation: {e}")
                self.root.after(0, _log_conv)
            
            # Remettre l'interface à l'état initial
            def _reset_ui():
                self._set_status("ready")
                try:
                    self.input_field.focus_set()
                except Exception:
                    pass
            self.root.after(100, _reset_ui)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du texte: {e}")
            self.root.after(100, lambda: messagebox.showerror("Erreur", f"Erreur: {str(e)}"))
            self.root.after(100, lambda: self._set_status("error_generic"))
        
        finally:
            # Réactiver le bouton et réinitialiser l'état PTT
            def _reenable():
                self.send_button.configure(state="normal")
                self.is_processing = False
                self.ptt_stopping = False  # ✅ CRITIQUE: Permet le 2ème enregistrement
            self.root.after(100, _reenable)
    
    def clear_text(self):
        """
        Efface le contenu de la zone de conversation.

        Cette opération ne modifie pas l'historique de conversation côté noyau,
        elle n'affecte que l'affichage dans l'interface.
        """
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            self.conversation_area.clear()

    def toggle_ptt(self):
        """
        Bascule le mode Push-To-Talk (début/fin enregistrement).

        Si aucun noyau n'est prêt ou si le micro n'est pas disponible,
        la méthode affiche un message explicite dans la conversation
        et ne démarre pas la capture audio.
        """
        # Noyau non prêt -> mode dégradé audio désactivé
        if not getattr(self, "qaia", None):
            if hasattr(self, "conversation_area") and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message(
                    "QAIA",
                    "Noyau non prêt, le mode vocal est temporairement désactivé."
                )
            return

        # Vérifier disponibilité sounddevice
        if not SD_AVAILABLE:
            if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message(
                    "QAIA",
                    "Micro non disponible (sounddevice)."
                )
            return

        # Interrompre TTS dès le début (barge-in) uniquement si parlant
        try:
            if hasattr(self.qaia, 'speech_agent') and getattr(self.qaia.speech_agent, 'is_speaking', False):
                if hasattr(self.qaia, 'stop_speech'):
                    self.qaia.stop_speech()
        except Exception:
            pass

        if not self.ptt_active:
            # Démarrer enregistrement
            self._start_ptt_recording()
        else:
            # Arrêter enregistrement
            self._stop_ptt_recording(finalize=True)

    def _start_ptt_recording(self):
        """
        Démarre la capture audio micro (mono 16 kHz) et prépare l'ASR.

        Gère l'initialisation du flux `sounddevice`, le préchauffage éventuel
        de l'agent vocal et met à jour l'interface (boutons, statut).

        Exceptions gérées:
            Toute erreur d'initialisation micro est journalisée et un message
            d'erreur utilisateur est affiché, sans faire crasher l'UI.
        """
        try:
            # Préparer l'agent vocal en arrière-plan au premier usage
            def _prepare_voice():
                try:
                    voice_agent = getattr(self.qaia, 'voice_agent', None)
                    if voice_agent and hasattr(voice_agent, 'prepare_for_conversation'):
                        voice_agent.prepare_for_conversation()
                except Exception:
                    pass
            threading.Thread(target=_prepare_voice, daemon=True).start()

            self.ptt_frames = []
            self.ptt_active = True
            self.ptt_button.configure(text="⏹ Arrêter")
            self._set_status("ptt_recording")
            self.send_button.configure(state="disabled")

            def _callback(indata, frames, time_info, status):  # noqa: ARG001
                try:
                    self.ptt_frames.append(indata.copy())
                except Exception:
                    pass

            stream_kw = dict(
                samplerate=self.ptt_sample_rate,
                channels=1,
                dtype='float32',
                callback=_callback,
            )
            if getattr(self, 'ptt_input_device_id', None) is not None:
                stream_kw["device"] = self.ptt_input_device_id
            self.ptt_stream = sd.InputStream(**stream_kw)
            self.ptt_stream.start()

            # Timeout auto arrêt après 7s
            self.ptt_timeout_after_id = self.root.after(self.ptt_max_duration_ms, lambda: self._stop_ptt_recording(finalize=True))
        except Exception as e:
            self.ptt_active = False
            self.ptt_button.configure(text="🎙 Parler")
            self._set_status("error_micro")
            self.logger.error(f"Erreur démarrage PTT: {e}")
            
            # Cleanup via AudioManager si disponible
            if self.audio_manager is not None and self.ptt_stream is not None:
                try:
                    self.audio_manager.cleanup_stream(self.ptt_stream)
                except Exception:
                    pass
            
            if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message("QAIA", f"Erreur enregistrement: {e}")

    def _stop_ptt_recording(self, finalize: bool = True):
        """
        Arrête la capture audio et, si demandé, lance la transcription.

        Utilise AudioManager pour le cleanup robuste des streams audio.

        Args:
            finalize (bool): Indique si la transcription doit être lancée
                après l'arrêt (True) ou si l'arrêt est simplement administratif.
        """
        try:
            # Anti-réentrance pour éviter doublons si timeout + clic simultané
            if getattr(self, 'ptt_stopping', False):
                return
            self.ptt_stopping = True
            # Annuler timeout si actif
            if self.ptt_timeout_after_id is not None:
                try:
                    self.root.after_cancel(self.ptt_timeout_after_id)
                except Exception:
                    pass
                self.ptt_timeout_after_id = None

            # Stop stream avec cleanup robuste via AudioManager si disponible
            if self.ptt_stream is not None:
                if self.audio_manager is not None:
                    # Utiliser AudioManager pour cleanup robuste
                    try:
                        self.audio_manager.cleanup_stream(self.ptt_stream)
                        self.logger.debug("✅ Stream nettoyé via AudioManager")
                    except Exception as e:
                        self.logger.warning(f"Erreur cleanup AudioManager: {e}, fallback direct")
                        try:
                            self.ptt_stream.stop()
                            self.ptt_stream.close()
                        except Exception:
                            pass
                else:
                    # Fallback direct si AudioManager non disponible
                    try:
                        self.ptt_stream.stop()
                        self.ptt_stream.close()
                    except Exception:
                        pass
                self.ptt_stream = None

            self.ptt_active = False
            self.ptt_button.configure(text="🎙 Parler")
            self._set_status("stt_transcribing")

            if not finalize:
                self.ptt_stopping = False
                return

            # Sauvegarder en WAV (nom unique) et lancer ASR dans un thread
            def _transcribe_worker(frames_list):
                try:
                    if not frames_list:
                        self.root.after(0, lambda: self._finish_ptt_with_error("Aucun audio capturé"))
                        return
                    audio = np.concatenate(frames_list, axis=0)
                    # ═══════════════════════════════════════════════════════════
                    # CONFIGURATION STT CPU (v2.2.0)
                    # ═══════════════════════════════════════════════════════════
                    # Conversion float32 -> int16 SANS double normalisation
                    # La normalisation audio est gérée uniquement par wav2vec_agent
                    # L'UI n'affaiblit plus le signal avant écriture WAV
                    # PTT = durée max 7s (ptt_max_duration_ms = 7000)
                    # ═══════════════════════════════════════════════════════════
                    audio_mono = audio[:, 0] if audio.ndim > 1 else audio
                    audio_clipped = np.clip(audio_mono, -1.0, 1.0)
                    audio_int16 = (audio_clipped * 32767.0).astype(np.int16)

                    # Écriture WAV via 'wave' (pas de dépendance externe)
                    audio_dir = AUDIO_DIR
                    audio_dir.mkdir(parents=True, exist_ok=True)
                    unique_ts = int(time.time() * 1000)
                    wav_path = audio_dir / f"utt_{unique_ts}.wav"
                    with wave.open(str(wav_path), 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(self.ptt_sample_rate)
                        wf.writeframes(audio_int16.tobytes())

                    # Identifier le locuteur (si service disponible)
                    speaker_id = None
                    speaker_identity = None
                    if hasattr(self, 'voice_identity_service') and self.voice_identity_service:
                        try:
                            speaker_identity = self.voice_identity_service.identifier_locuteur(str(wav_path))
                            if speaker_identity:
                                speaker_id = speaker_identity.get('speaker_id')
                                self.logger.info(f"Locuteur identifié: {speaker_identity}")
                                # Enregistrer le speaker dans la BDD si pas déjà présent
                                if self.db and speaker_id:
                                    speaker_info = self.db.get_speaker(speaker_id)
                                    if not speaker_info:
                                        # Créer l'entrée dans la BDD
                                        self.db.add_speaker(
                                            speaker_id=speaker_id,
                                            prenom=speaker_identity.get('prenom'),
                                            civilite=speaker_identity.get('civilite'),
                                            metadata=speaker_identity.get('metadata'),
                                            embedding_path=None  # Stocké dans voice_profiles/
                                        )
                        except Exception as e:
                            self.logger.warning(f"Erreur identification vocale (non bloquant): {e}")

                    # Transcrire
                    voice_agent = getattr(self.qaia, 'voice_agent', None)
                    if not voice_agent:
                        self.root.after(0, lambda: self._finish_ptt_with_error("Agent vocal indisponible"))
                        return

                    # Préférer la version avec événements (met à jour STT dans AgentsWindow)
                    if hasattr(voice_agent, 'transcribe_with_events'):
                        result = voice_agent.transcribe_with_events(str(wav_path))
                    elif hasattr(voice_agent, 'transcribe_audio'):
                        result = voice_agent.transcribe_audio(str(wav_path))
                    else:
                        self.root.after(0, lambda: self._finish_ptt_with_error("Agent vocal indisponible"))
                        return
                    # Normaliser le retour (éviter erreurs d'unpacking)
                    text, confidence = "", 0.0
                    try:
                        if isinstance(result, tuple):
                            if len(result) >= 1:
                                text = result[0]
                            if len(result) >= 2:
                                confidence = float(result[1])
                        elif isinstance(result, str):
                            text = result
                    except Exception:
                        text, confidence = str(result), 0.0
                    if not isinstance(text, str) or not text.strip() or text.lower().startswith("erreur"):
                        self.root.after(0, lambda: self._finish_ptt_with_error("Transcription vide ou erreur"))
                        return

                    # Seuil de confiance STT (configurable) : suggestion de répéter si faible
                    confidence_threshold = 0.4
                    if MODEL_CONFIG and "speech" in MODEL_CONFIG:
                        confidence_threshold = float(MODEL_CONFIG["speech"].get("confidence_threshold_low", 0.4))
                    low_confidence = confidence < confidence_threshold

                    # Détection de commandes vocales simples (stop vocal)
                    normalized = text.strip().lower()
                    simple_tokens = normalized.split()
                    if 0 < len(simple_tokens) <= 4:
                        if "stop" in normalized or "qaia" in normalized or "caya" in normalized or "cayna" in normalized:
                            # Interrompre la synthèse vocale en cours si possible, sans lancer le LLM
                            self.root.after(0, self.stop_tts)
                        return

                    duration_ms = int(len(audio_int16) * 1000 / self.ptt_sample_rate)

                    # Afficher et enchaîner (avec feedback confiance si faible)
                    def _after_transcription():
                        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                            self.conversation_area.add_message("Vous", text)
                            if low_confidence:
                                self.conversation_area.add_message(
                                    "QAIA",
                                    f"Confiance reconnaissance : {confidence * 100:.0f} %. Vous pouvez répéter pour une meilleure compréhension."
                                )
                        self._set_status("llm_typing")
                        
                        # Ajouter salutation personnalisée si locuteur identifié
                        greeting = None
                        if speaker_identity and hasattr(self, 'voice_identity_service') and self.voice_identity_service:
                            greeting = self.voice_identity_service.generer_salutation(speaker_identity)
                            if greeting and greeting != "Bonjour, comment puis-je vous aider ?":
                                # Afficher la salutation personnalisée avant la réponse LLM
                                if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                                    self.conversation_area.add_message("QAIA", greeting)
                        
                        # Lancer traitement LLM avec speaker_id et confiance STT
                        media = {
                            "user_audio_path": str(wav_path),
                            "user_audio_duration_ms": duration_ms,
                            "speaker_id": speaker_id,
                            "stt_confidence": confidence,
                        }
                        threading.Thread(target=self._process_text_thread, args=(text, media), daemon=True).start()
                    self.root.after(0, _after_transcription)
                except Exception as e:
                    err_msg = str(e)
                    self.root.after(0, lambda msg=err_msg: self._finish_ptt_with_error(msg))
                finally:
                    # Nettoyer systématiquement le fichier audio temporaire
                    try:
                        if wav_path and wav_path.exists():
                            wav_path.unlink()
                    except Exception:
                        # Ne pas faire échouer la transcription pour un simple problème de nettoyage
                        pass

            threading.Thread(target=_transcribe_worker, args=(self.ptt_frames.copy(),), daemon=True).start()
        except Exception as e:
            self._finish_ptt_with_error(str(e))

    def _finish_ptt_with_error(self, reason: str):
        """
        Finalise un cycle PTT en erreur et rétablit l'UI.

        Args:
            reason (str): Message décrivant la cause de l'erreur à afficher
                dans la zone de conversation.
        """
        self.ptt_active = False
        self.ptt_stopping = False
        self.ptt_button.configure(text="🎙 Parler")
        self.send_button.configure(state="normal")
        self._set_status("error_ptt")
        if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
            self.conversation_area.add_message("QAIA", reason)

    def stop_tts(self):
        """
        Interrompt la synthèse vocale en cours si le noyau le permet.

        En cas d'erreur lors de l'appel `stop_speech`, l'exception est
        simplement journalisée sans interrompre l'UI.
        """
        try:
            if hasattr(self.qaia, 'stop_speech'):
                self.qaia.stop_speech()
                self._set_status("tts_stopped")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'interruption TTS: {e}")
    
    def show_health_status(self):
        """
        Affiche un diagnostic rapide des composants QAIA.

        Le diagnostic inclut notamment l'état du LLM, du RAG et des agents
        actifs et est affiché dans la zone de conversation.
        """
        try:
            health = self.qaia.health_check() if getattr(self, "qaia", None) else {"status": "error", "error": "Noyau non initialisé"}

            # Diagnostic texte détaillé incluant état LLM/RAG
            diag_lines = []
            diag_lines.append(f"Statut général: {health.get('status', 'inconnu')}")
            details = health.get("details", {}) if isinstance(health, dict) else {}
            if isinstance(details, dict):
                llm_ok = details.get("llm_loaded", False)
                vector_db_ok = details.get("vector_db", False)
                active_agents = details.get("active_agents", [])
                diag_lines.append(f"LLM chargé: {'✅' if llm_ok else '❌'}")
                diag_lines.append(f"Base vectorielle (RAG): {'✅' if vector_db_ok else '❌'}")
                diag_lines.append(f"Agents actifs: {', '.join(active_agents) if active_agents else 'aucun'}")

            diag_text = "\n".join(diag_lines)

            if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message("QAIA", diag_text)
        except Exception as e:
            if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message("QAIA", f"Erreur diagnostic: {e}")

    def open_health_window(self):
        """Ouvre une fenêtre dédiée pour le diagnostic système."""
        try:
            win = ctk.CTkToplevel(self.root)
            win.title("Diagnostic QAIA")
            win.geometry("520x420")
            frame = ttk.Frame(win, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            text = tk.Text(frame, wrap=tk.WORD, height=20)
            text.pack(fill=tk.BOTH, expand=True)
            # Récupération non bloquante
            def _fill():
                try:
                    qaia = getattr(self, "qaia", None)
                    if qaia is None:
                        text.insert(tk.END, "Noyau non initialisé : diagnostic indisponible.")
                        return
                    health = qaia.health_check()
                    text.insert(tk.END, str(health))
                except Exception as e:
                    text.insert(tk.END, f"Erreur: {e}")
            self.root.after(0, _fill)
        except Exception as e:
            self.logger.error(f"Erreur ouverture fenêtre Diagnostic: {e}")

    def open_monitor_window(self):
        """
        Ouvre la fenêtre Monitoring modulaire (déprécié, utilise _open_monitoring).
        
        Cette méthode est conservée pour compatibilité mais redirige vers _open_monitoring
        qui utilise la fenêtre modulaire MonitoringWindow avec graphiques temps réel.
        """
        self._open_monitoring()

    def _show_welcome_message(self):
        """Affiche et prononce un message de bienvenue au démarrage."""
        welcome = "Bonjour, je suis QAIA, votre assistant intelligent. Comment puis-je vous aider ?"
        try:
            if hasattr(self, 'conversation_area') and isinstance(self.conversation_area, StreamingTextDisplay):
                self.conversation_area.add_message("QAIA", welcome)
            self._set_status("ready")
            # Lancer le premier essai après une courte pause pour stabiliser l'UI
            self.root.after(300, self._try_welcome_speak)
        except Exception:
            pass

    def _attempt_welcome_speak(self):
        """Point d’entrée central pour relancer la voix de bienvenue une fois le noyau prêt."""
        try:
            if not getattr(self, 'welcome_spoken', False):
                # Relancer la tentative SANS réinsérer le texte
                self._try_welcome_speak()
        except Exception:
            pass

    def _try_welcome_speak(self, attempt: int = 0):
        """Tente de prononcer la phrase de bienvenue sans dupliquer l’affichage."""
        if getattr(self, 'welcome_spoken', False):
            return
        qaia = getattr(self, 'qaia', None)
        # Vérifier la disponibilité du moteur TTS
        tts_ready = False
        try:
            if qaia is not None:
                speech_agent = getattr(qaia, 'speech_agent', None)
                if speech_agent and hasattr(speech_agent, 'speak') and getattr(speech_agent, 'is_available', True):
                    tts_ready = True
                elif hasattr(qaia, 'speak'):
                    tts_ready = True
        except Exception:
            tts_ready = False
        if qaia is not None and tts_ready:
            welcome = "Bonjour, je suis QAIA, votre assistant intelligent. Comment puis-je vous aider ?"
            try:
                self.welcome_spoken = True
                if hasattr(qaia, 'speech_agent') and hasattr(qaia.speech_agent, 'speak'):
                    self.logger.info("Bienvenue: TTS via speech_agent (wait=False)")
                    qaia.speech_agent.speak(welcome, wait=False)
                else:
                    self.logger.info("Bienvenue: TTS via qaia.speak (wait=False si supporté)")
                    try:
                        qaia.speak(welcome, wait=False)
                    except TypeError:
                        qaia.speak(welcome)
            except Exception:
                # Réessayer un peu plus tard en cas d'erreur transitoire
                self.welcome_spoken = False
                self.root.after(700, lambda: self._try_welcome_speak(attempt + 1))
        else:
            # Réessayer tant que le noyau/voix n'est pas prêt (limiter à ~10s)
            if attempt < 20:
                self.root.after(500, lambda: self._try_welcome_speak(attempt + 1))

    def _preheat_llm_safe(self):
        """Prépare le LLM pour le mode conversation sans bloquer l'UI."""
        try:
            llm_agent = getattr(self.qaia, 'llm_agent', None)
            if llm_agent and hasattr(llm_agent, 'prepare_for_conversation'):
                ok = llm_agent.prepare_for_conversation()
                if ok:
                    self.root.after(0, lambda: self._set_status("llm_ready"))
        except Exception as e:
            self.logger.error(f"Erreur lors du préchauffage LLM: {e}")