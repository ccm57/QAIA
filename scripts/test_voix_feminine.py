#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour la voix féminine QAIA
"""

# /// script
# dependencies = [
#   "pyttsx3>=2.90",
# ]
# ///

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyttsx3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_voix_feminine():
    """Teste différentes configurations de voix féminine"""
    print("="*70)
    print(" "*20 + "TEST VOIX FÉMININE QAIA")
    print("="*70)
    
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # 1. Lister voix françaises
    print("\n1. Voix françaises disponibles:")
    print("-"*70)
    french_voices = []
    for i, voice in enumerate(voices):
        if 'fr' in voice.id.lower() or 'french' in voice.name.lower():
            french_voices.append(voice)
            gender = voice.gender if hasattr(voice, 'gender') else 'N/A'
            print(f"  {len(french_voices)}. {voice.name}")
            print(f"     ID: {voice.id}")
            print(f"     Genre: {gender}")
    
    if not french_voices:
        print("  ⚠️ Aucune voix française trouvée")
        print("  Utilisation voix par défaut")
        french_voices = [voices[0]]
    
    # 2. Test voix avec différents pitch
    print("\n2. Test voix avec différents paramètres:")
    print("-"*70)
    
    test_text = "Bonjour, je suis QAIA, votre assistante intelligente."
    
    # Configuration de base
    voice = french_voices[0]
    engine.setProperty('voice', voice.id)
    
    # Test 1: Voix normale
    print("\n  Test 1: Voix normale (rate=185)")
    engine.setProperty('rate', 185)
    print(f"  Texte: {test_text}")
    print("  🔊 Lecture...")
    engine.say(test_text)
    engine.runAndWait()
    
    # Test 2: Voix féminine (rate augmenté)
    print("\n  Test 2: Voix féminine simulée (rate=205)")
    engine.setProperty('rate', 205)
    print(f"  Texte: {test_text}")
    print("  🔊 Lecture...")
    engine.say(test_text)
    engine.runAndWait()
    
    # Test 3: Voix féminine optimale
    print("\n  Test 3: Voix féminine optimisée (rate=195)")
    engine.setProperty('rate', 195)
    print(f"  Texte: {test_text}")
    print("  🔊 Lecture...")
    engine.say(test_text)
    engine.runAndWait()
    
    # 3. Recommandations
    print("\n3. Recommandations:")
    print("-"*70)
    print("  ✅ Configuration optimale pour voix féminine:")
    print(f"     - Voix: {voice.name} ({voice.id})")
    print("     - Rate: 195 (légèrement plus rapide)")
    print("     - Volume: 0.9")
    print("\n  💡 Pour une voix encore plus féminine:")
    print("     - Installer espeak-ng-mbrola")
    print("     - Ou utiliser gTTS (nécessite connexion internet)")
    
    print("\n" + "="*70)
    print("Test terminé")
    print("="*70)

if __name__ == "__main__":
    test_voix_feminine()

