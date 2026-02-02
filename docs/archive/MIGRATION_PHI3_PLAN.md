# Plan de Migration: Phi-3-mini + Thinking Mode

**Date:** 16 Décembre 2025  
**Objectif:** Remplacer Llama 3.1 8B par Phi-3-mini 3.8B avec mode thinking

---

## 📋 TODO LIST

### Phase 1: Téléchargement et Configuration (30 min)

- [ ] **TÉLÉCHARGER PHI-3-MINI**
  - Fichier: `Phi-3-mini-4k-instruct-q4.gguf`
  - Taille: 2.3 GB
  - Source: HuggingFace
  - Destination: `/media/ccm57/SSDIA/QAIA/models/`
  - Commande: `wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf`

- [ ] **CONFIGURER PARAMÈTRES DE BASE**
  - Fichier: `config/system_config.py`
  - Modifications:
    - `model_path`: Phi-3-mini-4k-instruct-q4.gguf
    - `n_ctx`: 2048 → 2048 (maintenu, Phi-3 natif 4K)
    - `max_tokens`: 150 → 100 (réponses concises)
    - `temperature`: 0.7 → 0.6 (optimal Phi-3)
    - Supprimer: `rope_freq_base`, `rope_freq_scale` (spécifique Llama)

- [ ] **AJOUTER CONFIG THINKING MODE**
  - Fichier: `config/system_config.py`
  - Nouveau bloc:
    ```python
    THINKING_MODE_CONFIG = {
        "enabled": False,  # Toggle par défaut
        "trigger_keywords": ["analyse", "explique", "pourquoi", "comment"],
        "prompt_template": "chain_of_thought",
        "max_thinking_tokens": 150,
        "show_reasoning": True
    }
    ```

---

### Phase 2: Modification Format Prompt (20 min)

- [ ] **MODIFIER agents/rag_agent.py - PROMPT FORMAT**
  - Fichier: `agents/rag_agent.py`
  - Ligne ~350-370 (fonction `process_query`)
  - **AVANT (Llama 3.1):**
    ```python
    query = f"""<|im_start|>system
    Vous êtes QAIA, un assistant IA utile, concis et précis.<|im_end|>
    <|im_start|>user
    {user_query}<|im_end|>
    <|im_start|>assistant
    """
    ```
  - **APRÈS (Phi-3):**
    ```python
    query = f"""<|system|>
    Vous êtes QAIA, un assistant IA utile, concis et précis.
    <|end|>
    <|user|>
    {user_query}
    <|end|>
    <|assistant|>
    """
    ```

- [ ] **MODIFIER agents/rag_agent.py - STOP TOKENS**
  - Ligne ~135 (initialisation LlamaCpp)
  - **AVANT:**
    ```python
    stop=["<|im_end|>", "<|endoftext|>", "\n\n\n"]
    ```
  - **APRÈS:**
    ```python
    stop=["<|end|>", "<|endoftext|>"]
    ```

- [ ] **MODIFIER agents/llm_agent.py - FORMAT (si utilisé)**
  - Vérifier si llm_agent.py construit des prompts
  - Appliquer même format que rag_agent.py

---

### Phase 3: Implémentation Thinking Mode (40 min)

- [ ] **CRÉER utils/thinking_mode.py**
  - Nouveau module pour gestion thinking mode
  - Classes:
    - `ThinkingModeManager`: Gestion activation/désactivation
    - `ThinkingPromptBuilder`: Construction prompts CoT
    - `ReasoningParser`: Extraction du raisonnement
  - Fonctions:
    - `detect_complex_query()`: Détection automatique
    - `build_thinking_prompt()`: Prompt avec CoT
    - `parse_reasoning()`: Extraction étapes

- [ ] **INTÉGRER THINKING MODE DANS RAG_AGENT**
  - Fichier: `agents/rag_agent.py`
  - Ajouter import: `from utils.thinking_mode import ThinkingModeManager`
  - Modifier `process_query()`:
    - Détecter si thinking mode requis
    - Adapter prompt selon mode
    - Parser réponse pour extraire raisonnement

- [ ] **AJOUTER TOGGLE DANS INTERFACE**
  - Fichier: `interface/qaia_interface.py`
  - Ajouter checkbox "🧠 Mode Réflexion"
  - Position: À côté du mode conversation
  - Event handler: Active/désactive thinking mode
  - Indicateur visuel quand actif

- [ ] **AFFICHER RAISONNEMENT DANS UI**
  - Modifier zone texte pour afficher:
    - Raisonnement (si thinking mode)
    - Séparateur visuel
    - Réponse finale
  - Format:
    ```
    🧠 Raisonnement:
    1. [étape 1]
    2. [étape 2]
    ---
    💬 Réponse: [réponse finale]
    ```

---

### Phase 4: Nettoyage et Tests (30 min)

- [ ] **NETTOYER CACHE PYTHON**
  - Commande: `find . -name "*.pyc" -delete`
  - Commande: `find . -name "__pycache__" -type d -exec rm -rf {} +`

- [ ] **TEST 1: Mode Normal - Question Simple**
  - Lancer: `python3 launcher.py`
  - Question: "Bonjour, comment vas-tu?"
  - Vérifier: Réponse rapide et concise
  - Mesurer: Temps de réponse
  - Attendu: ~20-25s (vs 50s avant)

- [ ] **TEST 2: Mode Normal - Question Complexe**
  - Question: "Explique-moi la différence entre Python et Java"
  - Vérifier: Réponse structurée
  - Attendu: ~25-30s

- [ ] **TEST 3: Thinking Mode - Question Mathématique**
  - Activer: Mode réflexion
  - Question: "Si j'ai 15 pommes et j'en donne 1/3 à Pierre, combien m'en reste-t-il?"
  - Vérifier: 
    - Affichage du raisonnement étape par étape
    - Réponse correcte (10 pommes)
  - Attendu: ~30-40s (plus lent car raisonnement)

- [ ] **TEST 4: Thinking Mode - Question Logique**
  - Question: "Pourquoi le ciel est-il bleu?"
  - Vérifier: Raisonnement scientifique visible
  - Attendu: Explication étape par étape

- [ ] **TEST 5: Conversation Multi-tours**
  - Test: 3 questions consécutives
  - Vérifier: Pas de blocage
  - Vérifier: Contexte maintenu

- [ ] **TEST 6: RAG avec Documents**
  - Ajouter doc: `data/documents/test_phi3.txt`
  - Question: Sur contenu du document
  - Vérifier: Récupération contexte fonctionne

---

### Phase 5: Benchmarking et Documentation (30 min)

- [ ] **BENCHMARK LATENCE**
  - Script: `scripts/benchmark_pipeline.py`
  - Mesures:
    - Temps STT (devrait rester ~3-5s)
    - Temps LLM Phi-3 (attendu ~20-25s)
    - Temps TTS (devrait rester ~1-2s)
    - Total (attendu ~25-32s vs 50s avant)
  - Sauvegarder: `logs/performance/phi3_benchmark.json`

- [ ] **COMPARER QUALITÉ**
  - 10 questions test
  - Comparer réponses Llama 3.1 vs Phi-3
  - Noter:
    - Précision
    - Pertinence
    - Style
    - Longueur

- [ ] **METTRE À JOUR CHANGELOG.md**
  - Ajouter section v1.0.2
  - Documenter:
    - Migration Phi-3-mini
    - Ajout thinking mode
    - Gains de performance
    - Breaking changes (si applicable)

- [ ] **METTRE À JOUR README.md**
  - Section "Modèles":
    - Remplacer Llama 3.1 par Phi-3-mini
    - Ajouter specs Phi-3
  - Section "Fonctionnalités":
    - Ajouter mode thinking
  - Section "Performance":
    - Mettre à jour benchmarks

---

## 🔧 FICHIERS À MODIFIER (Résumé)

| Fichier | Action | Priorité |
|---------|--------|----------|
| `models/` | Télécharger Phi-3 | 🔴 Critique |
| `config/system_config.py` | Config LLM + thinking | 🔴 Critique |
| `agents/rag_agent.py` | Format prompt + stop | 🔴 Critique |
| `agents/llm_agent.py` | Format prompt | 🟡 Important |
| `utils/thinking_mode.py` | Nouveau module | 🟡 Important |
| `interface/qaia_interface.py` | Toggle + UI | 🟡 Important |
| `README.md` | Documentation | 🟢 Optionnel |
| `CHANGELOG.md` | Historique | 🟢 Optionnel |

---

## ⚠️ POINTS D'ATTENTION

### Différences Critiques Llama → Phi-3

1. **Format Prompt:**
   - Llama: `<|im_start|>...<|im_end|>`
   - Phi-3: `<|system|>...<|end|>`
   - ❌ Ne PAS mélanger les formats!

2. **Stop Tokens:**
   - Llama: `<|im_end|>`
   - Phi-3: `<|end|>`
   - Important pour arrêt génération

3. **Context Window:**
   - Llama: 128K natif
   - Phi-3: 4K natif
   - ✅ 2048 tokens OK pour les deux

4. **Temperature:**
   - Llama optimal: 0.7
   - Phi-3 optimal: 0.5-0.6
   - Ajuster pour meilleure qualité

5. **Thinking Mode:**
   - Nouveau concept
   - Augmente latence (+30-50%)
   - Optionnel, à activer manuellement

---

## 📊 RÉSULTATS ATTENDUS

### Performance

| Métrique | Avant (Llama 8B) | Après (Phi-3 3.8B) | Gain |
|----------|------------------|-------------------|------|
| Latence LLM | 48s | 20-25s | -50% |
| Latence totale | 50-55s | 25-32s | -45% |
| Qualité | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | -10% |
| Contexte max | 128K | 4K | -97% |

### Fonctionnalités

- ✅ Mode normal: Conversation rapide
- ✅ Thinking mode: Raisonnement visible
- ✅ Compatibilité RAG: 100%
- ✅ Interface: Inchangée (+ toggle)

---

## 🚀 TEMPS ESTIMÉ TOTAL

- Phase 1: Téléchargement + Config = **30 min**
- Phase 2: Format prompt = **20 min**
- Phase 3: Thinking mode = **40 min**
- Phase 4: Tests = **30 min**
- Phase 5: Documentation = **30 min**

**TOTAL: ~2h30**

---

## ✅ CRITÈRES DE SUCCÈS

- [ ] Phi-3 génère des réponses cohérentes
- [ ] Latence réduite de ~45%
- [ ] Thinking mode fonctionne
- [ ] Pas de blocage à la 2ème question
- [ ] RAG fonctionne avec Phi-3
- [ ] Tests passent tous
- [ ] Documentation à jour

---

**Prêt à commencer!** 🚀

