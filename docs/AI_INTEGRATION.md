# Intégration IA Avancée dans QAIA

Ce document détaille l'architecture et les optimisations du système QAIA pour une intégration IA complète et performante.

## Architecture Générale

### 1. Système d'Agents Multi-Modaux

QAIA utilise une architecture modulaire avec des agents spécialisés :

- **QAIAInterface (V2)** - Interface utilisateur graphique moderne (CustomTkinter)
- **Wav2VecVoiceAgent** - Reconnaissance vocale avec Wav2Vec2 et monitoring
- **SpeechAgent** - Synthèse vocale et gestion audio
- **DataSources (RAG)** - Recherche augmentée avec ChromaDB et embeddings
- **SpeakerAuth** - Authentification vocale et profils utilisateurs
- **IntentDetector** - Détection d'intentions (question, clarification, confirmation, commande, salutation, fin de conversation) via règles regex en français. Sert à adapter le flux de dialogue et, à terme, à déclencher un pipeline commandes système sécurisé (détection → sécurité → exécution).

**Flux simplifié** : Interface → QAIACore → DialogueManager + IntentDetector → LLM/RAG ; pour intention COMMAND → (CommandGuard + CommandExecutor).

### 2. Gestion UV et Dépendances

Le projet utilise **UV** pour la gestion optimisée des dépendances :

```python
# /// script
# dependencies = [
#   "transformers>=4.30.0",
#   "torch>=2.0.0",
#   "sentence-transformers>=2.2.0",
#   "chromadb>=0.4.0",
# ]
# ///
```

**Avantages UV :**
- Installation ultra-rapide des dépendances
- Résolution de conflits automatique
- Cache intelligent partagé
- Support multi-environnements

### 3. Configuration Centralisée

Le système utilise `config/system_config.py` pour centraliser toutes les configurations :

```python
# Modèles IA configurables
QAIA_MODEL_CONFIG = {
    "llm": {
        "model_path": "models/qwen2.5-7b-instruct-q4_k_m.gguf",
        "n_gpu_layers": -1,
        "max_tokens": 2048
    },
    "embeddings": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2"
    },
    "wav2vec": {
        "model_name": "facebook/wav2vec2-base-960h"
    }
}
```

## Optimisations Techniques

### 4. Gestion Intelligente des Ressources

- **Détection automatique GPU/CPU** - Adaptation selon le matériel disponible
- **Allocation mémoire optimisée** - Gestion intelligente de la VRAM/RAM
- **Threading optimisé** - Utilisation efficace des cœurs CPU disponibles
- **Cache multi-niveaux** - Cache mémoire + disque pour les embeddings

### 5. Système RAG Hybride

```python
class DataSources:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectorstore = Chroma(persist_directory=str(PERSIST_DIR))
        self.cache = EmbeddingCache(CACHE_DIR)
```

**Fonctionnalités :**
- Recherche sémantique avec all-MiniLM-L6-v2
- Base vectorielle ChromaDB persistante
- Cache des embeddings pour performance
- Support multi-formats (PDF, TXT, MD, DOCX)

### 6. Reconnaissance Vocale Avancée

Le **Wav2VecVoiceAgent** combine :
- Wav2Vec2 pour la transcription haute qualité
- Détection automatique de langue
- Monitoring des performances audio
- Profils vocaux personnalisés avec SpeakerAuth

### 7. Interface Utilisateur Moderne (V2)

L'**interface QAIA V2** (`interface/qaia_interface.py`) offre :
- Chat en temps réel avec historique et streaming token-par-token
- Visualisation des niveaux audio et état PTT
- Mode conversationnel automatique (texte + vocal)
- Fenêtres modulaires (logs, métriques LLM, monitoring, agents)

## Tests et Validation

### 8. Suite de Tests Unifiée

Le dossier `tests/` contient des tests optimisés :

- **test_audio_unified.py** - Tests audio complets (WAV2VEC + utilitaires)
- **test_memory_unified.py** - Tests mémoire (long-terme + système)
- **test_wav2vec_unified.py** - Tests reconnaissance vocale avec monitoring
- **check_qaia_simple.py** - Vérification système complète

### 9. Scripts de Validation

```bash
# Test complet du système
python tests/check_qaia_simple.py

# Test audio unifié
python tests/test_audio_unified.py

# Test de l'interface
python tests/test_interface.py
```

## Sécurité et Fiabilité

### 10. Gestion des Erreurs

- **Logging centralisé** avec `config/setup_logging.py`
- **Gestion gracieuse des pannes** - Fallbacks pour chaque composant
- **Validation des entrées** - Sécurisation des inputs utilisateur
- **Isolation des processus** - Threading sécurisé pour les opérations lourdes

### 11. Optimisations de Performance

```python
# Optimisations GPU/CPU adaptatives
GPU_LAYERS = llm_config_from_system.get("n_gpu_layers", -1)
MAX_THREADS = max(2, multiprocessing.cpu_count() - 2)

# Cache intelligent
cache_size = embedding_config_from_system.get("cache_size", 1000)
self.cache = EmbeddingCache(CACHE_DIR, max_size=cache_size)
```

## Déploiement et Utilisation

### 12. Lancement Optimisé

Le `launcher.py` gère :
- Vérification des ressources système
- Initialisation des chemins et environnement
- Choix automatique CPU/GPU selon disponibilité
- Fallbacks d'interface (complète → simplifiée → terminal)

### 13. Configuration Hardware

**Configuration recommandée :**
- **CPU:** Intel i7-7700HQ (2.80GHz) ou équivalent
- **RAM:** 8GB minimum (7.89GB utilisable)
- **GPU:** NVIDIA GTX 1050 ou supérieur
- **Stockage:** SSD recommandé pour les modèles

### 14. Fichiers de Configuration

```
E:\QAIA\
├── config/
│   ├── system_config.py      # Configuration centralisée
│   └── setup_logging.py      # Configuration des logs
├── models/                   # Modèles IA (Qwen, Wav2Vec2)
├── data/
│   ├── documents/            # Base de connaissances RAG
│   ├── vector_db/            # ChromaDB persistante
│   ├── embeddings/           # Cache des embeddings
│   └── voice_profiles/       # Profils authentification vocale
└── logs/                     # Journalisation centralisée
```

## Monitoring et Métriques

### 15. Surveillance en Temps Réel

- **Métriques système** - CPU, RAM, GPU, stockage
- **Performance IA** - Temps de réponse, qualité transcription
- **Utilisation cache** - Taux de hit/miss des embeddings
- **Santé des agents** - État de chaque composant

Cette architecture permet à QAIA d'offrir une expérience IA complète, performante et adaptative sur différentes configurations matérielles. 