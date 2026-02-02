#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gestionnaire centralisé des agents QAIA (restauré)"""

# /// script
# dependencies = [
# ]
# ///

import logging
from typing import Dict, Any, Optional


class _AgentManager:
    def __init__(self) -> None:
        self.logger = logging.getLogger("AgentManager")
        self.agents: Dict[str, Any] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {
            # Déclaration minimale; les modules réels sont importés dans initialize_agent
            "rag": {"module": "agents.rag_agent", "essential": True},
            "voice": {"module": "agents.wav2vec_agent", "essential": False},
            "speech": {"module": "agents.speech_agent", "essential": False},
            "speaker_auth": {"module": "agents.speaker_auth", "essential": False},
            "llm": {"module": "agents.llm_agent", "essential": True},  # Agent LLM moderne
        }

    # API publique
    def get_agent(self, name: str) -> Optional[Any]:
        return self.agents.get(name)

    def has_agent(self, name: str) -> bool:
        return name in self.agents and self.agents[name] is not None

    def get_active_agents(self):
        return [k for k, v in self.agents.items() if v is not None]

    # Initialisation
    def initialize_agent(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Initialise un agent en fonction de sa configuration.

        Notes importantes :
            - Pour l'agent vocal ("voice"), on instancie explicitement
              `Wav2VecVoiceAgent` afin de disposer des méthodes:
              `prepare_for_conversation()`, `transcribe_with_events()`,
              etc. L'utilisation du module seul comme agent empêchait
              l'émission des événements STT (`agent.state_change`) et
              la mise à jour de la fenêtre États Agents.
        """
        try:
            import importlib
            module = importlib.import_module(config["module"])

            agent = None

            # Cas spécial : agent vocal STT
            if name == "voice":
                # L'agent doit être une instance de Wav2VecVoiceAgent
                if hasattr(module, "Wav2VecVoiceAgent"):
                    voice_cls = getattr(module, "Wav2VecVoiceAgent")
                    agent = voice_cls()
                else:
                    # Fallback exceptionnel : utiliser le module, mais cela
                    # désactive les événements STT temps réel.
                    self.logger.warning(
                        "Module agents.wav2vec_agent ne contient pas Wav2VecVoiceAgent, "
                        "utilisation du module comme agent (sans événements STT)."
                    )
                    agent = module

            # Cas génériques pour les autres agents
            elif hasattr(module, "Agent"):
                agent = getattr(module, "Agent")()
            elif hasattr(module, "init"):
                agent = getattr(module, "init")()
            elif hasattr(module, "LLMAgent"):  # Cas spécial pour l'agent LLM (singleton)
                agent_class = getattr(module, "LLMAgent")
                agent = agent_class()
            elif hasattr(module, "SpeechAgent"):  # Instancier l'agent de parole TTS
                agent = getattr(module, "SpeechAgent")()
            else:
                # Fallback: module lui-même (pour agents procéduraux comme rag_agent)
                agent = module

            self.agents[name] = agent
            self.logger.info(f"Agent {name} initialisé avec succès")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent {name}: {e}")
            return False

    def initialize_all_agents(self, model_config: Dict[str, Any]) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name, cfg in self.agent_configs.items():
            ok = self.initialize_agent(name, cfg)
            results[name] = ok
            if not ok and cfg.get("essential", False):
                self.logger.error(f"Agent essentiel {name} a échoué, arrêt de l'initialisation")
                break
        return results

    def cleanup_agents(self) -> None:
        # Nettoyer dans l'ordre inverse d'initialisation
        for name in list(self.agents.keys())[::-1]:
            agent = self.agents.get(name)
            try:
                if agent is None:
                    continue
                if hasattr(agent, "cleanup"):
                    agent.cleanup()
                elif hasattr(agent, "shutdown"):
                    agent.shutdown()
            except Exception:
                pass
            finally:
                self.agents[name] = None
        self.logger.info("Tous les agents ont été nettoyés et les ressources libérées")


agent_manager = _AgentManager()


