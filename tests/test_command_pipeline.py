#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Tests du pipeline commandes système : détection, sécurité, exécution.
"""

# /// script
# dependencies = []
# ///

import unittest

try:
    from utils.command_guard import evaluate_command, CommandVerdict
except ImportError:
    evaluate_command = None
    CommandVerdict = None


class TestIntentDetectorCommandParsing(unittest.TestCase):
    """Tests de parse_command et IntentResult pour COMMAND."""

    @classmethod
    def setUpClass(cls):
        try:
            from agents.intent_detector import IntentDetector, Intent
            cls.IntentDetector = IntentDetector
            cls.Intent = Intent
            cls.detector = IntentDetector()
        except ImportError as e:
            raise unittest.SkipTest(f"IntentDetector non disponible: {e}")

    def test_detect_command_arrete_enregistrement(self):
        """Détection phrase de commande -> COMMAND avec verb/target (phrase sans ambiguïté avec END_CONVERSATION)."""
        result = self.detector.detect("ouvre le micro")
        self.assertEqual(result.intent, self.Intent.COMMAND)
        self.assertIsNotNone(result.command_verb)
        self.assertIsNotNone(result.command_target)
        self.assertIn("micro", (result.command_target or ""))

    def test_detect_command_lance_navigateur(self):
        """Détection 'lance le navigateur' -> COMMAND."""
        result = self.detector.detect("lance le navigateur")
        self.assertEqual(result.intent, self.Intent.COMMAND)
        self.assertIsNotNone(result.command_verb)
        self.assertIsNotNone(result.command_target)

    def test_parse_command_returns_tuple(self):
        """parse_command retourne (verbe, cible, sous-type)."""
        v, t, s = self.detector.parse_command("arrête le micro")
        self.assertIsInstance(v, (type(None), str))
        self.assertIsInstance(t, (type(None), str))
        self.assertIsInstance(s, (type(None), str))

    def test_detect_greeting_not_command(self):
        """Salutation ne doit pas être détectée comme COMMAND."""
        result = self.detector.detect("bonjour")
        self.assertEqual(result.intent, self.Intent.GREETING)
        self.assertIsNone(result.command_verb)


class TestCommandGuard(unittest.TestCase):
    """Tests du garde-fou des commandes."""

    @classmethod
    def setUpClass(cls):
        if evaluate_command is None:
            raise unittest.SkipTest("command_guard non disponible")

    def test_whitelist_no_confirm(self):
        """(arrete, enregistrement) autorisé sans confirmation."""
        v = evaluate_command("arrete", "enregistrement")
        self.assertTrue(v.allowed)
        self.assertFalse(v.require_confirmation)
        self.assertEqual(v.risk_level, "low")

    def test_whitelist_confirm(self):
        """(lance, navigateur) autorisé avec confirmation."""
        v = evaluate_command("lance", "navigateur")
        self.assertTrue(v.allowed)
        self.assertTrue(v.require_confirmation)
        self.assertEqual(v.risk_level, "medium")

    def test_not_allowed_unknown_pair(self):
        """Paire inconnue non autorisée."""
        v = evaluate_command("supprime", "tout")
        self.assertFalse(v.allowed)
        self.assertIn("high", v.risk_level)

    def test_missing_verb(self):
        """Verbe manquant -> non autorisé."""
        v = evaluate_command(None, "navigateur")
        self.assertFalse(v.allowed)
        self.assertIn("Verbe", v.reason)

    def test_missing_target(self):
        """Cible manquante -> non autorisé."""
        v = evaluate_command("lance", None)
        self.assertFalse(v.allowed)
        self.assertIn("Cible", v.reason)


class TestCommandExecutor(unittest.TestCase):
    """Tests de l'exécuteur de commandes."""

    @classmethod
    def setUpClass(cls):
        try:
            from core.command_executor import CommandExecutor, ExecuteResult
            cls.CommandExecutor = CommandExecutor
            cls.ExecuteResult = ExecuteResult
            cls.executor = CommandExecutor()
        except ImportError as e:
            raise unittest.SkipTest(f"command_executor non disponible: {e}")

    def test_execute_arrete_enregistrement(self):
        """Exécution (arrete, enregistrement) retourne un message."""
        r = self.executor.execute_command("arrete", "enregistrement")
        self.assertTrue(r.success)
        self.assertTrue(len(r.message) > 0)
        self.assertIsNone(r.error)

    def test_execute_unknown_returns_failure(self):
        """Paire inconnue -> success=False."""
        r = self.executor.execute_command("inconnu", "cible")
        self.assertFalse(r.success)
        self.assertIsNotNone(r.error or r.message)

    def test_register_action(self):
        """Enregistrement d'une action personnalisée."""
        self.executor.register_action("test_verb", "test_target", "Message test.")
        r = self.executor.execute_command("test_verb", "test_target")
        self.assertTrue(r.success)
        self.assertIn("Message test", r.message)


if __name__ == "__main__":
    unittest.main()
