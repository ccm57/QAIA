#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Configuration QAIA Production - Optimisée Stabilité Maximale
Matériel: i7-7700HQ + GTX 1050 2GB + 40GB RAM
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
# ]
# ///

from pathlib import Path
import torch
import logging
import os


def charger_env_fichier(env_path: Path) -> None:
    """
    Charge un fichier .env minimal sans dépendance externe.

    Args:
        env_path (Path): Chemin du fichier .env à charger.
    """
    try:
        if not env_path.exists():
            return
        contenu = env_path.read_text(encoding="utf-8").splitlines()
        for ligne in contenu:
            brute = ligne.strip()
            if not brute or brute.startswith("#") or "=" not in brute:
                continue
            cle, valeur = brute.split("=", 1)
            cle = cle.strip()
            valeur = valeur.strip().strip('"').strip("'")
            if cle and cle not in os.environ:
                os.environ[cle] = valeur
    except Exception:
        # Ne pas interrompre l'initialisation si le .env est invalide
        return

# ═══════════════════════════════════════════════════════════
# CHEMINS SYSTÈME
# ═══════════════════════════════════════════════════════════
BASEDIR = Path(__file__).parent.parent
PLATFORM = "linux"

QAIA_ROOT = BASEDIR
# Charger le .env si présent (priorité aux variables déjà définies)
charger_env_fichier(QAIA_ROOT / ".env")

MODELS_DIR = Path(os.environ.get("QAIA_MODELS_DIR", QAIA_ROOT / "models"))
DATA_DIR = Path(os.environ.get("QAIA_DATA_DIR", QAIA_ROOT / "data"))
LOGS_DIR = Path(os.environ.get("QAIA_LOGS_DIR", QAIA_ROOT / "logs"))
CONFIG_DIR = Path(os.environ.get("QAIA_CONFIG_DIR", QAIA_ROOT / "config"))
VECTOR_DB_DIR = Path(os.environ.get("QAIA_VECTOR_DB_DIR", DATA_DIR / "vector_db"))
VOICE_PROFILES_DIR = DATA_DIR / "voice_profiles"
AUDIO_DIR = DATA_DIR / "audio"

# Clé de sécurité (fournie via variables d'environnement uniquement)
SECURITY_KEY = os.environ.get("QAIA_SECURITY_KEY")

for directory in [MODELS_DIR, DATA_DIR, LOGS_DIR, VECTOR_DB_DIR, VOICE_PROFILES_DIR, AUDIO_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# DÉTECTION MATÉRIEL
# ═══════════════════════════════════════════════════════════
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_AVAILABLE = torch.cuda.is_available()
CPU_THREADS = 6  # Optimal i7-7700HQ (4 cores + 2 HT)
GPU_LAYERS = 0   # ZÉRO risque crash VRAM

# ═══════════════════════════════════════════════════════════
# RESSOURCES DÉDIÉES PHI-3-MINI
# ═══════════════════════════════════════════════════════════
PHI3_RESOURCES = {
    "ram_limit_gb": 12,          # RAM max dédiée au modèle (sur 40GB total)
    "cpu_threads": CPU_THREADS,  # 6 threads i7-7700HQ
    "cpu_affinity": None,        # None = auto, ou liste cores [0,1,2,3,4,5]
    "memory_map": True,          # Memory mapping pour efficacité
    "lock_memory": False,        # Éviter swap (False pour flexibilité)
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION LLM - PHI-3-MINI 3.8B
# ═══════════════════════════════════════════════════════════
MODEL_CONFIG = {
    "llm": {
        "provider": "llama-cpp",
        "model_path": str(MODELS_DIR / "Phi-3-mini-4k-instruct-q4.gguf"),
        
        # Context Window: Phi-3 natif 4K, utilisé 2K pour conversation
        "n_ctx": 2048,               # 2K tokens suffisant pour conversation
        
        # CPU Configuration
        "n_threads": PHI3_RESOURCES["cpu_threads"],  # 6 threads optimal
        "n_batch": 512,              # Batch parallèle maintenu
        
        # GPU Configuration (DÉSACTIVÉ pour stabilité)
        "n_gpu_layers": GPU_LAYERS,  # 0 = CPU only, zéro risque
        
        # Paramètres génération optimisés Phi-3 (TODO-8)
        "temperature": 0.5,          # Réduit de 0.6 à 0.5 pour moins d'hallucinations
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.15,      # Augmenté de 1.1 à 1.15 pour éviter répétitions
        "max_tokens": 512,           # Réponses complètes pour le français (augmenté de 256 à 512)
        
        "verbose": False,
    },
    # ═══════════════════════════════════════════════════════════
    # PROMPT SYSTÈME QAIA - Version 2.2.0 (18 Décembre 2025)
    # Style: français professionnel, sans sources/liens sauf demande explicite
    # ═══════════════════════════════════════════════════════════
    "system_prompt": {
        "identity": (
            "Tu es une assistante multimodale intelligente et de qualité nommée QAIA, "
            "spécialisée pour un usage personnel sur le poste de l'utilisateur."
        ),
        "mission": (
            "Ton rôle est d'informer, conseiller, protéger et sécuriser les démarches "
            "de l'utilisateur contre les attaques extérieures. Tu t'appuies sur le texte, "
            "l'audio, la vidéo et, si nécessaire, sur des ressources externes, pour enrichir "
            "ton savoir sans jamais mettre l'utilisateur en danger."
        ),
        "core_principles": [
            "Toujours être honnête et factuelle.",
            "Ne pas inventer de faits : si tu ne sais pas, réponds clairement « Je ne sais pas ».",
            "Ne pas dramatiser ni moraliser : rester neutre, professionnel et bienveillant.",
            "Adapter ton vocabulaire au niveau apparent de l'utilisateur (simple et clair par défaut).",
            "Répondre en français correct, avec des phrases complètes et lisibles.",
            "NE PAS citer de sources, de liens ou de références EXTERNES sauf si l'utilisateur le demande explicitement.",
        ],
        "verification": (
            "Avant de répondre, vérifie mentalement : "
            "« Ai-je répondu clairement à la question de l'utilisateur, sans inventer, "
            "et sans ajouter de détails inutiles ? »."
        ),
        "style": {
            "tone": "professionnel, courtois, calme",
            "language": "français",
            "format": (
                "réponses courtes mais complètes, structurées si nécessaire "
                "(listes simples, explications étape par étape)."
            ),
            "adaptability": (
                "si l'utilisateur demande des détails techniques, tu peux approfondir, "
                "sinon reste synthétique."
            ),
        },
        "greeting": (
            "Bonjour, je suis QAIA, ton assistante multimodale. "
            "Que puis-je faire pour toi aujourd'hui ?"
        ),
    },
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION STT - WAV2VEC2
    # ═══════════════════════════════════════════════════════════
    "speech": {
        "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-french",
        "model_path": str(MODELS_DIR / "wav2vec2-large-xlsr-53-french"),
        "sampling_rate": 16000,
        "device": "cpu",              # GPU réservé LLM (si activé)
        "chunk_length_s": 10,
        "stride_length_s": 2,
        "confidence_threshold_low": 0.4,  # En dessous : suggestion « répétez » (affichage optionnel)
    },
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION GPU AUDIO (optionnel, moyen terme)
    # ═══════════════════════════════════════════════════════════
    # Flags pour activer l'utilisation GPU pour les modèles audio
    # Désactivés par défaut (CPU uniquement)
    # Si torch.cuda.is_available() == False, fallback CPU silencieux
    "gpu_audio": {
        "USE_GPU_FOR_STT": False,              # Activer GPU pour STT (Wav2Vec2)
        "USE_GPU_FOR_SPEAKER_AUTH": False,     # Activer GPU pour speaker_auth (Wav2Vec2 embeddings)
        # Note: Avec 2 Go VRAM (GTX 1050), activer un seul modèle audio à la fois
        # Priorité recommandée: speaker_auth (authentification) ou STT (latence)
    },
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION AUDIO
    # ═══════════════════════════════════════════════════════════
    "audio": {
        "sampling_rate": 16000,
        "channels": 1,
        "format": "S16_LE",
        "buffer_size": 1024,
        "latency_target_ms": 300,
    },
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION MICROPHONE (À AJUSTER SELON TESTS)
    # ═══════════════════════════════════════════════════════════
    "microphone": {
        "input_device_id": None,      # None = périphérique d'entrée par défaut système
        "ptt_max_duration_ms": 7000,   # Durée max PTT (ms) avant arrêt auto
        "gain": 80,                   # Augmenté pour amplitude correcte
        "saturation_threshold": 20,   # % max acceptable
        "agc_enabled": False,         # AGC matériel désactivé
        "noise_gate_db": -40,
        "compression_ratio": 2.0,
    },
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION VAD (Voice Activity Detection)
    # ═══════════════════════════════════════════════════════════
    "vad": {
        "energy_threshold": -25,      # dB
        "silence_timeout": 1.5,       # secondes
        "pre_speech_buffer": 0.3,     # 300ms
        "post_speech_buffer": 0.5,    # 500ms
    },
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION RAG
# ═══════════════════════════════════════════════════════════
RAG_CONFIG = {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "top_k": 3,
    "similarity_threshold": 0.7,
    "embeddings_model": "sentence-transformers/all-MiniLM-L6-v2",
    "vector_db_path": str(VECTOR_DB_DIR),
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION UI-CONTROL
# ═══════════════════════════════════════════════════════════
UI_CONTROL_CONFIG = {
    "enabled": False,
    "dry_run": True,
    "confidence_threshold": 0.6,
    "allowlist": ["open_url", "click", "type", "scroll", "wait"],
    "denylist": ["download", "upload", "payment"],
}

# ═══════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════
LOG_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_dir": str(LOGS_DIR),
}

# ═══════════════════════════════════════════════════════════
# MODE D'INTERFACE (V2 / AUTO)
# ═══════════════════════════════════════════════════════════
INTERFACE_MODE = os.environ.get("QAIA_INTERFACE_MODE", "auto").lower()
"""
Mode d'interface QAIA (interface V2 unique).

Valeurs recommandées:
    - "v2": force l'utilisation de l'interface V2 (QAIAInterface).
    - "auto": identique à V2, conservé pour compatibilité.

Ancienne valeur "legacy":
    - n'est plus supportée (ancienne interface supprimée),
    - sera traitée comme alias de "v2" par le lanceur.

La variable d'environnement QAIA_INTERFACE_MODE a priorité sur cette valeur.
"""

# ═══════════════════════════════════════════════════════════
# AFFICHAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("✅ QAIA Configuration Production - Stabilité Maximale")
print("=" * 70)
print(f"Platform      : {PLATFORM}")
print(f"Base Dir      : {BASEDIR}")
print(f"Device        : {DEVICE}")
print(f"GPU Available : {GPU_AVAILABLE}")
print("-" * 70)
print("LLM Configuration:")
print(f"  Model       : Phi-3-mini-4k-instruct Q4")
print(f"  Context     : {MODEL_CONFIG['llm']['n_ctx']:,} tokens (4K)")
print(f"  CPU Threads : {MODEL_CONFIG['llm']['n_threads']}")
print(f"  GPU Layers  : {MODEL_CONFIG['llm']['n_gpu_layers']} (CPU only)")
print("-" * 70)
print("STT Configuration:")
print(f"  Model       : {MODEL_CONFIG['speech']['model_name']}")
print(f"  Device      : {MODEL_CONFIG['speech']['device']}")
print(f"  Sample Rate : {MODEL_CONFIG['speech']['sampling_rate']} Hz")
print("-" * 70)
print("Allocation RAM Estimée:")
print(f"  Phi-3-mini Q4      : ~2.3 GB")
print(f"  wav2vec2-large     : ~2 GB")
print(f"  ChromaDB           : ~1 GB")
print(f"  Agents             : ~2 GB")
print(f"  Système            : ~2 GB")
print(f"  ──────────────────────────")
print(f"  TOTAL              : ~9.3 GB / 40 GB (23%)")
print(f"  MARGE LIBRE        : ~31 GB (77%) ✅")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION TTS (Text-to-Speech)
# ═══════════════════════════════════════════════════════════════
TTS_CONFIG = {
    "engine": "piper",    # Moteur TTS: "piper" (qualité pro) ou "pyttsx3" (fallback)
    "voice": "fr",        # Voix française
    "gender": "female",   # Genre de voix souhaité (female/male)
    "rate": 195,          # Vitesse de parole (mots/min) - pour pyttsx3
    "volume": 0.3,        # Volume réduit à 30% (était 0.9)
    "pitch": 1.2,         # Pitch multiplier pour voix féminine
    "protection_window_ms": 1200  # Protection contre arrêt intempestif
}
