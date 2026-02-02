#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Tests pour l'interface streaming de QAIA
Tests basiques de charge et fonctionnalité
"""

# /// script
# dependencies = []
# ///

import unittest
import time
from interface.events.event_bus import event_bus, EventBus
from interface.models.events import StreamingToken, MetricsSnapshot, AgentState, LogEntry


class TestEventBus(unittest.TestCase):
    """Tests pour l'Event Bus."""
    
    def setUp(self):
        """Setup avant chaque test."""
        self.test_bus = EventBus()
        self.test_bus.start()
        self.received_events = []
    
    def tearDown(self):
        """Cleanup après chaque test."""
        self.test_bus.stop()
    
    def test_emit_and_subscribe(self):
        """Test émission et réception d'événement."""
        def callback(data):
            self.received_events.append(data)
        
        self.test_bus.subscribe('test.event', callback)
        self.test_bus.emit('test.event', {'value': 42})
        
        # Attendre traitement
        time.sleep(0.2)
        
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0]['value'], 42)
    
    def test_multiple_subscribers(self):
        """Test plusieurs abonnés au même événement."""
        counter = []
        
        def callback1(data):
            counter.append(1)
        
        def callback2(data):
            counter.append(2)
        
        self.test_bus.subscribe('test.multi', callback1)
        self.test_bus.subscribe('test.multi', callback2)
        self.test_bus.emit('test.multi', {})
        
        time.sleep(0.2)
        
        self.assertEqual(len(counter), 2)
    
    def test_unsubscribe(self):
        """Test désabonnement."""
        def callback(data):
            self.received_events.append(data)
        
        self.test_bus.subscribe('test.unsub', callback)
        self.test_bus.emit('test.unsub', {'first': True})
        
        time.sleep(0.2)
        
        self.test_bus.unsubscribe('test.unsub', callback)
        self.test_bus.emit('test.unsub', {'second': True})
        
        time.sleep(0.2)
        
        # Seul le premier événement devrait être reçu
        self.assertEqual(len(self.received_events), 1)
        self.assertTrue(self.received_events[0]['first'])


class TestDataModels(unittest.TestCase):
    """Tests pour les modèles de données."""
    
    def test_streaming_token(self):
        """Test modèle StreamingToken."""
        token = StreamingToken(text="test", metadata={'index': 1})
        
        self.assertEqual(token.text, "test")
        self.assertEqual(token.metadata['index'], 1)
        self.assertIsInstance(token.timestamp, float)
    
    def test_metrics_snapshot(self):
        """Test modèle MetricsSnapshot."""
        metrics = MetricsSnapshot(
            cpu=45.5,
            ram=10.2,
            gpu=None,
            latency=2.3
        )
        
        self.assertEqual(metrics.cpu, 45.5)
        self.assertEqual(metrics.ram, 10.2)
        self.assertIsNone(metrics.gpu)
        self.assertEqual(metrics.latency, 2.3)
    
    def test_agent_state(self):
        """Test modèle AgentState."""
        state = AgentState(
            name="LLM",
            status="ACTIF",
            activity_percentage=75.0
        )
        
        self.assertEqual(state.name, "LLM")
        self.assertEqual(state.status, "ACTIF")
        self.assertEqual(state.activity_percentage, 75.0)
        self.assertEqual(state.status_emoji, '🟢')
        self.assertEqual(state.status_color, '#4CAF50')
    
    def test_log_entry(self):
        """Test modèle LogEntry."""
        log = LogEntry(
            level="ERROR",
            message="Test error",
            source="test_module"
        )
        
        self.assertEqual(log.level, "ERROR")
        self.assertEqual(log.message, "Test error")
        self.assertEqual(log.source, "test_module")
        self.assertEqual(log.level_color, '#F44336')


class TestStreamingPerformance(unittest.TestCase):
    """Tests de performance pour le streaming."""
    
    def test_1000_tokens_streaming(self):
        """Test streaming de 1000 tokens."""
        test_bus = EventBus()
        test_bus.start()
        
        received_count = []
        
        def callback(data):
            received_count.append(1)
        
        test_bus.subscribe('llm.token', callback)
        
        start_time = time.time()
        
        # Émettre 1000 tokens
        for i in range(1000):
            test_bus.emit('llm.token', {'token': f'token_{i}'})
        
        # Attendre traitement
        time.sleep(1.0)
        
        elapsed = time.time() - start_time
        test_bus.stop()
        
        # Vérifier que tous les tokens ont été reçus
        self.assertEqual(len(received_count), 1000)
        
        # Performance: doit traiter 1000 tokens en moins de 2 secondes
        self.assertLess(elapsed, 2.0)
        
        print(f"\n✅ Test streaming 1000 tokens: {elapsed:.2f}s ({len(received_count)/elapsed:.0f} tokens/s)")


def run_tests():
    """Lance tous les tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tests
    suite.addTests(loader.loadTestsFromTestCase(TestEventBus))
    suite.addTests(loader.loadTestsFromTestCase(TestDataModels))
    suite.addTests(loader.loadTestsFromTestCase(TestStreamingPerformance))
    
    # Lancer
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)

