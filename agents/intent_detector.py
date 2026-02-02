#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Détecteur d'Intentions pour QAIA
Classifie les messages utilisateur par type d'intention.
"""

# /// script
# dependencies = []
# ///

import logging
import re
from typing import Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class Intent(Enum):
    """Types d'intentions détectables."""
    QUESTION = "question"                # Question nécessitant réponse
    CLARIFICATION = "clarification"       # Demande de précision
    CONFIRMATION = "confirmation"         # Accusé réception / oui/non
    END_CONVERSATION = "end_conversation" # Signaux de fin
    OFF_TOPIC = "off_topic"              # Hors sujet
    COMMAND = "command"                   # Commande système
    GREETING = "greeting"                 # Salutation
    UNKNOWN = "unknown"                   # Non déterminé

@dataclass
class IntentResult:
    """Résultat de détection d'intention."""
    intent: Intent
    confidence: float
    keywords: List[str]
    requires_response: bool
    # Champs optionnels pour intention COMMAND (remplis par parse_command)
    command_verb: Optional[str] = None
    command_target: Optional[str] = None
    command_subtype: Optional[str] = None

class IntentDetector:
    """
    Détecteur d'intentions basé sur règles.
    
    Analyse le texte utilisateur pour déterminer:
    - Type d'intention (question, confirmation, etc.)
    - Confiance de la détection
    - Si une réponse est nécessaire
    """
    
    def __init__(self):
        """Initialise le détecteur d'intentions."""
        self.logger = logging.getLogger(__name__)
        
        # Patterns d'intentions
        self.patterns = {
            Intent.GREETING: [
                r'\b(bonjour|salut|hello|hey|coucou)\b',
                r'\b(bonne (matinée|journée|soirée))\b'
            ],
            Intent.QUESTION: [
                r'\b(qui|quoi|quand|où|comment|pourquoi|combien)\b',
                r'\?$',
                r'\b(peux-tu|pouvez-vous|est-ce que)\b',
                r'\b(qu\'est-ce|quelle|quel)\b'
            ],
            Intent.CLARIFICATION: [
                r'\b(pardon|comment|répète|peux-tu (répéter|clarifier))\b',
                r'\b(je (ne )?comprends pas)\b',
                r'\b(c\'est-à-dire|c\'est quoi)\b'
            ],
            Intent.CONFIRMATION: [
                r'^\s*(oui|ouais|ok|d\'accord|entendu|compris)\s*$',
                r'^\s*(non|pas du tout|jamais)\s*$',
                r'\b(exactement|précisément|tout à fait)\b'
            ],
            Intent.END_CONVERSATION: [
                r'\b(au revoir|bye|salut|à bientôt|à plus)\b',
                r'\b(merci|merci beaucoup)\s+(au revoir|bye)?\b',
                r'\b(stop|arrête|termine)\b',
                r'\b(c\'est (tout|bon)|fini)\b'
            ],
            Intent.COMMAND: [
                r'\b(lance|démarre|arrête|ferme|ouvre)\b',
                r'\b(active|désactive|configure)\b'
            ]
        }
        
        # Compiler patterns
        self.compiled_patterns = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.patterns.items()
        }
        
        self.logger.info("IntentDetector initialisé")
    
    def detect(self, text: str) -> IntentResult:
        """
        Détecte l'intention d'un message.
        
        Args:
            text: Texte à analyser
            
        Returns:
            IntentResult avec intention et métadonnées
        """
        if not text or not text.strip():
            return IntentResult(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                keywords=[],
                requires_response=False,
                command_verb=None,
                command_target=None,
                command_subtype=None,
            )
        
        text = text.strip().lower()
        
        # Scores par intention
        scores = {intent: 0.0 for intent in Intent}
        matched_keywords = {intent: [] for intent in Intent}
        
        # Tester patterns
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    scores[intent] += len(matches)
                    matched_keywords[intent].extend(matches)
        
        # Intention avec score max
        max_score = max(scores.values())
        
        if max_score == 0:
            detected_intent = Intent.UNKNOWN
            confidence = 0.0
            keywords = []
        else:
            detected_intent = max(scores, key=scores.get)
            confidence = min(max_score / 3.0, 1.0)  # Normaliser
            keywords = matched_keywords[detected_intent]
        
        # Déterminer si réponse nécessaire
        requires_response = detected_intent in [
            Intent.QUESTION,
            Intent.CLARIFICATION,
            Intent.GREETING,
            Intent.COMMAND
        ]
        
        # Pour COMMAND, extraire verbe/cible/sous-type
        command_verb = None
        command_target = None
        command_subtype = None
        if detected_intent == Intent.COMMAND:
            command_verb, command_target, command_subtype = self.parse_command(text)

        self.logger.debug(
            f"Intention détectée: {detected_intent.value} "
            f"(confiance={confidence:.2f}, keywords={keywords})"
        )

        return IntentResult(
            intent=detected_intent,
            confidence=confidence,
            keywords=keywords,
            requires_response=requires_response,
            command_verb=command_verb,
            command_target=command_target,
            command_subtype=command_subtype,
        )
    
    def parse_command(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extrait verbe, cible et sous-type d'une phrase de commande.

        Args:
            text: Texte déjà en minuscules, à analyser (intent COMMAND supposé).

        Returns:
            Tuple (verbe, cible, sous-type). Ex: ("arrête", "enregistrement", "assistant").
        """
        if not text or not text.strip():
            return (None, None, None)
        text = text.strip().lower()
        verb = None
        target = None
        subtype = None

        # Verbes (ordre: plus spécifique en premier)
        verb_patterns = [
            (r"\b(redémarre|redemarre)\b", "redemarre"),
            (r"\b(arrête|arrete|stop)\b", "arrete"),
            (r"\b(ferme|fermer)\b", "ferme"),
            (r"\b(ouvre|ouvrir)\b", "ouvre"),
            (r"\b(lance|démarre|demarre)\b", "lance"),
            (r"\b(active)\b", "active"),
            (r"\b(désactive|desactive)\b", "desactive"),
            (r"\b(configure)\b", "configure"),
            (r"\b(coupe|éteins|eteins)\b", "coupe"),
            (r"\b(allume)\b", "allume"),
        ]
        for pattern, v in verb_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                verb = v
                break

        # Cibles (assistant, enregistrement, micro, interface, navigateur, etc.)
        target_map = [
            (r"\b(enregistrement|enregistrer|record)\b", "enregistrement", "assistant"),
            (r"\b(micro|microphone)\b", "micro", "assistant"),
            (r"\b(assistant|qaia)\b", "assistant", "assistant"),
            (r"\b(interface|écran|ecran)\b", "interface", "assistant"),
            (r"\b(navigateur|navigateur web|chrome|firefox)\b", "navigateur", "app"),
            (r"\b(lecture|tts|voix|synthèse)\b", "lecture", "assistant"),
            (r"\b(application|app)\b", "application", "app"),
            (r"\b(lumière|lumiere|lampe)\b", "lumiere", "device"),
        ]
        for pattern, t, st in target_map:
            if re.search(pattern, text, re.IGNORECASE):
                target = t
                subtype = st
                break
        if not subtype and target:
            subtype = "app"

        return (verb, target, subtype)

    def is_end_conversation(self, text: str) -> bool:
        """
        Vérifie si le message indique une fin de conversation.
        
        Args:
            text: Texte à analyser
            
        Returns:
            True si fin de conversation détectée
        """
        result = self.detect(text)
        return result.intent == Intent.END_CONVERSATION and result.confidence > 0.5
    
    def adapt_response_length(self, intent: Intent) -> str:
        """
        Suggère longueur de réponse selon intention.
        
        Args:
            intent: Intention détectée
            
        Returns:
            "short", "normal" ou "detailed"
        """
        if intent in [Intent.CONFIRMATION, Intent.GREETING]:
            return "short"
        elif intent == Intent.CLARIFICATION:
            return "detailed"
        else:
            return "normal"

# Instance globale
intent_detector = IntentDetector()

