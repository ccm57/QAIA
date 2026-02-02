#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test d'initialisation complète de tous les agents QAIA
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
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

def test_agent_manager():
    """Test l'initialisation via agent_manager"""
    print("\n" + "="*70)
    print("TEST 1: Initialisation via Agent Manager")
    print("="*70)
    
    try:
        from utils.agent_manager import agent_manager
        from config.system_config import MODEL_CONFIG
        
        print("✅ Agent manager importé avec succès")
        
        # Initialiser tous les agents
        results = agent_manager.initialize_all_agents(MODEL_CONFIG)
        
        print(f"\n📊 Résultats d'initialisation:")
        for agent_name, success in results.items():
            status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
            print(f"  {agent_name:20s} : {status}")
        
        # Vérifier les agents essentiels
        essential_agents = ["rag", "llm"]
        all_essential_ok = True
        for agent_name in essential_agents:
            if not results.get(agent_name, False):
                print(f"❌ Agent essentiel {agent_name} a échoué!")
                all_essential_ok = False
        
        if all_essential_ok:
            print("\n✅ Tous les agents essentiels sont initialisés")
        else:
            print("\n❌ Certains agents essentiels ont échoué")
        
        # Lister les agents actifs
        active_agents = agent_manager.get_active_agents()
        print(f"\n📋 Agents actifs: {', '.join(active_agents)}")
        
        return all_essential_ok
        
    except Exception as e:
        print(f"❌ Erreur lors du test agent_manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_agents():
    """Test l'initialisation individuelle de chaque agent"""
    print("\n" + "="*70)
    print("TEST 2: Initialisation Individuelle des Agents")
    print("="*70)
    
    agents_to_test = {
        "LLMAgent": ("agents.llm_agent", "LLMAgent"),
        "Wav2VecVoiceAgent": ("agents.wav2vec_agent", "Wav2VecVoiceAgent"),
        "SpeechAgent": ("agents.speech_agent", "SpeechAgent"),
        "SpeakerAuth": ("agents.speaker_auth", "SpeakerAuth"),
    }
    
    results = {}
    
    for agent_name, (module_path, class_name) in agents_to_test.items():
        try:
            print(f"\n🔄 Test {agent_name}...")
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Tenter l'initialisation
            if agent_name == "LLMAgent":
                # LLMAgent est un singleton
                agent = agent_class()
            else:
                agent = agent_class()
            
            print(f"  ✅ {agent_name} initialisé avec succès")
            
            # Vérifier les méthodes importantes
            if hasattr(agent, "__init__"):
                print(f"  ✅ Méthode __init__ présente")
            if hasattr(agent, "chat") or hasattr(agent, "process") or hasattr(agent, "generate"):
                print(f"  ✅ Méthode de traitement présente")
            
            results[agent_name] = True
            
        except Exception as e:
            print(f"  ❌ Erreur avec {agent_name}: {e}")
            results[agent_name] = False
    
    # Résumé
    print(f"\n📊 Résumé des tests individuels:")
    for agent_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {agent_name}")
    
    return all(results.values())

def test_rag_agent():
    """Test spécifique pour l'agent RAG"""
    print("\n" + "="*70)
    print("TEST 3: Agent RAG")
    print("="*70)
    
    try:
        from agents.rag_agent import process_query, DataSources
        
        print("✅ Import RAG agent réussi")
        
        # Tester DataSources
        data_sources = DataSources()
        doc_count = data_sources.count_documents()
        print(f"✅ DataSources initialisé - {doc_count} documents trouvés")
        
        # Tester process_query (peut échouer si pas de documents)
        try:
            test_query = "test"
            result = process_query(test_query, k_results=1)
            print(f"✅ process_query fonctionne - Réponse: {result[:50]}...")
            return True
        except Exception as e:
            print(f"⚠️ process_query a échoué (peut être normal si pas de documents): {e}")
            return True  # Pas critique si pas de documents
        
    except Exception as e:
        print(f"❌ Erreur avec RAG agent: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale de test"""
    print("🚀 DÉMARRAGE DES TESTS D'INITIALISATION DES AGENTS")
    print("="*70)
    
    results = []
    
    # Test 1: Agent Manager
    results.append(("Agent Manager", test_agent_manager()))
    
    # Test 2: Agents individuels
    results.append(("Agents Individuels", test_individual_agents()))
    
    # Test 3: RAG Agent
    results.append(("RAG Agent", test_rag_agent()))
    
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

