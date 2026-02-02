#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de la méthode chat() de LLMAgent
"""

# /// script
# dependencies = [
# ]
# ///

import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_llm_agent_import():
    """Test l'import de LLMAgent"""
    print("\n" + "="*70)
    print("TEST 1: Import LLMAgent")
    print("="*70)
    
    try:
        from agents.llm_agent import LLMAgent
        print("✅ LLMAgent importé avec succès")
        return True
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_agent_initialization():
    """Test l'initialisation de LLMAgent"""
    print("\n" + "="*70)
    print("TEST 2: Initialisation LLMAgent")
    print("="*70)
    
    try:
        from agents.llm_agent import LLMAgent
        
        agent = LLMAgent()
        print("✅ LLMAgent initialisé avec succès")
        
        # Vérifier les attributs
        if hasattr(agent, '_initialized'):
            print("✅ Attribut _initialized présent")
        if hasattr(agent, 'model_path'):
            print(f"✅ Chemin du modèle: {agent.model_path}")
        if hasattr(agent, 'device'):
            print(f"✅ Device: {agent.device}")
        
        # Vérifier la méthode chat
        if hasattr(agent, 'chat'):
            print("✅ Méthode chat() présente")
        else:
            print("❌ Méthode chat() manquante!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_method_simple():
    """Test simple de la méthode chat()"""
    print("\n" + "="*70)
    print("TEST 3: Méthode chat() - Test Simple")
    print("="*70)
    
    try:
        from agents.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test avec un message simple
        message = "Bonjour, comment allez-vous ?"
        print(f"📤 Message: {message}")
        
        response = agent.chat(message)
        print(f"📥 Réponse: {response[:200]}...")
        
        if response and len(response) > 0:
            print("✅ La méthode chat() retourne une réponse")
            return True
        else:
            print("❌ La méthode chat() retourne une réponse vide")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test chat(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_method_with_history():
    """Test de la méthode chat() avec historique"""
    print("\n" + "="*70)
    print("TEST 4: Méthode chat() - Avec Historique")
    print("="*70)
    
    try:
        from agents.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Créer un historique de conversation
        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
            {"role": "user", "content": "Quelle est la capitale de la France ?"}
        ]
        
        print(f"📤 Message avec historique ({len(history)} tours)")
        print(f"   Dernier message: {history[-1]['content']}")
        
        response = agent.chat(
            message=history[-1]['content'],
            conversation_history=history[:-1]  # Exclure le dernier message
        )
        
        print(f"📥 Réponse: {response[:200]}...")
        
        if response and len(response) > 0:
            print("✅ La méthode chat() avec historique fonctionne")
            return True
        else:
            print("❌ La méthode chat() avec historique retourne une réponse vide")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test chat() avec historique: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_method_parameters():
    """Test des paramètres de la méthode chat()"""
    print("\n" + "="*70)
    print("TEST 5: Méthode chat() - Paramètres")
    print("="*70)
    
    try:
        from agents.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        message = "Test avec paramètres personnalisés"
        
        # Test avec max_tokens réduit
        response1 = agent.chat(message, max_tokens=50)
        print(f"✅ Test avec max_tokens=50: {len(response1)} caractères")
        
        # Test avec température personnalisée
        response2 = agent.chat(message, temperature=0.5)
        print(f"✅ Test avec temperature=0.5: {len(response2)} caractères")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test des paramètres: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale de test"""
    print("🚀 DÉMARRAGE DES TESTS DE LLM_AGENT.CHAT()")
    print("="*70)
    
    results = []
    
    # Test 1: Import
    results.append(("Import LLMAgent", test_llm_agent_import()))
    
    if not results[-1][1]:
        print("\n❌ L'import a échoué, arrêt des tests")
        return 1
    
    # Test 2: Initialisation
    results.append(("Initialisation", test_llm_agent_initialization()))
    
    if not results[-1][1]:
        print("\n❌ L'initialisation a échoué, arrêt des tests")
        return 1
    
    # Test 3: Chat simple
    results.append(("Chat Simple", test_chat_method_simple()))
    
    # Test 4: Chat avec historique
    results.append(("Chat avec Historique", test_chat_method_with_history()))
    
    # Test 5: Paramètres
    results.append(("Paramètres", test_chat_method_parameters()))
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ FINAL")
    print("="*70)
    
    for test_name, success in results:
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        print(f"{test_name:30s} : {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        return 0
    else:
        print("\n⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

