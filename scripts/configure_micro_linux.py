#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de configuration automatique du micro pour Linux Mint
Aide à ajuster le gain d'entrée pour éviter la saturation STT

Usage:
    python scripts/configure_micro_linux.py --diagnostic
    python scripts/configure_micro_linux.py --target-rms 0.2 --auto-adjust
    python scripts/configure_micro_linux.py --set-volume 40
"""

# /// script
# dependencies = [
#   "sounddevice>=0.4.5",
#   "numpy>=1.22.0"
# ]
# ///

import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("❌ Erreur: sounddevice et numpy sont requis.")
    print("   Installation: pip install sounddevice numpy")
    sys.exit(1)


def get_audio_metrics(duration: float = 1.0, sample_rate: int = 44100) -> dict:
    """
    Enregistre un échantillon audio et calcule les métriques.
    
    Args:
        duration: Durée de l'enregistrement en secondes
        sample_rate: Fréquence d'échantillonnage
        
    Returns:
        Dict avec métriques (rms, peak, clipping_count, clipping_percent, quality)
    """
    try:
        print(f"🎤 Enregistrement de {duration}s... (parlez normalement)")
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        
        audio = audio.flatten()
        
        # Calculer métriques
        rms = float(np.sqrt(np.mean(audio**2)))
        peak = float(np.abs(audio).max())
        clipping_count = int(np.sum(np.abs(audio) >= 0.95))
        clipping_percent = (clipping_count / len(audio)) * 100
        
        # Qualité
        if clipping_percent > 50:
            quality = "🔴 Très saturé (réduire fortement)"
        elif clipping_percent > 20:
            quality = "⚠️ Trop fort (réduire)"
        elif clipping_percent > 5:
            quality = "🟡 Légèrement fort (réduire un peu)"
        elif rms > 0.3:
            quality = "🟡 Niveau correct mais peut être réduit"
        elif rms < 0.05:
            quality = "🔵 Trop faible (augmenter)"
        else:
            quality = "✅ Niveau correct"
        
        return {
            'rms': rms,
            'peak': peak,
            'clipping_count': clipping_count,
            'clipping_percent': clipping_percent,
            'quality': quality,
            'status': 'ok' if clipping_percent < 5 and 0.05 < rms < 0.3 else 'adjust'
        }
    except Exception as e:
        return {
            'rms': 0.0,
            'peak': 0.0,
            'clipping_count': 0,
            'clipping_percent': 0.0,
            'quality': f"❌ Erreur: {e}",
            'status': 'error'
        }


def get_pactl_sources():
    """Récupère la liste des sources audio (micros) via pactl."""
    try:
        result = subprocess.run(
            ['pactl', 'list', 'short', 'sources'],
            capture_output=True,
            text=True,
            check=True
        )
        sources = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    sources.append({
                        'index': parts[0],
                        'name': parts[1],
                        'description': parts[-1] if len(parts) > 2 else parts[1]
                    })
        return sources
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def get_source_volume(source_name: str) -> float:
    """Récupère le volume actuel d'une source (0-100%)."""
    try:
        result = subprocess.run(
            ['pactl', 'get-source-volume', source_name],
            capture_output=True,
            text=True,
            check=True
        )
        # Format: "Volume: front-left: 65536 / 100% / 0.00 dB"
        for line in result.stdout.split('\n'):
            if 'front-left:' in line or 'mono:' in line:
                parts = line.split('/')
                if len(parts) >= 2:
                    percent_str = parts[1].strip().replace('%', '')
                    return float(percent_str)
        return 100.0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 100.0


def set_source_volume(source_name: str, volume_percent: float) -> bool:
    """
    Définit le volume d'une source (0-100%).
    
    Args:
        source_name: Nom de la source (ex: "alsa_input.pci-0000_00_1f.3.analog-stereo")
        volume_percent: Volume en pourcentage (0-100)
        
    Returns:
        True si succès, False sinon
    """
    try:
        volume = int(volume_percent)
        subprocess.run(
            ['pactl', 'set-source-volume', source_name, f'{volume}%'],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def diagnostic():
    """Affiche un diagnostic complet du micro."""
    print("=" * 60)
    print("🔍 DIAGNOSTIC MICRO LINUX MINT")
    print("=" * 60)
    
    # Lister les sources
    sources = get_pactl_sources()
    if not sources:
        print("❌ Aucune source audio trouvée (pactl non disponible?)")
        print("   Essayez: sudo apt install pulseaudio-utils")
        return
    
    print(f"\n📋 Sources audio disponibles ({len(sources)}):")
    for i, source in enumerate(sources):
        volume = get_source_volume(source['name'])
        print(f"  {i+1}. {source['description']}")
        print(f"     Nom: {source['name']}")
        print(f"     Volume actuel: {volume:.0f}%")
    
    # Source par défaut
    try:
        result = subprocess.run(
            ['pactl', 'get-default-source'],
            capture_output=True,
            text=True,
            check=True
        )
        default_source = result.stdout.strip()
        print(f"\n🎤 Source par défaut: {default_source}")
    except:
        default_source = sources[0]['name'] if sources else None
    
    # Métriques audio
    print("\n📊 Métriques audio actuelles:")
    metrics = get_audio_metrics(duration=2.0)
    print(f"  RMS: {metrics['rms']:.3f}")
    print(f"  Peak: {metrics['peak']:.3f}")
    print(f"  Clipping: {metrics['clipping_count']} échantillons ({metrics['clipping_percent']:.1f}%)")
    print(f"  Qualité: {metrics['quality']}")
    
    # Recommandations
    print("\n💡 Recommandations:")
    if metrics['clipping_percent'] > 5:
        current_vol = get_source_volume(default_source) if default_source else 100
        target_vol = max(20, current_vol * (0.3 / metrics['rms']))
        target_vol = min(60, target_vol)  # Limiter à 60%
        print(f"  ⚠️  Réduire le volume d'entrée à {target_vol:.0f}%")
        print(f"     Commande: python {sys.argv[0]} --set-volume {target_vol:.0f}")
    elif metrics['rms'] < 0.05:
        current_vol = get_source_volume(default_source) if default_source else 100
        target_vol = min(80, current_vol * (0.2 / metrics['rms']))
        print(f"  ⚠️  Augmenter le volume d'entrée à {target_vol:.0f}%")
        print(f"     Commande: python {sys.argv[0]} --set-volume {target_vol:.0f}")
    else:
        print("  ✅ Niveau correct, aucun ajustement nécessaire")
    
    print("\n" + "=" * 60)


def auto_adjust(target_rms: float = 0.2, max_iterations: int = 5):
    """
    Ajuste automatiquement le volume pour atteindre un RMS cible.
    
    Args:
        target_rms: RMS cible (0.1-0.3 recommandé)
        max_iterations: Nombre maximum d'itérations
    """
    print("=" * 60)
    print("🔧 AJUSTEMENT AUTOMATIQUE DU MICRO")
    print("=" * 60)
    
    # Récupérer source par défaut
    try:
        result = subprocess.run(
            ['pactl', 'get-default-source'],
            capture_output=True,
            text=True,
            check=True
        )
        default_source = result.stdout.strip()
    except:
        print("❌ Impossible de récupérer la source par défaut")
        return
    
    current_vol = get_source_volume(default_source)
    print(f"🎤 Source: {default_source}")
    print(f"📊 Volume actuel: {current_vol:.0f}%")
    print(f"🎯 RMS cible: {target_rms:.3f}")
    print()
    
    for iteration in range(max_iterations):
        print(f"Iteration {iteration + 1}/{max_iterations}...")
        
        # Mesurer métriques
        metrics = get_audio_metrics(duration=2.0)
        current_rms = metrics['rms']
        
        print(f"  RMS actuel: {current_rms:.3f} (cible: {target_rms:.3f})")
        print(f"  Clipping: {metrics['clipping_percent']:.1f}%")
        print(f"  Qualité: {metrics['quality']}")
        
        # Vérifier si on est proche de la cible
        if abs(current_rms - target_rms) < 0.05 and metrics['clipping_percent'] < 5:
            print("\n✅ Niveau optimal atteint !")
            break
        
        # Calculer nouveau volume
        if current_rms > 0.01:
            ratio = target_rms / current_rms
            new_vol = current_vol * ratio
            new_vol = max(20, min(80, new_vol))  # Limiter entre 20% et 80%
        else:
            new_vol = min(80, current_vol * 1.5)  # Augmenter si signal trop faible
        
        if abs(new_vol - current_vol) < 1:
            print("  ⚠️  Ajustement minimal, arrêt")
            break
        
        print(f"  🔧 Ajustement: {current_vol:.0f}% → {new_vol:.0f}%")
        set_source_volume(default_source, new_vol)
        current_vol = new_vol
        
        time.sleep(1)  # Attendre stabilisation
    
    print("\n📊 Résultat final:")
    final_metrics = get_audio_metrics(duration=2.0)
    print(f"  RMS: {final_metrics['rms']:.3f}")
    print(f"  Clipping: {final_metrics['clipping_percent']:.1f}%")
    print(f"  Qualité: {final_metrics['quality']}")
    print(f"  Volume: {get_source_volume(default_source):.0f}%")
    print("\n" + "=" * 60)


def set_volume(volume_percent: float):
    """Définit le volume d'entrée manuellement."""
    try:
        result = subprocess.run(
            ['pactl', 'get-default-source'],
            capture_output=True,
            text=True,
            check=True
        )
        default_source = result.stdout.strip()
    except:
        print("❌ Impossible de récupérer la source par défaut")
        return
    
    if set_source_volume(default_source, volume_percent):
        print(f"✅ Volume défini à {volume_percent:.0f}%")
        print("\n📊 Vérification...")
        time.sleep(1)
        metrics = get_audio_metrics(duration=2.0)
        print(f"  RMS: {metrics['rms']:.3f}")
        print(f"  Clipping: {metrics['clipping_percent']:.1f}%")
        print(f"  Qualité: {metrics['quality']}")
    else:
        print("❌ Erreur lors de la définition du volume")


def main():
    parser = argparse.ArgumentParser(
        description="Configuration automatique du micro pour Linux Mint"
    )
    parser.add_argument(
        '--diagnostic',
        action='store_true',
        help='Affiche un diagnostic complet du micro'
    )
    parser.add_argument(
        '--auto-adjust',
        action='store_true',
        help='Ajuste automatiquement le volume pour atteindre un RMS cible'
    )
    parser.add_argument(
        '--target-rms',
        type=float,
        default=0.2,
        help='RMS cible pour auto-adjust (défaut: 0.2)'
    )
    parser.add_argument(
        '--set-volume',
        type=float,
        help='Définit le volume d\'entrée manuellement (0-100%%)'
    )
    
    args = parser.parse_args()
    
    if args.set_volume is not None:
        set_volume(args.set_volume)
    elif args.auto_adjust:
        auto_adjust(args.target_rms)
    else:
        diagnostic()


if __name__ == '__main__':
    main()

