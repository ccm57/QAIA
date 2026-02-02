#!/bin/bash
# Script de test rapide QAIA
# Usage: ./test_qaia.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QAIA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$QAIA_ROOT"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          TEST RAPIDE QAIA - Audio & Conversation          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Vérifier volume micro
echo "📊 Vérification configuration audio..."
VOLUME=$(amixer sget Capture | grep -oP '\[\d+%\]' | head -1 | tr -d '[]%')
echo "   Volume microphone: ${VOLUME}%"

if [ "$VOLUME" -gt 40 ]; then
    echo "   ⚠️  Volume élevé (>${VOLUME}%) - risque saturation"
    echo "   Réduction automatique à 30%..."
    amixer set Capture 30% > /dev/null
    echo "   ✅ Volume réduit à 30%"
elif [ "$VOLUME" -lt 20 ]; then
    echo "   ⚠️  Volume faible (<${VOLUME}%) - risque audio trop faible"
    echo "   Augmentation automatique à 30%..."
    amixer set Capture 30% > /dev/null
    echo "   ✅ Volume ajusté à 30%"
else
    echo "   ✅ Volume correct (${VOLUME}%)"
fi

# Nettoyer cache Python
echo ""
echo "🧹 Nettoyage cache Python..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Cache nettoyé"

# Vérifier derniers fichiers audio
echo ""
echo "📁 Derniers fichiers audio:"
if [ -d "data/audio" ]; then
    ls -lht data/audio/utt_*.wav 2>/dev/null | head -3 | awk '{print "   " $9 " (" $5 ")"}'
else
    echo "   Aucun fichier audio trouvé"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    INSTRUCTIONS TEST                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Lancer QAIA:"
echo "   python3 launcher.py"
echo ""
echo "2️⃣  PREMIÈRE QUESTION:"
echo "   • Maintenez 🎙 Parler"
echo "   • Dites: \"Bonjour QAIA, comment vas-tu ?\""
echo "   • Relâchez le bouton"
echo "   • Attendez la réponse"
echo ""
echo "3️⃣  DEUXIÈME QUESTION (test critique):"
echo "   • Maintenez 🎙 Parler"
echo "   • Dites: \"Quelle est la météo aujourd'hui ?\""
echo "   • Relâchez le bouton"
echo "   • Vérifiez: PAS de blocage"
echo ""
echo "4️⃣  ANALYSE POST-TEST:"
echo "   python3 $SCRIPT_DIR/test_audio_pipeline.py"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  RÉSULTATS ATTENDUS                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Audio non saturé (clipping < 5%)"
echo "✅ Transcription précise"
echo "✅ Réponse fluide"
echo "✅ PAS de blocage à la 2ème question"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   COMMANDES UTILES                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "# Analyser dernier audio"
echo "python3 -c 'import scipy.io.wavfile as w, numpy as n; from pathlib import Path; f=sorted(Path(\"data/audio\").glob(\"utt_*.wav\"), key=lambda x: x.stat().st_mtime)[-1]; s,d=w.read(str(f)); print(f\"Fichier: {f.name}\"); print(f\"RMS: {n.sqrt(n.mean(d**2)):.0f}\"); print(f\"Clipping: {(n.abs(d)>=32767).sum()/len(d)*100:.1f}%\")'"
echo ""
echo "# Voir logs système"
echo "tail -100 logs/system.log"
echo ""
echo "# Ajuster volume micro"
echo "amixer set Capture 30%"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "Prêt pour le test! Lancez: python3 launcher.py"
echo "════════════════════════════════════════════════════════════"

