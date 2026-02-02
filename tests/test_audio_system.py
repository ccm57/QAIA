#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test du système audio et vérification des paramètres
"""

# /// script
# dependencies = [
#   "sounddevice>=0.4.5",
#   "soundfile>=0.10.3",
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

def test_audio_dir_import():
    """Test l'import de AUDIO_DIR depuis system_config"""
    print("\n" + "="*70)
    print("TEST 1: Import AUDIO_DIR")
    print("="*70)
    
    try:
        from config.system_config import AUDIO_DIR
        print(f"✅ AUDIO_DIR importé avec succès: {AUDIO_DIR}")
        
        # Vérifier que le dossier existe
        if AUDIO_DIR.exists():
            print(f"✅ Le dossier AUDIO_DIR existe: {AUDIO_DIR}")
        else:
            print(f"⚠️ Le dossier AUDIO_DIR n'existe pas, création...")
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Dossier créé: {AUDIO_DIR}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import AUDIO_DIR: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_interface_agent_import():
    """
    Ancien test d'import de `agents.interface_agent` (interface legacy).

    L'ancienne interface a été supprimée au profit de la V2. Ce test est
    conservé pour compatibilité historique et retourne toujours True.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Import interface_agent (SUPPRIMÉ - V2 uniquement)")
    print("=" * 70)
    return True

def test_sounddevice():
    """Test de la disponibilité de sounddevice"""
    print("\n" + "="*70)
    print("TEST 3: SoundDevice")
    print("="*70)
    
    try:
        import sounddevice as sd
        print("✅ sounddevice importé avec succès")
        
        # Lister les périphériques audio
        devices = sd.query_devices()
        print(f"✅ {len(devices)} périphériques audio détectés")
        
        # Afficher le périphérique par défaut
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        print(f"✅ Périphérique d'entrée par défaut: {default_input}")
        print(f"✅ Périphérique de sortie par défaut: {default_output}")
        
        # Afficher les informations du périphérique par défaut
        if default_input is not None:
            device_info = sd.query_devices(default_input)
            print(f"   Nom: {device_info['name']}")
            print(f"   Canaux: {device_info['max_input_channels']}")
            print(f"   Sample rate: {device_info['default_samplerate']}")
        
        return True
        
    except ImportError:
        print("❌ sounddevice non disponible")
        return False
    except Exception as e:
        print(f"⚠️ Erreur avec sounddevice: {e}")
        return False

def test_speech_agent():
    """Test de l'agent de synthèse vocale"""
    print("\n" + "="*70)
    print("TEST 4: SpeechAgent")
    print("="*70)
    
    try:
        from agents.speech_agent import SpeechAgent
        
        agent = SpeechAgent()
        print("✅ SpeechAgent initialisé")
        
        if agent.is_available:
            print("✅ SpeechAgent est disponible")
            
            # Vérifier les propriétés
            if hasattr(agent, 'engine'):
                print("✅ Moteur TTS initialisé")
            
            return True
        else:
            print("⚠️ SpeechAgent n'est pas disponible (peut être normal)")
            return True  # Pas critique
            
    except Exception as e:
        print(f"⚠️ Erreur avec SpeechAgent (peut être normal): {e}")
        return True  # Pas critique

def test_wav2vec_agent():
    """Test de l'agent de reconnaissance vocale"""
    print("\n" + "="*70)
    print("TEST 5: Wav2VecVoiceAgent")
    print("="*70)
    
    try:
        from agents.wav2vec_agent import Wav2VecVoiceAgent
        
        agent = Wav2VecVoiceAgent()
        print("✅ Wav2VecVoiceAgent initialisé")
        
        # Vérifier les attributs
        if hasattr(agent, 'device'):
            print(f"✅ Device: {agent.device}")
        if hasattr(agent, 'sample_rate'):
            print(f"✅ Sample rate: {agent.sample_rate}")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Erreur avec Wav2VecVoiceAgent (peut être normal): {e}")
        import traceback
        traceback.print_exc()
        return True  # Pas critique si dépendances manquantes

def test_audio_config():
    """Test de la configuration audio"""
    print("\n" + "="*70)
    print("TEST 6: Configuration Audio")
    print("="*70)
    
    try:
        from config.system_config import (
            MODEL_CONFIG,
            AUDIO_DIR,
            DATA_DIR
        )
        
        print("✅ Configuration audio importée")
        
        # Vérifier la configuration audio
        audio_config = MODEL_CONFIG.get("audio", {})
        if audio_config:
            print(f"✅ Configuration audio trouvée:")
            print(f"   Sample rate: {audio_config.get('sampling_rate', 'N/A')}")
            print(f"   Channels: {audio_config.get('channels', 'N/A')}")
            print(f"   Format: {audio_config.get('format', 'N/A')}")
        
        # Vérifier les chemins
        print(f"✅ AUDIO_DIR: {AUDIO_DIR}")
        print(f"✅ DATA_DIR: {DATA_DIR}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur avec la configuration audio: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale de test"""
    print("🚀 DÉMARRAGE DES TESTS DU SYSTÈME AUDIO")
    print("="*70)
    
    results = []
    
    # Test 1: Import AUDIO_DIR
    results.append(("Import AUDIO_DIR", test_audio_dir_import()))
    
    # Test 2: Import interface_agent (legacy supprimée)
    results.append(("Import interface_agent (legacy supprimée)", test_interface_agent_import()))
    
    # Test 3: SoundDevice
    results.append(("SoundDevice", test_sounddevice()))
    
    # Test 4: SpeechAgent
    results.append(("SpeechAgent", test_speech_agent()))
    
    # Test 5: Wav2VecVoiceAgent
    results.append(("Wav2VecVoiceAgent", test_wav2vec_agent()))
    
    # Test 6: Configuration
    results.append(("Configuration Audio", test_audio_config()))
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ FINAL")
    print("="*70)
    
    for test_name, success in results:
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        print(f"{test_name:30s} : {status}")
    
    critical_tests = [results[0], results[5]]  # Import AUDIO_DIR et Configuration
    all_critical_passed = all(result[1] for result in critical_tests)
    
    if all_critical_passed:
        print("\n🎉 TOUS LES TESTS CRITIQUES SONT PASSÉS !")
        print("⚠️ Certains tests optionnels peuvent avoir échoué (normal si dépendances manquantes)")
        return 0
    else:
        print("\n❌ Certains tests critiques ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

