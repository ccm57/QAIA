#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Tests d'intégration AudioManager dans qaia_interface.py
"""

# /// script
# dependencies = []
# ///

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_audio_manager_import():
    """Test que AudioManager peut être importé."""
    try:
        from agents.audio_manager import AudioManager, RecordingStrategy
        assert AudioManager is not None
        assert RecordingStrategy is not None
        print("✅ AudioManager import OK")
        return True
    except ImportError as e:
        print(f"❌ Erreur import AudioManager: {e}")
        return False

def test_audio_manager_singleton():
    """Test que AudioManager est un singleton."""
    try:
        from agents.audio_manager import AudioManager
        
        manager1 = AudioManager()
        manager2 = AudioManager()
        
        assert manager1 is manager2, "AudioManager devrait être un singleton"
        print("✅ AudioManager singleton OK")
        return True
    except Exception as e:
        print(f"❌ Erreur test singleton: {e}")
        return False

def test_audio_manager_initialization():
    """Test l'initialisation d'AudioManager."""
    try:
        from agents.audio_manager import AudioManager
        
        manager = AudioManager()
        assert manager.sample_rate == 16000
        assert manager.channels == 1
        assert manager.dtype == 'float32'
        print("✅ AudioManager initialisation OK")
        return True
    except Exception as e:
        print(f"❌ Erreur test initialisation: {e}")
        return False

def test_audio_manager_cleanup_stream():
    """Test le cleanup de stream via AudioManager."""
    try:
        from agents.audio_manager import AudioManager
        
        manager = AudioManager()
        
        # Test cleanup avec stream None (devrait réussir)
        result = manager.cleanup_stream(None)
        assert result is True, "Cleanup avec None devrait réussir"
        
        print("✅ AudioManager cleanup_stream OK")
        return True
    except Exception as e:
        print(f"❌ Erreur test cleanup: {e}")
        return False

def test_qaia_interface_audio_manager_integration():
    """Test que qaia_interface.py peut utiliser AudioManager."""
    try:
        # Vérifier que AudioManager est importé dans le fichier
        qaia_interface_path = Path(__file__).parent.parent / "interface" / "qaia_interface.py"
        
        with open(qaia_interface_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "from agents.audio_manager import AudioManager" in content or \
                   "from agents.audio_manager import" in content, \
                   "AudioManager devrait être importé dans qaia_interface.py"
            assert "self.audio_manager" in content, \
                   "audio_manager devrait être utilisé dans qaia_interface.py"
            assert "cleanup_stream" in content, \
                   "cleanup_stream devrait être utilisé dans qaia_interface.py"
        
        print("✅ Intégration AudioManager dans qaia_interface.py OK")
        return True
    except Exception as e:
        print(f"❌ Erreur test intégration: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS D'INTÉGRATION AUDIOMANAGER")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Import AudioManager", test_audio_manager_import()))
    results.append(("Singleton", test_audio_manager_singleton()))
    results.append(("Initialisation", test_audio_manager_initialization()))
    results.append(("Cleanup stream", test_audio_manager_cleanup_stream()))
    results.append(("Intégration qaia_interface", test_qaia_interface_audio_manager_integration()))
    
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
