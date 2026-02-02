# Changelog QAIA

## [2.2.8] - 2 Février 2026 - Phase 3 : exécution réelle des commandes

### Exécution réelle (Phase 3)
- **qaia_core.py** : `_register_command_actions()` enregistre les callbacks pour les commandes autorisées : arrête lecture (stop_speech), arrête enregistrement/micro (événement `command.stop_recording`), lance/ouvre navigateur (webbrowser), active micro (message informatif).
- **interface/qaia_interface.py** : abonnement à `command.stop_recording` ; `_on_command_stop_recording` appelle `_stop_ptt_recording(finalize=False)` pour arrêter le PTT sans lancer la transcription.
- **docs/PIPELINE_COMMANDES.md** : section « Actions réelles (Phase 3) » avec le tableau des paires et actions.

## [2.2.7] - 2 Février 2026 - Corrections tests pipeline commandes + robustesse guard

### Corrections
- **tests/test_command_pipeline.py** : appel direct à `evaluate_command` au lieu de `self._evaluate` pour éviter le binding (premier argument = TestCase) ; import au niveau module.
- **utils/command_guard.py** : normalisation des types pour `command_verb` et `command_target` avec `isinstance(..., str)` avant `.strip()`, évitant un crash en cas d’appel erroné.

## [2.2.8] - 27 Janvier 2026 - Audit interaction vocale + corrections complémentaires

### Corrections
- **agents/llm_agent.py** : initialisation défensive de `max_tokens` dans `chat()` et `chat_stream()` avec `(MODEL_CONFIG.get("llm") or {}).get("max_tokens", 512)` puis coercition en `int`.
- **utils/text_processor.py** : `_remove_duplicate_consecutive_sentences()` pour supprimer phrases consécutives quasi-dupliquées (réponses garbled) ; appel dans `process_streamed_text()`.

### Documentation
- **docs/AUDIT_INTERACTION_VOCALE.md** : audit flux STT → LLM → affichage → TTS, bugs, corrections et plan de vérification.

## [2.2.6] - 27 Janvier 2026 - Corrections doublon préfixe, NoneType*int, décalage TTS

### 🐛 Corrections
- **Erreur `NoneType * int`** : Dans `agents/llm_agent.py`, `chat()` utilisait `max_tokens` sans l’initialiser quand il était `None` (appel depuis `dialogue_manager` sans `max_tokens`). Initialisation de `max_tokens` depuis `MODEL_CONFIG["llm"]["max_tokens"]` avant la génération.
- **Doublon préfixe « (HH:MM) QAIA: »** :  
  - Dans `interface/components/streaming_text.py`, `replace_current_message()` supprime désormais tout préfixe « (HH:MM) QAIA: » du texte inséré pour éviter le doublon dans la bulle.  
  - En cas d’erreur LLM pendant le streaming, `_on_llm_error()` remplace le contenu du message en cours au lieu d’ajouter un second bloc, évitant « (16:06) QAIA: (16:06) QAIA: Erreur… ».
- **Décalage TTS** : Dans `_on_llm_complete()`, le TTS est lancé immédiatement après le nettoyage du texte streamé (avant la mise à jour UI), pour réduire le délai entre l’affichage du texte et le début de la voix.

## [2.2.5] - 2 Février 2026 - Documentation modules + pipeline commandes

### 📚 Documentation
- **docs/MODULES_FUTURS.md** : mise à jour du statut des modules `audio_manager`, `context_manager`, `intent_detector` (désormais intégrés au flux principal). Précision du rôle d'IntentDetector et de l'intention COMMAND pour le pipeline commandes.
- **docs/AI_INTEGRATION.md** : ajout d'IntentDetector dans la liste des agents et schéma du flux (Interface → QAIACore → DialogueManager + IntentDetector ; COMMAND → CommandGuard + CommandExecutor).
- **docs/PIPELINE_DESKTOP_WEB.md** : section Détection d'intentions (Desktop) ; mention du champ `intent` et des réponses commandes dans le mode Web.

### 🔧 Pipeline commandes système (détection + sécurité + exécution)
- **agents/intent_detector.py** : IntentResult enrichi (command_verb, command_target, command_subtype) ; méthode `parse_command()` pour extraire verbe/cible ; détection COMMAND avec remplissage des champs.
- **utils/command_guard.py** : nouveau module de sécurité (liste blanche verbe/cible, niveau de risque, require_confirmation, journalisation).
- **core/command_executor.py** : nouveau module d'exécution contrôlée (mapping verbe/cible → actions internes, pas de shell, timeout).
- **core/dialogue_manager.py** : branche COMMAND (guard → confirmation si besoin → executor) ; réponses structurées (command_confirmation_pending, command_executed, command_refused).
- **Interface desktop** : gestion des confirmations pour les commandes à risque.
- **Tests** : tests unitaires et d'intégration du pipeline (tests/test_command_pipeline.py, tests test_conversation_flow mis à jour).

## [2.2.4] - 27 Janvier 2026 - Configuration Chroma/RAG unifiée

### 📚 Documentation et configuration unifiée
- **docs/CONFIG_CHROMA_RAG.md** : documentation des variables unifiées (`QAIA_DATA_DIR`, `QAIA_VECTOR_DB_DIR`), mode Chroma embarqué uniquement, et mode fallback (RAG désactivé sans crash).
- **README.md** : ajout d’une section « RAG et base vectorielle (Chroma) » avec lien vers la doc et mention du fallback automatique.

### 🔧 DevOps-Center (alignement)
- **ConfigMap Minikube** : inchangé et conforme (pas de `CHROMA_*` utilisées par l’app).
- **sync_qaia_source.sh** : commentaire rappelant d’exécuter le script après modification de `qaia_core.py` / `rag_agent.py` ; sync exécuté pour propager la version où Chroma n’est initialisé que dans `rag_agent`.
- **Manifests secrets** : nomenclature alignée sur `CHROMA_HOST` / `CHROMA_PORT` (env) et clés secret `chroma_host` / `chroma_port` ; documentation dans README-SECRETS et qaia-configmap.yaml précisant que ces variables ne sont pas encore utilisées par QAIA (Chroma embarqué uniquement).
- **Health / UI** : vérification que `/health` et l’interface exposent `vector_db: true/false` pour refléter le mode RAG actif ou désactivé (fallback).

## [2.2.3] - 2 Février 2026 - Suppression V-JEPA 2

### 🗑 Suppression agent V-JEPA 2 (vjepa2)
- Retrait de toute référence à l'agent vjepa2 dans le projet QAIA.
- `utils/agent_manager.py` : aucun agent vjepa/vjepa2 (déjà absent).
- `utils/monitoring.py` : retrait de l'agent « Vision » (affichage UI lié à vjepa) de la liste des agents connus.
- `docs/FICHIERS_OBSOLETES.md` : mise à jour des références à `agents/vjepa2_agent.py` (fichier obsolète supprimé).
- Suppression du checkpoint partiel vjepa2 : `models/torch_cache/hub/checkpoints/vjepa2-ac-vitg.pt.*.partial`.
- Note : les modules VJEPA2 dans `.venv` (transformers) ne sont pas modifiés (dépendance tierce).

## [2.2.2] - 31 Janvier 2026 - Priorité 2 (consolidations)

### 📊 Monitoring unifié
- `utils.monitoring` devient le point d'entrée centralisé (délégation vers `MetricsCollector`).
- `utils.performance_metrics` simplifié en wrapper de compatibilité.
- Import unifié dans `interface/qaia_interface.py`.

### 🧼 Nettoyage texte centralisé
- `utils.encoding_utils.clean_text()` délègue au module `utils.text_processor`.
- Nettoyage des artefacts Phi-3 centralisé dans `agents/rag_agent.py`.

### 🧾 Logs & archivage
- Archivage automatique des logs de performance JSON (dossier `logs/archive/performance`).
- Variable `QAIA_LOG_ARCHIVE_DAYS` supportée (par défaut 30 jours).
- `.gitignore` mis à jour pour ignorer les logs JSON.

### 🔧 CI/CD
- Workflow CI simplifié: utilisation exclusive de `requirements.txt` (suppression de `requirements-lock.txt`).

### 🧪 Tests
- Test d'intégration contexte/intention ajusté pour valider `dialogue_manager.py`.

### 🐳 Docker
- Ajout d'un `Dockerfile` CPU-only (Python 3.12 slim) pour exécution de `launcher.py`.
- Ajout d'un `.dockerignore` pour exclure `.venv`, logs, caches et modèles volumineux.

## [2.2.1] - 31 Janvier 2026 - Corrections prioritaires

### 🔐 Sécurité & configuration
- Migration de la clé de sécurité vers `.env` (variable `QAIA_SECURITY_KEY`).
- Suppression de `config/.security_key` (clé déplacée hors dépôt).
- Chargement local de `.env` dans `config/system_config.py` (sans dépendance externe).
- Ajout de `.env`/`.env.*` dans `.gitignore`.

### 🧭 Cohérence des chemins
- Alignement de `QAIA_VECTOR_DB_DIR` sur `DATA_DIR` dans `launcher.py`.
- Lecture des overrides `QAIA_*_DIR` dans `config/system_config.py`.

### 🧠 Persistance ChromaDB
- Passage à `chromadb.PersistentClient` dans `qaia_core.py`.

### 🧹 Nettoyage
- Suppression du fichier orphelin `=0.8.0`.

## [2.2.0] - 18 Décembre 2025 - Interface V2 unique

### 🧹 Décommission de l’ancienne interface
- Suppression de l’ancienne interface graphique `agents/interface_agent.py`.
- `launcher.py` utilise désormais exclusivement `interface/qaia_interface.QAIAInterface` (V2).
- `INTERFACE_MODE` (voir `config/system_config.py`) ne supporte plus `legacy` et pointe toujours vers la V2.
- Documentation mise à jour :
  - `ARBORESCENCE.txt` sans référence à `interface_agent.py`,
  - `README.md` (structure projet, docs V2),
  - `docs/AI_INTEGRATION.md`,
  - `docs/decommission_old_interface.md`.

### ✅ Validation & campagne de tests
- Ajout de `docs/TEST_CAMPAIGN_V2.md` (matrice de tests + procédure de campagne).
- Alignement avec `docs/INTERFACE_V2_VALIDATION.md` pour la validation fonctionnelle et UX de la V2.

## [2.1.0] - 16 Décembre 2025 - Migration Phi-3

### 🚀 Migration Majeure
- **LLM**: Migration de Llama 3.1 8B vers Phi-3-mini-4k-instruct (3.8B)
  - Latence moyenne: -45% (46s → 25.5s)
  - Questions consécutives: -59% (46s → 19s)
  - RAM utilisée: -58% (5.5GB → 2.3GB)
  - Format prompt: `<|system|>` / `<|user|>` / `<|assistant|>` (Phi-3)
  - Stop tokens: `<|end|>` au lieu de `<|im_end|>`

### ⚙️ Configuration
- Ajout ressources dédiées Phi-3 (RAM limit 12GB, CPU threads 6)
- Paramètres optimisés: temp=0.6, max_tokens=100
- Suppression paramètres Llama (rope_freq_base, rope_freq_scale)

### 🎯 Prompt Système
Refonte complète avec directives utilisateur:
- Principe de vérité absolue
- Citation de sources obligatoire
- Protection et sécurité prioritaires
- Présentation: "Bonjour, je suis QAIA votre assistante multimodale..."

### 📝 Fichiers Modifiés
1. **config/system_config.py**: Nouveau modèle, ressources, prompt système
2. **agents/llm_agent.py**: Format prompt Phi-3, nettoyage artefacts
3. **agents/rag_agent.py**: Stop tokens Phi-3
4. **qaia_core.py**: Format prompt fallback Phi-3
5. **README.md**: Documentation mise à jour
6. **launch_qaia.sh**: Message d'accueil Phi-3

### 🧹 Nettoyage
- Suppression scripts de test obsolètes
- Nettoyage références Llama dans code/docs
- Cache Python nettoyé

## [1.0.1] - 16 Décembre 2025

### ✅ Corrections Critiques

#### Blocage Audio (2ème question)
**Problème:** Le système se bloquait systématiquement à la 2ème question en mode vocal
**Cause:** Flag `ptt_stopping` non réinitialisé après traitement
**Solution:** Ajout `self.ptt_stopping = False` dans `_process_text_thread` finally block
**Fichier:** `interface/qaia_interface.py` ligne 509

#### Saturation Audio
**Problème:** Audio saturé (26.6% clipping, RMS 18,496) → transcription impossible
**Causes:**
- Volume microphone trop élevé (80%)
- Pas de réduction de gain dans le code
**Solutions:**
- Volume micro réduit à 30%
- Gain audio réduit à 0.3 (-10dB) dans `interface/qaia_interface.py` ligne 618
**Impact:** RMS attendu < 10,000, clipping < 5%

### 📝 Fichiers Modifiés

1. **interface/qaia_interface.py**
   - Ligne 509: Ajout réinitialisation `ptt_stopping`
   - Ligne 618: Ajout gain audio 0.3

### 🆕 Nouveaux Outils

1. **scripts/test_audio_pipeline.py**
   - Diagnostic complet pipeline audio
   - Analyse qualité (RMS, clipping, silence)
   - Test prétraitement et transcription

2. **test_qaia.sh**
   - Script de test rapide
   - Configuration automatique volume micro
   - Instructions interactives

### 🗑️ Nettoyage Arborescence

**Supprimés:**
- 47 fichiers de rapport/audit redondants (15 déc)
- 7 fichiers .txt obsolètes
- 7 fichiers temporaires racine

**Résultat:** docs/ : 60 → 4 fichiers essentiels

---

## [1.0.0] - 15 Décembre 2025

### 🎉 Version Initiale

#### Fonctionnalités
- Reconnaissance vocale (Wav2Vec2 français)
- Synthèse vocale féminine (Piper TTS)
- RAG avec ChromaDB
- LLM Llama 3.1 8B (Q4_K_M)
- Interface graphique Tkinter
- Mode conversation Push-to-Talk

#### Architecture
- Agents modulaires (voice, speech, RAG, LLM, vision)
- Système de logs centralisé
- Base de données SQLite
- Prétraitement audio (filtrage, normalisation)

---

## Configuration Système Actuelle

**Matériel:** Intel i7-7700HQ, 40GB RAM, CPU only
**OS:** Linux 6.14.0
**Python:** 3.11
**Modèles:**
- LLM: Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
- STT: jonatasgrosman/wav2vec2-large-xlsr-53-french
- TTS: Piper fr_FR-siwis-medium (voix féminine)

**Paramètres Optimisés:**
- LLM: n_ctx=2048, max_tokens=150, n_batch=512
- Audio: sample_rate=16kHz, gain=0.3, volume_micro=30%
- TTS: volume=0.3 (30%)

