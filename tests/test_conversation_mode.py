#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test du mode conversationnel QAIA
Vérifie l'intégration complète des agents pour le mode conversation
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "transformers>=4.26.0",
#   "numpy>=1.22.0"
# ]
# ///

import os
import sys
import logging
import traceback
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_qaia_core_initialization():
    """Test l'initialisation du core QAIA avec tous les agents"""
    print("🔄 Test d'initialisation du core QAIA...")
    
    try:
        from qaia_core import QAIACore
        
        # Initialiser QAIA
        qaia = QAIACore()
        
        # Vérifier que les agents sont chargés
        print(f"✅ Agents disponibles: {list(qaia.agents.keys())}")
        
        # Vérifier les agents essentiels
        essential_agents = ['rag', 'llm']
        for agent_name in essential_agents:
            if hasattr(qaia, f'{agent_name}_agent') and getattr(qaia, f'{agent_name}_agent') is not None:
                print(f"✅ Agent {agent_name} chargé")
            else:
                print(f"❌ Agent {agent_name} manquant")
                return False
        
        # Test de génération de texte
        print("\n🔄 Test de génération de texte...")
        response = qaia.interpret_command("Bonjour, comment allez-vous ?")
        print(f"✅ Réponse générée: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        print(traceback.format_exc())
        return False

def test_llm_agent_direct():
    """Test direct de l'agent LLM"""
    print("\n🔄 Test direct de l'agent LLM...")
    
    try:
        from agents.llm_agent import LLMAgent
        
        # Initialiser l'agent LLM
        llm_agent = LLMAgent(debug=True)
        
        # Test de génération
        response = llm_agent.generate_text("Explique-moi l'intelligence artificielle en quelques phrases.")
        print(f"✅ Réponse LLM: {response[:100]}...")
        
        # Test du mode conversation
        print("\n🔄 Test du mode conversation...")
        success = llm_agent.prepare_for_conversation()
        if success:
            print("✅ Mode conversation préparé")
            
            # Test de génération en mode conversation
            response = llm_agent.generate_text("Quelle est la capitale de la France ?")
            print(f"✅ Réponse conversationnelle: {response[:100]}...")
            
            # Sortir du mode conversation
            llm_agent.exit_conversation_mode()
            print("✅ Sortie du mode conversation")
        else:
            print("❌ Échec de préparation du mode conversation")
            return False
        
        # Nettoyage
        llm_agent.cleanup()
        print("✅ Agent LLM nettoyé")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test LLM: {e}")
        print(traceback.format_exc())
        return False

def test_voice_agent():
    """Test de l'agent vocal"""
    print("\n🔄 Test de l'agent vocal...")
    
    try:
        from agents.wav2vec_agent import Wav2VecVoiceAgent
        
        # Initialiser l'agent vocal
        voice_agent = Wav2VecVoiceAgent(debug=True)
        
        # Créer un fichier audio de test sur F: si nécessaire
        from config.system_config import DATA_DIR
        audio_file = DATA_DIR / "audio" / "test_16000.wav"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not audio_file.exists():
            try:
                import soundfile as sf
                import numpy as np
                # Créer un fichier audio de test simple
                samplerate = 16000
                duration = 1  # seconde
                frequency = 440  # Hz
                t = np.linspace(0., duration, int(samplerate * duration), endpoint=False)
                amplitude = 0.5
                data = amplitude * np.sin(2. * np.pi * frequency * t)
                sf.write(str(audio_file), data, samplerate)
                print(f"✅ Fichier audio de test créé sur F:: {audio_file}")
            except ImportError:
                print("⚠️ soundfile non disponible, impossible de créer un fichier audio de test")
            except Exception as e:
                print(f"⚠️ Erreur lors de la création du fichier audio: {e}")
        
        # Test de préparation pour conversation
        success = voice_agent.prepare_for_conversation()
        if success:
            print("✅ Agent vocal préparé pour conversation")
            
            # Test de transcription (si fichier audio disponible)
            if audio_file.exists():
                text, confidence = voice_agent.transcribe_audio(str(audio_file))
                print(f"✅ Transcription: {text} (confiance: {confidence:.2f})")
            else:
                print("⚠️ Fichier audio de test non trouvé, test de transcription ignoré")
            
            # Sortir du mode conversation
            voice_agent.exit_conversation_mode()
            print("✅ Sortie du mode conversation vocal")
        else:
            print("❌ Échec de préparation de l'agent vocal")
            return False
        
        # Nettoyage
        voice_agent.cleanup()
        print("✅ Agent vocal nettoyé")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test vocal: {e}")
        print(traceback.format_exc())
        return False

def test_conversation_integration():
    """Test d'intégration complète du mode conversation"""
    print("\n🔄 Test d'intégration du mode conversation...")
    
    try:
        from qaia_core import QAIACore
        
        # Initialiser QAIA
        qaia = QAIACore()
        
        # Vérifier que les agents nécessaires sont disponibles
        if not (hasattr(qaia, 'llm_agent') and qaia.llm_agent is not None):
            print("❌ Agent LLM non disponible")
            return False
        
        if not (hasattr(qaia, 'voice_agent') and qaia.voice_agent is not None):
            print("❌ Agent vocal non disponible")
            return False
        
        # Préparer les agents pour le mode conversation
        print("🔄 Préparation des agents pour conversation...")
        
        llm_success = qaia.llm_agent.prepare_for_conversation()
        voice_success = qaia.voice_agent.prepare_for_conversation()
        
        if llm_success and voice_success:
            print("✅ Tous les agents préparés pour conversation")
            
            # Test de traitement de message
            print("🔄 Test de traitement de message...")
            response = qaia.interpret_command("Bonjour, peux-tu m'expliquer ce qu'est l'IA ?")
            print(f"✅ Réponse intégrée: {response[:100]}...")
            
            # Sortir du mode conversation
            qaia.llm_agent.exit_conversation_mode()
            qaia.voice_agent.exit_conversation_mode()
            print("✅ Sortie du mode conversation")
            
            return True
        else:
            print(f"❌ Échec de préparation: LLM={llm_success}, Voice={voice_success}")
            return False
        
    except Exception as e:
        print(f"❌ Erreur lors du test d'intégration: {e}")
        print(traceback.format_exc())
        return False

def test_paths_on_f_drive():
    """Vérifie que tous les chemins pointent vers F:"""
    print("\n🔄 Vérification des chemins F:...")
    
    try:
        from config.system_config import BASE_DIR, MODELS_DIR, DATA_DIR, LOGS_DIR
        
        paths_to_check = {
            "BASE_DIR": BASE_DIR,
            "MODELS_DIR": MODELS_DIR,
            "DATA_DIR": DATA_DIR,
            "LOGS_DIR": LOGS_DIR
        }
        
        all_on_f = True
        for name, path in paths_to_check.items():
            if str(path).startswith("F:"):
                print(f"✅ {name}: {path}")
            else:
                print(f"❌ {name}: {path} (pas sur F:!)")
                all_on_f = False
        
        return all_on_f
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des chemins: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 DÉMARRAGE DES TESTS DU MODE CONVERSATIONNEL QAIA")
    print("=" * 60)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        ("Vérification des chemins F:", test_paths_on_f_drive),
        ("Test agent LLM direct", test_llm_agent_direct),
        ("Test agent vocal", test_voice_agent),
        ("Test core QAIA", test_qaia_core_initialization),
        ("Test intégration conversation", test_conversation_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: SUCCÈS")
            else:
                print(f"❌ {test_name}: ÉCHEC")
        except Exception as e:
            print(f"❌ {test_name}: ERREUR - {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ SUCCÈS" if result else "❌ ÉCHEC"
        print(f"{test_name}: {status}")
    
    print(f"\nRésultat global: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 TOUS LES TESTS SONT PASSÉS ! Le mode conversationnel est prêt !")
        return 0
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
