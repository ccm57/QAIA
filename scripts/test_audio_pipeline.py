#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# \QAIA\

"""
Test complet du pipeline audio QAIA
Vérifie: capture → prétraitement → transcription
"""

# /// script
# dependencies = [
#   "numpy>=1.22.0",
#   "scipy>=1.9.0",
# ]
# ///

import sys
import numpy as np
import scipy.io.wavfile as wav
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_audio_file(filepath: str):
    """Analyse un fichier audio WAV"""
    sr, data = wav.read(filepath)
    
    # Convertir en float32 si nécessaire
    if data.dtype == np.int16:
        data_float = data.astype(np.float32) / 32768.0
    else:
        data_float = data.astype(np.float32)
    
    # Statistiques
    duration = len(data) / sr
    rms_int16 = np.sqrt(np.mean(data**2))
    rms_float = np.sqrt(np.mean(data_float**2))
    max_val = np.max(np.abs(data))
    clipping = (np.abs(data) >= 32767).sum()
    clipping_pct = (clipping / len(data)) * 100
    silence = (np.abs(data) < 100).sum()
    silence_pct = (silence / len(data)) * 100
    
    print(f"\n{'='*60}")
    print(f"ANALYSE: {Path(filepath).name}")
    print(f"{'='*60}")
    print(f"Durée:           {duration:.2f}s")
    print(f"Sample rate:     {sr} Hz")
    print(f"Samples:         {len(data):,}")
    print(f"RMS (int16):     {rms_int16:.0f}")
    print(f"RMS (float):     {rms_float:.3f}")
    print(f"Max absolu:      {max_val}")
    print(f"Clipping:        {clipping:,} samples ({clipping_pct:.1f}%)")
    print(f"Silence (<100):  {silence:,} samples ({silence_pct:.1f}%)")
    
    # Évaluation qualité
    print(f"\n{'='*60}")
    print("ÉVALUATION QUALITÉ")
    print(f"{'='*60}")
    
    if clipping_pct > 5.0:
        print("❌ AUDIO SATURÉ (>5% clipping) → Transcription impossible")
        print("   → Réduire volume micro: amixer set Capture 20%")
    elif clipping_pct > 1.0:
        print("⚠️  Audio légèrement saturé (1-5% clipping)")
        print("   → Réduire volume micro: amixer set Capture 25%")
    elif rms_float < 0.01:
        print("⚠️  Audio trop faible (RMS < 0.01)")
        print("   → Augmenter volume micro: amixer set Capture 40%")
    else:
        print("✅ Qualité audio CORRECTE")
    
    if silence_pct > 80:
        print("⚠️  Trop de silence (>80%) - vérifier micro")
    
    return {
        'duration': duration,
        'rms_float': rms_float,
        'clipping_pct': clipping_pct,
        'silence_pct': silence_pct,
        'quality_ok': clipping_pct < 5.0 and rms_float > 0.01
    }


def test_preprocessing():
    """Test le prétraitement audio"""
    print(f"\n{'='*60}")
    print("TEST PRÉTRAITEMENT AUDIO")
    print(f"{'='*60}")
    
    try:
        from agents.wav2vec_agent import Wav2VecVoiceAgent
        
        # Trouver le dernier fichier audio
        audio_dir = Path(__file__).parent.parent / "data" / "audio"
        audio_files = sorted(audio_dir.glob("utt_*.wav"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not audio_files:
            print("❌ Aucun fichier audio trouvé")
            return False
        
        latest = audio_files[0]
        print(f"Fichier: {latest.name}")
        
        # Analyser avant prétraitement
        stats_before = analyze_audio_file(str(latest))
        
        # Charger et prétraiter
        sr, data = wav.read(str(latest))
        data_float = data.astype(np.float32) / 32768.0
        
        agent = Wav2VecVoiceAgent()
        data_processed = agent._preprocess_audio(data_float, sr)
        
        # Statistiques après prétraitement
        rms_after = np.sqrt(np.mean(data_processed**2))
        max_after = np.max(np.abs(data_processed))
        
        print(f"\n{'='*60}")
        print("APRÈS PRÉTRAITEMENT")
        print(f"{'='*60}")
        print(f"RMS:        {stats_before['rms_float']:.3f} → {rms_after:.3f}")
        print(f"Max:        {max_after:.3f}")
        
        if rms_after > 0.5:
            print("⚠️  RMS élevé après prétraitement (risque saturation)")
        else:
            print("✅ Niveau correct après prétraitement")
        
        return stats_before['quality_ok']
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transcription():
    """Test la transcription"""
    print(f"\n{'='*60}")
    print("TEST TRANSCRIPTION")
    print(f"{'='*60}")
    
    try:
        from agents.wav2vec_agent import Wav2VecVoiceAgent
        
        # Trouver le dernier fichier audio
        audio_dir = Path(__file__).parent.parent / "data" / "audio"
        audio_files = sorted(audio_dir.glob("utt_*.wav"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not audio_files:
            print("❌ Aucun fichier audio trouvé")
            return False
        
        latest = audio_files[0]
        print(f"Fichier: {latest.name}")
        
        agent = Wav2VecVoiceAgent()
        result = agent.transcribe_audio(str(latest))
        
        if isinstance(result, tuple):
            text, confidence = result
        else:
            text = result
            confidence = 0.0
        
        print(f"\nTranscription: '{text}'")
        print(f"Confiance:     {confidence:.2f}")
        
        if not text or text.lower().startswith("erreur"):
            print("❌ Transcription ÉCHOUÉE")
            return False
        else:
            print("✅ Transcription RÉUSSIE")
            return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print(f"\n{'#'*60}")
    print("  TEST PIPELINE AUDIO QAIA")
    print(f"{'#'*60}")
    
    # Vérifier volume micro
    import subprocess
    try:
        result = subprocess.run(['amixer', 'sget', 'Capture'], 
                              capture_output=True, text=True)
        if '[' in result.stdout:
            volume = result.stdout.split('[')[1].split(']')[0]
            print(f"\n📊 Volume microphone: {volume}")
            
            vol_pct = int(volume.rstrip('%'))
            if vol_pct > 40:
                print("⚠️  Volume élevé - risque de saturation")
                print("   → Recommandé: amixer set Capture 30%")
            elif vol_pct < 20:
                print("⚠️  Volume faible - risque audio trop faible")
                print("   → Recommandé: amixer set Capture 30%")
            else:
                print("✅ Volume correct")
    except:
        pass
    
    # Tests
    results = []
    
    # 1. Analyse audio
    audio_dir = Path(__file__).parent.parent / "data" / "audio"
    audio_files = sorted(audio_dir.glob("utt_*.wav"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if audio_files:
        stats = analyze_audio_file(str(audio_files[0]))
        results.append(('Qualité audio', stats['quality_ok']))
    else:
        print("\n⚠️  Aucun fichier audio trouvé - enregistrez d'abord")
        return
    
    # 2. Test prétraitement
    results.append(('Prétraitement', test_preprocessing()))
    
    # 3. Test transcription
    results.append(('Transcription', test_transcription()))
    
    # Résumé
    print(f"\n{'#'*60}")
    print("  RÉSUMÉ")
    print(f"{'#'*60}")
    
    for name, success in results:
        status = "✅ OK" if success else "❌ ÉCHEC"
        print(f"{name:20s} {status}")
    
    all_ok = all(r[1] for r in results)
    
    print(f"\n{'='*60}")
    if all_ok:
        print("✅ TOUS LES TESTS RÉUSSIS")
        print("\nLe pipeline audio fonctionne correctement.")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("\nActions recommandées:")
        print("1. Vérifier volume micro: amixer set Capture 30%")
        print("2. Tester à nouveau: python3 launcher.py")
        print("3. Parler clairement et normalement (pas fort)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

