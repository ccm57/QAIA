#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Collecteur de Métriques pour QAIA
Collecte latences, qualité audio, utilisation ressources.
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
#   "torch>=2.0.0",
# ]
# ///

import logging
import time
import psutil
import torch
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Metric:
    """Métrique individuelle."""
    name: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire."""
        return asdict(self)

class MetricsCollector:
    """
    Collecteur de métriques système.
    
    Collecte:
    - Latences (STT, LLM, TTS, totale)
    - Qualité audio (RMS, SNR, clipping%)
    - Taux succès/échec par composant
    - Utilisation ressources (CPU, RAM, GPU)
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialise le collecteur.
        
        Args:
            max_history: Nombre max de métriques en historique
        """
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        
        # Historique métriques
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.Lock()
        
        # Compteurs
        self._counters = defaultdict(int)
        
        # Timestamps
        self._operation_starts = {}
        
        self.logger.info("MetricsCollector initialisé")
    
    def record_latency(
        self,
        component: str,
        operation: str,
        latency: float
    ):
        """
        Enregistre une latence.
        
        Args:
            component: Composant (ex: "stt", "llm", "tts")
            operation: Opération (ex: "transcribe", "generate")
            latency: Latence en secondes
        """
        metric_name = f"{component}.{operation}.latency"
        
        metric = Metric(
            name=metric_name,
            value=latency,
            unit="seconds"
        )
        
        with self._lock:
            self._metrics[metric_name].append(metric)
        
        self.logger.debug(f"Latence enregistrée: {metric_name}={latency:.3f}s")
    
    def start_operation(self, operation_id: str):
        """
        Démarre le chrono pour une opération.
        
        Args:
            operation_id: ID unique de l'opération
        """
        self._operation_starts[operation_id] = time.time()
    
    def end_operation(
        self,
        operation_id: str,
        component: str,
        operation: str
    ) -> float:
        """
        Termine le chrono et enregistre la latence.
        
        Args:
            operation_id: ID de l'opération
            component: Composant
            operation: Type d'opération
            
        Returns:
            Latence mesurée (secondes)
        """
        if operation_id not in self._operation_starts:
            self.logger.warning(f"Opération {operation_id} non démarrée")
            return 0.0
        
        latency = time.time() - self._operation_starts[operation_id]
        del self._operation_starts[operation_id]
        
        self.record_latency(component, operation, latency)
        return latency
    
    def record_audio_quality(
        self,
        rms: float,
        snr: Optional[float] = None,
        clipping_percent: float = 0.0
    ):
        """
        Enregistre métriques qualité audio.
        
        Args:
            rms: RMS du signal
            snr: Signal-to-Noise Ratio (optionnel)
            clipping_percent: Pourcentage de clipping
        """
        metrics = [
            Metric("audio.rms", rms, "amplitude"),
            Metric("audio.clipping_percent", clipping_percent, "percent")
        ]
        
        if snr is not None:
            metrics.append(Metric("audio.snr", snr, "dB"))
        
        with self._lock:
            for metric in metrics:
                self._metrics[metric.name].append(metric)
    
    def increment_counter(self, counter_name: str, increment: int = 1):
        """
        Incrémente un compteur.
        
        Args:
            counter_name: Nom du compteur (ex: "stt.success", "llm.failure")
            increment: Valeur d'incrémentation
        """
        with self._lock:
            self._counters[counter_name] += increment
    
    def record_resource_usage(self):
        """Enregistre utilisation ressources système."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.record_metric("system.cpu_percent", cpu_percent, "percent")
        
        # RAM
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_used_gb = ram.used / (1024**3)
        self.record_metric("system.ram_percent", ram_percent, "percent")
        self.record_metric("system.ram_used_gb", ram_used_gb, "GB")
        
        # GPU (si disponible)
        if torch.cuda.is_available():
            try:
                vram_allocated = torch.cuda.memory_allocated(0) / (1024**3)
                vram_reserved = torch.cuda.memory_reserved(0) / (1024**3)
                self.record_metric("system.vram_allocated_gb", vram_allocated, "GB")
                self.record_metric("system.vram_reserved_gb", vram_reserved, "GB")
            except Exception as e:
                self.logger.warning(f"Erreur lecture VRAM: {e}")
    
    def record_metric(self, name: str, value: float, unit: str):
        """
        Enregistre une métrique générique.
        
        Args:
            name: Nom métrique
            value: Valeur
            unit: Unité
        """
        metric = Metric(name=name, value=value, unit=unit)
        
        with self._lock:
            self._metrics[name].append(metric)
    
    def get_stats(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Retourne statistiques métriques.
        
        Args:
            metric_name: Nom métrique spécifique (None = toutes)
            
        Returns:
            Statistiques (min, max, avg, count)
        """
        with self._lock:
            if metric_name:
                metrics_to_analyze = {metric_name: self._metrics.get(metric_name, deque())}
            else:
                metrics_to_analyze = dict(self._metrics)
        
        stats = {}
        
        for name, metrics in metrics_to_analyze.items():
            if not metrics:
                continue
            
            values = [m.value for m in metrics]
            stats[name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "last": values[-1],
                "unit": metrics[-1].unit
            }
        
        return stats
    
    def get_counters(self) -> Dict[str, int]:
        """Retourne les compteurs."""
        with self._lock:
            return dict(self._counters)
    
    def get_success_rate(self, component: str) -> float:
        """
        Calcule taux de succès d'un composant.
        
        Args:
            component: Nom du composant
            
        Returns:
            Taux succès (0.0-1.0)
        """
        with self._lock:
            success = self._counters.get(f"{component}.success", 0)
            failure = self._counters.get(f"{component}.failure", 0)
        
        total = success + failure
        return success / total if total > 0 else 0.0
    
    def export_metrics(self, filepath: Path):
        """
        Exporte métriques en JSON.
        
        Args:
            filepath: Chemin fichier de sortie
        """
        try:
            with self._lock:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        name: [m.to_dict() for m in metrics]
                        for name, metrics in self._metrics.items()
                    },
                    "counters": dict(self._counters),
                    "stats": self.get_stats()
                }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"✅ Métriques exportées: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Erreur export métriques: {e}")
    
    def clear(self):
        """Réinitialise toutes les métriques."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._operation_starts.clear()
        
        self.logger.info("Métriques réinitialisées")
    
    def start_monitoring(self, interval: float = 1.0):
        """
        Démarre un thread de monitoring continu des métriques système.
        Émet des événements 'metrics.update' via l'Event Bus.
        
        Args:
            interval: Intervalle entre collectes (secondes)
        """
        from interface.events.event_bus import event_bus
        
        if hasattr(self, '_monitoring_thread') and self._monitoring_thread.is_alive():
            self.logger.warning("Thread monitoring déjà actif")
            return
        
        self._monitoring_active = True
        
        def monitoring_loop():
            """Boucle de monitoring qui tourne dans un thread séparé."""
            self.logger.info(f"Thread monitoring démarré (interval={interval}s)")
            
            while self._monitoring_active:
                try:
                    # Collecter métriques système
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    ram = psutil.virtual_memory()
                    ram_used_gb = ram.used / (1024**3)
                    
                    # GPU (si disponible)
                    gpu_percent = None
                    if torch.cuda.is_available():
                        try:
                            # Utilisation GPU (approximation via mémoire)
                            vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                            vram_allocated = torch.cuda.memory_allocated(0) / (1024**3)
                            gpu_percent = (vram_allocated / vram_total) * 100 if vram_total > 0 else 0
                        except Exception as e:
                            self.logger.warning(f"Erreur lecture GPU: {e}")
                    
                    # Température CPU (si disponible)
                    temperature = None
                    try:
                        temps = psutil.sensors_temperatures()
                        if 'coretemp' in temps:
                            # Moyenne des températures des cores
                            core_temps = [t.current for t in temps['coretemp']]
                            temperature = sum(core_temps) / len(core_temps) if core_temps else None
                    except (AttributeError, KeyError):
                        pass  # sensors_temperatures pas disponible sur tous les systèmes
                    
                    # Enregistrer dans historique
                    self.record_metric("system.cpu_percent", cpu_percent, "percent")
                    self.record_metric("system.ram_used_gb", ram_used_gb, "GB")
                    
                    if gpu_percent is not None:
                        self.record_metric("system.gpu_percent", gpu_percent, "percent")
                    
                    if temperature is not None:
                        self.record_metric("system.temperature", temperature, "celsius")
                    
                    # Préparer données pour Event Bus
                    metrics_data = {
                        'cpu': cpu_percent,
                        'ram': ram_used_gb,
                        'gpu': gpu_percent,
                        'timestamp': time.time(),
                        'additional': {}
                    }
                    
                    if temperature is not None:
                        metrics_data['additional']['temperature'] = temperature
                    
                    # Émettre via Event Bus
                    event_bus.emit('metrics.update', metrics_data)
                    
                    # Attendre l'intervalle
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Erreur monitoring loop: {e}")
                    time.sleep(interval)  # Continue malgré l'erreur
            
            self.logger.info("Thread monitoring arrêté")
        
        # Démarrer thread
        self._monitoring_thread = threading.Thread(
            target=monitoring_loop,
            name="MetricsMonitoring",
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info("✅ Monitoring système démarré")
    
    def stop_monitoring(self):
        """Arrête le thread de monitoring."""
        if hasattr(self, '_monitoring_active'):
            self._monitoring_active = False
            
            if hasattr(self, '_monitoring_thread'):
                self._monitoring_thread.join(timeout=2.0)
            
            self.logger.info("Monitoring système arrêté")

# Instance globale
metrics_collector = MetricsCollector()

