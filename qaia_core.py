#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Module principal de QAIA
Gère le cœur de l'application et coordonne les différents composants
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "chromadb>=0.4.0",
#   "psutil>=5.9.0",
#   "llama-cpp-python>=0.2.71",  # Backend GGUF (Phi-3, etc.)
#   "transformers>=4.26.0",
# ]
# ///

import os
import sys
import gc
import logging
import torch
import traceback
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import psutil
from utils.memory_manager import MemoryManager
from agents.context_manager import ConversationContext
from agents.intent_detector import IntentDetector
from utils.agent_manager import agent_manager
from utils.monitoring import performance_monitor, start_monitoring, record_timing, update_active_agents
from interface.events.event_bus import event_bus
from core.dialogue_manager import DialogueManager
from core.command_executor import get_command_executor
from ui_control.pipeline import UIControlPipeline

# Importer llama-cpp-python (utilisé pour GGUF: Phi-3, etc.)
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("⚠️ llama-cpp-python non disponible, agents LLM uniquement")

# Importer la configuration centralisée depuis system_config.py
from config.system_config import (
    MODEL_CONFIG as QAIA_MODEL_CONFIG,
    MODELS_DIR as QAIA_MODELS_DIR,
    DATA_DIR as QAIA_DATA_DIR,
    LOGS_DIR as QAIA_LOGS_DIR,
    VECTOR_DB_DIR as QAIA_VECTOR_DB_DIR,
    UI_CONTROL_CONFIG as QAIA_UI_CONTROL_CONFIG,
)

def build_system_prompt(context: Optional[str] = None) -> str:
    """
    Construit le prompt système QAIA à partir de la configuration centralisée.
    
    Args:
        context (Optional[str]): Contexte additionnel (ex: RAG) à inclure dans le prompt
        
    Returns:
        str: Prompt système formaté pour Phi-3
    """
    system_config = QAIA_MODEL_CONFIG.get("system_prompt", {})
    
    # Construire le prompt de base
    system_prompt = f"{system_config.get('identity', '')}\n\n{system_config.get('mission', '')}\n\nPrincipes:\n"
    for principle in system_config.get('core_principles', []):
        system_prompt += f"- {principle}\n"
    system_prompt += f"\n{system_config.get('verification', '')}"
    
    # Ajouter le contexte RAG si fourni
    if context:
        system_prompt += f"\n\nContexte additionnel (utilise ces informations si pertinentes):\n{context}"
    
    return system_prompt

# Les imports des agents sont déplacés dans les méthodes spécifiques pour éviter les erreurs circulaires
# Ils seront chargés dynamiquement lors de l'initialisation des agents

# Configuration des chemins (utilise system_config)
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = QAIA_DATA_DIR
LOGS_DIR = QAIA_LOGS_DIR
VECTOR_DB_DIR = QAIA_VECTOR_DB_DIR

class QAIACore:
    """Classe principale de QAIA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
        # Flag pour suivre si c'est la première interaction (pour présentation unique)
        self._first_interaction = True
        self.memory_manager = MemoryManager()
        self.is_initialized = False
        self.vector_db = None
        self.models = {}
        self.agents = {}
        # ContextManager pour mémoire conversationnelle enrichie (résumés, entités)
        try:
            self.context_manager = ConversationContext(
                max_recent_turns=10,
                max_summary_turns=50
            )
            self.logger.info("✅ ContextManager initialisé")
        except Exception as e:
            self.logger.warning(f"⚠️ ContextManager non disponible: {e}, utilisation historique simple")
            self.context_manager = None
        
        # IntentDetector pour adapter le comportement selon l'intention
        try:
            self.intent_detector = IntentDetector()
            self.logger.info("✅ IntentDetector initialisé")
        except Exception as e:
            self.logger.warning(f"⚠️ IntentDetector non disponible: {e}")
            self.intent_detector = None
        
        # Historique simple en fallback (compatibilité)
        self.conversation_history: List[Dict[str, str]] = []  # Historique en mémoire pour le LLM
        
        try:
            self._setup_environment()
            self._import_dependencies()
            self._initialize_components()
            self._verify_initialization()
            # Initialiser le pipeline UI-control (désactivé par défaut)
            self.ui_control_pipeline = UIControlPipeline(
                base_dir=BASE_DIR,
                config=QAIA_UI_CONTROL_CONFIG,
            )
            # Exécuteur de commandes système (détection → sécurité → exécution)
            self.command_executor = get_command_executor()
            self._register_command_actions()
            # Initialiser le gestionnaire de dialogue (réorganisation logique)
            self.dialogue_manager = DialogueManager(
                logger=self.logger,
                memory_manager=self.memory_manager,
                get_llm_agent=lambda: getattr(self, "llm_agent", None),
                get_models=lambda: self.models,
                get_context_manager=lambda: self.context_manager,
                append_history=self._append_history,
                get_conversation_history=lambda: self.conversation_history,
                get_first_interaction=lambda: self._first_interaction,
                set_first_interaction=self._set_first_interaction,
                build_system_prompt=build_system_prompt,
                model_config=QAIA_MODEL_CONFIG,
                get_speaker_context=self._get_speaker_context,
                record_timing=record_timing,
                get_ui_control_pipeline=lambda: self.ui_control_pipeline,
                get_command_executor=lambda: self.command_executor,
            )
            # Injecter IntentDetector si disponible
            self.dialogue_manager.intent_detector = self.intent_detector
            # Précharger LLM et voix en arrière-plan pour réduire la première latence
            try:
                import threading
                def _preheat():
                    try:
                        if hasattr(self, 'llm_agent') and self.llm_agent and hasattr(self.llm_agent, 'prepare_for_conversation'):
                            self.llm_agent.prepare_for_conversation()
                    except Exception:
                        pass
                    try:
                        if hasattr(self, 'voice_agent') and self.voice_agent and hasattr(self.voice_agent, 'prepare_for_conversation'):
                            self.voice_agent.prepare_for_conversation()
                    except Exception:
                        pass
                threading.Thread(target=_preheat, daemon=True).start()
                self.logger.info("Préchargement LLM/Voix déclenché en arrière-plan")
            except Exception:
                pass
            
            # Démarrer le monitoring
            start_monitoring()
            # Mettre à jour les états des agents (émet événements agent.state_change)
            active_agents = list(agent_manager.get_active_agents())
            update_active_agents(active_agents)
            self.logger.info("Monitoring de performance activé")
            
            self.is_initialized = True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def _setup_environment(self) -> None:
        """Configure l'environnement"""
        try:
            # Vérifier les chemins
            for path in [DATA_DIR, VECTOR_DB_DIR]:
                path.mkdir(parents=True, exist_ok=True)
            
            # Configurer PyTorch
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = True
            # Stabiliser l'utilisation CPU
            try:
                torch.set_num_threads(6)
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la configuration de l'environnement: {e}")
            raise
    
    def _import_dependencies(self) -> None:
        """Importe les dépendances nécessaires"""
        try:
            # Importer le Tokenizer standard (peut être utile pour d'autres agents/tâches)
            # Mais ne pas importer AutoModel de transformers pour le LLM principal
            from transformers import AutoTokenizer
            # self.AutoModel = AutoModel # Supprimé
            self.AutoTokenizer = AutoTokenizer
            
            # Importer les utilitaires
            from utils.encoding_utils import setup_encoding
            from utils.log_manager import LogManager
            from utils.version_manager import VersionManager
            
            # Configurer l'encodage
            setup_encoding()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'import des dépendances: {e}")
            raise
    
    def _initialize_components(self) -> None:
        """Initialise les composants"""
        try:
            # L'initialisation de la base vectorielle (ChromaDB) est déléguée
            # à l'agent RAG (`agents.rag_agent`) afin d'éviter les conflits
            # de configuration (PersistentClient vs Client) sur le même répertoire.
            # Ici, on se contente de laisser `self.vector_db` à None ; la santé
            # de RAG est suivie via ses propres logs et métriques.
            self.vector_db = None
            
            # Charger les modèles
            self._load_models()
            
            # Initialiser les agents
            self._initialize_agents()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des composants: {e}")
            raise
    
    def _load_models(self) -> None:
        """Charge les modèles nécessaires en utilisant la configuration de system_config.py"""
        try:
            llm_config = QAIA_MODEL_CONFIG.get("llm")
            if not llm_config:
                self.logger.error("Configuration LLM (MODEL_CONFIG['llm']) non trouvée dans system_config.py")
                raise ValueError("Configuration LLM manquante")

            model_path_str = llm_config.get("model_path")
            if not model_path_str:
                self.logger.error("Chemin du modèle LLM (model_path) non trouvé dans MODEL_CONFIG['llm']")
                raise ValueError("Chemin du modèle LLM manquant dans la configuration")

            model_path = Path(model_path_str)
            backend = llm_config.get("backend", "auto").lower()

            # Forcer Transformers si backend=transformers OU si ce n'est pas un fichier .gguf
            if backend == "transformers" or not (model_path.is_file() and model_path.suffix.lower() == ".gguf"):
                self.logger.info("Backend LLM: Transformers (aucun chargement GGUF)")
                self.models["language"] = None
                return

            # À partir d'ici, backend GGUF
            if not model_path.exists():
                self.logger.error(f"Fichier modèle GGUF non trouvé : {model_path}")
                raise FileNotFoundError(f"Fichier modèle GGUF non trouvé : {model_path}")

            n_gpu_layers = llm_config.get("n_gpu_layers", -1)
            n_ctx = llm_config.get("n_ctx", 2048)
            n_threads = llm_config.get("n_threads", 6)

            if not LLAMA_CPP_AVAILABLE:
                self.logger.warning("llama-cpp-python non disponible, agents LLM uniquement")
                self.models["language"] = None
                return

            try:
                self.models["language"] = Llama(
                    model_path=str(model_path),
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=n_ctx,
                    n_threads=n_threads,
                    verbose=False
                )
                self.logger.info(f"Modèle {model_path.name} chargé avec succès (GGUF)")
                return
            except Exception as e1:
                self.logger.warning(f"Échec du chargement GGUF: {e1}")
                self.models["language"] = None
                return
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des modèles: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def _initialize_agents(self) -> None:
        """Initialise les agents de QAIA avec le gestionnaire centralisé"""
        try:
            # Utiliser le gestionnaire d'agents pour éviter les imports circulaires
            results = agent_manager.initialize_all_agents(model_config=QAIA_MODEL_CONFIG)
            
            # Référencer les agents via le gestionnaire
            self.agents = agent_manager.agents
            
            # Créer des références pratiques pour les agents les plus utilisés
            self.voice_agent = agent_manager.get_agent("voice")
            self.speech_agent = agent_manager.get_agent("speech")
            self.speaker_auth_agent = agent_manager.get_agent("speaker_auth")  # Authentification locuteur
            self.llm_agent = agent_manager.get_agent("llm")  # Nouvel agent LLM
            
            # Vérifier les agents essentiels
            if not agent_manager.has_agent("rag"):
                raise RuntimeError("Agent RAG essentiel non initialisé")
            
            self.logger.info(f"Agents initialisés via gestionnaire: {', '.join(agent_manager.get_active_agents())}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des agents: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def _verify_initialization(self) -> None:
        """Vérifie l'initialisation"""
        try:
            # Vérifier la mémoire
            if not self.memory_manager.check_memory_usage():
                self.logger.warning("Utilisation mémoire élevée détectée après chargement du modèle.")
                self.memory_manager.optimize_memory()
                
            # Vérifier les composants
            if not self.vector_db:
                self.logger.warning("ChromaDB non initialisé ou échec initialisation.")
                # raise RuntimeError("ChromaDB non initialisé")

            # Vérifier que l'agent LLM est disponible
            if not hasattr(self, 'llm_agent') or self.llm_agent is None:
                self.logger.warning("Agent LLM non disponible, utilisation du modèle de fallback")
                if not self.models.get("language"):
                    raise RuntimeError("Aucun modèle de langage (LLM) disponible")

            self.logger.info("Vérification de l'initialisation terminée.")
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de l'initialisation: {e}")
            raise
    
    def interpret_command(self, message: str) -> str:
        """Interprète une commande utilisateur et retourne une réponse"""
        try:
            result = self.process_message(message)
            if isinstance(result, dict):
                if "error" in result:
                    return f"Erreur: {result['error']}"
                elif "response" in result:
                    return result["response"]
                else:
                    return str(result)
            return str(result)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'interprétation de la commande: {e}")
            return "Désolé, je n'ai pas pu traiter votre demande."
    
    def process_message(
        self,
        message: str,
        speaker_id: Optional[str] = None,
        confirmation_pending: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Traite un message via le DialogueManager."""
        if not self.is_initialized:
            return {"error": "QAIA non initialisé"}
        if not hasattr(self, "dialogue_manager") or self.dialogue_manager is None:
            return {"error": "DialogueManager non initialisé"}
        return self.dialogue_manager.process_message(
            message, speaker_id=speaker_id, confirmation_pending=confirmation_pending
        )

    def _get_speaker_context(self, speaker_id: Optional[str]) -> str:
        """
        Récupère un contexte conversationnel récent pour un locuteur.

        Args:
            speaker_id (Optional[str]): Identifiant du locuteur

        Returns:
            str: Contexte formaté ou chaîne vide
        """
        speaker_context = ""
        if speaker_id:
            try:
                from data.database import Database
                db = Database()
                recent_convs = db.get_recent_conversations(limit=5, speaker_id=speaker_id)
                if recent_convs:
                    context_parts = []
                    for conv in recent_convs[:3]:
                        user_input = conv[3] if len(conv) > 3 else ""
                        qaia_response = conv[4] if len(conv) > 4 else ""
                        if user_input and qaia_response:
                            context_parts.append(f"Q: {user_input}\nR: {qaia_response}")
                    if context_parts:
                        speaker_context = "\n\nContexte conversationnel récent:\n" + "\n---\n".join(context_parts)
                        self.logger.debug(
                            f"Contexte conversationnel chargé pour speaker_id={speaker_id} "
                            f"({len(recent_convs)} conversations)"
                        )
            except Exception as e:
                self.logger.warning(
                    f"Erreur lors de la récupération de l'historique du locuteur {speaker_id}: {e}"
                )
        return speaker_context

    def _set_first_interaction(self, value: bool) -> None:
        """Met à jour le flag de première interaction."""
        self._first_interaction = value
    
    def _append_history(self, role: str, content: str) -> None:
        """
        Ajoute un tour à l'historique de conversation en mémoire.

        Utilise ContextManager pour mémoire enrichie (résumés, entités) si disponible,
        sinon fallback vers historique simple.

        Args:
            role (str): 'user' ou 'assistant'
            content (str): Contenu du message
        """
        try:
            if not isinstance(content, str):
                return
            
            # Utiliser ContextManager si disponible
            if self.context_manager is not None:
                self.context_manager.add_turn(role=role, content=content)
                self.logger.debug(f"Tour ajouté via ContextManager: {role} ({len(content)} chars)")
            
            # Maintenir historique simple en parallèle (compatibilité)
            self.conversation_history.append({"role": role, "content": content.strip()})
            # Garder les 10 derniers tours pour limiter la taille
            max_turns = 10
            if len(self.conversation_history) > max_turns:
                self.conversation_history = self.conversation_history[-max_turns:]
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout à l'historique: {e}")

    def clear_conversation(self) -> None:
        """
        Réinitialise l'historique de conversation en mémoire.
        
        Réinitialise également ContextManager si disponible.
        """
        # Réinitialiser ContextManager si disponible
        if self.context_manager is not None:
            self.context_manager.clear()
        self.conversation_history = []

    def health_check(self) -> Dict[str, Any]:
        """Renvoie un diagnostic de santé des composants principaux."""
        try:
            status = {
                "llm_loaded": bool(getattr(self.llm_agent, "_model_loaded", False)) if hasattr(self, 'llm_agent') and self.llm_agent else False,
                "voice_available": bool(getattr(self.voice_agent, "_initialized", False)) if hasattr(self, 'voice_agent') and self.voice_agent else False,
                "speech_available": bool(getattr(self.speech_agent, "is_available", False)) if hasattr(self, 'speech_agent') and self.speech_agent else False,
                "vector_db": self.vector_db is not None,
                "active_agents": list(agent_manager.get_active_agents()),
            }
            return {"status": "ok", "details": status}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def speak(self, text: str) -> None:
        """Convertit le texte en parole"""
        try:
            if not self.is_initialized:
                raise RuntimeError("QAIA non initialisé")
        
            # Vérifier la mémoire
            self.memory_manager.optimize_memory()
            
            # Utiliser l'agent de synthèse vocale si disponible
            if hasattr(self, 'speech_agent') and self.speech_agent and self.speech_agent.is_available:
                # Forcer l'attente pour éviter coupures et chevauchements
                self.speech_agent.speak(text, wait=True)
                self.logger.info(f"Synthèse vocale: {text[:50]}{'...' if len(text) > 50 else ''}")
            else:
                self.logger.info(f"(Pas de TTS) Réponse: {text}")
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la synthèse vocale: {e}")
            # Ne pas lever d'erreur ici pour que l'app continue même sans TTS
    
    def stop_speech(self) -> None:
        """Arrête la synthèse vocale en cours"""
        try:
            if hasattr(self, 'speech_agent') and self.speech_agent:
                # Anti-rebond: ignorer si stop appelé trop tôt après un lancement
                try:
                    import time as _time
                    last = getattr(self, '_last_tts_stop', 0)
                    if _time.time() - last < 0.8:
                        self.logger.info("Stop TTS ignoré (anti-rebond)")
                        return
                    self._last_tts_stop = _time.time()
                except Exception:
                    pass
                self.speech_agent.stop()
                self.logger.info("Synthèse vocale arrêtée")
            else:
                self.logger.info("Pas d'agent de synthèse vocale à arrêter")
        except Exception as e:
                self.logger.error(f"Erreur lors de l'arrêt de la synthèse vocale: {e}")
            # Ne pas lever d'erreur ici pour que l'app continue même sans TTS

    def _register_command_actions(self) -> None:
        """Enregistre les callbacks d'exécution réelle pour les commandes autorisées."""
        try:
            self.command_executor.register_action("arrete", "lecture", self._cmd_stop_lecture)
            self.command_executor.register_action("arrete", "enregistrement", self._cmd_stop_recording)
            self.command_executor.register_action("arrete", "micro", self._cmd_stop_recording)
            self.command_executor.register_action("lance", "navigateur", self._cmd_open_browser)
            self.command_executor.register_action("ouvre", "navigateur", self._cmd_open_browser)
            self.command_executor.register_action("desactive", "micro", self._cmd_stop_recording)
            self.command_executor.register_action("active", "micro", self._cmd_micro_info)
            self.logger.info("Actions commandes système enregistrées")
        except Exception as e:
            self.logger.warning(f"Enregistrement actions commandes partiel: {e}")

    def _cmd_stop_lecture(self) -> str:
        """Arrête la synthèse vocale (lecture TTS). Retourne le message pour l'utilisateur."""
        self.stop_speech()
        return "J'ai arrêté la lecture."

    def _cmd_stop_recording(self) -> str:
        """Demande l'arrêt de l'enregistrement (PTT) via l'Event Bus. Retourne le message pour l'utilisateur."""
        try:
            event_bus.emit("command.stop_recording", {"finalize": False})
        except Exception as e:
            self.logger.warning(f"Emission command.stop_recording: {e}")
        return "J'ai arrêté l'enregistrement."

    def _cmd_open_browser(self) -> str:
        """Ouvre le navigateur par défaut sur une page d'accueil. Retourne le message pour l'utilisateur."""
        try:
            import webbrowser
            webbrowser.open("https://www.google.com")
            return "Navigateur ouvert."
        except Exception as e:
            self.logger.warning(f"Ouverture navigateur: {e}")
            return "Impossible d'ouvrir le navigateur."

    def _cmd_micro_info(self) -> str:
        """Message informatif pour « active le micro » (pas d'action système)."""
        return "Le micro est géré par le bouton Parler dans l'interface."
    
    def cleanup(self) -> None:
        """Nettoie les ressources"""
        try:
            self.logger.info("Nettoyage des ressources QAIA Core...")
            
            # Nettoyer tous les agents via le gestionnaire centralisé
            self.logger.info("Nettoyage des agents via le gestionnaire...")
            agent_manager.cleanup_agents()
            
            # Fermer ChromaDB
            if hasattr(self, 'vector_db') and self.vector_db:
                self.logger.info("Fermeture de la connexion à ChromaDB...")
                try:
                    # ChromaDB se ferme automatiquement, pas besoin d'action explicite
                    self.vector_db = None
                except Exception as e:
                    self.logger.error(f"Erreur lors de la fermeture de ChromaDB: {e}")
            
            # Arrêter le gestionnaire de ressources
            if hasattr(self, 'resource_manager') and self.resource_manager is not None:
                self.logger.info("Arrêt du gestionnaire de ressources...")
                try:
                    if hasattr(self.resource_manager, 'shutdown'):
                        self.resource_manager.shutdown()
                    elif hasattr(self.resource_manager, 'cleanup'):
                        self.resource_manager.cleanup()
                    else:
                        self.logger.info("Gestionnaire de ressources sans méthode shutdown/cleanup")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'arrêt du gestionnaire de ressources: {e}")
            
            # Libérer la mémoire GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.info("Cache CUDA vidé.")

            # Supprimer explicitement le modèle LLM pour libérer la mémoire (important pour GGUF)
            if "language" in self.models and self.models["language"] is not None:
                try:
                    # llama.cpp (backend GGUF) : supprimer la référence pour GC
                    del self.models["language"]
                    self.models["language"] = None
                    self.logger.info("Référence au modèle LLM supprimée.")
                except Exception as e_del:
                    self.logger.error(f"Erreur lors de la tentative de déchargement du LLM: {e_del}")

            # Nettoyer la mémoire Python
            gc.collect()
            self.logger.info("Garbage collection effectuée.")

            # Fermer ChromaDB (si initialisé)
            if self.vector_db:
                try:
                    # self.vector_db.reset() # ATTENTION: Ceci supprime toutes les collections et données.
                    # La persistance est gérée par persist_directory. Pas besoin de reset() pour un cleanup normal.
                    # Si une méthode close() ou similaire existe pour libérer des ressources, l'utiliser.
                    # Pour l'instant, ne rien faire devrait être sûr si la persistance est active.
                    self.logger.info("Client ChromaDB: nettoyage normal (pas de reset).")
                except Exception as e_chroma:
                    self.logger.error(f"Erreur lors du nettoyage de ChromaDB: {e_chroma}")

            self.logger.info("Nettoyage QAIA Core terminé.")

        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage général: {e}")
            # raise # Optionnel: lever l'erreur si le nettoyage échoue est critique
        