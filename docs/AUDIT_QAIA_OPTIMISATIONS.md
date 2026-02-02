# Audit QAIA – Liste d’optimisations par importance

**Date :** 27 janvier 2026  
**Périmètre :** Code source, config, CI, Docker, tests, sécurité.

---

## Résumé

- **Fichiers Python scannés :** ~85 (hors .venv)
- **Bloquants / critiques :** 6
- **Importants :** 12
- **Recommandés :** 14

---

## Critique (P0) – À traiter en priorité

### 1. ChromaDB : `Client` au lieu de `PersistentClient` (persistance)

**Fichier :** `qaia_core.py` (l.232)

**Problème :**  
`chromadb.Client(Settings(persist_directory=...))` ne garantit pas la persistance sur disque. Pour ChromaDB 0.4.x, la persistance s’obtient avec `PersistentClient(path=...)`.

**Action :**  
Remplacer par `chromadb.PersistentClient(path=str(VECTOR_DB_DIR), settings=Settings(anonymized_telemetry=False, allow_reset=False))` (ou API équivalente selon la version) et vérifier en redémarrant que les collections survivent.

---

### 2. Incohérence `VECTOR_DB_DIR` : launcher vs `system_config`

**Fichiers :** `launcher.py` (l.33, 46), `config/system_config.py` (l.21)

**Problème :**  
- Launcher : `VECTOR_DB_DIR = BASE_DIR / "vector_db"` et `QAIA_VECTOR_DB_DIR=BASE_DIR/vector_db`.  
- `system_config` : `VECTOR_DB_DIR = DATA_DIR / "vector_db"` (= `data/vector_db`) et ne lit pas `os.environ`.  

Résultat : le launcher crée et exporte `vector_db/` à la racine, tandis que QAIA utilise `data/vector_db`. Deux emplacements différents, risques de vide ou d’incohérence.

**Action :**  
- Faire lire `VECTOR_DB_DIR` dans `system_config` depuis `os.environ.get("QAIA_VECTOR_DB_DIR")` avec repli sur `DATA_DIR / "vector_db"`.  
- Dans le launcher, définir `VECTOR_DB_DIR = DATA_DIR / "vector_db"` (et `QAIA_VECTOR_DB_DIR` en conséquence) pour aligner avec `system_config`.

---

### 3. `data/database.py` : `get_recent_conversations` – mauvais unpacking dans `__main__`

**Fichier :** `data/database.py` (l.322–325)

**Problème :**  
`get_recent_conversations` renvoie `(id, timestamp, speaker_id, user_input, qaia_response)` (5 colonnes). Le test fait :  
`for id, timestamp, user_input, qaia_response in history` → 4 variables ⇒ `ValueError: too many values to unpack`.

**Action :**  
Adapter le unpacking, par ex. :  
`for id, timestamp, speaker_id, user_input, qaia_response in history`  
et adapter les `print` si besoin. Vérifier aussi les autres usages de `get_recent_conversations`.

---

### 4. `rag_agent` : modèle d’embeddings ignoré (`RAG_CONFIG` vs `MODEL_CONFIG`)

**Fichiers :** `agents/rag_agent.py` (l.75–76), `config/system_config.py` (`RAG_CONFIG`)

**Problème :**  
Le code fait :  
`embedding_config_from_system = MODEL_CONFIG.get("embeddings", {})`  
et `EMBEDDING_MODEL = embedding_config_from_system.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")`.  
`MODEL_CONFIG` n’a pas de clé `"embeddings"`, donc `RAG_CONFIG["embeddings_model"]` n’est jamais utilisé.

**Action :**  
Utiliser `RAG_CONFIG.get("embeddings_model", "sentence-transformers/all-MiniLM-L6-v2")` pour `EMBEDDING_MODEL`.

---

### 5. Verrou d’instance unique Windows-only dans `launcher.py`

**Fichier :** `launcher.py` (l.104–117)

**Problème :**  
Le mutex `CreateMutexW` / `kernel32` est propre à Windows. Sur Linux, l’import ou l’appel échouent et sont ignorés (`except: pass`), donc pas de verrou mono‑instance sur Linux.

**Action :**  
- Implémenter un verrou fichier (p.ex. `fcntl.flock` ou fichier lock dans `logs/` ou `data/`) pour Linux/macOS.  
- Garder le mutex Windows derrière `if sys.platform == "win32"` et éviter `except: pass` en gardant un log si échec.

---

### 6. Fichier parasite `=0.8.0` à la racine

**Fichier :** `=0.8.0` (racine du projet)

**Problème :**  
Contenu typique de sortie `pip install` (p.ex. `pyspellchecker`), pas un fichier de version. Peut induire en erreur (scripts, packaging).

**Action :**  
Supprimer `=0.8.0` et ajouter `=0.8.0` (ou un pattern équivalent) dans `.gitignore` si des commandes peuvent en recréer.

---

## Important (P1)

### 7. `.python-version` avec une valeur non standard

**Fichier :** `.python-version`

**Problème :**  
Contenu `qaia-env` (nom d’env) au lieu d’une version (3.10, 3.11, 3.12). Incompatible avec les usages classiques (pyenv, CI, doc).

**Action :**  
Mettre `3.11` ou `3.12` selon la cible. Documenter l’env `qaia-env` ailleurs (README, Makefile, etc.) si nécessaire.

---

### 8. Doublon `EmbeddingCache` : `rag_agent` et `utils/embedding_cache`

**Fichiers :** `agents/rag_agent.py` (classe `EmbeddingCache`), `utils/embedding_cache.py`, `agents/__init__.py`

**Problème :**  
Deux implémentations (signatures et comportements différents). Risque de confusion et de maintenance double.

**Action :**  
- Choisir une implémentation (idéalement `utils.embedding_cache`) et une interface commune.  
- Faire utiliser `utils.embedding_cache` dans `rag_agent` (avec un wrapper si besoin pour le `model`) et supprimer la classe dupliquée dans `rag_agent`.

---

### 9. Triple stack de logging (redondance et chemins)

**Fichiers :**  
`config/logging_config.py`, `config/setup_logging.py`, `utils/log_manager.py`,  
`launcher.py` (basicConfig + `system.log`), `agents/rag_agent.py` (basicConfig + `rag_agent_*.log`).

**Problème :**  
- Plusieurs `basicConfig` et handlers (fichiers + console) qui se chevauchent.  
- `logging_config.LOG_DIR = Path("logs")` en dur au lieu de `LOGS_DIR` de `system_config`.  
- Fichiers de log multiples (`launcher.log`, `system.log`, `rag_agent_YYYYMMDD.log`, `interface.log`, etc.) sans stratégie claire.

**Action :**  
- Un seul point d’entrée (p.ex. `utils.log_manager` ou `config/logging_config`) appelé au démarrage.  
- Utiliser `LOGS_DIR` de `system_config` partout.  
- Éviter `basicConfig` dans les modules (rag_agent, etc.) ; laisser le launcher / log_manager configurer le root logger.  
- Documenter dans README ou `docs/` la structure des logs (fichiers, niveaux, rotation).

---

### 10. `config/.security_key` non dans `.gitignore`

**Fichier :** `config/.security_key`

**Problème :**  
Fichier potentiellement sensible non listé dans `.gitignore`. S’il est versionné, risque de fuite de secret.

**Action :**  
- Ajouter `config/.security_key` et plus généralement `**/.security_key` ou `*.key` dans `.gitignore` (selon la politique).  
- Vérifier qu’il n’a jamais été commité (`git log -p -- config/.security_key`).  
- Si clé déjà exposée, la révoquer et en générer une nouvelle, puis documenter son usage (`.env.example`, `docs/`).

---

### 11. `data/database.py` : chemins et test en dur

**Fichier :** `data/database.py`

**Problème :**  
- En-tête `# E:\QAIA\data\database.py` (Windows).  
- Bloc `__main__` :  
  - `db.set_setting("model_path", "E:/QAIA/models/phi-3-mini-4k-instruct.Q5_K_M.gguf")` en dur.  
  - Déjà mentionné : unpacking incorrect de `get_recent_conversations`.

**Action :**  
- Remplacer le chemin de test par `str(MODELS_DIR / "Phi-3-mini-4k-instruct-q4.gguf")` (ou la config réelle) et corriger l’unpacking (cf. P0 #3).  
- Nettoyer l’en-tête ou le remplacer par un chemin relatif / générique.

---

### 12. `requirements.txt` vs `requirements-docker.txt` incohérents

**Fichiers :** `requirements.txt`, `requirements-docker.txt`

**Problème :**  
- Docker : `pyaudio`, `sounddevice` absent ; projet principal : `sounddevice`, pas `pyaudio`.  
- Versions Docker très figées (p.ex. `llama-cpp-python==0.2.20` vs `>=0.2.71` dans `requirements.txt`).  
- Docker : `pandas`, `pyyaml`, `requests` ; absents de `requirements.txt`.  
- `python-dotenv` dans les deux ; aucun `load_dotenv()` dans le code → inutilisé.

**Action :**  
- Aligner les dépendances (audio, LLM, Chroma, etc.) entre les deux fichiers.  
- Soit dériver `requirements-docker.txt` de `requirements.txt` avec des surcharges de versions, soit documenter les écarts.  
- Si `.env` est prévu : appeler `load_dotenv()` au démarrage (launcher ou `system_config`) et documenter dans `.env.example`.

---

### 13. CI : `requirements-lock.txt` et Chemins

**Fichier :** `.github/workflows/qaia-ci.yml`

**Problème :**  
- Plusieurs jobs supposent `requirements-lock.txt` qui n’existe pas → repli sur `requirements.txt` (documenté dans les `run`).  
- `code-quality` : `black --check`, `isort --check`, `flake8`, `mypy`, `radon` sans config dédiée (pyproject.toml, `setup.cfg`, `.flake8`) → sensibles aux changements de défauts.  
- `codecov` : `file: ./coverage.xml` alors que pytest produit `--cov-report=xml` → `coverage.xml` par défaut ; à confirmer.

**Action :**  
- Introduire `requirements-lock.txt` (pip freeze ou lockfile) et l’utiliser en CI, ou supprimer les branches “if requirements-lock” et ne garder que `requirements.txt`.  
- Ajouter `pyproject.toml` (ou config flake8/isort/mypy) et l’aligner avec le formatage du projet.  
- Vérifier le chemin du rapport de couverture (p.ex. `--cov-report=xml:coverage.xml` ou `--cov-report=xml` et `file` dans Codecov).

---

### 14. Pas de chargement `.env` malgré `python-dotenv`

**Fichiers :** `requirements.txt`, `requirements-docker.txt`, launcher / `system_config`

**Problème :**  
`python-dotenv` est installé mais `load_dotenv()` n’est jamais appelé. Les secrets et overrides ne peuvent pas être chargés depuis `.env`.

**Action :**  
- Au tout début du launcher (avant toute import de config), faire :  
  `from dotenv import load_dotenv` puis `load_dotenv()` (éventuellement `load_dotenv(Path(__file__).parent / ".env")`).  
- Créer `.env.example` avec les variables QAIA (`QAIA_DATA_DIR`, `QAIA_LOGS_DIR`, `QAIA_VECTOR_DB_DIR`, `QAIA_UI_CONTROL_*`, etc.) et les documenter.

---

### 15. Docker : CMD `--safe-mode` et `pyaudio`

**Fichier :** `Dockerfile`

**Problème :**  
- `CMD ["python", "launcher.py", "--safe-mode"]` lance sans interface graphique. Pas de variable d’env pour activer l’UI (si jamais envisagé en conteneur).  
- `requirements-docker.txt` inclut `pyaudio` alors que le projet utilise `sounddevice` ; `pyaudio` peut poser des soucis de build (portaudio).

**Action :**  
- Remplacer `pyaudio` par `sounddevice` dans `requirements-docker.txt` et ajuster les paquets système (portaudio) si nécessaire pour `sounddevice`.  
- Documenter que l’image par défaut est “sans UI” et, si besoin, prévoir une var (p.ex. `QAIA_SAFE_MODE`) pour piloter `--safe-mode`.

---

### 16. `logging_config` : `LOG_DIR` en dur

**Fichier :** `config/logging_config.py` (l.17)

**Problème :**  
`LOG_DIR = Path("logs")` empêche d’utiliser un répertoire centralisé (p.ex. `LOGS_DIR` de `system_config`), surtout en Docker ou avec `QAIA_LOGS_DIR`.

**Action :**  
Importer `LOGS_DIR` depuis `system_config` (avec import différé si `system_config` charge torch) ou depuis `os.environ.get("QAIA_LOGS_DIR", "logs")` et utiliser ce `Path` pour les handlers.

---

### 17. Logs de perf et anciens JSON

**Dossier :** `logs/performance/`

**Problème :**  
Nombreux fichiers `transcription_perf_*.json` (plus de 20). Pas de rotation ni de rétention documentée ; en production, accumulation possible.

**Action :**  
- Mettre en place une rotation ou une purge (âge, nombre max) dans le script qui écrit ces JSON (ou dans un cron/tâche planifiée).  
- Documenter la politique (durée de rétention, taille max) dans `docs/` ou `README`.

---

### 18. `resource_manager` dans `qaia_core.cleanup` sans attribution

**Fichier :** `qaia_core.py` (l.413–424)

**Problème :**  
`cleanup()` utilise `self.resource_manager` alors que `__init__` ne l’attribue nulle part.  
`hasattr(self, 'resource_manager') and self.resource_manager` peut éviter un crash mais le code est mort ou dépend d’une injection externe non visible.

**Action :**  
- Soit instancier/clé `resource_manager` dans `__init__` (ou l’injecter explicitement).  
- Soit retirer le bloc si la ressource n’existe pas et documenter que le cleanup des “resources” est fait ailleurs.

---

## Recommandé (P2)

### 19. `llm_agent` : duplication de la construction du system prompt

**Fichier :** `agents/llm_agent.py`

**Problème :**  
La construction du system prompt (identity, mission, principles, verification, règles de formatage, etc.) est dupliquée entre `chat()` et `chat_stream()`, avec de légères variations.

**Action :**  
Extraire une méthode `_build_system_prompt(is_first_interaction: bool) -> str` (ou une fonction dans un module `prompts`) et l’appeler depuis `chat` et `chat_stream`.

---

### 20. `rag_agent` : `MODEL_CONFIG["llm"]` sans `n_batch`

**Fichiers :** `agents/rag_agent.py`, `config/system_config.py`

**Problème :**  
`rag_agent` utilise `n_batch=512` en dur dans `LlamaCpp`, alors que `MODEL_CONFIG["llm"]` ne définit pas `n_batch`.  
Incohérence et difficulté à tuner (CPU/GPU, mémoire).

**Action :**  
Ajouter `n_batch` dans `MODEL_CONFIG["llm"]` (p.ex. 512) et dans `rag_agent` faire :  
`n_batch=llm_config.get("n_batch", 512)`.

---

### 21. `dialogue_manager` : `llm.complete` émis deux fois

**Fichiers :** `core/dialogue_manager.py` (l.316–330), `agents/llm_agent.py` (`chat` / `chat_stream`)

**Problème :**  
`DialogueManager.process_message` appelle `llm_agent.chat()` qui, via `rag_agent` / `process_query`, émet déjà `llm.complete`.  
En plus, `DialogueManager` émet un second `llm.complete` (l.316–330) avec des champs partiels (tokens estimés par `split()`).  
Risque de doublons côté UI et métriques.

**Action :**  
- Ne pas émettre `llm.complete` dans `DialogueManager` lorsque `llm_agent.chat()` est utilisé (il le fait déjà).  
- Ou centraliser l’émission dans un seul endroit (p.ex. uniquement dans `llm_agent` ou dans un wrapper) et supprimer l’autre.

---

### 22. Typage et docstrings incomplets

**Fichiers :** multiples

**Problème :**  
Plusieurs fonctions sans type de retour ou sans types pour les arguments ; docstrings inégales. La CI mypy est en `continue-on-error`.

**Action :**  
- Ajouter progressivement les annotations (retour, arguments) sur les modules les plus utilisés (`qaia_core`, `dialogue_manager`, `llm_agent`, `rag_agent`, `database`).  
- Aligner les docstrings sur le format (Args, Returns, Raises) et viser que mypy passe sans `--ignore-missing-imports` sur un sous-ensemble ciblé.

---

### 23. Tests : chemins et dépendances lourdes

**Fichiers :** `tests/` (conftest, `test_*.py`)

**Problème :**  
- `test_performance` et d’autres peuvent charger des modèles lourds ; `SKIP_MODEL_DOWNLOAD` / `DISABLE_OPTIONAL_MODELS` utilisés dans certains tests seulement.  
- Pas de marqueurs pytest clairs (`slow`, `integration`, `requires_model`) ni de `-m "not slow"` par défaut en CI.

**Action :**  
- Introduire des marqueurs (`@pytest.mark.slow`, `@pytest.mark.integration`) et les documenter dans `pytest.ini` ou `pyproject.toml`.  
- En CI, lancer d’abord les tests “rapides” (`-m "not slow"`) puis, si besoin, un job dédié pour les tests lents.  
- S’assurer que les chemins de modèles/data en test passent par des variables d’env ou des fixtures (répertoire temporaire).

---

### 24. `config/system_config` : `print` au chargement

**Fichier :** `config/system_config.py` (l.235–264)

**Problème :**  
Une longue sortie `print` au moment de l’import (bannière de config). Peut polluer les logs, les tests et les environnements sans TTY (Docker, CI, services).

**Action :**  
- Remplacer par un `logging.info` (ou logger dédié) après configuration du logging.  
- Ou n’afficher la bannière que si `os.environ.get("QAIA_SHOW_CONFIG")` ou un flag CLI (launcher) est défini.

---

### 25. `agents/llm_agent` : `generate()` inutile

**Fichier :** `agents/llm_agent.py` (l.99–120)

**Problème :**  
`generate()` retourne une chaîne fixe indiquant d’utiliser le RAG agent. Aucun appel trouvé ; dead code ou API de compatibilité non documentée.

**Action :**  
- Si inutile : supprimer et mettre à jour les éventuels appels.  
- Si conservé pour compatibilité : le marquer `@deprecated` et documenter le remplacement par `chat()` / `rag_agent.process_query`.

---

### 26. `data/database` : `__del__` et gestion de la connexion

**Fichier :** `data/database.py`

**Problème :**  
`__del__` appelle `self.close()`. `__del__` n’est pas déterministe et peut être appelé dans un contexte où les modules sont en cours de déchargement. De plus, `sqlite3` n’aime pas que la connexion soit fermée après que le curseur soit garbage-collecté dans un ordre imprévisible.

**Action :**  
- Privilégier un context manager : `with Database() as db:` et `def __enter__` / `__exit__` qui ferment la connexion.  
- Garder `close()` explicite pour les usages non-`with`.  
- Réduire ou supprimer `__del__` et documenter que les callers doivent fermer la connexion (ou utiliser `with`).

---

### 27. Dépendances : `transitions` et `state machine`

**Fichier :** `requirements.txt`

**Problème :**  
`transitions` est listé (state machine) ; aucun import `transitions` ou usage de machine à états détecté dans le code.

**Action :**  
- Si inutilisé : retirer de `requirements.txt`.  
- Si prévu pour une évolution : ajouter un TODO dans le code ou la doc et garder la dépendance en la justifiant.

---

### 28. Fichier `backups/.../eval.py`

**Chemin :** `backups/wav2vec2-large-xlsr-53-french.FLAX_BACKUP/eval.py`

**Problème :**  
Script dans un dossier de backup, susceptible d’être exécuté par erreur ou de compliquer les recherches de code.

**Action :**  
- Exclure `backups/` des imports et des racines de tests (pytest, mypy).  
- Si ce script n’est plus nécessaire, le supprimer ou le déplacer dans `scripts/` / `experiments/` en le renommant clairement (p.ex. `legacy_eval_...`).

---

### 29. `LightweightTextArea` dans `qaia_interface.py`

**Fichier :** `interface/qaia_interface.py`

**Problème :**  
Classe `LightweightTextArea` (tk.Canvas) définie dans le même fichier que `QAIAInterface`. Le README et les composants évoquent `StreamingTextDisplay` ; il n’est pas clair si `LightweightTextArea` est encore utilisée.

**Action :**  
- Si utilisée : la déplacer dans `interface/components/` pour cohérence.  
- Si obsolète : la supprimer et s’assurer qu’aucun code ne l’utilise.

---

### 30. Index et chemins Chroma / `rag_agent`

**Fichiers :** `agents/rag_agent.py`, config RAG

**Problème :**  
`VECTOR_DB_DIR` (data/vector_db) vs répertoire des documents `DOC_DIR` (data/documents). Si `chromadb` et `rag_agent` pointent vers des bases ou des dossiers différents selon l’env, les index RAG peuvent ne pas être trouvés après déploiement.

**Action :**  
- Documenter que `data/vector_db` et `data/documents` sont requis et doivent être pérennes (volumes Docker, etc.).  
- Vérifier que `rag_agent` et `qaia_core` utilisent bien le même `VECTOR_DB_DIR` (après correction P0 #2).

---

## Synthèse des actions prioritaires

| Priorité | Quantité | Principales actions |
|----------|----------|---------------------|
| **P0**   | 6        | ChromaDB PersistentClient, VECTOR_DB_DIR launcher/config, correctif database `__main__`, RAG embeddings, verrou Linux, suppression `=0.8.0` |
| **P1**   | 12       | .python-version, fusion EmbeddingCache, unification logging, .security_key/.gitignore, database chemins/test, requirements Docker vs txt, CI, .env, Docker CMD/pyaudio, logging_config LOG_DIR, logs perf, resource_manager |
| **P2**   | 12       | DRY system prompt LLM, n_batch, doublon llm.complete, typage, marqueurs tests, print system_config, generate() LLM, Database context manager, transitions, backups/eval, LightweightTextArea, RAG/Chroma docs |

---

## Bonnes pratiques déjà en place

- Validation des entrées utilisateur (`utils/security.validate_user_input`) et sanitization de l’historique.
- Gestion centralisée des agents (`utils/agent_manager`).
- Configuration centralisée dans `config/system_config.py` (MODEL_CONFIG, RAG_CONFIG, TTS, etc.).
- Event bus pour le découplage UI / agents.
- `.gitignore` couvrant modèles, BDD, backups, logs, .venv.
- CI avec jobs sécurité, qualité, deps, tests, Docker, doc.
- Dockerfile dédié et CMD explicite.

---

*Rapport généré dans le cadre de l’audit QAIA. Pour toute question : voir `CHANGELOG.md` ou la doc dans `docs/`.*
