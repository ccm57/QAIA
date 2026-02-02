#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cache d'embeddings pour QAIA
Gère la mise en cache des embeddings pour optimiser les performances
"""

# /// script
# dependencies = [
#   "numpy>=1.22.0",
# ]
# ///

import os
import pickle
import hashlib
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """Cache d'embeddings pour optimiser les performances"""
    
    def __init__(self, cache_dir: Optional[Path] = None, max_size: int = 1000):
        """
        Initialise le cache d'embeddings.
        
        Args:
            cache_dir (Optional[Path]): Répertoire de cache
            max_size (int): Taille maximale du cache
        """
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "cache" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size = max_size
        self.cache_data = {}
        self.cache_metadata = {}
        self.access_times = {}
        
        # Charger le cache existant
        self._load_cache()
        
    def _get_cache_key(self, text: str, model_name: str) -> str:
        """
        Génère une clé de cache pour un texte et un modèle.
        
        Args:
            text (str): Texte à cacher
            model_name (str): Nom du modèle
            
        Returns:
            str: Clé de cache
        """
        content = f"{model_name}:{text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """
        Récupère le chemin du fichier de cache.
        
        Args:
            cache_key (str): Clé de cache
            
        Returns:
            Path: Chemin du fichier
        """
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _get_metadata_file_path(self) -> Path:
        """
        Récupère le chemin du fichier de métadonnées.
        
        Returns:
            Path: Chemin du fichier
        """
        return self.cache_dir / "metadata.json"
    
    def _load_cache(self):
        """Charge le cache depuis le disque"""
        try:
            metadata_file = self._get_metadata_file_path()
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.cache_metadata = json.load(f)
                
                # Charger les embeddings les plus récents
                for cache_key, metadata in list(self.cache_metadata.items())[:self.max_size]:
                    cache_file = self._get_cache_file_path(cache_key)
                    if cache_file.exists():
                        try:
                            with open(cache_file, 'rb') as f:
                                self.cache_data[cache_key] = pickle.load(f)
                            self.access_times[cache_key] = metadata.get('last_access', time.time())
                        except Exception as e:
                            logger.warning(f"Erreur lors du chargement du cache {cache_key}: {e}")
                            
                logger.info(f"Cache d'embeddings chargé: {len(self.cache_data)} entrées")
            else:
                logger.info("Aucun cache d'embeddings existant trouvé")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cache: {e}")
            self.cache_data = {}
            self.cache_metadata = {}
            self.access_times = {}
    
    def _save_cache(self):
        """Sauvegarde le cache sur le disque"""
        try:
            # Sauvegarder les métadonnées
            metadata_file = self._get_metadata_file_path()
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_metadata, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder les embeddings
            for cache_key, embedding in self.cache_data.items():
                cache_file = self._get_cache_file_path(cache_key)
                with open(cache_file, 'wb') as f:
                    pickle.dump(embedding, f)
                    
            logger.debug(f"Cache d'embeddings sauvegardé: {len(self.cache_data)} entrées")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def _cleanup_cache(self):
        """Nettoie le cache en supprimant les entrées les plus anciennes"""
        if len(self.cache_data) <= self.max_size:
            return
            
        # Trier par temps d'accès
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        
        # Supprimer les entrées les plus anciennes
        items_to_remove = len(self.cache_data) - self.max_size
        for i in range(items_to_remove):
            cache_key = sorted_items[i][0]
            
            # Supprimer du cache en mémoire
            if cache_key in self.cache_data:
                del self.cache_data[cache_key]
            if cache_key in self.cache_metadata:
                del self.cache_metadata[cache_key]
            if cache_key in self.access_times:
                del self.access_times[cache_key]
            
            # Supprimer le fichier de cache
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression du fichier {cache_file}: {e}")
        
        logger.info(f"Cache nettoyé: {items_to_remove} entrées supprimées")
    
    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """
        Récupère un embedding depuis le cache.
        
        Args:
            text (str): Texte
            model_name (str): Nom du modèle
            
        Returns:
            Optional[np.ndarray]: Embedding ou None si non trouvé
        """
        try:
            cache_key = self._get_cache_key(text, model_name)
            
            if cache_key in self.cache_data:
                # Mettre à jour le temps d'accès
                self.access_times[cache_key] = time.time()
                self.cache_metadata[cache_key]['last_access'] = time.time()
                
                logger.debug(f"Embedding trouvé dans le cache: {cache_key[:8]}...")
                return self.cache_data[cache_key]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {e}")
            return None
    
    def put(self, text: str, model_name: str, embedding: np.ndarray) -> bool:
        """
        Ajoute un embedding au cache.
        
        Args:
            text (str): Texte
            model_name (str): Nom du modèle
            embedding (np.ndarray): Embedding à cacher
            
        Returns:
            bool: True si succès
        """
        try:
            cache_key = self._get_cache_key(text, model_name)
            current_time = time.time()
            
            # Ajouter au cache
            self.cache_data[cache_key] = embedding.copy()
            self.access_times[cache_key] = current_time
            self.cache_metadata[cache_key] = {
                'text': text[:100] + "..." if len(text) > 100 else text,
                'model_name': model_name,
                'created_at': current_time,
                'last_access': current_time,
                'size': embedding.nbytes
            }
            
            # Nettoyer le cache si nécessaire
            self._cleanup_cache()
            
            # Sauvegarder périodiquement
            if len(self.cache_data) % 10 == 0:
                self._save_cache()
            
            logger.debug(f"Embedding ajouté au cache: {cache_key[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout au cache: {e}")
            return False
    
    def clear(self):
        """Vide le cache"""
        try:
            # Supprimer tous les fichiers de cache
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression de {cache_file}: {e}")
            
            # Supprimer le fichier de métadonnées
            metadata_file = self._get_metadata_file_path()
            if metadata_file.exists():
                try:
                    metadata_file.unlink()
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression de {metadata_file}: {e}")
            
            # Vider la mémoire
            self.cache_data.clear()
            self.cache_metadata.clear()
            self.access_times.clear()
            
            logger.info("Cache d'embeddings vidé")
            
        except Exception as e:
            logger.error(f"Erreur lors du vidage du cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache.
        
        Returns:
            Dict[str, Any]: Statistiques
        """
        try:
            total_size = sum(metadata.get('size', 0) for metadata in self.cache_metadata.values())
            
            return {
                'entries_count': len(self.cache_data),
                'max_size': self.max_size,
                'usage_percent': (len(self.cache_data) / self.max_size) * 100,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'cache_dir': str(self.cache_dir),
                'oldest_entry': min(self.access_times.values()) if self.access_times else None,
                'newest_entry': max(self.access_times.values()) if self.access_times else None
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
    
    def cleanup_old_entries(self, max_age_days: int = 30):
        """
        Nettoie les entrées anciennes du cache.
        
        Args:
            max_age_days (int): Âge maximum en jours
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            entries_to_remove = []
            for cache_key, last_access in self.access_times.items():
                if current_time - last_access > max_age_seconds:
                    entries_to_remove.append(cache_key)
            
            for cache_key in entries_to_remove:
                # Supprimer du cache en mémoire
                if cache_key in self.cache_data:
                    del self.cache_data[cache_key]
                if cache_key in self.cache_metadata:
                    del self.cache_metadata[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
                
                # Supprimer le fichier de cache
                cache_file = self._get_cache_file_path(cache_key)
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.warning(f"Erreur lors de la suppression de {cache_file}: {e}")
            
            if entries_to_remove:
                logger.info(f"Cache nettoyé: {len(entries_to_remove)} entrées anciennes supprimées")
                self._save_cache()
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des entrées anciennes: {e}")
    
    def __del__(self):
        """Destructeur - sauvegarde le cache"""
        try:
            self._save_cache()
        except:
            pass

# Instance globale
_embedding_cache = None

def get_embedding_cache() -> EmbeddingCache:
    """Récupère l'instance globale du cache d'embeddings"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache

def cache_embedding(text: str, model_name: str, embedding: np.ndarray) -> bool:
    """
    Fonction utilitaire pour cacher un embedding.
    
    Args:
        text (str): Texte
        model_name (str): Nom du modèle
        embedding (np.ndarray): Embedding
        
    Returns:
        bool: True si succès
    """
    cache = get_embedding_cache()
    return cache.put(text, model_name, embedding)

def get_cached_embedding(text: str, model_name: str) -> Optional[np.ndarray]:
    """
    Fonction utilitaire pour récupérer un embedding du cache.
    
    Args:
        text (str): Texte
        model_name (str): Nom du modèle
        
    Returns:
        Optional[np.ndarray]: Embedding ou None
    """
    cache = get_embedding_cache()
    return cache.get(text, model_name)

def clear_embedding_cache():
    """Fonction utilitaire pour vider le cache d'embeddings"""
    cache = get_embedding_cache()
    cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """
    Fonction utilitaire pour récupérer les statistiques du cache.
    
    Returns:
        Dict[str, Any]: Statistiques
    """
    cache = get_embedding_cache()
    return cache.get_stats()

# Test du module
if __name__ == "__main__":
    # Test basique du cache
    cache = EmbeddingCache()
    
    # Test d'ajout
    test_embedding = np.random.rand(384)  # Embedding de test
    success = cache.put("Test text", "test-model", test_embedding)
    print(f"Ajout au cache: {'Succès' if success else 'Échec'}")
    
    # Test de récupération
    retrieved = cache.get("Test text", "test-model")
    print(f"Récupération du cache: {'Succès' if retrieved is not None else 'Échec'}")
    
    # Test des statistiques
    stats = cache.get_stats()
    print(f"Statistiques: {stats}")
    
    # Nettoyage
    cache.clear()
    print("Cache vidé")
