#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Tests d'intégration ContextManager et IntentDetector dans qaia_core.py
"""

# /// script
# dependencies = []
# ///

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_context_manager_import():
    """Test que ContextManager peut être importé."""
    try:
        from agents.context_manager import ConversationContext
        assert ConversationContext is not None
        print("✅ ContextManager import OK")
        return True
    except ImportError as e:
        print(f"❌ Erreur import ContextManager: {e}")
        return False

def test_context_manager_functionality():
    """Test le fonctionnement de ContextManager."""
    try:
        from agents.context_manager import ConversationContext
        
        ctx = ConversationContext()
        ctx.add_turn('user', 'Bonjour')
        ctx.add_turn('assistant', 'Bonjour ! Comment puis-je vous aider ?')
        ctx.add_turn('user', 'Quelle est la météo ?')
        
        context = ctx.get_context_for_llm()
        assert len(context) >= 3, f"Attendu au moins 3 tours, obtenu {len(context)}"
        
        # Vérifier format
        for turn in context:
            assert 'role' in turn, "Tour devrait avoir 'role'"
            assert 'content' in turn, "Tour devrait avoir 'content'"
        
        print("✅ ContextManager fonctionnel")
        return True
    except Exception as e:
        print(f"❌ Erreur test ContextManager: {e}")
        return False

def test_intent_detector_import():
    """Test que IntentDetector peut être importé."""
    try:
        from agents.intent_detector import IntentDetector, Intent
        assert IntentDetector is not None
        assert Intent is not None
        print("✅ IntentDetector import OK")
        return True
    except ImportError as e:
        print(f"❌ Erreur import IntentDetector: {e}")
        return False

def test_intent_detector_functionality():
    """Test le fonctionnement d'IntentDetector."""
    try:
        from agents.intent_detector import IntentDetector, Intent
        
        detector = IntentDetector()
        
        # Test salutation
        result = detector.detect("Bonjour")
        assert result.intent == Intent.GREETING, f"Attendu GREETING, obtenu {result.intent}"
        assert result.confidence > 0, "Confiance devrait être > 0"
        
        # Test question
        result = detector.detect("Quelle est la météo ?")
        assert result.intent == Intent.QUESTION, f"Attendu QUESTION, obtenu {result.intent}"
        
        # Test fin conversation
        result = detector.detect("Au revoir")
        assert result.intent == Intent.END_CONVERSATION, f"Attendu END_CONVERSATION, obtenu {result.intent}"
        
        print("✅ IntentDetector fonctionnel")
        return True
    except Exception as e:
        print(f"❌ Erreur test IntentDetector: {e}")
        return False

def test_qaia_core_integration():
    """Test que qaia_core.py et dialogue_manager.py intègrent bien le contexte et l'intention."""
    try:
        base_dir = Path(__file__).parent.parent
        qaia_core_path = base_dir / "qaia_core.py"
        dialogue_manager_path = base_dir / "core" / "dialogue_manager.py"

        # Vérifier que les imports sont présents dans qaia_core.py
        with open(qaia_core_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "from agents.context_manager import ConversationContext" in content, \
                   "ContextManager devrait être importé dans qaia_core.py"
            assert "from agents.intent_detector import IntentDetector" in content or \
                   "from agents.intent_detector import" in content, \
                   "IntentDetector devrait être importé dans qaia_core.py"
            assert "self.context_manager" in content, \
                   "context_manager devrait être initialisé dans qaia_core.py"
            assert "self.intent_detector" in content, \
                   "intent_detector devrait être initialisé dans qaia_core.py"
            assert "get_context_manager" in content, \
                   "get_context_manager devrait être passé à DialogueManager"
            assert "self.dialogue_manager.intent_detector" in content, \
                   "intent_detector devrait être injecté dans DialogueManager"

        # Vérifier que le DialogueManager utilise contexte + intention
        with open(dialogue_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "get_context_for_llm" in content, \
                   "get_context_for_llm devrait être utilisé dans dialogue_manager.py"
            assert "intent_result" in content, \
                   "intent_result devrait être utilisé dans dialogue_manager.py"

        print("✅ Intégration ContextManager et IntentDetector OK (core + dialogue_manager)")
        return True
    except Exception as e:
        print(f"❌ Erreur test intégration: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS D'INTÉGRATION CONTEXTMANAGER ET INTENTDETECTOR")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Import ContextManager", test_context_manager_import()))
    results.append(("Fonctionnalité ContextManager", test_context_manager_functionality()))
    results.append(("Import IntentDetector", test_intent_detector_import()))
    results.append(("Fonctionnalité IntentDetector", test_intent_detector_functionality()))
    results.append(("Intégration qaia_core", test_qaia_core_integration()))
    
    print()
    print("=" * 60)
    print("RÉSULTATS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passés")
    
    if passed == total:
        print("✅ Tous les tests sont passés!")
        sys.exit(0)
    else:
        print("❌ Certains tests ont échoué")
        sys.exit(1)

