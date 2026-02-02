#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Script de lancement QAIA - Version professionnelle
# Généré automatiquement le jeu. 11 déc. 2025 16:33:12 CET
# ═══════════════════════════════════════════════════════════════

# Chemins absolus (garantis de fonctionner)
QAIA_DIR="/media/ccm57/SSDIA/QAIA"
PYTHON="/home/ccm57/.pyenv/versions/qaia-env/bin/python"

# Validation
if [ ! -d "$QAIA_DIR" ]; then
    echo "❌ ERREUR: Répertoire QAIA introuvable"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "❌ ERREUR: Python introuvable: $PYTHON"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Changement répertoire de travail
cd "$QAIA_DIR" || {
    echo "❌ ERREUR: Impossible d'accéder à $QAIA_DIR"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
}

# Configuration environnement
export PYTHONPATH="$QAIA_DIR:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# Bannière
clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       QAIA - Phi-3-mini (4K Context) + Piper TTS          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Répertoire: $QAIA_DIR"
echo "Python: $PYTHON"
echo "Version: $($PYTHON --version)"
echo ""
echo "Initialisation en cours..."
echo ""

# Lancement QAIA
"$PYTHON" launcher.py

# Gestion code de sortie
EXIT_CODE=$?
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  QAIA terminé normalement                                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
else
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  ERREUR DÉTECTÉE                                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Code de sortie: $EXIT_CODE"
    echo ""
    echo "Appuyez sur Entrée pour fermer..."
    read
fi

exit $EXIT_CODE
