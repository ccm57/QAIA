#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test et diagnostic de l'enregistrement audio
Identifie les problèmes de gain, saturation, et qualité audio
"""

# /// script
# dependencies = [
#   "sounddevice>=0.4.5",
#   "soundfile>=0.10.3",
#   "numpy>=1.22.0",
#   "scipy>=1.9.0",
# ]
# ///

import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path
import time
import sys

def analyze_audio_file(filepath):
    """Analyse un fichier audio et retourne des métriques"""
    data, sr = sf.read(filepath)
    
    # Convertir en mono si stéréo
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    
    metrics = {
        'sample_rate': sr,
        'duration': len(data) / sr,
        'samples': len(data),
        'dtype': str(data.dtype),
        'min': float(data.min()),
        'max': float(data.max()),
        'mean_abs': float(np.abs(data).mean()),
        'rms': float(np.sqrt(np.mean(data**2))),
        'clipping_samples': int((np.abs(data) > 0.99).sum()),
        'clipping_percent': float((np.abs(data) > 0.99).sum() / len(data) * 100),
        'silence_samples': int((np.abs(data) < 0.01).sum()),
        'silence_percent': float((np.abs(data) < 0.01).sum() / len(data) * 100),
        'peak_to_rms_ratio': float(np.abs(data).max() / (np.sqrt(np.mean(data**2)) + 1e-10)),
    }
    
    return metrics

def print_metrics(metrics, title="Analyse Audio"):
    """Affiche les métriques de manière formatée"""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")
    print(f"Sample Rate      : {metrics['sample_rate']} Hz")
    print(f"Durée            : {metrics['duration']:.2f}s")
    print(f"Samples          : {metrics['samples']}")
    print(f"Type             : {metrics['dtype']}")
    print(f"-" * 70)
    print(f"Amplitude min    : {metrics['min']:.4f}")
    print(f"Amplitude max    : {metrics['max']:.4f}")
    print(f"Amplitude moyenne: {metrics['mean_abs']:.4f}")
    print(f"RMS              : {metrics['rms']:.4f}")
    print(f"-" * 70)
    print(f"Clipping         : {metrics['clipping_samples']} samples ({metrics['clipping_percent']:.1f}%)")
    print(f"Silence          : {metrics['silence_samples']} samples ({metrics['silence_percent']:.1f}%)")
    print(f"Peak/RMS ratio   : {metrics['peak_to_rms_ratio']:.2f}")
    print(f"{'='*70}")
    
    # Diagnostic
    print(f"\n{'DIAGNOSTIC':^70}")
    print(f"{'-'*70}")
    
    issues = []
    warnings = []
    
    if metrics['clipping_percent'] > 5:
        issues.append(f"❌ SATURATION CRITIQUE: {metrics['clipping_percent']:.1f}% de clipping (> 5%)")
    elif metrics['clipping_percent'] > 1:
        warnings.append(f"⚠️ Clipping modéré: {metrics['clipping_percent']:.1f}% (> 1%)")
    
    if metrics['rms'] > 0.5:
        issues.append(f"❌ SIGNAL TROP FORT: RMS={metrics['rms']:.2f} (devrait être ~0.15-0.25)")
    elif metrics['rms'] < 0.05:
        warnings.append(f"⚠️ Signal faible: RMS={metrics['rms']:.2f} (devrait être ~0.15-0.25)")
    
    if metrics['silence_percent'] > 50:
        warnings.append(f"⚠️ Beaucoup de silence: {metrics['silence_percent']:.1f}%")
    
    if metrics['sample_rate'] != 16000:
        warnings.append(f"⚠️ Sample rate non-standard: {metrics['sample_rate']}Hz (attendu: 16000Hz)")
    
    if issues:
        for issue in issues:
            print(issue)
    if warnings:
        for warning in warnings:
            print(warning)
    
    if not issues and not warnings:
        print("✅ Audio de bonne qualité")
    
    print(f"{'='*70}\n")
    
    return len(issues) == 0

def test_recording(duration=3, gain_factor=1.0):
    """Enregistre un test audio avec un facteur de gain spécifique"""
    print(f"\n🎤 Enregistrement test ({duration}s, gain={gain_factor})...")
    print("Parlez maintenant...")
    
    sample_rate = 16000
    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    
    # Appliquer gain
    audio_data = audio_data * gain_factor
    
    # Clipper pour éviter overflow
    audio_data = np.clip(audio_data, -1.0, 1.0)
    
    # Sauvegarder
    output_dir = Path(__file__).parent.parent / "data" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    output_file = output_dir / f"test_recording_{timestamp}_gain{gain_factor}.wav"
    
    sf.write(output_file, audio_data, sample_rate)
    print(f"✅ Enregistré: {output_file}")
    
    return str(output_file)

def main():
    """Fonction principale"""
    print("="*70)
    print(" "*15 + "DIAGNOSTIC AUDIO QAIA")
    print("="*70)
    
    # 1. Vérifier périphériques
    print("\n1. Périphériques Audio Disponibles:")
    print("-" * 70)
    devices = sd.query_devices()
    print(devices)
    
    default_input = sd.query_devices(kind='input')
    default_output = sd.query_devices(kind='output')
    print(f"\nPériphérique entrée par défaut: {default_input['name']}")
    print(f"Périphérique sortie par défaut: {default_output['name']}")
    
    # 2. Analyser enregistrements récents
    print("\n2. Analyse Enregistrements Récents:")
    print("-" * 70)
    
    audio_dir = Path(__file__).parent.parent / "data" / "audio"
    recent_files = sorted(audio_dir.glob("utt_*.wav"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    
    if recent_files:
        for i, audio_file in enumerate(recent_files, 1):
            metrics = analyze_audio_file(audio_file)
            print_metrics(metrics, f"Enregistrement {i}: {audio_file.name}")
    else:
        print("Aucun enregistrement récent trouvé")
    
    # 3. Test enregistrement avec différents gains
    print("\n3. Test Enregistrement avec Gains Différents:")
    print("-" * 70)
    
    response = input("\nVoulez-vous tester l'enregistrement avec différents gains? (o/N): ")
    if response.lower() == 'o':
        for gain in [0.3, 0.5, 1.0]:
            test_file = test_recording(duration=3, gain_factor=gain)
            metrics = analyze_audio_file(test_file)
            print_metrics(metrics, f"Test avec gain={gain}")
            time.sleep(0.5)
    
    # 4. Recommandations
    print("\n4. Recommandations:")
    print("-" * 70)
    
    if recent_files:
        # Analyser le plus récent
        latest = recent_files[0]
        metrics = analyze_audio_file(latest)
        
        if metrics['clipping_percent'] > 5:
            print("❌ PROBLÈME CRITIQUE: Saturation audio")
            print("\nCauses possibles:")
            print("  1. Gain micro trop élevé dans système")
            print("  2. Distance micro trop proche")
            print("  3. Volume parole trop fort")
            print("\nSolutions:")
            print("  1. Réduire gain système: alsamixer ou pavucontrol")
            print("  2. Ajouter normalisation dans code:")
            print("     audio_data = audio_data * 0.3  # Réduire gain 70%")
            print("  3. Augmenter distance micro-bouche (30-50cm)")
        
        if metrics['rms'] < 0.05:
            print("⚠️ Signal trop faible")
            print("\nSolutions:")
            print("  1. Augmenter gain système")
            print("  2. Rapprocher micro")
            print("  3. Parler plus fort")
    
    print("\n" + "="*70)
    print("Diagnostic terminé")
    print("="*70)

if __name__ == "__main__":
    main()

