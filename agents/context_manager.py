#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Gestionnaire de Contexte Conversationnel pour QAIA
Gestion mémoire court/moyen/long terme avec résumé automatique.
"""

# /// script
# dependencies = []
# ///

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Turn:
    """Un tour de conversation."""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Entity:
    """Entité extraite de la conversation."""
    name: str
    entity_type: str  # "person", "location", "date", etc.
    mentions: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

@dataclass
class Fact:
    """Fait extrait de la conversation."""
    content: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

class ConversationContext:
    """
    Gestionnaire de contexte conversationnel.
    
    Gère trois niveaux de mémoire:
    - Court terme: 5-10 derniers tours (détail complet)
    - Moyen terme: Résumé des 50 derniers tours
    - Long terme: Entités et faits persistants
    """
    
    def __init__(
        self,
        max_recent_turns: int = 10,
        max_summary_turns: int = 50
    ):
        """
        Initialise le gestionnaire de contexte.
        
        Args:
            max_recent_turns: Nombre de tours en mémoire détaillée
            max_summary_turns: Nombre de tours pour résumé
        """
        self.logger = logging.getLogger(__name__)
        
        # Mémoire court terme (détail complet)
        self.recent_history: List[Turn] = []
        self.max_recent_turns = max_recent_turns
        
        # Mémoire moyen terme (résumé)
        self.summary: str = ""
        self.max_summary_turns = max_summary_turns
        self.summary_history: List[Turn] = []
        
        # Mémoire long terme
        self.entities: Dict[str, Entity] = {}
        self.facts: List[Fact] = []
        
        # Métadonnées conversation
        self.topic: Optional[str] = None
        self.start_time: datetime = datetime.now()
        self.turn_count: int = 0
        
        self.logger.info("ContextManager initialisé")
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Ajoute un tour de conversation.
        
        Args:
            role: "user" ou "assistant"
            content: Contenu du message
            metadata: Métadonnées optionnelles
        """
        turn = Turn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Ajouter à l'historique récent
        self.recent_history.append(turn)
        self.turn_count += 1
        
        # Gérer limite mémoire court terme
        if len(self.recent_history) > self.max_recent_turns:
            # Déplacer tour plus ancien vers summary_history
            old_turn = self.recent_history.pop(0)
            self.summary_history.append(old_turn)
            
            # Créer résumé si nécessaire
            if len(self.summary_history) >= self.max_summary_turns:
                self._create_summary()
        
        # Extraction entités/faits (simplifié)
        if role == "user":
            self._extract_entities(content)
        
        self.logger.debug(f"Tour ajouté: {role} ({len(content)} chars)")
    
    def _extract_entities(self, text: str):
        """
        Extrait entités du texte (version simplifiée).
        
        Args:
            text: Texte à analyser
        """
        # Version simple: détection noms propres (majuscules)
        words = text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 1 and word.isalpha():
                entity_name = word
                
                if entity_name in self.entities:
                    # Entité existante: mettre à jour
                    entity = self.entities[entity_name]
                    entity.mentions += 1
                    entity.last_seen = datetime.now()
                else:
                    # Nouvelle entité
                    self.entities[entity_name] = Entity(
                        name=entity_name,
                        entity_type="unknown"
                    )
    
    def _create_summary(self):
        """Crée un résumé de l'historique ancien."""
        if not self.summary_history:
            return
        
        # Résumé simple: concatener derniers tours
        summary_parts = []
        for turn in self.summary_history[-20:]:  # 20 derniers tours
            summary_parts.append(f"{turn.role}: {turn.content[:100]}")
        
        self.summary = " | ".join(summary_parts)
        
        # Nettoyer historique résumé
        self.summary_history = []
        
        self.logger.debug(f"Résumé créé ({len(self.summary)} chars)")
    
    def get_context_for_llm(
        self,
        include_summary: bool = True,
        max_turns: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Retourne contexte formaté pour LLM.
        
        Args:
            include_summary: Inclure résumé conversation
            max_turns: Limiter nombre de tours (None = tous)
            
        Returns:
            Liste de tours au format {"role": "...", "content": "..."}
        """
        context = []
        
        # Ajouter résumé si disponible
        if include_summary and self.summary:
            context.append({
                "role": "system",
                "content": f"Résumé conversation précédente: {self.summary}"
            })
        
        # Ajouter tours récents
        recent = self.recent_history
        if max_turns and len(recent) > max_turns:
            recent = recent[-max_turns:]
        
        for turn in recent:
            context.append({
                "role": turn.role,
                "content": turn.content
            })
        
        return context
    
    def get_last_n_turns(self, n: int) -> List[Turn]:
        """Retourne les N derniers tours."""
        return self.recent_history[-n:] if n < len(self.recent_history) else self.recent_history
    
    def find_entity(self, name: str) -> Optional[Entity]:
        """Recherche une entité par nom."""
        return self.entities.get(name)
    
    def get_top_entities(self, n: int = 5) -> List[Entity]:
        """Retourne les N entités les plus mentionnées."""
        sorted_entities = sorted(
            self.entities.values(),
            key=lambda e: e.mentions,
            reverse=True
        )
        return sorted_entities[:n]
    
    def clear(self):
        """Réinitialise le contexte."""
        self.recent_history = []
        self.summary = ""
        self.summary_history = []
        self.entities = {}
        self.facts = []
        self.topic = None
        self.turn_count = 0
        self.start_time = datetime.now()
        self.logger.info("Contexte réinitialisé")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne statistiques du contexte."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "turn_count": self.turn_count,
            "recent_turns": len(self.recent_history),
            "has_summary": bool(self.summary),
            "entity_count": len(self.entities),
            "fact_count": len(self.facts),
            "duration_seconds": duration,
            "topic": self.topic
        }

# Instance globale
conversation_context = ConversationContext()

