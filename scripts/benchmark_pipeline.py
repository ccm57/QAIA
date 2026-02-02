#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de benchmark complet du pipeline conversationnel QAIA
Mesure les temps de réponse de chaque composant
"""

# /// script
# dependencies = [
#   "sounddevice>=0.4.5",
#   "soundfile>=0.10.3",
#   "numpy>=1.22.0",
#   "torch>=2.0.0",
#   "transformers>=4.26.0",
# ]
# ///

import sys
import time
from pathlib import Path
import logging

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)

def benchmark_stt():
    """Benchmark STT (Wav2Vec2)"""
    print("\n" + "="*70)
    print("BENCHMARK STT (WAV2VEC2)")
    print("="*70)
    
    from agents.wav2vec_agent import Wav2VecVoiceAgent
    
    # Initialisation
    t_start = time.time()
    agent = Wav2VecVoiceAgent()
    t_init = time.time() - t_start
    print(f"✓ Initialisation: {t_init:.2f}s")
    
    # Chargement modèle
    t_start = time.time()
    agent._ensure_model_loaded()
    t_load = time.time() - t_start
    print(f"✓ Chargement modèle: {t_load:.2f}s")
    
    # Enregistrement
    print("\n🎤 Enregistrement audio (5s)...")
    t_start = time.time()
    audio_file = agent.record_audio(duration=5)
    t_record = time.time() - t_start
    print(f"✓ Enregistrement: {t_record:.2f}s")
    
    # Transcription
    t_start = time.time()
    text, conf = agent.transcribe_audio(audio_file)
    t_transcribe = time.time() - t_start
    print(f"✓ Transcription: {t_transcribe:.2f}s")
    print(f"  Texte: {text[:80]}...")
    print(f"  Confiance: {conf:.2f}")
    
    total_stt = t_record + t_transcribe
    print(f"\n🔹 TOTAL STT: {total_stt:.2f}s")
    
    return {
        'init': t_init,
        'load': t_load,
        'record': t_record,
        'transcribe': t_transcribe,
        'total': total_stt,
        'text': text
    }

def benchmark_llm(prompt):
    """Benchmark LLM (Phi-3)"""
    print("\n" + "="*70)
    print("BENCHMARK LLM (LLAMA 3.1 8B)")
    print("="*70)
    
    from agents.llm_agent import LLMAgent
    
    # Initialisation
    t_start = time.time()
    agent = LLMAgent()
    t_init = time.time() - t_start
    print(f"✓ Initialisation: {t_init:.2f}s")
    
    # Préparation mode conversation
    t_start = time.time()
    agent.prepare_conversation_mode()
    t_prepare = time.time() - t_start
    print(f"✓ Préparation: {t_prepare:.2f}s")
    
    # Génération réponse
    print(f"\n💬 Génération réponse...")
    print(f"   Prompt: {prompt[:60]}...")
    t_start = time.time()
    response = agent.chat(prompt, max_tokens=150)
    t_generate = time.time() - t_start
    print(f"✓ Génération: {t_generate:.2f}s")
    print(f"  Réponse: {response[:80]}...")
    
    # Tokens par seconde
    tokens = len(response.split())
    tps = tokens / t_generate if t_generate > 0 else 0
    print(f"  Tokens: {tokens} ({tps:.1f} tokens/s)")
    
    print(f"\n🔹 TOTAL LLM: {t_generate:.2f}s")
    
    return {
        'init': t_init,
        'prepare': t_prepare,
        'generate': t_generate,
        'total': t_generate,
        'tokens': tokens,
        'tps': tps,
        'response': response
    }

def benchmark_tts(text):
    """Benchmark TTS (pyttsx3)"""
    print("\n" + "="*70)
    print("BENCHMARK TTS (PYTTSX3)")
    print("="*70)
    
    from agents.speech_agent import SpeechAgent
    
    # Initialisation
    t_start = time.time()
    agent = SpeechAgent()
    t_init = time.time() - t_start
    print(f"✓ Initialisation: {t_init:.2f}s")
    
    # Synthèse vocale
    print(f"\n🔊 Synthèse vocale...")
    print(f"   Texte: {text[:60]}...")
    t_start = time.time()
    
    # Sauvegarder au lieu de lire (plus rapide pour test)
    output_file = Path(__file__).parent.parent / "data" / "audio" / "test_tts.wav"
    agent.speak(text, save_to_file=str(output_file))
    
    t_synthesize = time.time() - t_start
    print(f"✓ Synthèse: {t_synthesize:.2f}s")
    
    print(f"\n🔹 TOTAL TTS: {t_synthesize:.2f}s")
    
    return {
        'init': t_init,
        'synthesize': t_synthesize,
        'total': t_synthesize
    }

def benchmark_rag():
    """Benchmark RAG (ChromaDB + embeddings)"""
    print("\n" + "="*70)
    print("BENCHMARK RAG (CHROMADB)")
    print("="*70)
    
    try:
        from agents.rag_agent import process_query
        
        # Query simple (sans RAG)
        prompt = "Bonjour, comment vas-tu?"
        print(f"\n🔍 Query sans RAG...")
        t_start = time.time()
        response = process_query(prompt, k_results=0, min_similarity=0.0)
        t_no_rag = time.time() - t_start
        print(f"✓ Sans RAG: {t_no_rag:.2f}s")
        
        # Query avec RAG
        print(f"\n🔍 Query avec RAG...")
        t_start = time.time()
        response = process_query(prompt, k_results=3, min_similarity=0.5)
        t_with_rag = time.time() - t_start
        print(f"✓ Avec RAG: {t_with_rag:.2f}s")
        
        overhead = t_with_rag - t_no_rag
        print(f"  Overhead RAG: {overhead:.2f}s")
        
        return {
            'no_rag': t_no_rag,
            'with_rag': t_with_rag,
            'overhead': overhead
        }
    except Exception as e:
        print(f"⚠️ RAG non disponible: {e}")
        return None

def main():
    """Fonction principale"""
    print("="*70)
    print(" "*20 + "BENCHMARK PIPELINE QAIA")
    print("="*70)
    print("\n⚠️ Ce test nécessite:")
    print("  - Un micro fonctionnel")
    print("  - Tous les modèles téléchargés")
    print("  - ~27 GB RAM disponible")
    
    input("\nAppuyez sur Entrée pour commencer...")
    
    results = {}
    
    # 1. STT
    try:
        results['stt'] = benchmark_stt()
    except Exception as e:
        print(f"❌ Erreur STT: {e}")
        import traceback
        traceback.print_exc()
        results['stt'] = None
    
    # 2. LLM (utiliser texte du STT si disponible)
    prompt = results['stt']['text'] if results.get('stt') else "Bonjour, comment vas-tu?"
    try:
        results['llm'] = benchmark_llm(prompt)
    except Exception as e:
        print(f"❌ Erreur LLM: {e}")
        import traceback
        traceback.print_exc()
        results['llm'] = None
    
    # 3. TTS (utiliser réponse du LLM si disponible)
    text = results['llm']['response'] if results.get('llm') else "Je suis QAIA, votre assistant."
    try:
        results['tts'] = benchmark_tts(text[:100])  # Limiter à 100 chars pour test
    except Exception as e:
        print(f"❌ Erreur TTS: {e}")
        import traceback
        traceback.print_exc()
        results['tts'] = None
    
    # 4. RAG (optionnel)
    try:
        results['rag'] = benchmark_rag()
    except Exception as e:
        print(f"⚠️ RAG skip: {e}")
        results['rag'] = None
    
    # Résumé
    print("\n" + "="*70)
    print(" "*25 + "RÉSUMÉ")
    print("="*70)
    
    total_latency = 0
    
    if results.get('stt'):
        stt_time = results['stt']['total']
        total_latency += stt_time
        print(f"🎤 STT (enregistrement + transcription): {stt_time:.2f}s")
        print(f"   - Enregistrement: {results['stt']['record']:.2f}s")
        print(f"   - Transcription: {results['stt']['transcribe']:.2f}s")
    
    if results.get('llm'):
        llm_time = results['llm']['total']
        total_latency += llm_time
        print(f"💬 LLM (génération réponse): {llm_time:.2f}s")
        print(f"   - Tokens/s: {results['llm']['tps']:.1f}")
    
    if results.get('tts'):
        tts_time = results['tts']['total']
        total_latency += tts_time
        print(f"🔊 TTS (synthèse vocale): {tts_time:.2f}s")
    
    if results.get('rag'):
        print(f"🔍 RAG (overhead): {results['rag']['overhead']:.2f}s")
    
    print(f"\n{'='*70}")
    print(f"⏱️  LATENCE TOTALE: {total_latency:.2f}s")
    print(f"{'='*70}")
    
    # Analyse
    print("\n📊 ANALYSE:")
    
    if results.get('stt') and results.get('llm'):
        if results['llm']['total'] > results['stt']['total'] * 2:
            print("⚠️ LLM est le principal goulot d'étranglement (>2× STT)")
        elif results['stt']['transcribe'] > 3.0:
            print("⚠️ STT transcription lente (>3s)")
    
    if results.get('llm') and results['llm']['tps'] < 10:
        print("⚠️ Génération LLM très lente (<10 tokens/s)")
    
    if total_latency > 15:
        print("❌ Latence totale excessive (>15s)")
        print("   Recommandations:")
        print("   1. Réduire n_ctx LLM (actuellement 8192)")
        print("   2. Réduire max_tokens réponse (actuellement 2048)")
        print("   3. Optimiser batch_size")
    elif total_latency > 10:
        print("⚠️ Latence élevée (>10s)")
        print("   Considérer optimisations mineures")
    else:
        print("✅ Latence acceptable (<10s)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()

