#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# \QAIA\

"""
Test de latence après optimisations.
Mesure le temps de réponse du pipeline complet.
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "transformers>=4.26.0",
# ]
# ///

import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_llm_latence():
    """Test latence LLM seul."""
    print("=== TEST LATENCE LLM ===\n")
    
    from agents.llm_agent import LLMAgent
    
    print("1. Initialisation LLMAgent...")
    t_start = time.time()
    agent = LLMAgent()
    t_init = time.time() - t_start
    print(f"   Temps init: {t_init:.2f}s")
    
    print("\n2. Génération réponse courte...")
    message = "Bonjour, comment vas-tu ?"
    
    t_start = time.time()
    response = agent.chat(message=message, max_tokens=150)
    t_gen = time.time() - t_start
    
    print(f"   Temps génération: {t_gen:.2f}s")
    print(f"   Réponse: {response[:100]}...")
    
    # Vérification
    if t_gen < 15:
        print(f"\n✅ Latence LLM OK: {t_gen:.2f}s < 15s")
        return True
    else:
        print(f"\n❌ Latence LLM excessive: {t_gen:.2f}s > 15s")
        return False

def test_pipeline_complet():
    """Test pipeline complet STT→LLM→TTS."""
    print("\n=== TEST PIPELINE COMPLET ===\n")
    
    from agents.wav2vec_agent import Wav2VecVoiceAgent
    from agents.llm_agent import LLMAgent
    from agents.speech_agent import SpeechAgent
    
    print("1. Initialisation agents...")
    t_start = time.time()
    
    stt_agent = Wav2VecVoiceAgent()
    llm_agent = LLMAgent()
    tts_agent = SpeechAgent()
    
    t_init = time.time() - t_start
    print(f"   Temps init: {t_init:.2f}s")
    
    print("\n2. Test STT (simulation avec texte)...")
    # Simuler transcription
    transcription = "Bonjour QAIA"
    print(f"   Transcription: {transcription}")
    
    print("\n3. Test LLM...")
    t_start = time.time()
    response = llm_agent.chat(message=transcription, max_tokens=150)
    t_llm = time.time() - t_start
    print(f"   Temps LLM: {t_llm:.2f}s")
    print(f"   Réponse: {response[:100]}...")
    
    print("\n4. Test TTS...")
    t_start = time.time()
    tts_agent.speak(response[:100], wait=True)
    t_tts = time.time() - t_start
    print(f"   Temps TTS: {t_tts:.2f}s")
    
    # Calcul total (sans STT réel)
    t_total = t_llm + t_tts
    print(f"\n📊 RÉSUMÉ:")
    print(f"   LLM: {t_llm:.2f}s")
    print(f"   TTS: {t_tts:.2f}s")
    print(f"   TOTAL: {t_total:.2f}s (sans STT)")
    
    # Vérification
    if t_llm < 15:
        print(f"\n✅ Pipeline optimisé: LLM {t_llm:.2f}s < 15s")
        return True
    else:
        print(f"\n❌ Pipeline non optimisé: LLM {t_llm:.2f}s > 15s")
        return False

def main():
    """Point d'entrée principal."""
    print("╔════════════════════════════════════════════════════════╗")
    print("║   TEST LATENCE APRÈS OPTIMISATIONS                     ║")
    print("╚════════════════════════════════════════════════════════╝\n")
    
    try:
        # Test 1: LLM seul
        result_llm = test_llm_latence()
        
        # Test 2: Pipeline complet
        result_pipeline = test_pipeline_complet()
        
        # Résultat final
        print("\n" + "="*60)
        print("RÉSULTAT FINAL")
        print("="*60)
        
        if result_llm and result_pipeline:
            print("✅ TOUS LES TESTS PASSÉS")
            print("   Optimisations appliquées avec succès !")
            return 0
        else:
            print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
            print("   Vérifier les optimisations")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

