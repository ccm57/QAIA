#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Tests Automatisés - Flux Conversationnel QAIA
Tests de stabilité et robustesse du système conversationnel.
"""

# /// script
# dependencies = []
# ///

import sys
import logging
from pathlib import Path

# Ajouter projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import unittest
from typing import List, Dict

logger = logging.getLogger(__name__)

class TestConversationFlow(unittest.TestCase):
    """Tests du flux conversationnel."""
    
    @classmethod
    def setUpClass(cls):
        """Setup avant tous les tests."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logger.info("Initialisation tests conversationnels...")
        
        # Importer composants
        try:
            from agents.audio_manager import audio_manager
            from agents.vad_engine import create_vad
            from agents.context_manager import conversation_context
            from agents.intent_detector import intent_detector
            from utils.metrics_collector import metrics_collector
            from utils.health_monitor import health_monitor
            
            cls.audio_manager = audio_manager
            cls.vad_engine = create_vad(profile="normal")
            cls.context_manager = conversation_context
            cls.intent_detector = intent_detector
            cls.metrics = metrics_collector
            cls.health = health_monitor
            
            logger.info("✅ Composants chargés")
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement composants: {e}")
            raise
    
    def test_01_audio_manager_initialization(self):
        """Test 1: Initialisation AudioManager."""
        logger.info("Test 1: AudioManager initialization")
        
        # Vérifier initialisation
        self.assertIsNotNone(self.audio_manager)
        self.assertTrue(self.audio_manager._initialized)
        
        # Test microphone
        test_result = self.audio_manager.test_microphone()
        self.assertEqual(test_result.get("status"), "ok")
        
        logger.info("✅ Test 1 réussi")
    
    def test_02_vad_engine_functionality(self):
        """Test 2: Fonctionnalité VAD Engine."""
        logger.info("Test 2: VAD Engine functionality")
        
        import numpy as np
        
        # Créer signal test (silence)
        silence = np.zeros(16000, dtype=np.float32)  # 1s silence
        
        # Traiter
        audio_speech, duration = self.vad_engine.process_audio(silence, max_duration=1.0)
        
        # Vérifier (devrait détecter aucune parole)
        self.assertIsNone(audio_speech)
        
        logger.info("✅ Test 2 réussi")
    
    def test_03_intent_detection(self):
        """Test 3: Détection d'intentions."""
        logger.info("Test 3: Intent detection")
        
        # Test différents types
        test_cases = [
            ("Bonjour", "greeting"),
            ("Comment vas-tu ?", "question"),
            ("Merci au revoir", "end_conversation"),
            ("Oui", "confirmation")
        ]
        
        for text, expected_intent in test_cases:
            result = self.intent_detector.detect(text)
            self.assertEqual(result.intent.value, expected_intent)
            logger.info(f"  '{text}' → {result.intent.value} ✅")
        
        logger.info("✅ Test 3 réussi")
    
    def test_04_context_manager(self):
        """Test 4: Gestion contexte conversationnel."""
        logger.info("Test 4: Context Manager")
        
        # Réinitialiser
        self.context_manager.clear()
        
        # Ajouter tours
        self.context_manager.add_turn("user", "Bonjour, comment vas-tu ?")
        self.context_manager.add_turn("assistant", "Je vais bien, merci !")
        self.context_manager.add_turn("user", "Parle-moi de Python.")
        
        # Vérifier
        self.assertEqual(self.context_manager.turn_count, 3)
        self.assertEqual(len(self.context_manager.recent_history), 3)
        
        # Contexte LLM
        context = self.context_manager.get_context_for_llm(max_turns=2)
        self.assertEqual(len(context), 2)
        
        logger.info("✅ Test 4 réussi")
    
    def test_05_metrics_collection(self):
        """Test 5: Collecte métriques."""
        logger.info("Test 5: Metrics collection")
        
        # Enregistrer métriques test
        self.metrics.record_latency("stt", "transcribe", 1.5)
        self.metrics.record_latency("llm", "generate", 2.3)
        self.metrics.increment_counter("stt.success")
        self.metrics.increment_counter("llm.success")
        
        # Vérifier stats
        stats = self.metrics.get_stats("stt.transcribe.latency")
        self.assertIn("stt.transcribe.latency", stats)
        
        counters = self.metrics.get_counters()
        self.assertGreater(counters.get("stt.success", 0), 0)
        
        logger.info("✅ Test 5 réussi")
    
    def test_06_health_monitor(self):
        """Test 6: Health Monitor."""
        logger.info("Test 6: Health Monitor")
        
        # Enregistrer composant test
        def mock_health_check():
            return True
        
        self.health.register_component("test_component", mock_health_check)
        
        # Vérifier enregistrement
        status = self.health.get_component_health("test_component")
        self.assertIsNotNone(status)
        self.assertEqual(status.component, "test_component")
        
        logger.info("✅ Test 6 réussi")
    
    def test_07_audio_recording_stability(self):
        """Test 7: Stabilité enregistrement audio (3 enregistrements consécutifs)."""
        logger.info("Test 7: Audio recording stability")
        
        num_recordings = 3
        successful_recordings = 0
        
        for i in range(num_recordings):
            logger.info(f"  Enregistrement {i+1}/{num_recordings}...")
            
            try:
                audio_data = self.audio_manager.record(duration=1.0)  # 1s test rapide
                
                if audio_data is not None:
                    successful_recordings += 1
                    logger.info(f"  ✅ Enregistrement {i+1} réussi")
                else:
                    logger.warning(f"  ❌ Enregistrement {i+1} échoué")
                
                # Pause entre enregistrements
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ Exception enregistrement {i+1}: {e}")
        
        # Au moins 2/3 doivent réussir
        success_rate = successful_recordings / num_recordings
        self.assertGreaterEqual(success_rate, 0.66, f"Taux succès trop faible: {success_rate:.0%}")
        
        logger.info(f"✅ Test 7 réussi ({successful_recordings}/{num_recordings} enregistrements)")
    
    def test_08_conversation_context_persistence(self):
        """Test 8: Persistance contexte sur 20 tours."""
        logger.info("Test 8: Context persistence (20 tours)")
        
        self.context_manager.clear()
        
        # Simuler 20 tours
        for i in range(20):
            self.context_manager.add_turn("user", f"Question numéro {i+1}")
            self.context_manager.add_turn("assistant", f"Réponse numéro {i+1}")
        
        # Vérifier
        self.assertEqual(self.context_manager.turn_count, 40)
        
        # Historique récent devrait être limité
        self.assertLessEqual(len(self.context_manager.recent_history), self.context_manager.max_recent_turns)
        
        # Résumé devrait exister
        if self.context_manager.turn_count > self.context_manager.max_summary_turns:
            self.assertIsNotNone(self.context_manager.summary)
        
        logger.info("✅ Test 8 réussi")
    
    @classmethod
    def tearDownClass(cls):
        """Cleanup après tous les tests."""
        logger.info("Nettoyage après tests...")
        
        try:
            cls.context_manager.clear()
            cls.metrics.clear()
            cls.audio_manager.cleanup()
            logger.info("✅ Cleanup terminé")
        except Exception as e:
            logger.error(f"Erreur cleanup: {e}")

def run_tests():
    """Lance les tests."""
    print("=" * 70)
    print("QAIA - Suite de Tests Conversationnels")
    print("=" * 70)
    print()
    
    # Créer suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestConversationFlow)
    
    # Lancer tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Résumé
    print()
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

