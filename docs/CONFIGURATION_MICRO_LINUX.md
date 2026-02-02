# Configuration du Micro pour Linux Mint - Guide Complet

**Date** : 2025-12-22  
**Problème** : Saturation micro (~80% clipping) causant des transcriptions STT de mauvaise qualité  
**Solution** : Ajustement du gain d'entrée micro via `pavucontrol` ou `alsamixer`

---

## 📋 Diagnostic Actuel

Les logs QAIA montrent actuellement :
- **RMS** : ~1.45 (trop élevé, idéal : 0.1-0.3)
- **Peak** : ~1.76 (saturation maximale)
- **Clipping** : ~80% (très élevé, idéal : < 5%)
- **Qualité** : ⚠️ Trop fort (risque saturation)

---

## 🎯 Objectif

Réduire le gain d'entrée micro pour obtenir :
- **RMS** : 0.1-0.3 (signal audible mais non saturé)
- **Clipping** : < 5% (signal propre)
- **Qualité** : ✅ Niveau correct

---

## 🔧 Méthode 1 : pavucontrol (Interface Graphique - Recommandée)

### Installation

```bash
sudo apt update
sudo apt install pavucontrol
```

### Configuration

1. **Lancer pavucontrol** :
   ```bash
   pavucontrol
   ```

2. **Onglet "Input Devices"** :
   - Sélectionner votre micro dans la liste
   - Vérifier que le micro n'est pas **muet** (icône 🔊 doit être visible)
   - **Réduire le volume d'entrée** à **30-50%** (glisser le curseur vers la gauche)
   - Vérifier que le niveau ne dépasse pas **50%** dans la barre de niveau

3. **Onglet "Configuration"** :
   - Sélectionner votre carte son
   - Vérifier que le profil est correct (ex: "Analog Stereo Input")

4. **Tester** :
   - Parler normalement dans le micro
   - Observer la barre de niveau : elle ne doit **jamais** atteindre 100% (rouge)
   - Si elle atteint 100%, réduire encore le volume d'entrée

5. **Sauvegarder** :
   - Les paramètres sont sauvegardés automatiquement
   - Redémarrer QAIA pour appliquer les changements

---

## 🔧 Méthode 2 : alsamixer (Ligne de Commande)

### Installation

```bash
sudo apt install alsa-utils
```

### Configuration

1. **Lister les cartes audio** :
   ```bash
   arecord -l
   ```
   Notez le numéro de votre carte (ex: `card 0`)

2. **Ouvrir alsamixer** :
   ```bash
   alsamixer
   ```
   - Appuyer sur `F4` pour passer en mode "Capture"
   - Utiliser les flèches `←` et `→` pour naviguer
   - Utiliser les flèches `↑` et `↓` pour ajuster le volume

3. **Ajuster le gain d'entrée** :
   - Trouver "Capture" ou "Mic" dans la liste
   - Réduire le niveau à **30-50%** (utiliser `↓`)
   - Appuyer sur `M` pour activer/désactiver le micro (doit être activé)

4. **Sauvegarder** :
   ```bash
   sudo alsactl store
   ```

---

## 🔧 Méthode 3 : Script de Configuration Automatique

Un script Python est disponible dans `scripts/configure_micro_linux.py` pour :
- Diagnostiquer le niveau actuel
- Ajuster automatiquement le gain via `pactl`
- Vérifier que les changements sont appliqués

### Utilisation

```bash
cd /media/ccm57/SSDIA/QAIA
python scripts/configure_micro_linux.py --target-rms 0.2 --auto-adjust
```

---

## 📊 Vérification des Paramètres

### Via pavucontrol

1. Ouvrir `pavucontrol`
2. Onglet "Input Devices"
3. Parler dans le micro
4. Observer la barre de niveau : elle doit rester **en dessous de 50%** (vert/jaune, jamais rouge)

### Via QAIA

1. Lancer QAIA
2. Vérifier les logs au démarrage :
   ```
   Diagnostics micro natif: {
       'rms': 0.15-0.30,  # ✅ Bon niveau
       'peak': 0.5-0.8,   # ✅ Pas de saturation
       'clipping_percent': < 5%,  # ✅ Signal propre
       'quality': '✅ Niveau correct'
   }
   ```

### Via commande terminal

```bash
# Enregistrer 2 secondes de test
arecord -d 2 -f cd test_micro.wav

# Analyser avec sox (si installé)
sox test_micro.wav -n stat
```

---

## 🎚️ Niveaux Recommandés

| Paramètre | Valeur Actuelle | Valeur Cible | Commentaire |
|-----------|----------------|--------------|-------------|
| **RMS** | ~1.45 | 0.1-0.3 | Signal audible mais non saturé |
| **Peak** | ~1.76 | 0.5-0.8 | Pas de saturation |
| **Clipping %** | ~80% | < 5% | Signal propre |
| **Volume d'entrée** | 100% | 30-50% | Ajuster selon votre micro |

---

## 🔍 Dépannage

### Le micro ne fonctionne pas après ajustement

1. Vérifier que le micro n'est pas muet dans `pavucontrol`
2. Vérifier que le profil audio est correct (onglet "Configuration")
3. Tester avec `arecord -d 2 -f cd test.wav && aplay test.wav`

### Le niveau est toujours trop élevé

1. Réduire encore le volume d'entrée (jusqu'à 20-30%)
2. Vérifier s'il y a un gain matériel sur le micro (bouton physique)
3. Vérifier la distance au micro (parler à 20-30 cm)

### Le niveau est trop faible

1. Augmenter légèrement le volume d'entrée (50-60%)
2. Vérifier que le micro n'est pas muet
3. Vérifier la distance au micro (parler plus près, 10-15 cm)

---

## 📝 Notes Importantes

- **Les paramètres sont sauvegardés automatiquement** dans `pavucontrol`
- **Redémarrer QAIA** après modification pour que les changements soient pris en compte
- **Tester régulièrement** : les paramètres peuvent être réinitialisés après une mise à jour système
- **Distance optimale** : 20-30 cm du micro pour une qualité optimale

---

## 🔗 Références

- [Documentation PulseAudio](https://www.freedesktop.org/wiki/Software/PulseAudio/)
- [Documentation ALSA](https://www.alsa-project.org/wiki/Documentation)
- [Guide Linux Mint Audio](https://linuxmint.com/documentation.php)

---

**Dernière mise à jour** : 2025-12-22  
**Auteur** : Guide généré automatiquement pour QAIA

