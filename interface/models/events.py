#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Data Models pour les événements QAIA
Classes immuables pour garantir la cohérence des données
"""

# /// script
# dependencies = []
# ///

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import time


@dataclass(frozen=True)
class StreamingToken:
    """
    Token de streaming LLM.
    
    Attributes:
        text: Texte du token
        timestamp: Timestamp Unix de génération
        metadata: Métadonnées additionnelles (ex: confidence, model_name)
    """
    text: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"StreamingToken(text='{self.text}', time={self.timestamp:.2f})"


@dataclass(frozen=True)
class MetricsSnapshot:
    """
    Snapshot des métriques système.
    
    Attributes:
        cpu: Utilisation CPU en pourcentage (0-100)
        ram: RAM utilisée en GB
        gpu: Utilisation GPU en pourcentage (0-100), None si indisponible
        latency: Latence dernière génération LLM en secondes
        timestamp: Timestamp Unix de capture
        additional: Métriques additionnelles (ex: température, tokens/s)
    """
    cpu: float
    ram: float
    gpu: Optional[float]
    latency: Optional[float]
    timestamp: float = field(default_factory=time.time)
    additional: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return (
            f"MetricsSnapshot(CPU={self.cpu:.1f}%, "
            f"RAM={self.ram:.1f}GB, "
            f"latency={self.latency:.2f}s)"
        )


@dataclass(frozen=True)
class AgentState:
    """
    État d'un agent QAIA.
    
    Attributes:
        name: Nom de l'agent (ex: 'LLM', 'STT', 'TTS')
        status: Statut actuel ('ACTIF', 'EN_COURS', 'ERREUR', 'IDLE', 'STOPPED')
        last_update: Timestamp dernière mise à jour
        details: Détails additionnels (ex: message d'erreur, activité en cours)
        activity_percentage: Pourcentage d'activité (0-100) pour jauges
    """
    name: str
    status: str  # ACTIF, EN_COURS, ERREUR, IDLE, STOPPED
    last_update: float = field(default_factory=time.time)
    details: str = ""
    activity_percentage: float = 0.0
    
    def __str__(self) -> str:
        return f"AgentState({self.name}: {self.status}, {self.activity_percentage:.0f}%)"
    
    @property
    def status_emoji(self) -> str:
        """Retourne l'emoji correspondant au statut."""
        emoji_map = {
            'ACTIF': '🟢',
            'EN_COURS': '🟡',
            'ERREUR': '🔴',
            'IDLE': '⚪',
            'STOPPED': '⚫'
        }
        return emoji_map.get(self.status, '⚪')
    
    @property
    def status_color(self) -> str:
        """Retourne la couleur hex correspondant au statut."""
        color_map = {
            'ACTIF': '#4CAF50',      # Vert
            'EN_COURS': '#FFC107',   # Jaune
            'ERREUR': '#F44336',     # Rouge
            'IDLE': '#9E9E9E',       # Gris
            'STOPPED': '#424242'     # Gris foncé
        }
        return color_map.get(self.status, '#9E9E9E')


@dataclass(frozen=True)
class LogEntry:
    """
    Entrée de log.
    
    Attributes:
        level: Niveau de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        message: Message de log
        timestamp: Timestamp Unix
        source: Source du log (ex: 'llm_agent', 'interface', 'core')
        extra: Données additionnelles (ex: traceback, context)
    """
    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        from datetime import datetime
        dt = datetime.fromtimestamp(self.timestamp)
        time_str = dt.strftime('%H:%M:%S')
        return f"[{time_str}] {self.level} {self.source}: {self.message}"
    
    @property
    def level_color(self) -> str:
        """Retourne la couleur hex correspondant au niveau."""
        color_map = {
            'DEBUG': '#9E9E9E',      # Gris
            'INFO': '#2196F3',       # Bleu
            'WARNING': '#FF9800',    # Orange
            'ERROR': '#F44336',      # Rouge
            'CRITICAL': '#D32F2F'    # Rouge foncé
        }
        return color_map.get(self.level, '#9E9E9E')

