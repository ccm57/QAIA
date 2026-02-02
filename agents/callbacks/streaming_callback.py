#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Streaming Callback pour LLM
Émet chaque token via l'Event Bus pour affichage temps réel.

Note:
    La classe de base est importée depuis ``langchain_core.callbacks``
    (nouvelle architecture LangChain) pour éviter de dépendre du vieux
    paquet monolithique ``langchain``.
"""

# /// script
# dependencies = [
#   "langchain-core>=0.1.0",
# ]
# ///

from langchain_core.callbacks import BaseCallbackHandler
from interface.events.event_bus import event_bus
import time
import logging

logger = logging.getLogger(__name__)


class StreamingCallback(BaseCallbackHandler):
    """
    Callback Langchain pour streaming LLM.
    Émet événements 'llm.token' pour chaque token généré.
    """
    
    def __init__(self):
        """Initialise le callback streaming."""
        super().__init__()
        self._start_time = None
        self._token_count = 0
        self._token_buffer = ""  # Buffer pour détecter préfixes multi-tokens
        
        logger.debug("StreamingCallback initialisé")
    
    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        """
        Appelé au début de génération LLM.
        
        Args:
            serialized: Données sérialisées du modèle
            prompts: Liste des prompts
            **kwargs: Arguments additionnels
        """
        self._start_time = time.time()
        self._token_count = 0
        self._token_buffer = ""  # Réinitialiser le buffer
        
        # Émettre événement début génération
        event_bus.emit('llm.start', {
            'timestamp': self._start_time,
            'prompts': prompts
        })
        
        logger.debug("Génération LLM démarrée")
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """
        Appelé pour chaque nouveau token généré.
        
        Args:
            token: Token généré
            **kwargs: Arguments additionnels
        """
        # Accumuler dans le buffer pour détecter préfixes multi-tokens
        self._token_buffer += token
        
        # Vérifier si le buffer contient un préfixe indésirable
        try:
            from utils.text_processor import filter_streaming_token
            import re
            
            # Vérifier si le buffer commence par un préfixe
            buffer_clean = self._token_buffer.strip()
            
            # Patterns de préfixes à détecter (insensible à la casse)
            prefix_patterns = [
                r'^\(\d{1,2}:\d{2}\)\s*QAIA\s*:?\s*',  # "(17:30) QAIA:" ou "(17:30) QAIA"
                r'^\(\d{1,2}:\d{2}\)\s*',  # "(17:30)"
                r'^QAIA\s*:?\s*',  # "QAIA:" ou "QAIA"
            ]
            
            # Vérifier si le buffer commence par un préfixe
            is_prefix = False
            prefix_length = 0
            
            for pattern in prefix_patterns:
                match = re.match(pattern, buffer_clean, re.IGNORECASE)
                if match:
                    is_prefix = True
                    prefix_length = len(match.group(0))
                    logger.debug(f"Préfixe détecté dans buffer: '{match.group(0)}'")
                    break
            
            # Si c'est un préfixe complet, ignorer tous les tokens jusqu'à présent
            if is_prefix:
                # Vérifier si on a atteint la fin du préfixe (espace ou fin)
                if len(buffer_clean) == prefix_length or buffer_clean[prefix_length:prefix_length+1] in [' ', '\n', '\t']:
                    logger.debug(f"Préfixe complet détecté, réinitialisation buffer")
                    self._token_buffer = buffer_clean[prefix_length:].lstrip()
                    # Ne pas émettre ce token ni les précédents
                    return
            
            # Filtrer le token individuel
            filtered_token = filter_streaming_token(token)
            
            # Si le token est filtré (None), ne pas l'émettre
            if filtered_token is None:
                logger.debug(f"Token filtré et ignoré: '{token}'")
                # Réinitialiser le buffer si token filtré
                if len(self._token_buffer) <= len(token):
                    self._token_buffer = ""
                else:
                    self._token_buffer = self._token_buffer[:-len(token)]
                return
        except Exception as e:
            logger.warning(f"Erreur filtrage token: {e}, utilisation token original")
            filtered_token = token
        
        # Réinitialiser le buffer après avoir émis un token valide
        # (on garde seulement les derniers caractères pour détection préfixes)
        if len(self._token_buffer) > 20:
            self._token_buffer = self._token_buffer[-20:]
        
        self._token_count += 1
        
        # Émettre événement token (déjà filtré)
        event_bus.emit('llm.token', {
            'token': filtered_token,
            'timestamp': time.time(),
            'token_index': self._token_count
        })
    
    def on_llm_end(self, response, **kwargs) -> None:
        """
        Appelé à la fin de génération LLM.
        
        Args:
            response: Réponse complète du LLM
            **kwargs: Arguments additionnels
        """
        end_time = time.time()
        latency = end_time - self._start_time if self._start_time else 0
        
        # Récupérer config LLM pour métriques complètes
        from config.system_config import MODEL_CONFIG
        llm_config = MODEL_CONFIG.get("llm", {})
        
        # Émettre événement fin génération avec métriques complètes
        event_bus.emit('llm.complete', {
            'timestamp': end_time,
            'latency': latency,
            'tokens': self._token_count,
            'tokens_per_sec': self._token_count / latency if latency > 0 else 0,
            'temperature': llm_config.get('temperature', 0.6),
            'top_p': llm_config.get('top_p', 0.9),
            'max_tokens': llm_config.get('max_tokens', 256)
        })
        
        logger.info(
            f"Génération LLM terminée: {self._token_count} tokens "
            f"en {latency:.2f}s ({self._token_count / latency:.1f} t/s)"
        )
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """
        Appelé en cas d'erreur LLM.
        
        Args:
            error: Exception levée
            **kwargs: Arguments additionnels
        """
        # Émettre événement erreur
        event_bus.emit('llm.error', {
            'timestamp': time.time(),
            'error': str(error)
        })
        
        logger.error(f"Erreur génération LLM: {error}")

