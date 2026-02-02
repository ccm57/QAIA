#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de sauvegarde complet pour QAIA
Sauvegarde QAIA entier avec toutes les dépendances sur E:\Data Kaia\QAIA
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
#   "tqdm>=4.64.0",
# ]
# ///

import os
import sys
import shutil
import zipfile
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import psutil
from tqdm import tqdm

logger = logging.getLogger(__name__)

class QAIBackupManager:
    """Gestionnaire de sauvegarde complet pour QAIA"""
    
    def __init__(self, source_dir: Optional[Path] = None, backup_dir: Optional[Path] = None):
        """
        Initialise le gestionnaire de sauvegarde.
        
        Args:
            source_dir (Optional[Path]): Répertoire source (par défaut: F:\QAIA)
            backup_dir (Optional[Path]): Répertoire de sauvegarde (par défaut: E:\Data Kaia\QAIA)
        """
        self.source_dir = source_dir or Path(__file__).parent.parent.absolute()
        self.backup_dir = backup_dir or Path("E:/Data Kaia/QAIA")
        
        # Vérifier que le répertoire source existe
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Répertoire source non trouvé: {self.source_dir}")
        
        # Créer le répertoire de sauvegarde
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration de la sauvegarde
        self.backup_config = {
            "include_patterns": [
                "*.py",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.so",
                "*.dll",
                "*.pyd",
                "*.json",
                "*.yaml",
                "*.yml",
                "*.txt",
                "*.md",
                "*.cfg",
                "*.ini",
                "*.log",
                "*.pkl",
                "*.bin",
                "*.model",
                "*.pt",
                "*.pth",
                "*.safetensors",
                "*.gguf",
                "*.onnx",
                "*.tflite",
                "*.h5",
                "*.pb",
                "*.pkl",
                "*.joblib",
                "*.npy",
                "*.npz",
                "*.wav",
                "*.mp3",
                "*.flac",
                "*.ogg",
                "*.m4a",
                "*.aac",
                "*.wma",
                "*.avi",
                "*.mp4",
                "*.mov",
                "*.mkv",
                "*.webm",
                "*.jpg",
                "*.jpeg",
                "*.png",
                "*.gif",
                "*.bmp",
                "*.tiff",
                "*.svg",
                "*.pdf",
                "*.doc",
                "*.docx",
                "*.xls",
                "*.xlsx",
                "*.ppt",
                "*.pptx",
                "*.csv",
                "*.tsv",
                "*.xml",
                "*.html",
                "*.htm",
                "*.css",
                "*.js",
                "*.sql",
                "*.db",
                "*.sqlite",
                "*.sqlite3"
            ],
            "exclude_patterns": [
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".git",
                ".gitignore",
                ".DS_Store",
                "Thumbs.db",
                "*.tmp",
                "*.temp",
                "*.swp",
                "*.swo",
                "*~",
                ".vscode",
                ".idea",
                "node_modules",
                ".pytest_cache",
                ".coverage",
                "htmlcov",
                ".tox",
                ".mypy_cache",
                ".ruff_cache",
                "*.egg-info",
                "dist",
                "build",
                ".eggs"
            ],
            "exclude_dirs": [
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "node_modules",
                ".vscode",
                ".idea",
                "htmlcov",
                ".tox",
                "dist",
                "build",
                ".eggs"
            ]
        }
        
        # Métadonnées de sauvegarde
        self.backup_metadata = {
            "timestamp": datetime.now().isoformat(),
            "source_dir": str(self.source_dir),
            "backup_dir": str(self.backup_dir),
            "python_version": sys.version,
            "platform": sys.platform,
            "total_size": 0,
            "file_count": 0,
            "backup_type": "full"
        }
    
    def get_file_size(self, file_path: Path) -> int:
        """Récupère la taille d'un fichier en octets."""
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def should_include_file(self, file_path: Path) -> bool:
        """
        Détermine si un fichier doit être inclus dans la sauvegarde.
        
        Args:
            file_path (Path): Chemin du fichier
            
        Returns:
            bool: True si le fichier doit être inclus
        """
        # Vérifier les patterns d'exclusion
        for pattern in self.backup_config["exclude_patterns"]:
            if file_path.match(pattern):
                return False
        
        # Vérifier les répertoires d'exclusion
        for part in file_path.parts:
            if part in self.backup_config["exclude_dirs"]:
                return False
        
        # Vérifier les patterns d'inclusion
        for pattern in self.backup_config["include_patterns"]:
            if file_path.match(pattern):
                return True
        
        # Inclure par défaut les fichiers sans extension
        if not file_path.suffix:
            return True
        
        return False
    
    def scan_files(self) -> List[Path]:
        """
        Scanne tous les fichiers à sauvegarder.
        
        Returns:
            List[Path]: Liste des fichiers à sauvegarder
        """
        files_to_backup = []
        
        logger.info(f"Scan des fichiers dans {self.source_dir}...")
        
        for file_path in tqdm(self.source_dir.rglob("*"), desc="Scan des fichiers"):
            if file_path.is_file() and self.should_include_file(file_path):
                files_to_backup.append(file_path)
        
        logger.info(f"Trouvé {len(files_to_backup)} fichiers à sauvegarder")
        return files_to_backup
    
    def calculate_total_size(self, files: List[Path]) -> int:
        """
        Calcule la taille totale des fichiers à sauvegarder.
        
        Args:
            files (List[Path]): Liste des fichiers
            
        Returns:
            int: Taille totale en octets
        """
        total_size = 0
        for file_path in tqdm(files, desc="Calcul de la taille"):
            total_size += self.get_file_size(file_path)
        return total_size
    
    def backup_python_environment(self) -> bool:
        """
        Sauvegarde l'environnement Python complet.
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Sauvegarde de l'environnement Python...")
            
            # Chemin de l'environnement virtuel
            venv_path = self.source_dir / ".venv"
            if not venv_path.exists():
                logger.warning("Environnement virtuel non trouvé, tentative de sauvegarde du système Python")
                return self.backup_system_python()
            
            # Copier l'environnement virtuel
            backup_venv_path = self.backup_dir / ".venv"
            if backup_venv_path.exists():
                shutil.rmtree(backup_venv_path)
            
            logger.info(f"Copie de {venv_path} vers {backup_venv_path}...")
            shutil.copytree(venv_path, backup_venv_path, 
                          ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
            
            # Sauvegarder la liste des packages installés
            packages_file = self.backup_dir / "installed_packages.txt"
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pip", "list", "--format=freeze"
                ], capture_output=True, text=True, cwd=self.source_dir)
                
                if result.returncode == 0:
                    with open(packages_file, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)
                    logger.info(f"Liste des packages sauvegardée: {packages_file}")
                else:
                    logger.warning(f"Impossible de récupérer la liste des packages: {result.stderr}")
            except Exception as e:
                logger.warning(f"Erreur lors de la sauvegarde des packages: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'environnement Python: {e}")
            return False
    
    def backup_system_python(self) -> bool:
        """
        Sauvegarde du système Python (fallback).
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Sauvegarde du système Python...")
            
            # Créer un répertoire pour les informations Python
            python_info_dir = self.backup_dir / "python_info"
            python_info_dir.mkdir(exist_ok=True)
            
            # Sauvegarder les informations Python
            python_info = {
                "executable": sys.executable,
                "version": sys.version,
                "version_info": list(sys.version_info),
                "platform": sys.platform,
                "path": sys.path
            }
            
            with open(python_info_dir / "python_info.json", 'w', encoding='utf-8') as f:
                json.dump(python_info, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder la liste des packages
            packages_file = python_info_dir / "installed_packages.txt"
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pip", "list", "--format=freeze"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    with open(packages_file, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)
                else:
                    logger.warning(f"Impossible de récupérer la liste des packages: {result.stderr}")
            except Exception as e:
                logger.warning(f"Erreur lors de la sauvegarde des packages: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du système Python: {e}")
            return False
    
    def backup_models_and_data(self) -> bool:
        """
        Sauvegarde des modèles et données.
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Sauvegarde des modèles et données...")
            
            # Répertoires importants à sauvegarder
            important_dirs = [
                "models",
                "data", 
                "logs",
                "cache",
                "config",
                "agents",
                "utils",
                "tests"
            ]
            
            for dir_name in important_dirs:
                source_path = self.source_dir / dir_name
                if source_path.exists():
                    backup_path = self.backup_dir / dir_name
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    
                    logger.info(f"Copie de {source_path} vers {backup_path}...")
                    shutil.copytree(source_path, backup_path,
                                  ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
                else:
                    logger.debug(f"Répertoire non trouvé: {source_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des modèles et données: {e}")
            return False
    
    def backup_configuration_files(self) -> bool:
        """
        Sauvegarde des fichiers de configuration.
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Sauvegarde des fichiers de configuration...")
            
            # Fichiers de configuration importants
            config_files = [
                "requirements.txt",
                "README.md",
                "qaia_core.py",
                "main.py",
                "setup.py",
                "pyproject.toml",
                "environment.yml",
                "conda.yml",
                ".env",
                ".env.local",
                "config.json",
                "settings.json"
            ]
            
            for config_file in config_files:
                source_path = self.source_dir / config_file
                if source_path.exists():
                    backup_path = self.backup_dir / config_file
                    shutil.copy2(source_path, backup_path)
                    logger.debug(f"Copié: {config_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des fichiers de configuration: {e}")
            return False
    
    def create_backup_metadata(self, files: List[Path], total_size: int) -> bool:
        """
        Crée les métadonnées de sauvegarde.
        
        Args:
            files (List[Path]): Liste des fichiers sauvegardés
            total_size (int): Taille totale
            
        Returns:
            bool: True si succès
        """
        try:
            # Mettre à jour les métadonnées
            self.backup_metadata.update({
                "file_count": len(files),
                "total_size": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "total_size_gb": total_size / (1024 * 1024 * 1024),
                "files": [str(f.relative_to(self.source_dir)) for f in files]
            })
            
            # Sauvegarder les métadonnées
            metadata_file = self.backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Métadonnées sauvegardées: {metadata_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des métadonnées: {e}")
            return False
    
    def create_restore_script(self) -> bool:
        """
        Crée un script de restauration.
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Création du script de restauration...")
            
            restore_script = self.backup_dir / "restore_qaia.py"
            
            script_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de restauration pour QAIA
Généré automatiquement le {datetime.now().isoformat()}
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def restore_qaia():
    """Restaure QAIA depuis la sauvegarde"""
    print("🔄 Restauration de QAIA...")
    
    # Chemin de destination (modifiez selon vos besoins)
    restore_path = Path("F:/QAIA_RESTORED")
    
    # Créer le répertoire de destination
    restore_path.mkdir(parents=True, exist_ok=True)
    
    # Copier tous les fichiers
    source_path = Path(__file__).parent
    for item in source_path.iterdir():
        if item.name != "restore_qaia.py":
            dest_item = restore_path / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)
    
    print(f"✅ QAIA restauré dans: {{restore_path}}")
    print("📝 N'oubliez pas de:")
    print("   1. Activer l'environnement virtuel: .venv\\Scripts\\activate")
    print("   2. Installer les dépendances: pip install -r requirements.txt")
    print("   3. Vérifier les chemins dans config/system_config.py")

if __name__ == "__main__":
    restore_qaia()
'''
            
            with open(restore_script, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logger.info(f"Script de restauration créé: {restore_script}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du script de restauration: {e}")
            return False
    
    def create_zip_backup(self) -> bool:
        """
        Crée une archive ZIP de la sauvegarde.
        
        Returns:
            bool: True si succès
        """
        try:
            logger.info("Création de l'archive ZIP...")
            
            zip_path = self.backup_dir.parent / f"QAIA_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for file_path in tqdm(self.backup_dir.rglob("*"), desc="Création ZIP"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.backup_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Archive ZIP créée: {zip_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'archive ZIP: {e}")
            return False
    
    def full_backup(self, create_zip: bool = True) -> bool:
        """
        Effectue une sauvegarde complète de QAIA.
        
        Args:
            create_zip (bool): Créer une archive ZIP
            
        Returns:
            bool: True si succès
        """
        try:
            logger.info("🚀 Début de la sauvegarde complète de QAIA...")
            logger.info(f"Source: {self.source_dir}")
            logger.info(f"Destination: {self.backup_dir}")
            
            # Vérifier l'espace disque disponible
            disk_usage = psutil.disk_usage(str(self.backup_dir.parent))
            free_space_gb = disk_usage.free / (1024**3)
            logger.info(f"Espace disque disponible: {free_space_gb:.2f} GB")
            
            if free_space_gb < 10:  # Moins de 10 GB
                logger.warning("⚠️ Espace disque faible, la sauvegarde pourrait échouer")
            
            # 1. Scanner les fichiers
            files = self.scan_files()
            if not files:
                logger.error("Aucun fichier à sauvegarder trouvé")
                return False
            
            # 2. Calculer la taille totale
            total_size = self.calculate_total_size(files)
            logger.info(f"Taille totale à sauvegarder: {total_size / (1024**3):.2f} GB")
            
            # 3. Sauvegarder l'environnement Python
            if not self.backup_python_environment():
                logger.error("Échec de la sauvegarde de l'environnement Python")
                return False
            
            # 4. Sauvegarder les modèles et données
            if not self.backup_models_and_data():
                logger.error("Échec de la sauvegarde des modèles et données")
                return False
            
            # 5. Sauvegarder les fichiers de configuration
            if not self.backup_configuration_files():
                logger.error("Échec de la sauvegarde des fichiers de configuration")
                return False
            
            # 6. Créer les métadonnées
            if not self.create_backup_metadata(files, total_size):
                logger.error("Échec de la création des métadonnées")
                return False
            
            # 7. Créer le script de restauration
            if not self.create_restore_script():
                logger.error("Échec de la création du script de restauration")
                return False
            
            # 8. Créer l'archive ZIP (optionnel)
            if create_zip:
                if not self.create_zip_backup():
                    logger.warning("Échec de la création de l'archive ZIP, mais la sauvegarde est complète")
            
            logger.info("✅ Sauvegarde complète terminée avec succès!")
            logger.info(f"📁 Sauvegarde disponible dans: {self.backup_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde complète: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_backup_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur la sauvegarde.
        
        Returns:
            Dict[str, Any]: Informations de sauvegarde
        """
        try:
            metadata_file = self.backup_dir / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"error": "Métadonnées non trouvées"}
        except Exception as e:
            return {"error": str(e)}

# Fonctions utilitaires
def create_backup(source_dir: Optional[Path] = None, backup_dir: Optional[Path] = None, create_zip: bool = True) -> bool:
    """
    Fonction utilitaire pour créer une sauvegarde.
    
    Args:
        source_dir (Optional[Path]): Répertoire source
        backup_dir (Optional[Path]): Répertoire de sauvegarde
        create_zip (bool): Créer une archive ZIP
        
    Returns:
        bool: True si succès
    """
    backup_manager = QAIBackupManager(source_dir, backup_dir)
    return backup_manager.full_backup(create_zip)

def restore_from_backup(backup_dir: Path, restore_dir: Path) -> bool:
    """
    Fonction utilitaire pour restaurer depuis une sauvegarde.
    
    Args:
        backup_dir (Path): Répertoire de sauvegarde
        restore_dir (Path): Répertoire de restauration
        
    Returns:
        bool: True si succès
    """
    try:
        if not backup_dir.exists():
            logger.error(f"Répertoire de sauvegarde non trouvé: {backup_dir}")
            return False
        
        logger.info(f"Restauration de {backup_dir} vers {restore_dir}")
        
        # Créer le répertoire de destination
        restore_dir.mkdir(parents=True, exist_ok=True)
        
        # Copier tous les fichiers
        for item in backup_dir.iterdir():
            if item.name != "restore_qaia.py":
                dest_item = restore_dir / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
        
        logger.info("✅ Restauration terminée avec succès!")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la restauration: {e}")
        return False

# Test du module
if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Créer une sauvegarde
    print("🚀 Création de la sauvegarde QAIA...")
    success = create_backup()
    
    if success:
        print("✅ Sauvegarde terminée avec succès!")
    else:
        print("❌ Échec de la sauvegarde!")
        sys.exit(1)
