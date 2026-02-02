#!/usr/bin/env python
# -*- coding: utf-8 -*-
# F:\QAIA\
"""Test de l'agent LLM Huihui-Qwen3-4B-Instruct-2507-abliterated."""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "transformers>=4.26.0",
#   "accelerate>=0.20.0",
#   "bitsandbytes>=0.41.0",
#   "numpy>=1.22.0",
#   "tokenizers>=0.13.0"
# ]
# ///

from importlib.machinery import SourceFileLoader
from pathlib import Path

LLM_AGENT_PATH = Path(__file__).resolve().parents[1] / "agents" / "llm_agent.py"
llm_module = SourceFileLoader("llm_agent", str(LLM_AGENT_PATH)).load_module()
LLMAgent = llm_module.LLMAgent


def test_basic_generation():
    """Test de génération de texte basique."""
    print("🔄 Test de génération de texte basique...")
    
    agent = LLMAgent(debug=True)
    print(f"Device: {agent.device}")
    
    # Test simple
    prompt = "Bonjour, comment allez-vous ?"
    response = agent.generate_text(prompt, max_tokens=50)
    
    print(f"Prompt: {prompt}")
    print(f"Réponse: {response}")
    
    agent.cleanup()
    return response


def test_conversation():
    """Test de conversation."""
    print("\n🔄 Test de conversation...")
    
    agent = LLMAgent(debug=True)
    
    # Préparer le mode conversation
    if not agent.prepare_for_conversation():
        print("❌ Échec de la préparation du mode conversation")
        return False
    
    # Test de conversation
    conversation_history = []
    
    messages = [
        "Salut ! Comment ça va ?",
        "Peux-tu m'expliquer ce qu'est l'intelligence artificielle ?",
        "Merci pour l'explication !"
    ]
    
    for message in messages:
        print(f"\nUtilisateur: {message}")
        response = agent.chat(message, conversation_history)
        print(f"Assistant: {response}")
        
        # Ajouter à l'historique
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": response})
    
    # Sortir du mode conversation
    agent.exit_conversation_mode()
    agent.cleanup()
    
    return True


def test_performance():
    """Test de performance."""
    print("\n🔄 Test de performance...")
    
    agent = LLMAgent(debug=True)
    
    import time
    
    prompts = [
        "Qu'est-ce que Python ?",
        "Explique-moi le machine learning",
        "Comment fonctionne un réseau de neurones ?"
    ]
    
    total_time = 0
    for i, prompt in enumerate(prompts, 1):
        print(f"\nTest {i}/3: {prompt}")
        start_time = time.time()
        
        response = agent.generate_text(prompt, max_tokens=100)
        
        end_time = time.time()
        duration = end_time - start_time
        total_time += duration
        
        print(f"Réponse: {response[:100]}...")
        print(f"Temps: {duration:.2f}s")
    
    print(f"\nTemps total: {total_time:.2f}s")
    print(f"Temps moyen: {total_time/len(prompts):.2f}s")
    
    agent.cleanup()
    return total_time


def main():
    """Fonction principale de test."""
    print("🚀 Démarrage des tests de l'agent LLM Huihui-Qwen3-4B")
    print("=" * 60)
    
    try:
        # Test 1: Génération basique
        test_basic_generation()
        
        # Test 2: Conversation
        test_conversation()
        
        # Test 3: Performance
        test_performance()
        
        print("\n✅ Tous les tests sont terminés avec succès !")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
