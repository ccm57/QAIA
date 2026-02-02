#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Couche 2 : Gestionnaire de profils vocaux
Gère l'enrôlement, l'identification et la vérification de locuteurs.
"""

# /// script
# dependencies = [
#   "numpy>=1.22.0",
# ]
# ///

import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import numpy as np
from .embedding_extractor import VoiceEmbeddingExtractor
from config.system_config import VOICE_PROFILES_DIR

logger = logging.getLogger(__name__)


class VoiceProfileManager:
    """
    Gestionnaire de profils vocaux.
    
    Cette classe gère :
    - L'enrôlement de nouveaux locuteurs (enroll)
    - L'identification d'un locuteur parmi tous les profils (identify)
    - La vérification d'un locuteur déclaré (verify)
    """
    
    def __init__(self, profiles_dir: Optional[Path] = None, similarity_threshold: float = 0.75):
        """
        Initialise le gestionnaire de profils vocaux.
        
        Args:
            profiles_dir (Optional[Path]): Répertoire de stockage des profils (défaut: VOICE_PROFILES_DIR)
            similarity_threshold (float): Seuil de similarité pour identification/vérification (défaut: 0.75)
        """
        self.logger = logging.getLogger(f"{__name__}.VoiceProfileManager")
        self.profiles_dir = profiles_dir or VOICE_PROFILES_DIR
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = similarity_threshold
        
        # Extracteur d'empreinte (réutilise la couche 1)
        self.extractor = VoiceEmbeddingExtractor(use_gpu=False)  # GPU optionnel via flag plus tard
        
        self.logger.info(f"Gestionnaire de profils vocaux initialisé (répertoire: {self.profiles_dir})")
    
    def _compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings.
        
        Args:
            embedding1 (np.ndarray): Premier vecteur d'embedding
            embedding2 (np.ndarray): Deuxième vecteur d'embedding
            
        Returns:
            float: Score de similarité entre 0.0 et 1.0
        """
        # Normaliser les vecteurs (déjà normalisés par l'extracteur, mais on s'assure)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1_norm = embedding1 / norm1
        embedding2_norm = embedding2 / norm2
        
        # Similarité cosinus
        similarity = np.dot(embedding1_norm, embedding2_norm)
        return float(np.clip(similarity, -1.0, 1.0))
    
    def enroller_locuteur(self, audio_path: str, speaker_id: str, metadata: Optional[Dict] = None) -> bool:
        """
        Enrôle un nouveau locuteur (crée un profil vocal).
        
        Args:
            audio_path (str): Chemin vers le fichier audio d'enrôlement (3-10s recommandé)
            speaker_id (str): Identifiant unique du locuteur
            metadata (Optional[Dict]): Métadonnées optionnelles (prénom, civilité, etc.)
            
        Returns:
            bool: True si l'enrôlement a réussi, False sinon
        """
        try:
            # Extraire l'empreinte vocale
            embedding = self.extractor.extraire_empreinte(audio_path)
            if embedding is None:
                self.logger.error(f"Échec extraction empreinte pour enrôlement {speaker_id}")
                return False
            
            # Sauvegarder l'embedding
            profile_path = self.profiles_dir / f"{speaker_id}.npy"
            np.save(profile_path, embedding)
            
            # Sauvegarder les métadonnées si fournies
            if metadata:
                metadata_path = self.profiles_dir / f"{speaker_id}_metadata.json"
                import json
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Locuteur {speaker_id} enrôlé avec succès (profil: {profile_path})")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enrôlement de {speaker_id}: {e}")
            return False
    
    def identifier_locuteur(self, audio_path: str) -> Optional[Tuple[str, float]]:
        """
        Identifie un locuteur parmi tous les profils enregistrés.
        
        Args:
            audio_path (str): Chemin vers le fichier audio à identifier
            
        Returns:
            Optional[Tuple[str, float]]: (speaker_id, score_similarité) du meilleur match, ou None si aucun match au-dessus du seuil
        """
        try:
            # Extraire l'empreinte de l'audio à identifier
            embedding = self.extractor.extraire_empreinte(audio_path)
            if embedding is None:
                return None
            
            # Parcourir tous les profils
            best_match = None
            best_score = 0.0
            
            for profile_file in self.profiles_dir.glob("*.npy"):
                if profile_file.name.endswith("_metadata.json"):
                    continue
                
                speaker_id = profile_file.stem
                reference_embedding = np.load(profile_file)
                
                # Calculer la similarité
                similarity = self._compute_similarity(embedding, reference_embedding)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = speaker_id
            
            # Retourner le meilleur match si au-dessus du seuil
            if best_match and best_score >= self.similarity_threshold:
                self.logger.info(f"Locuteur identifié: {best_match} (score: {best_score:.3f})")
                return (best_match, best_score)
            else:
                self.logger.debug(f"Aucun locuteur identifié (meilleur score: {best_score:.3f}, seuil: {self.similarity_threshold})")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'identification: {e}")
            return None
    
    def verifier_locuteur(self, audio_path: str, speaker_id: str) -> Tuple[float, bool]:
        """
        Vérifie qu'un enregistrement correspond bien à un locuteur déclaré.
        
        Args:
            audio_path (str): Chemin vers le fichier audio à vérifier
            speaker_id (str): Identifiant du locuteur déclaré
            
        Returns:
            Tuple[float, bool]: (score_similarité, est_vérifié)
        """
        try:
            # Charger le profil de référence
            profile_path = self.profiles_dir / f"{speaker_id}.npy"
            if not profile_path.exists():
                self.logger.warning(f"Profil {speaker_id} non trouvé")
                return (0.0, False)
            
            reference_embedding = np.load(profile_path)
            
            # Extraire l'empreinte de l'audio à vérifier
            embedding = self.extractor.extraire_empreinte(audio_path)
            if embedding is None:
                return (0.0, False)
            
            # Calculer la similarité
            similarity = self._compute_similarity(embedding, reference_embedding)
            is_verified = similarity >= self.similarity_threshold
            
            self.logger.info(f"Vérification {speaker_id}: score={similarity:.3f}, vérifié={is_verified}")
            return (similarity, is_verified)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de {speaker_id}: {e}")
            return (0.0, False)
    
    def lister_profils(self) -> List[str]:
        """
        Liste tous les identifiants de profils enregistrés.
        
        Returns:
            List[str]: Liste des speaker_id
        """
        profiles = []
        for profile_file in self.profiles_dir.glob("*.npy"):
            if not profile_file.name.endswith("_metadata.json"):
                profiles.append(profile_file.stem)
        return profiles
    
    def charger_metadonnees(self, speaker_id: str) -> Optional[Dict]:
        """
        Charge les métadonnées d'un profil vocal.
        
        Args:
            speaker_id (str): Identifiant du locuteur
            
        Returns:
            Optional[Dict]: Métadonnées (prénom, civilité, etc.) ou None si absentes
        """
        metadata_path = self.profiles_dir / f"{speaker_id}_metadata.json"
        if not metadata_path.exists():
            return None
        
        try:
            import json
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Erreur chargement métadonnées {speaker_id}: {e}")
            return None

