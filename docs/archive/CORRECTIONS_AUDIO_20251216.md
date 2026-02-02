# Corrections Audio - 16 Décembre 2025

## Problème Initial

**Symptômes:**
- Blocage à la deuxième question en mode conversation
- QAIA ne comprend pas les paroles
- Trois couleurs de texte dans l'interface (vert, bleu, noir)

**Diagnostic:**
1. ❌ Audio complètement saturé (26.6% clipping)
2. ❌ Volume microphone trop élevé (80%)
3. ❌ Pas de réduction de gain dans le code
4. ❌ Cache Python (.pyc) empêchait les modifications d'être appliquées

## Analyse Technique

### Fichier Audio Analysé
```
Fichier: utt_1765874651196.wav
Durée: 7.02s
RMS (int16): 18496
RMS (float): 0.564
Clipping: 29,893 samples (26.6%)
Max absolu: 32767
```

**Problème:** 26.6% de clipping = audio complètement distordu → transcription impossible

### Prétraitement Audio
Le prétraitement dans `wav2vec_agent.py` applique:
1. Filtrage passe-haut (80Hz) pour éliminer bruit basse fréquence
2. Normalisation RMS cible (0.15) avec gain limité (0.5-3.0x)
3. Clipping soft pour éviter distorsion

**Résultat:** RMS 0.564 → 0.214 (réduction efficace)

## Corrections Appliquées

### 1. Réduction Volume Microphone
```bash
amixer set Capture 30%
```
**Avant:** 80% → **Après:** 30%

### 2. Réduction Gain Audio (interface/qaia_interface.py)

**Avant (ligne 616-619):**
```python
audio = np.concatenate(frames_list, axis=0)
# Conversion float32 -> int16
audio_int16 = np.clip(audio[:, 0] if audio.ndim > 1 else audio, -1.0, 1.0)
audio_int16 = (audio_int16 * 32767.0).astype(np.int16)
```

**Après:**
```python
audio = np.concatenate(frames_list, axis=0)
# Conversion float32 -> int16 avec GAIN RÉDUIT (0.3 = -10dB)
audio_mono = audio[:, 0] if audio.ndim > 1 else audio
audio_normalized = np.clip(audio_mono * 0.3, -1.0, 1.0)  # GAIN 30% pour éviter saturation
audio_int16 = (audio_normalized * 32767.0).astype(np.int16)
```

**Impact:** Réduction de -10dB du signal audio avant sauvegarde

### 3. Nettoyage Cache Python
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

**Raison:** Les modifications de code n'étaient pas prises en compte car Python utilisait les fichiers `.pyc` en cache.

### 4. Script de Test Créé

**Fichier:** `scripts/test_audio_pipeline.py`

**Fonctionnalités:**
- Analyse qualité audio (RMS, clipping, silence)
- Test prétraitement audio
- Test transcription complète
- Recommandations automatiques

**Usage:**
```bash
python3 scripts/test_audio_pipeline.py
```

## Résultats Attendus

### Avant Corrections
```
RMS (int16):     18496
Clipping:        26.6%
Transcription:   Imprécise ("voir quel marmah suis clode")
```

### Après Corrections (attendu)
```
RMS (int16):     < 10000
Clipping:        < 5%
Transcription:   Précise et fluide
```

## Explication des Couleurs de Texte

Les trois couleurs observées sont **NORMALES** et correspondent aux niveaux de log:

- **Vert:** INFO (informations normales)
- **Bleu:** WARNING (avertissements)
- **Noir:** ERROR (erreurs)

Ce n'est pas un bug, c'est la coloration syntaxique des logs.

## Test de Validation

### Procédure
1. Lancer QAIA: `python3 launcher.py`
2. Première question: "Bonjour QAIA, comment vas-tu ?"
3. Attendre réponse
4. **Deuxième question (test critique):** "Quelle est la météo ?"
5. Vérifier: pas de blocage, transcription correcte

### Analyse Post-Test
```bash
# Analyser le dernier fichier audio
python3 scripts/test_audio_pipeline.py

# Vérifier les logs si problème
tail -100 logs/system.log
```

## Architecture Audio Complète

```
Microphone (30%)
    ↓
sounddevice.InputStream
    ↓
interface/qaia_interface.py
    ├─ Capture frames audio (float32)
    ├─ Gain 0.3 (réduction -10dB)
    ├─ Clip [-1.0, 1.0]
    └─ Conversion int16 → fichier WAV
         ↓
agents/wav2vec_agent.py
    ├─ Lecture WAV
    ├─ Prétraitement:
    │   ├─ Filtrage passe-haut (80Hz)
    │   ├─ Normalisation RMS (target=0.15)
    │   └─ Clipping soft
    └─ Transcription Wav2Vec2
         ↓
Texte transcrit
```

## Fichiers Modifiés

1. **interface/qaia_interface.py** (ligne 616-619)
   - Ajout gain 0.3 avant conversion int16

2. **scripts/test_audio_pipeline.py** (nouveau)
   - Script de diagnostic complet

## Commandes Utiles

```bash
# Vérifier volume micro
amixer sget Capture

# Réduire volume micro
amixer set Capture 30%

# Nettoyer cache Python
find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} +

# Tester pipeline audio
python3 scripts/test_audio_pipeline.py

# Analyser dernier fichier audio
python3 -c "
import scipy.io.wavfile as w, numpy as n
from pathlib import Path
f = sorted(Path('data/audio').glob('utt_*.wav'), key=lambda x: x.stat().st_mtime)[-1]
s, d = w.read(str(f))
print(f'Fichier: {f.name}')
print(f'RMS: {n.sqrt(n.mean(d**2)):.0f}')
print(f'Clipping: {(n.abs(d)>=32767).sum()/len(d)*100:.1f}%')
"

# Logs système
tail -100 logs/system.log
```

## Notes Importantes

1. **Volume Micro:** Ne pas dépasser 40% pour éviter saturation
2. **Gain Audio:** Le gain 0.3 est un compromis entre qualité et protection contre saturation
3. **Prétraitement:** Le prétraitement peut amplifier jusqu'à 3x, d'où l'importance du gain initial
4. **Cache Python:** Toujours nettoyer après modifications de code
5. **Tests:** Utiliser `test_audio_pipeline.py` pour valider chaque changement

## Prochaines Étapes

1. ✅ Corrections appliquées
2. ⏳ Test utilisateur avec nouveau fichier audio
3. ⏳ Validation absence de blocage à la 2ème question
4. ⏳ Analyse qualité transcription
5. ⏳ Ajustements fins si nécessaire

---

**Date:** 16 Décembre 2025  
**Version:** QAIA 1.0  
**Statut:** En attente de validation utilisateur

