#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestionnaire de logs pour QAIA
Centralise la gestion des logs et du monitoring
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0"
# ]
# ///

import os
import sys
import logging
import traceback
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import psutil

class LogManager:
    """Gestionnaire centralisé des logs pour QAIA"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialise le gestionnaire de logs.
        
        Args:
            base_dir (Optional[Path]): Répertoire de base pour les logs
        """
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Configuration des logs
        self._setup_logging()
        
        # Logger principal
        self.logger = logging.getLogger("QAIA")
        
    def _setup_logging(self):
        """Configure le système de logging"""
        try:
            # Configuration de base
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(
                        self.logs_dir / "qaia.log", 
                        encoding='utf-8'
                    ),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            
            # Configuration spécifique pour QAIA
            qaia_logger = logging.getLogger("QAIA")
            qaia_logger.setLevel(logging.INFO)
            
            # Handler pour les erreurs critiques
            error_handler = logging.FileHandler(
                self.logs_dir / "error.log",
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            qaia_logger.addHandler(error_handler)
            
            # Handler pour les performances
            perf_handler = logging.FileHandler(
                self.logs_dir / "performance.log",
                encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(message)s')
            )
            
            perf_logger = logging.getLogger("PERFORMANCE")
            perf_logger.addHandler(perf_handler)
            perf_logger.setLevel(logging.INFO)

            # Handler EventBus pour l'interface (logs temps réel)
            try:
                from interface.events.event_bus import event_bus  # Import retardé pour éviter les cycles

                class EventBusLogHandler(logging.Handler):
                    """Handler qui relaie les logs vers l'Event Bus UI."""

                    def emit(self, record: logging.LogRecord) -> None:
                        try:
                            event_bus.emit(
                                "log.message",
                                {
                                    "level": record.levelname,
                                    "message": self.format(record),
                                    "source": record.name,
                                    "timestamp": record.created,
                                },
                            )
                        except Exception:
                            # Ne jamais casser le logging si l'UI n'est pas disponible
                            pass

                ui_handler = EventBusLogHandler()
                ui_handler.setLevel(logging.INFO)
                ui_handler.setFormatter(
                    logging.Formatter("%(message)s")
                )
                qaia_logger.addHandler(ui_handler)
                
                # Ajouter le handler aux loggers des agents et du core
                # pour que tous les logs soient visibles dans l'interface
                important_loggers = [
                    'QAIA',
                    'agents.llm_agent',
                    'agents.wav2vec_agent',
                    'agents.speech_agent',
                    'agents.rag_agent',
                    'agents.vision_agent',
                    'qaia_core',
                    'interface.qaia_interface',
                ]
                
                for logger_name in important_loggers:
                    logger_obj = logging.getLogger(logger_name)
                    # Vérifier si le handler n'est pas déjà présent
                    if not any(isinstance(h, EventBusLogHandler) for h in logger_obj.handlers):
                        logger_obj.addHandler(ui_handler)
                        logger_obj.setLevel(logging.INFO)
            except Exception:
                # Si l'interface n'est pas disponible, on se contente des fichiers
                pass

        except Exception as e:
            print(f"Erreur lors de la configuration du logging: {e}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Récupère un logger pour un module spécifique.
        
        Args:
            name (str): Nom du module
            
        Returns:
            logging.Logger: Logger configuré
        """
        return logging.getLogger(f"QAIA.{name}")
    
    def log_system_info(self):
        """Enregistre les informations système"""
        try:
            info = {
                "timestamp": datetime.now().isoformat(),
                "platform": sys.platform,
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage(self.base_dir).percent
            }
            
            self.logger.info(f"Informations système: {info}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement des infos système: {e}")
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """
        Enregistre une métrique de performance.
        
        Args:
            operation (str): Nom de l'opération
            duration (float): Durée en secondes
            **kwargs: Métriques supplémentaires
        """
        try:
            perf_logger = logging.getLogger("PERFORMANCE")
            metrics = {
                "operation": operation,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            
            perf_logger.info(f"PERF: {metrics}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement de performance: {e}")
    
    def log_error(self, error: Exception, context: str = ""):
        """
        Enregistre une erreur avec contexte.
        
        Args:
            error (Exception): Exception à enregistrer
            context (str): Contexte de l'erreur
        """
        try:
            error_info = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "traceback": traceback.format_exc()
            }
            
            self.logger.error(f"ERREUR: {error_info}")
            
        except Exception as e:
            print(f"Erreur lors de l'enregistrement d'erreur: {e}")
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Nettoie les anciens logs.
        
        Args:
            days_to_keep (int): Nombre de jours à conserver
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in self.logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.logger.info(f"Ancien log supprimé: {log_file.name}")
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage des logs: {e}")

    def archive_performance_logs(self, days_to_keep: int = 30) -> int:
        """
        Archive les logs de performance JSON anciens.

        Args:
            days_to_keep (int): Nombre de jours à conserver

        Returns:
            int: Nombre de fichiers déplacés
        """
        try:
            source_dir = self.logs_dir / "performance"
            archive_dir = self.logs_dir / "archive" / "performance"
            if not source_dir.exists():
                return 0

            archive_dir.mkdir(parents=True, exist_ok=True)
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            moved = 0

            for perf_file in source_dir.glob("*.json"):
                if perf_file.stat().st_mtime < cutoff_date.timestamp():
                    target = archive_dir / perf_file.name
                    if target.exists():
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        target = archive_dir / f"{perf_file.stem}_{stamp}{perf_file.suffix}"
                    shutil.move(str(perf_file), str(target))
                    moved += 1

            if moved > 0:
                self.logger.info(f"Archives performance: {moved} fichier(s) déplacé(s)")

            return moved

        except Exception as e:
            self.logger.error(f"Erreur lors de l'archivage des logs performance: {e}")
            return 0
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques des logs.
        
        Returns:
            Dict[str, Any]: Statistiques des logs
        """
        try:
            stats = {
                "total_logs": 0,
                "error_logs": 0,
                "warning_logs": 0,
                "info_logs": 0,
                "log_files": []
            }
            
            for log_file in self.logs_dir.glob("*.log"):
                file_stats = {
                    "name": log_file.name,
                    "size": log_file.stat().st_size,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
                stats["log_files"].append(file_stats)
                stats["total_logs"] += 1
                
                # Compter les types de logs (approximation)
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        stats["error_logs"] += content.count("ERROR")
                        stats["warning_logs"] += content.count("WARNING")
                        stats["info_logs"] += content.count("INFO")
                except:
                    pass
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {}
    
    def shutdown(self):
        """Arrête le gestionnaire de logs"""
        try:
            # Fermer tous les handlers
            for handler in logging.getLogger().handlers[:]:
                handler.close()
                logging.getLogger().removeHandler(handler)
                
            self.logger.info("Gestionnaire de logs arrêté")
            
        except Exception as e:
            print(f"Erreur lors de l'arrêt du gestionnaire de logs: {e}")

# Instance globale
_log_manager = None

def get_log_manager() -> LogManager:
    """Récupère l'instance globale du gestionnaire de logs"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager

def setup_global_logging():
    """Configure le logging global pour QAIA"""
    try:
        log_manager = get_log_manager()
        log_manager.log_system_info()
        try:
            days_to_keep = int(os.environ.get("QAIA_LOG_ARCHIVE_DAYS", "30"))
        except Exception:
            days_to_keep = 30
        log_manager.archive_performance_logs(days_to_keep=days_to_keep)
        return True
    except Exception as e:
        print(f"Erreur lors de la configuration du logging global: {e}")
        return False

# Initialisation automatique
if __name__ == "__main__":
    setup_global_logging()
