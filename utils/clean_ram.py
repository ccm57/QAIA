#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Nettoyage de la mémoire RAM pour QAIA
Gère l'optimisation et le nettoyage de la mémoire
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
# ]
# ///

import gc
import psutil
import logging
import threading
import time
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class MemoryCleaner:
    """Nettoyeur de mémoire pour QAIA"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialise le nettoyeur de mémoire.
        
        Args:
            base_dir (Optional[Path]): Répertoire de base
        """
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.cleanup_threshold = 80.0  # Seuil d'utilisation mémoire en %
        self.cleanup_interval = 30.0  # Intervalle de nettoyage en secondes
        self._cleaning = False
        self._cleanup_thread = None
        
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Récupère l'utilisation actuelle de la mémoire.
        
        Returns:
            Dict[str, float]: Métriques de mémoire
        """
        try:
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "free": memory.free
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisation mémoire: {e}")
            return {}
    
    def is_memory_pressure(self) -> bool:
        """
        Vérifie s'il y a une pression mémoire.
        
        Returns:
            bool: True si pression mémoire détectée
        """
        try:
            memory_usage = self.get_memory_usage()
            return memory_usage.get("percent", 0) > self.cleanup_threshold
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de pression mémoire: {e}")
            return False
    
    def clean_python_memory(self) -> bool:
        """
        Nettoie la mémoire Python (garbage collection).
        
        Returns:
            bool: True si succès
        """
        try:
            # Forcer le garbage collection
            collected = gc.collect()
            
            logger.debug(f"Garbage collection effectué: {collected} objets collectés")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage Python: {e}")
            return False
    
    def clean_torch_memory(self) -> bool:
        """
        Nettoie la mémoire PyTorch si disponible.
        
        Returns:
            bool: True si succès
        """
        try:
            import torch
            
            if torch.cuda.is_available():
                # Nettoyer le cache CUDA
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                
                # Forcer le garbage collection après nettoyage CUDA
                gc.collect()
                
                logger.debug("Cache CUDA nettoyé")
            
            return True
            
        except ImportError:
            logger.debug("PyTorch non disponible, nettoyage CUDA ignoré")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage PyTorch: {e}")
            return False
    
    def clean_system_memory(self) -> bool:
        """
        Nettoie la mémoire système (si possible).
        
        Returns:
            bool: True si succès
        """
        try:
            # Sur Windows, on peut essayer de forcer le garbage collection
            # et libérer la mémoire non utilisée
            gc.collect()
            
            # Attendre un peu pour que le système libère la mémoire
            time.sleep(0.1)
            
            logger.debug("Mémoire système nettoyée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage système: {e}")
            return False
    
    def full_cleanup(self) -> Dict[str, Any]:
        """
        Effectue un nettoyage complet de la mémoire.
        
        Returns:
            Dict[str, Any]: Résultats du nettoyage
        """
        try:
            # Récupérer l'utilisation avant nettoyage
            memory_before = self.get_memory_usage()
            
            # Nettoyage Python
            python_success = self.clean_python_memory()
            
            # Nettoyage PyTorch
            torch_success = self.clean_torch_memory()
            
            # Nettoyage système
            system_success = self.clean_system_memory()
            
            # Récupérer l'utilisation après nettoyage
            memory_after = self.get_memory_usage()
            
            # Calculer les économies
            memory_freed = memory_before.get("used", 0) - memory_after.get("used", 0)
            percent_freed = (memory_freed / memory_before.get("total", 1)) * 100 if memory_before.get("total", 0) > 0 else 0
            
            result = {
                "success": python_success and torch_success and system_success,
                "memory_before": memory_before,
                "memory_after": memory_after,
                "memory_freed_bytes": memory_freed,
                "memory_freed_percent": percent_freed,
                "python_cleanup": python_success,
                "torch_cleanup": torch_success,
                "system_cleanup": system_success
            }
            
            logger.info(f"Nettoyage mémoire effectué: {memory_freed / (1024**2):.1f} MB libérés ({percent_freed:.1f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage complet: {e}")
            return {"success": False, "error": str(e)}
    
    def start_auto_cleanup(self):
        """Démarre le nettoyage automatique en arrière-plan"""
        if self._cleaning:
            return
            
        self._cleaning = True
        self._cleanup_thread = threading.Thread(target=self._auto_cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Nettoyage automatique de la mémoire démarré")
    
    def stop_auto_cleanup(self):
        """Arrête le nettoyage automatique"""
        self._cleaning = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2.0)
        logger.info("Nettoyage automatique de la mémoire arrêté")
    
    def _auto_cleanup_loop(self):
        """Boucle de nettoyage automatique"""
        while self._cleaning:
            try:
                if self.is_memory_pressure():
                    logger.info("Pression mémoire détectée, nettoyage automatique...")
                    result = self.full_cleanup()
                    if result.get("success"):
                        logger.info("Nettoyage automatique réussi")
                    else:
                        logger.warning("Nettoyage automatique échoué")
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de nettoyage automatique: {e}")
                time.sleep(5.0)
    
    def optimize_memory(self) -> bool:
        """
        Optimise la mémoire pour les performances.
        
        Returns:
            bool: True si succès
        """
        try:
            # Vérifier l'utilisation actuelle
            memory_usage = self.get_memory_usage()
            current_percent = memory_usage.get("percent", 0)
            
            if current_percent > 70:  # Si plus de 70% utilisé
                logger.info(f"Mémoire à {current_percent:.1f}%, optimisation nécessaire")
                result = self.full_cleanup()
                return result.get("success", False)
            else:
                logger.debug(f"Mémoire à {current_percent:.1f}%, pas d'optimisation nécessaire")
                return True
                
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation mémoire: {e}")
            return False
    
    def get_memory_recommendations(self) -> Dict[str, Any]:
        """
        Génère des recommandations pour l'optimisation mémoire.
        
        Returns:
            Dict[str, Any]: Recommandations
        """
        try:
            memory_usage = self.get_memory_usage()
            current_percent = memory_usage.get("percent", 0)
            
            recommendations = {
                "current_usage": current_percent,
                "status": "good",
                "recommendations": [],
                "warnings": []
            }
            
            if current_percent > 90:
                recommendations["status"] = "critical"
                recommendations["warnings"].append("Utilisation mémoire critique (>90%)")
                recommendations["recommendations"].append("Redémarrer l'application")
            elif current_percent > 80:
                recommendations["status"] = "warning"
                recommendations["warnings"].append("Utilisation mémoire élevée (>80%)")
                recommendations["recommendations"].append("Effectuer un nettoyage mémoire")
            elif current_percent > 70:
                recommendations["status"] = "caution"
                recommendations["recommendations"].append("Surveiller l'utilisation mémoire")
            
            # Recommandations générales
            if current_percent > 60:
                recommendations["recommendations"].extend([
                    "Fermer les applications non essentielles",
                    "Réduire la taille des modèles chargés",
                    "Activer le nettoyage automatique"
                ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Nettoie les ressources du nettoyeur"""
        try:
            self.stop_auto_cleanup()
            logger.info("Nettoyeur de mémoire nettoyé")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du nettoyeur: {e}")

# Instance globale
_memory_cleaner = None

def get_memory_cleaner() -> MemoryCleaner:
    """Récupère l'instance globale du nettoyeur de mémoire"""
    global _memory_cleaner
    if _memory_cleaner is None:
        _memory_cleaner = MemoryCleaner()
    return _memory_cleaner

def clean_ram() -> bool:
    """
    Fonction utilitaire pour nettoyer la RAM.
    
    Returns:
        bool: True si succès
    """
    cleaner = get_memory_cleaner()
    result = cleaner.full_cleanup()
    return result.get("success", False)

def optimize_memory() -> bool:
    """
    Fonction utilitaire pour optimiser la mémoire.
    
    Returns:
        bool: True si succès
    """
    cleaner = get_memory_cleaner()
    return cleaner.optimize_memory()

def start_auto_cleanup():
    """Démarre le nettoyage automatique global"""
    cleaner = get_memory_cleaner()
    cleaner.start_auto_cleanup()

def stop_auto_cleanup():
    """Arrête le nettoyage automatique global"""
    cleaner = get_memory_cleaner()
    cleaner.stop_auto_cleanup()

# Initialisation automatique
if __name__ == "__main__":
    cleaner = get_memory_cleaner()
    result = cleaner.full_cleanup()
    print(f"Nettoyage mémoire: {'Succès' if result.get('success') else 'Échec'}")
