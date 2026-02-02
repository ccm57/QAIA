#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Gestionnaire de dialogue central pour QAIA."""

# /// script
# dependencies = []
# ///

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import logging
import time
import traceback

from agents.intent_detector import Intent
from utils.security import validate_user_input


@dataclass
class DialogueResult:
    """Structure standardisée de réponse du gestionnaire de dialogue."""

    response: str
    context: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


class DialogueManager:
    """
    Orchestrateur des interactions texte/voix.

    Centralise la validation, la détection d'intention, la gestion
    d'historique et le routage vers le LLM.
    """

    def __init__(
        self,
        logger: logging.Logger,
        memory_manager: Any,
        get_llm_agent: Callable[[], Any],
        get_models: Callable[[], Dict[str, Any]],
        get_context_manager: Callable[[], Any],
        append_history: Callable[[str, str], None],
        get_conversation_history: Callable[[], List[Dict[str, str]]],
        get_first_interaction: Callable[[], bool],
        set_first_interaction: Callable[[bool], None],
        build_system_prompt: Callable[[Optional[str]], str],
        model_config: Dict[str, Any],
        get_speaker_context: Callable[[Optional[str]], str],
        record_timing: Callable[[str, str, float], None],
        get_ui_control_pipeline: Optional[Callable[[], Any]] = None,
        get_command_executor: Optional[Callable[[], Any]] = None,
    ) -> None:
        """
        Initialise le gestionnaire de dialogue.

        Args:
            logger (logging.Logger): Logger principal
            memory_manager (Any): Gestionnaire mémoire
            get_llm_agent (Callable[[], Any]): Getter LLM agent
            get_models (Callable[[], Dict[str, Any]]): Getter modèles LLM
            get_context_manager (Callable[[], Any]): Getter context manager
            append_history (Callable[[str, str], None]): Ajout historique
            get_conversation_history (Callable[[], List[Dict[str, str]]]): Historique
            get_first_interaction (Callable[[], bool]): Flag première interaction
            set_first_interaction (Callable[[bool], None]): Setter première interaction
            build_system_prompt (Callable[[Optional[str]], str]): Génère prompt système
            model_config (Dict[str, Any]): Configuration LLM
            get_speaker_context (Callable[[Optional[str]], str]): Contexte locuteur
            record_timing (Callable[[str, str, float], None]): Métriques timing
        """
        self.logger = logger
        self.memory_manager = memory_manager
        self.get_llm_agent = get_llm_agent
        self.get_models = get_models
        self.get_context_manager = get_context_manager
        self.append_history = append_history
        self.get_conversation_history = get_conversation_history
        self.get_first_interaction = get_first_interaction
        self.set_first_interaction = set_first_interaction
        self.build_system_prompt = build_system_prompt
        self.model_config = model_config
        self.get_speaker_context = get_speaker_context
        self.record_timing = record_timing
        self.intent_detector = None
        self.get_ui_control_pipeline = get_ui_control_pipeline or (lambda: None)
        self.get_command_executor = get_command_executor or (lambda: None)

    def process_message(
        self,
        message: str,
        speaker_id: Optional[str] = None,
        confirmation_pending: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Traite un message utilisateur via le pipeline de dialogue.

        Args:
            message (str): Message utilisateur
            speaker_id (Optional[str]): Identifiant locuteur pour mémoire personnalisée
            confirmation_pending (Optional[Dict[str, str]]): Si fourni, exécute la commande
                en attente (command_verb, command_target) après confirmation "oui".

        Returns:
            Dict[str, Any]: Résultat standardisé (response/error, intent, etc.)
        """
        try:
            # Validation sécurisée de l'input utilisateur
            validation_result = validate_user_input(message, max_length=4000)
            if not validation_result['is_valid']:
                self.logger.warning(f"Input utilisateur rejeté: {validation_result['blocked_reason']}")
                return {"error": f"Input invalide: {validation_result['blocked_reason']}"}

            # Utiliser l'input nettoyé
            clean_message = validation_result['cleaned_input']
            if validation_result['warnings']:
                self.logger.warning(f"Patterns suspects détectés dans l'input: {validation_result['warnings']}")

            # Normalisation phonétique STT (corriger erreurs transcription)
            try:
                from utils.stt_text_processor import normalize_stt_text
                clean_message = normalize_stt_text(clean_message)
                self.logger.debug(f"Message STT normalisé: '{message[:50]}...' → '{clean_message[:50]}...'")
            except Exception as e_norm:
                self.logger.warning(f"Erreur normalisation STT: {e_norm}, utilisation message brut")

            # Confirmation d'une commande en attente : exécuter si l'utilisateur dit oui
            if confirmation_pending:
                verb = (confirmation_pending.get("command_verb") or "").strip().lower()
                target = (confirmation_pending.get("command_target") or "").strip().lower()
                oui_patterns = ("oui", "ouais", "ok", "d'accord", "oui c'est bon", "confirme", "valide")
                if clean_message.strip().lower() in oui_patterns and verb and target:
                    executor = self.get_command_executor()
                    if executor is not None:
                        exec_result = executor.execute_command(verb, target, context={})
                        if exec_result.success:
                            self.append_history(role="user", content=clean_message)
                            self.append_history(role="assistant", content=exec_result.message)
                            return {
                                "response": exec_result.message,
                                "intent": "command_executed",
                            }
                        return {
                            "response": exec_result.message or exec_result.error or "Erreur d'exécution.",
                            "intent": "command_refused",
                        }
                if clean_message.strip().lower() in ("non", "non merci", "annule", "annuler"):
                    self.append_history(role="user", content=clean_message)
                    self.append_history(role="assistant", content="Commande annulée.")
                    return {"response": "Commande annulée.", "intent": "command_cancelled"}

            # Détecter l'intention si IntentDetector disponible
            intent_detector = getattr(self, "intent_detector", None)
            intent_result = None
            if intent_detector is not None:
                try:
                    intent_result = intent_detector.detect(clean_message)
                    self.logger.info(
                        f"Intention détectée: {intent_result.intent.value} "
                        f"(confiance: {intent_result.confidence:.2f})"
                    )

                    # Gérer les intentions spéciales
                    if intent_result.intent == Intent.END_CONVERSATION and intent_result.confidence > 0.7:
                        return {
                            "response": "Au revoir ! À bientôt.",
                            "intent": intent_result.intent.value,
                            "confidence": intent_result.confidence
                        }
                    if intent_result.intent == Intent.GREETING and intent_result.confidence > 0.7:
                        greeting_response = "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
                        self.append_history(role="user", content=clean_message)
                        self.append_history(role="assistant", content=greeting_response)
                        return {
                            "response": greeting_response,
                            "intent": intent_result.intent.value,
                            "confidence": intent_result.confidence
                        }
                    if intent_result.intent == Intent.CONFIRMATION and intent_result.confidence > 0.7:
                        confirmation_response = "D'accord, je comprends."
                        self.append_history(role="user", content=clean_message)
                        self.append_history(role="assistant", content=confirmation_response)
                        return {
                            "response": confirmation_response,
                            "intent": intent_result.intent.value,
                            "confidence": intent_result.confidence
                        }
                    # Pipeline commandes système : détection → sécurité → exécution
                    if intent_result.intent == Intent.COMMAND and intent_result.confidence >= 0.5:
                        from utils.command_guard import evaluate_command
                        verdict = evaluate_command(
                            intent_result.command_verb,
                            intent_result.command_target,
                            user_context={"speaker_id": speaker_id},
                            raw_text=clean_message,
                        )
                        if verdict.require_confirmation:
                            response_confirmation = (
                                f"Souhaitez-vous vraiment exécuter : {intent_result.command_verb or '?'} "
                                f"{intent_result.command_target or '?'} ? Répondez oui ou non."
                            )
                            self.append_history(role="user", content=clean_message)
                            self.append_history(role="assistant", content=response_confirmation)
                            return {
                                "response": response_confirmation,
                                "intent": "command_confirmation_pending",
                                "command_verb": intent_result.command_verb,
                                "command_target": intent_result.command_target,
                                "confidence": intent_result.confidence,
                            }
                        if verdict.allowed:
                            executor = self.get_command_executor()
                            if executor is not None:
                                exec_result = executor.execute_command(
                                    intent_result.command_verb or "",
                                    intent_result.command_target or "",
                                    context={},
                                )
                                if exec_result.success:
                                    self.append_history(role="user", content=clean_message)
                                    self.append_history(role="assistant", content=exec_result.message)
                                    return {
                                        "response": exec_result.message,
                                        "intent": "command_executed",
                                        "confidence": intent_result.confidence,
                                    }
                                return {
                                    "response": exec_result.message or exec_result.error or "Erreur d'exécution.",
                                    "intent": "command_refused",
                                }
                            self.append_history(role="user", content=clean_message)
                            self.append_history(role="assistant", content=verdict.reason)
                            return {
                                "response": verdict.reason,
                                "intent": "command_executed",
                                "confidence": intent_result.confidence,
                            }
                        self.append_history(role="user", content=clean_message)
                        self.append_history(role="assistant", content=verdict.reason)
                        return {
                            "response": verdict.reason,
                            "intent": "command_refused",
                            "confidence": intent_result.confidence,
                        }
                except Exception as e:
                    self.logger.warning(f"Erreur détection intention: {e}")

            # Tentative de routage UI-control si activé
            ui_pipeline = self.get_ui_control_pipeline()
            if ui_pipeline and getattr(ui_pipeline, "can_handle", None) and ui_pipeline.can_handle(clean_message):
                ui_result = ui_pipeline.handle_command(clean_message, require_confirmation=True)
                if ui_result.response:
                    self.append_history(role="user", content=clean_message)
                    self.append_history(role="assistant", content=ui_result.response)
                if ui_result.status == "confirmation_required":
                    return {
                        "response": ui_result.response,
                        "intent": "ui_action_pending",
                        "ui_action": {
                            "plan_id": ui_result.action_plan.plan_id if ui_result.action_plan else None,
                            "steps": [step.__dict__ for step in ui_result.action_plan.steps] if ui_result.action_plan else []
                        }
                    }
                if ui_result.status == "executed":
                    return {
                        "response": ui_result.response,
                        "intent": "ui_action",
                        "ui_action": {"status": "executed"}
                    }
                if ui_result.error:
                    return {"error": ui_result.error, "response": ui_result.response}
                if ui_result.response:
                    return {"response": ui_result.response}

            # Vérifier la disponibilité du LLM
            llm_agent = self.get_llm_agent()
            models = self.get_models()
            llm_available = False
            if llm_agent is not None:
                llm_available = True
                self.logger.debug("Utilisation de l'agent LLM moderne")
            elif models.get("language") is not None:
                llm_available = True
                self.logger.debug("Utilisation du modèle LLM de fallback")

            if not llm_available:
                self.logger.error("Tentative de traitement de message sans modèle LLM chargé.")
                return {"error": "LLM non disponible"}

            # Vérifier la mémoire avant la génération
            self.memory_manager.optimize_memory()
            if not self.memory_manager.check_memory_usage():
                self.logger.warning("Utilisation mémoire élevée avant la génération de réponse.")

            # Récupérer l'historique récent du locuteur si identifié
            speaker_context = self.get_speaker_context(speaker_id)

            # Contexte pour fallback (si besoin futur)
            context = speaker_context

            # Générer la réponse avec le LLM approprié (avec historique)
            try:
                start_time = time.time()

                if llm_agent is not None:
                    # Mettre à jour l'historique avec le message utilisateur
                    self.append_history(role="user", content=clean_message)

                    # Émettre événement agent.state_change pour LLM (EN_COURS)
                    try:
                        from interface.events.event_bus import event_bus
                        event_bus.emit('agent.state_change', {
                            'name': 'LLM',
                            'status': 'EN_COURS',
                            'activity_percentage': 75.0,
                            'details': 'Génération de réponse en cours...',
                            'last_update': time.time()
                        })
                    except Exception:
                        pass

                    # Récupérer contexte enrichi via ContextManager si disponible
                    context_manager = self.get_context_manager()
                    if context_manager is not None:
                        conversation_history = context_manager.get_context_for_llm(
                            include_summary=True,
                            max_turns=10
                        )
                        self.logger.debug(
                            f"Contexte enrichi: {len(conversation_history)} tours "
                            f"(résumé: {bool(context_manager.summary)})"
                        )
                    else:
                        conversation_history = self.get_conversation_history()

                    # Sanitizer l'historique avant envoi au LLM
                    try:
                        from utils.history_sanitizer import sanitize_conversation_history
                        conversation_history = sanitize_conversation_history(conversation_history)
                        self.logger.debug(f"Historique sanitizé: {len(conversation_history)} tours valides")
                    except Exception as e_sanitize:
                        self.logger.warning(
                            f"Erreur sanitization historique: {e_sanitize}, utilisation historique brut"
                        )

                    response_text = llm_agent.chat(
                        message=clean_message,
                        conversation_history=conversation_history,
                        is_first_interaction=self.get_first_interaction()
                    )

                    if self.get_first_interaction():
                        self.set_first_interaction(False)

                    try:
                        from interface.events.event_bus import event_bus
                        event_bus.emit('agent.state_change', {
                            'name': 'LLM',
                            'status': 'ACTIF',
                            'activity_percentage': 100.0,
                            'details': f'Réponse générée ({len(response_text)} caractères)',
                            'last_update': time.time()
                        })
                    except Exception:
                        pass
                else:
                    # Utiliser le modèle LLM de fallback
                    system_prompt = self.build_system_prompt(context=context)
                    prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{clean_message}<|end|>\n<|assistant|>\n"
                    llm_cfg = self.model_config.get("llm", {})
                    response = models["language"](
                        prompt=prompt,
                        temperature=llm_cfg.get("temperature", 0.6),
                        top_p=llm_cfg.get("top_p", 0.9),
                        top_k=llm_cfg.get("top_k", 40),
                        repeat_penalty=llm_cfg.get("repeat_penalty", 1.1),
                        stop=[
                            "<|end|>", "\n\n", "Utilisateur:", "User:", "Human:",
                            "Assistant:", "<|user|>", "<|assistant|>"
                        ],
                        max_tokens=llm_cfg.get("max_tokens", 256),
                        echo=False
                    )

                    response_text = response["choices"][0]["text"] if response and "choices" in response else ""
                    response_text = response_text.strip()
                    for artifact in ["<|im_end|>", "<|endoftext|>", "<|end|>"]:
                        response_text = response_text.replace(artifact, "")

                self.logger.debug(f"Réponse nettoyée du LLM: {response_text}")

                processing_time = time.time() - start_time
                self.record_timing("llm", "response", processing_time)

                # Émettre un événement llm.complete pour les métriques LLM de l'UI
                try:
                    from interface.events.event_bus import event_bus
                    token_count = len(response_text.split()) if response_text else 0
                    event_bus.emit(
                        "llm.complete",
                        {
                            "timestamp": time.time(),
                            "latency": processing_time,
                            "tokens": token_count,
                            "tokens_per_sec": token_count / processing_time if processing_time > 0 else 0,
                        },
                    )
                except Exception:
                    pass

                if response_text:
                    self.append_history(role="assistant", content=response_text)

                result = DialogueResult(
                    response=response_text.strip(),
                    context=context if context else None,
                    intent=intent_result.intent.value if intent_result else None,
                    confidence=intent_result.confidence if intent_result else None,
                    processing_time=processing_time,
                )
                return result.__dict__
            except Exception as e_llm:
                self.logger.error(f"Erreur lors de la génération LLM: {e_llm}")
                self.logger.error(traceback.format_exc())
                return {"error": f"Erreur de génération LLM: {e_llm}"}

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du message: {e}")
            self.logger.error(traceback.format_exc())
            return {"error": f"Erreur interne: {e}"}
