#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Couche 3 : Service d'identité conversationnelle QAIA
Intègre l'identification vocale dans le flux QAIA (PTT, salutations personnalisées, mémoire).
"""

# /// script
# dependencies = []
# ///

import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from .profile_manager import VoiceProfileManager

logger = logging.getLogger(__name__)


class VoiceIdentityService:
    """
    Service d'identité vocale pour QAIA.
    
    Cette classe intègre l'identification vocale dans le flux conversationnel :
    - Identification automatique lors des tours PTT
    - Salutations personnalisées (Bonjour Claude, etc.)
    - Association speaker_id avec les conversations en BDD
    """
    
    def __init__(self, profile_manager: Optional[VoiceProfileManager] = None):
        """
        Initialise le service d'identité vocale.
        
        Args:
            profile_manager (Optional[VoiceProfileManager]): Gestionnaire de profils (créé si None)
        """
        self.logger = logging.getLogger(f"{__name__}.VoiceIdentityService")
        self.profile_manager = profile_manager or VoiceProfileManager()
        self.logger.info("Service d'identité vocale initialisé")
    
    def identifier_locuteur(self, audio_path: str) -> Optional[Dict[str, any]]:
        """
        Identifie un locuteur à partir d'un fichier audio et retourne ses informations.
        
        Args:
            audio_path (str): Chemin vers le fichier audio (ex: audio capturé via PTT)
            
        Returns:
            Optional[Dict[str, any]]: Dictionnaire avec 'speaker_id', 'score', 'prenom', 'civilite', etc., ou None si non identifié
        """
        try:
            # Identifier le locuteur
            result = self.profile_manager.identifier_locuteur(audio_path)
            if result is None:
                return None
            
            speaker_id, score = result
            
            # Charger les métadonnées
            metadata = self.profile_manager.charger_metadonnees(speaker_id)
            
            # Construire le dictionnaire de résultat
            identity = {
                'speaker_id': speaker_id,
                'score': score,
                'prenom': metadata.get('prenom') if metadata else None,
                'civilite': metadata.get('civilite') if metadata else None,
                'metadata': metadata or {},
            }
            
            self.logger.info(f"Locuteur identifié: {speaker_id} (prénom: {identity['prenom']}, score: {score:.3f})")
            return identity
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'identification de locuteur: {e}")
            return None
    
    def generer_salutation(self, identity: Optional[Dict]) -> str:
        """
        Génère une salutation personnalisée basée sur l'identité du locuteur.
        
        Args:
            identity (Optional[Dict]): Résultat de identifier_locuteur() ou None
            
        Returns:
            str: Salutation personnalisée (ex: "Bonjour Claude, ...") ou salutation générique
        """
        if identity is None:
            return "Bonjour, comment puis-je vous aider ?"
        
        prenom = identity.get('prenom')
        civilite = identity.get('civilite')
        
        if prenom:
            if civilite:
                # Ex: "Bonjour Monsieur Dupont, ..."
                return f"Bonjour {civilite} {prenom}, comment puis-je vous aider ?"
            else:
                # Ex: "Bonjour Claude, ..."
                return f"Bonjour {prenom}, comment puis-je vous aider ?"
        elif civilite:
            # Ex: "Bonjour Monsieur, ..."
            return f"Bonjour {civilite}, comment puis-je vous aider ?"
        else:
            # Fallback générique
            return "Bonjour, comment puis-je vous aider ?"
    
    def enroller_nouveau_locuteur(self, audio_path: str, speaker_id: str, prenom: Optional[str] = None, 
                                   civilite: Optional[str] = None, **kwargs) -> bool:
        """
        Enrôle un nouveau locuteur avec métadonnées.
        
        Args:
            audio_path (str): Chemin vers le fichier audio d'enrôlement
            speaker_id (str): Identifiant unique du locuteur
            prenom (Optional[str]): Prénom du locuteur
            civilite (Optional[str]): Civilité (Monsieur, Madame, etc.)
            **kwargs: Autres métadonnées optionnelles
            
        Returns:
            bool: True si l'enrôlement a réussi
        """
        metadata = {
            'prenom': prenom,
            'civilite': civilite,
            **kwargs
        }
        return self.profile_manager.enroller_locuteur(audio_path, speaker_id, metadata)

