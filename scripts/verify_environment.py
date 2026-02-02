#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification complète de l'environnement QAIA
Vérifie toutes les dépendances et la configuration avant lancement
"""

# /// script
# dependencies = []
# ///

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict

# Couleurs pour terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text: str):
    """Affiche un en-tête formaté"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text: str):
    """Affiche un message de succès"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    """Affiche un message d'erreur"""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    """Affiche un avertissement"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    """Affiche une information"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

def check_python_version() -> bool:
    """Vérifie la version de Python"""
    print_header("Vérification Version Python")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print_info(f"Version Python: {version_str}")
    print_info(f"Exécutable: {sys.executable}")
    
    if version.major == 3 and version.minor >= 10:
        print_success(f"Version Python compatible (>= 3.10)")
        return True
    else:
        print_error(f"Version Python incompatible (requiert >= 3.10)")
        return False

def check_virtual_env() -> bool:
    """Vérifie si un environnement virtuel est actif"""
    print_header("Vérification Environnement Virtuel")
    
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print_success(f"Environnement virtuel actif")
        print_info(f"Préfixe: {sys.prefix}")
        return True
    else:
        print_error(f"Aucun environnement virtuel actif")
        print_warning(f"Activez l'environnement avec:")
        print_warning(f"  source ~/.pyenv/versions/qaia-env/bin/activate")
        print_warning(f"ou:")
        print_warning(f"  pyenv activate qaia-env")
        return False

def check_critical_dependencies() -> Tuple[bool, List[str]]:
    """Vérifie les dépendances critiques"""
    print_header("Vérification Dépendances Critiques")
    
    critical_deps = {
        # Core
        "psutil": "Monitoring système",
        "torch": "PyTorch (CPU)",
        "transformers": "Modèles Hugging Face",
        
        # LLM & RAG
        "langchain": "Framework RAG",
        "langchain_community": "Intégrations LangChain",
        "chromadb": "Base vectorielle",
        "sentence_transformers": "Embeddings",
        "llama_cpp": "Inférence GGUF",
        
        # Audio
        "sounddevice": "Capture audio",
        "soundfile": "Traitement audio",
        "pyttsx3": "Text-to-Speech",
        
        # Interface
        "pygame": "Interface audio",
    }
    
    missing = []
    installed = []
    
    for module, description in critical_deps.items():
        try:
            __import__(module)
            print_success(f"{module:25} - {description}")
            installed.append(module)
        except ImportError:
            print_error(f"{module:25} - {description} (MANQUANT)")
            missing.append(module)
    
    print(f"\n{BLUE}Résumé:{RESET}")
    print_info(f"Installées: {len(installed)}/{len(critical_deps)}")
    if missing:
        print_error(f"Manquantes: {len(missing)}")
    
    return len(missing) == 0, missing

def check_optional_dependencies() -> Dict[str, bool]:
    """Vérifie les dépendances optionnelles"""
    print_header("Vérification Dépendances Optionnelles")
    
    optional_deps = {
        "pyaudio": "Capture audio alternative",
        "gtts": "Text-to-Speech Google",
        "opencv-python": "Traitement vidéo",
    }
    
    status = {}
    
    for module, description in optional_deps.items():
        module_name = module.replace("-", "_")
        try:
            __import__(module_name)
            print_success(f"{module:25} - {description}")
            status[module] = True
        except ImportError:
            print_warning(f"{module:25} - {description} (optionnel, non installé)")
            status[module] = False
    
    return status

def check_project_structure() -> bool:
    """Vérifie la structure du projet"""
    print_header("Vérification Structure Projet")
    
    base_dir = Path(__file__).parent.parent
    required_dirs = [
        "agents",
        "config",
        "data",
        "models",
        "logs",
        "utils",
        "tests",
    ]
    
    required_files = [
        "launcher.py",
        "qaia_core.py",
        "requirements.txt",
        "config/system_config.py",
    ]
    
    all_ok = True
    
    print_info("Dossiers requis:")
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print_success(f"  {dir_name}/")
        else:
            print_error(f"  {dir_name}/ (MANQUANT)")
            all_ok = False
    
    print_info("\nFichiers requis:")
    for file_name in required_files:
        file_path = base_dir / file_name
        if file_path.exists() and file_path.is_file():
            print_success(f"  {file_name}")
        else:
            print_error(f"  {file_name} (MANQUANT)")
            all_ok = False
    
    return all_ok

def check_models() -> bool:
    """Vérifie la présence des modèles"""
    print_header("Vérification Modèles")
    
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "models"
    
    if not models_dir.exists():
        print_error("Dossier models/ manquant")
        return False
    
    # Chercher le modèle GGUF
    gguf_files = list(models_dir.glob("*.gguf"))
    if gguf_files:
        print_success(f"Modèle GGUF trouvé: {gguf_files[0].name}")
        print_info(f"  Taille: {gguf_files[0].stat().st_size / (1024**3):.2f} GB")
    else:
        print_error("Aucun modèle GGUF trouvé")
        print_warning("Téléchargez un modèle depuis https://huggingface.co/")
        return False
    
    # Vérifier cache Hugging Face
    hf_cache = Path.home() / ".cache" / "huggingface"
    if hf_cache.exists():
        print_success(f"Cache Hugging Face présent")
    else:
        print_warning(f"Cache Hugging Face absent (normal au premier lancement)")
    
    return True

def check_vector_db() -> bool:
    """Vérifie la base vectorielle"""
    print_header("Vérification Base Vectorielle")
    
    base_dir = Path(__file__).parent.parent
    vector_db_dir = base_dir / "data" / "vector_db"
    
    if not vector_db_dir.exists():
        print_warning("Base vectorielle absente (sera créée au premier lancement)")
        return True
    
    chroma_db = vector_db_dir / "chroma.sqlite3"
    if chroma_db.exists():
        size_mb = chroma_db.stat().st_size / (1024**2)
        print_success(f"Base ChromaDB présente ({size_mb:.2f} MB)")
        return True
    else:
        print_warning("Base ChromaDB vide (sera créée au premier lancement)")
        return True

def main():
    """Fonction principale"""
    print_header("QAIA - Vérification Environnement Complet")
    print_info(f"Date: {Path(__file__).stat().st_mtime}")
    
    results = {
        "python": check_python_version(),
        "venv": check_virtual_env(),
        "deps_critical": check_critical_dependencies()[0],
        "structure": check_project_structure(),
        "models": check_models(),
        "vector_db": check_vector_db(),
    }
    
    # Dépendances optionnelles (ne bloquent pas)
    check_optional_dependencies()
    
    # Résumé final
    print_header("Résumé Final")
    
    all_ok = all(results.values())
    
    if all_ok:
        print_success("✅ Tous les contrôles sont passés avec succès!")
        print_info("\nPour lancer QAIA:")
        print_info("  python3 launcher.py")
        print_info("\nOu en mode debug:")
        print_info("  python3 launcher.py --debug")
        return 0
    else:
        print_error("❌ Certains contrôles ont échoué:")
        for check, status in results.items():
            if not status:
                print_error(f"  - {check}")
        
        print_info("\nActions recommandées:")
        if not results["venv"]:
            print_warning("1. Activez l'environnement virtuel:")
            print_warning("   source ~/.pyenv/versions/qaia-env/bin/activate")
        
        if not results["deps_critical"]:
            print_warning("2. Installez les dépendances:")
            print_warning("   pip install -r requirements.txt")
        
        if not results["models"]:
            print_warning("3. Téléchargez le modèle LLM (GGUF)")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())

