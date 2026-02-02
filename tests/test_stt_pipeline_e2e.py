#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Test de bout en bout du pipeline vocal : WAV → STT → normalisation → intention.

Valide la chaîne complète avant de considérer les commandes vocales comme fiables.
Peut être exécuté avec un fichier WAV réel (variable QAIA_STT_E2E_WAV) ou avec
un fichier de test minimal (silence) généré à la volée.
"""

# /// script
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///

import os
import sys
import tempfile
import wave
from pathlib import Path

import pytest

# Racine projet pour imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.stt_text_processor import normalize_stt_text
from agents.intent_detector import IntentDetector, Intent


def _creer_wav_silence(duration_sec: float = 0.5, sample_rate: int = 16000) -> str:
    """Crée un fichier WAV de silence pour test sans dépendance à un enregistrement réel."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    avec = wave.open(path, "wb")
    avec.setnchannels(1)
    avec.setsampwidth(2)
    avec.setframerate(sample_rate)
    n = int(duration_sec * sample_rate)
    avec.writeframes(b"\x00\x00" * n)
    avec.close()
    return path


@pytest.fixture(scope="module")
def wav_path():
    """
    Chemin vers un WAV pour le test E2E.
    Si QAIA_STT_E2E_WAV est défini et pointe vers un fichier existant, l'utilise.
    Sinon crée un court WAV de silence (le STT peut retourner une chaîne vide ou du bruit).
    """
    env_path = os.environ.get("QAIA_STT_E2E_WAV")
    if env_path and Path(env_path).exists():
        return env_path
    path = _creer_wav_silence(0.5)
    yield path
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


@pytest.mark.slow
def test_pipeline_stt_normalize_intent(wav_path):
    """
    Enchaîne : transcription WAV → normalisation → détection d'intention.
    Vérifie que chaque étape retourne les types attendus et que la chaîne ne lève pas.
    """
    from agents.wav2vec_agent import Wav2VecVoiceAgent

    # 1) STT
    agent = Wav2VecVoiceAgent()
    text, confidence = agent.transcribe_audio(wav_path)
    assert isinstance(text, str), "STT doit retourner un texte (str)"
    assert isinstance(confidence, (int, float)), "STT doit retourner un score de confiance"

    # 2) Normalisation
    normalized = normalize_stt_text(text)
    assert isinstance(normalized, str), "normalize_stt_text doit retourner un str"

    # 3) Intention (sur le texte normalisé, ou original si vide)
    to_analyze = normalized.strip() or text.strip() or "bonjour"
    detector = IntentDetector()
    result = detector.detect(to_analyze)
    assert result is not None
    assert hasattr(result, "intent") and hasattr(result, "confidence")
    assert result.intent in Intent

    # Cohérence : confiance STT entre 0 et 1 (ou très proche)
    assert 0 <= confidence <= 1.5, "Confiance STT typiquement dans [0, 1]"


def test_normalize_et_intent_sans_wav():
    """
    Sans fichier WAV : vérifie uniquement normalisation + intention sur texte simulé.
    Permet de valider la chaîne texte → normalisation → intention sans charger le modèle STT.
    """
    detector = IntentDetector()

    # Texte brut simulé (comme sortie STT typique)
    text_brut = "bonjour caya qu est ce que tu peux faire"
    normalized = normalize_stt_text(text_brut)
    assert isinstance(normalized, str)
    assert "QAIA" in normalized or "caya" in normalized.lower() or "bonjour" in normalized.lower()

    result = detector.detect(normalized)
    assert result is not None
    assert result.intent in Intent
