#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestionnaire de versions pour QAIA
Gère les versions des modèles et des composants
"""

# /// script
# dependencies = [
# ]
# ///

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VersionManager:
    """Gestionnaire de versions pour QAIA"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialise le gestionnaire de versions.
        
        Args:
            base_dir (Optional[Path]): Répertoire de base
        """
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.version_file = self.base_dir / "version_info.json"
        
        # Version de QAIA
        self.qaia_version = "1.0.0"
        
        # Charger les informations de version
        self.version_info = self._load_version_info()
        
    def _load_version_info(self) -> Dict[str, Any]:
        """Charge les informations de version depuis le fichier"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._create_default_version_info()
        except Exception as e:
            logger.error(f"Erreur lors du chargement des versions: {e}")
            return self._create_default_version_info()
    
    def _create_default_version_info(self) -> Dict[str, Any]:
        """Crée les informations de version par défaut"""
        return {
            "qaia_version": self.qaia_version,
            "last_updated": datetime.now().isoformat(),
            "models": {},
            "dependencies": {},
            "components": {}
        }
    
    def _save_version_info(self):
        """Sauvegarde les informations de version"""
        try:
            self.version_info["last_updated"] = datetime.now().isoformat()
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(self.version_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des versions: {e}")
    
    def get_qaia_version(self) -> str:
        """Récupère la version de QAIA"""
        return self.qaia_version
    
    def get_model_version(self, model_name: str) -> Optional[str]:
        """
        Récupère la version d'un modèle.
        
        Args:
            model_name (str): Nom du modèle
            
        Returns:
            Optional[str]: Version du modèle ou None
        """
        return self.version_info.get("models", {}).get(model_name)
    
    def set_model_version(self, model_name: str, version: str):
        """
        Définit la version d'un modèle.
        
        Args:
            model_name (str): Nom du modèle
            version (str): Version du modèle
        """
        if "models" not in self.version_info:
            self.version_info["models"] = {}
        
        self.version_info["models"][model_name] = version
        self._save_version_info()
        logger.info(f"Version du modèle {model_name} définie à {version}")
    
    def get_dependency_version(self, dependency: str) -> Optional[str]:
        """
        Récupère la version d'une dépendance.
        
        Args:
            dependency (str): Nom de la dépendance
            
        Returns:
            Optional[str]: Version de la dépendance ou None
        """
        return self.version_info.get("dependencies", {}).get(dependency)
    
    def set_dependency_version(self, dependency: str, version: str):
        """
        Définit la version d'une dépendance.
        
        Args:
            dependency (str): Nom de la dépendance
            version (str): Version de la dépendance
        """
        if "dependencies" not in self.version_info:
            self.version_info["dependencies"] = {}
        
        self.version_info["dependencies"][dependency] = version
        self._save_version_info()
        logger.info(f"Version de la dépendance {dependency} définie à {version}")
    
    def get_component_version(self, component: str) -> Optional[str]:
        """
        Récupère la version d'un composant.
        
        Args:
            component (str): Nom du composant
            
        Returns:
            Optional[str]: Version du composant ou None
        """
        return self.version_info.get("components", {}).get(component)
    
    def set_component_version(self, component: str, version: str):
        """
        Définit la version d'un composant.
        
        Args:
            component (str): Nom du composant
            version (str): Version du composant
        """
        if "components" not in self.version_info:
            self.version_info["components"] = {}
        
        self.version_info["components"][component] = version
        self._save_version_info()
        logger.info(f"Version du composant {component} définie à {version}")
    
    def get_all_versions(self) -> Dict[str, Any]:
        """Récupère toutes les informations de version"""
        return self.version_info.copy()
    
    def check_compatibility(self, component: str, required_version: str) -> bool:
        """
        Vérifie la compatibilité d'un composant.
        
        Args:
            component (str): Nom du composant
            required_version (str): Version requise
            
        Returns:
            bool: True si compatible, False sinon
        """
        try:
            current_version = self.get_component_version(component)
            if not current_version:
                return False
            
            # Comparaison simple des versions (peut être améliorée)
            return current_version >= required_version
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
            return False
    
    def update_from_requirements(self, requirements_file: str = "requirements.txt"):
        """
        Met à jour les versions depuis le fichier requirements.txt.
        
        Args:
            requirements_file (str): Chemin vers le fichier requirements
        """
        try:
            req_file = self.base_dir / requirements_file
            if not req_file.exists():
                logger.warning(f"Fichier {requirements_file} non trouvé")
                return
            
            with open(req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' in line:
                            package, version = line.split('==', 1)
                            self.set_dependency_version(package.strip(), version.strip())
                        elif '>=' in line:
                            package, version = line.split('>=', 1)
                            self.set_dependency_version(package.strip(), f">={version.strip()}")
                        else:
                            self.set_dependency_version(line, "unknown")
            
            logger.info("Versions mises à jour depuis requirements.txt")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour depuis requirements: {e}")
    
    def generate_version_report(self) -> str:
        """Génère un rapport des versions"""
        try:
            report = f"=== RAPPORT DES VERSIONS QAIA ===\n"
            report += f"Version QAIA: {self.qaia_version}\n"
            report += f"Dernière mise à jour: {self.version_info.get('last_updated', 'Inconnue')}\n\n"
            
            # Modèles
            if self.version_info.get("models"):
                report += "=== MODÈLES ===\n"
                for model, version in self.version_info["models"].items():
                    report += f"  {model}: {version}\n"
                report += "\n"
            
            # Dépendances
            if self.version_info.get("dependencies"):
                report += "=== DÉPENDANCES ===\n"
                for dep, version in self.version_info["dependencies"].items():
                    report += f"  {dep}: {version}\n"
                report += "\n"
            
            # Composants
            if self.version_info.get("components"):
                report += "=== COMPOSANTS ===\n"
                for comp, version in self.version_info["components"].items():
                    report += f"  {comp}: {version}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            return f"Erreur lors de la génération du rapport: {e}"
    
    def cleanup_old_versions(self, days_to_keep: int = 30):
        """
        Nettoie les anciennes informations de version.
        
        Args:
            days_to_keep (int): Nombre de jours à conserver
        """
        try:
            # Pour l'instant, on garde tout
            # Cette fonction peut être étendue pour gérer l'historique
            logger.info("Nettoyage des versions (fonctionnalité à implémenter)")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des versions: {e}")

# Instance globale
_version_manager = None

def get_version_manager() -> VersionManager:
    """Récupère l'instance globale du gestionnaire de versions"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager

def get_qaia_version() -> str:
    """Récupère la version de QAIA"""
    return get_version_manager().get_qaia_version()

def check_system_compatibility() -> bool:
    """Vérifie la compatibilité du système"""
    try:
        # Vérifications de base
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            logger.error(f"Python {python_version.major}.{python_version.minor} non supporté (minimum 3.8)")
            return False
        
        # Vérifier que nous sommes sur F:
        base_dir = Path(__file__).parent.parent
        if not str(base_dir).startswith("F:"):
            logger.error(f"QAIA doit être installé sur F: mais se trouve sur {base_dir}")
            return False
        
        logger.info("Compatibilité système vérifiée")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
        return False

# Initialisation automatique
if __name__ == "__main__":
    check_system_compatibility()
