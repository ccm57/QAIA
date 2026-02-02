#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de lancement de QAIA
Gère l'initialisation et le démarrage de l'application
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
# ]
# ///

import os
import sys
import logging
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
import psutil
import subprocess
import platform
from config.system_config import INTERFACE_MODE
from utils.log_manager import setup_global_logging

# Configuration des chemins
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = Path(os.environ.get("QAIA_DATA_DIR", BASE_DIR / "data"))
MODELS_DIR = Path(os.environ.get("QAIA_MODELS_DIR", BASE_DIR / "models"))
LOGS_DIR = Path(os.environ.get("QAIA_LOGS_DIR", BASE_DIR / "logs"))
# SWAP_DIR = Path(os.environ.get("QAIA_SWAP_DIR", BASE_DIR / "swap"))  # Commenté - Swap non utilisé
VECTOR_DB_DIR = Path(os.environ.get("QAIA_VECTOR_DB_DIR", DATA_DIR / "vector_db"))

class LauncherConfig:
    """Configuration du lanceur"""
    
    def __init__(self):
        self.paths = {
            "data": DATA_DIR,
            "models": MODELS_DIR,
            "logs": LOGS_DIR,
            # "swap": SWAP_DIR,  # Commenté - Swap non utilisé
            "vector_db": VECTOR_DB_DIR
        }
        self.env_vars = {
            "QAIA_DATA_DIR": str(DATA_DIR),
            "QAIA_MODELS_DIR": str(MODELS_DIR),
            "QAIA_LOGS_DIR": str(LOGS_DIR),
            # "QAIA_SWAP_DIR": str(SWAP_DIR),  # Commenté - Swap non utilisé
            "QAIA_VECTOR_DB_DIR": str(VECTOR_DB_DIR)
        }
    
    def initialize_paths(self) -> None:
        """Initialise les chemins nécessaires"""
        try:
            for path in self.paths.values():
                path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation des chemins: {e}")
            raise
    
    def setup_environment(self) -> None:
        """Configure l'environnement"""
        try:
            for key, value in self.env_vars.items():
                os.environ[key] = value
        except Exception as e:
            logging.error(f"Erreur lors de la configuration de l'environnement: {e}")
            raise

def parse_arguments() -> Dict[str, Any]:
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Lanceur QAIA")
    parser.add_argument("--debug", action="store_true", help="Mode debug")
    parser.add_argument("--config", type=str, help="Chemin vers le fichier de configuration")
    parser.add_argument("--cpu", action="store_true", help="Forcer l'utilisation du CPU")
    parser.add_argument("--memory-limit", type=int, help="Limite de mémoire en Go")
    parser.add_argument("--safe-mode", action="store_true", help="Mode sécurisé (sans interface graphique)")
    return vars(parser.parse_args())

def check_system_resources() -> None:
    """Vérifie les ressources système"""
    try:
        # Vérifier la mémoire
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            logging.warning("Utilisation mémoire élevée: {}%".format(memory.percent))
        
        # Vérifier le CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            logging.warning("Utilisation CPU élevée: {}%".format(cpu_percent))
            
    except Exception as e:
        logging.error(f"Erreur lors de la vérification des ressources: {e}")
        raise

def main() -> int:
    """Fonction principale"""
    try:
        # Verrou d'instance unique (évite ouvertures multiples)
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            mutex_name = 'Global\\QAIA_SINGLE_INSTANCE_MUTEX'
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            ERROR_ALREADY_EXISTS = 183
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                print("Une instance de QAIA est déjà en cours d'exécution. Fermeture de cette instance.")
                return 0
        except Exception:
            # Continuer sans verrou si indisponible
            pass

        # Configurer l'encodage UTF-8
        try:
            from utils.encoding_utils import setup_encoding
            setup_encoding()
        except Exception as e:
            logging.warning(f"Erreur lors de la configuration de l'encodage: {e}")
        
        # Parser les arguments
        args = parse_arguments()
        
        # Mode sécurisé
        safe_mode = args.get("safe_mode", False)
        
        # Configurer le logging
        logging.basicConfig(
            level=logging.DEBUG if args.get("debug") else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(LOGS_DIR / "launcher.log", encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
        # Ajouter un handler racine vers system.log pour centraliser tous les logs
        try:
            system_fh = logging.FileHandler(LOGS_DIR / "system.log", encoding="utf-8")
            system_fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            root_logger = logging.getLogger()
            root_logger.addHandler(system_fh)
            root_logger.setLevel(logging.INFO)
        except Exception:
            pass
        
        # Initialiser la configuration
        config = LauncherConfig()
        config.initialize_paths()
        config.setup_environment()

        # Initialiser le gestionnaire de logs global (inclut EventBusLogHandler pour l'UI)
        try:
            setup_global_logging()
        except Exception:
            logging.warning(
                "Impossible d'initialiser LogManager, poursuite avec la configuration de logging actuelle."
            )
        
        # Vérifier les ressources
        check_system_resources()
        
        # La partie initialisation du swap a été supprimée
        
        print("\nDémarrage de QAIA ...")
        
        # Importer et lancer QAIA
        try:
            # Démarrer l'interface utilisateur rapidement, puis initialiser le noyau en arrière-plan
            print("\nInitialisation de l'interface utilisateur...\n")

            # Tentative d'interface graphique (V2 uniquement, legacy supprimée)
            if not safe_mode:
                mode = INTERFACE_MODE
                logging.info(f"Mode d'interface QAIA: {mode}")

                def _run_v2_interface() -> int:
                    """Lance l'interface V2 QAIAInterface (interface unique)."""
                    from interface.qaia_interface import QAIAInterface
                    interface = QAIAInterface(qaia_core=None)
                    print("Interface graphique V2 initialisée. Démarrage de l'application...")
                    interface.root.mainloop()
                    return 0

                # Tous les modes pointent désormais vers V2 (legacy supprimée)
                try:
                    if mode not in {"v2", "auto"}:
                        logging.warning(
                            "INTERFACE_MODE=%s n'est plus supporté (legacy supprimée), "
                            "utilisation forcée de l'interface V2.", mode
                        )
                    return _run_v2_interface()
                except Exception as e_v2:
                    if args.get("debug"):
                        logging.error(f"Erreur interface V2: {e_v2}")
                        logging.error(traceback.format_exc())
                    else:
                        logging.error(f"Erreur interface V2: {e_v2}")
                    print("Impossible de charger l'interface graphique V2, bascule en mode terminal.")
                    # Passer au mode terminal
            
            # Mode terminal (fallback sécurisé ou si toutes les interfaces ont échoué)
            print("Mode terminal activé.")
            print("Tapez 'exit', 'quit' ou 'q' pour quitter.")
            print("-------------------------------")
            try:
                from qaia_core import QAIACore
                qaia = QAIACore()
            except Exception as e_core:
                logging.error(f"Impossible d'initialiser QAIA Core en mode terminal: {e_core}")
                print(f"Erreur: impossible d'initialiser QAIA Core ({e_core})")
                return 1
            while True:
                try:
                    user_input = input(">>> ")
                    if user_input.lower() in ['exit', 'quit', 'q']:
                        break
                    response = qaia.process_message(user_input)
                    if "error" in response:
                        print(f"Erreur: {response['error']}")
                    else:
                        print(f"QAIA: {response.get('response', 'Pas de réponse')}")
                except KeyboardInterrupt:
                    print("\nArrêt demandé par l'utilisateur.")
                    break
                except Exception as e:
                    print(f"Erreur: {e}")
            
            return 0
        
        except Exception as e:
            logging.error(f"Erreur critique lors de l'initialisation de QAIA: {e}")
            logging.error(traceback.format_exc())
            
            print("\n-------------------------------")
            print(f"ERREUR CRITIQUE: {e}")
            print("Impossible d'initialiser QAIA Core.")
            print("Vérifiez les logs pour plus de détails.")
            print("-------------------------------\n")
            
            return 1
                
    except Exception as e:
        logging.error(f"Erreur lors du lancement: {e}")
        logging.error(traceback.format_exc())
        
        print("\n-------------------------------")
        print(f"ERREUR FATALE: {e}")
        print("Vérifiez les logs pour plus de détails.")
        print("-------------------------------\n")
        
        return 1

if __name__ == "__main__":
    sys.exit(main()) 