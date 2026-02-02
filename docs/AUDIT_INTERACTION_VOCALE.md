# Audit complet – Interaction conversationnelle vocale

**Date** : 27 janvier 2026  
**Objectif** : Identifier et corriger tous les bugs du flux STT → LLM → affichage → TTS (mode desktop, entrée vocale ou texte).

---

## 1. Flux global

```
[Micro / PTT] → STT (wav2vec) → transcription
     → Interface (_process_text_thread)
     → QAIACore.process_message()
     → DialogueManager.process_message()
     → IntentDetector / CommandGuard / LLM
     → llm_agent.chat()  [non-streaming appel]
          → process_query() dans rag_agent
          → LlamaCpp.invoke() avec StreamingCallback
          → Event Bus: llm.start, llm.token, llm.complete (ou llm.error)
     → Interface: _on_llm_start, append_token, _on_llm_complete
     → replace_current_message(cleaned_streamed) + TTS (speak)
```

- **Important** : Le flux utilise toujours `llm_agent.chat()` (pas `chat_stream`). Le streaming affiché vient du **StreamingCallback** LangChain lors de `llm.invoke()` dans `process_query()`.

---

## 2. Bugs identifiés et corrections

### 2.1 Erreur `unsupported operand type(s) for *: 'NoneType' and 'int'`

| Cause | Fichier | Correction |
|-------|---------|------------|
| `llm_agent.chat()` utilisait `max_tokens * 4` alors que `max_tokens` peut être `None` (appel sans argument depuis `dialogue_manager`). | `agents/llm_agent.py` | Initialisation défensive : `max_tokens = (MODEL_CONFIG.get("llm") or {}).get("max_tokens", 512)` puis `max_tokens = int(max_tokens) if max_tokens is not None else 512` **avant** toute utilisation. Appliqué dans `chat()` et `chat_stream()`. |

**Vérification** : Relancer une conversation (texte ou vocale) ; l’erreur ne doit plus apparaître.

---

### 2.2 Doublon de préfixe « (HH:MM) QAIA: (HH:MM) QAIA: »

| Cause | Fichier | Correction |
|-------|---------|------------|
| L’UI ajoute « (HH:MM) QAIA: » via `start_generation("QAIA")`, et le modèle peut générer le même préfixe dans le texte streamé. | `interface/components/streaming_text.py` | Dans `replace_current_message()` : suppression de tout préfixe « (HH:MM) QAIA: » en début de `new_text` avant insertion. |
| En cas d’erreur LLM pendant le streaming, un second bloc était ajouté avec `add_message("QAIA", erreur)` au lieu de réutiliser le bloc en cours. | `interface/qaia_interface.py` | Dans `_on_llm_error()` : si `_is_streaming` est vrai, appel à `replace_current_message(erreur)` puis `complete_generation()` et `add_spacing(4)` au lieu de `add_message()`. |

**Vérification** : Plus aucun affichage du type « (16:15) QAIA: (16:15) QAIA: … » dans une même bulle ou en double bloc.

---

### 2.3 Réponse dupliquée / garbled (ex. « Je suis là… » puis « Suis là pourvus aider… »)

| Cause | Fichier | Correction |
|-------|---------|------------|
| Le modèle répète la même phrase avec des variantes BPE (espaces, typos), ce qui donne une phrase correcte suivie d’une quasi-copie déformée. | `utils/text_processor.py` | Nouvelle fonction `_remove_duplicate_consecutive_sentences()` : découpage en phrases, similarité Jaccard entre phrases consécutives ; si ≥ 0,65, la seconde est supprimée. Appelée dans `process_streamed_text()` après corrections BPE. |

**Vérification** : Les réponses ne doivent plus contenir deux phrases consécutives quasi identiques (une correcte et une garbled).

---

### 2.4 Décalage TTS (voix qui démarre longtemps après le texte)

| Cause | Fichier | Correction (déjà faite) |
|-------|---------|--------------------------|
| Le TTS était lancé après la mise à jour UI. | `interface/qaia_interface.py` | Dans `_on_llm_complete()` : le thread TTS est démarré **avant** `root.after(0, replace_current_message)` pour réduire le délai perçu. |

**Vérification** : La voix doit commencer au plus tôt après l’affichage du texte (le premier appel Piper peut rester lent ; c’est un effet moteur TTS).

---

## 3. Plan de vérification

### 3.1 Tests manuels (obligatoires après chaque correction)

1. **Erreur NoneType * int**
   - Lancer QAIA (desktop), envoyer un message texte ou vocal.
   - Vérifier qu’aucun message « Erreur lors de la génération de réponse: unsupported operand type(s) for *: 'NoneType' and 'int' » n’apparaît.
   - Si l’erreur apparaît encore : vérifier que `agents/llm_agent.py` contient bien l’initialisation défensive de `max_tokens` dans `chat()` et `chat_stream()`, puis redémarrer l’application.

2. **Doublon préfixe**
   - Envoyer plusieurs messages (texte et/ou vocal).
   - Vérifier qu’aucune bulle ne commence par « (HH:MM) QAIA: (HH:MM) QAIA: ».
   - Provoquer une erreur (ex. couper le modèle / crash) pendant une génération : le message d’erreur doit remplacer le contenu de la bulle en cours, pas créer une seconde bulle « (HH:MM) QAIA: Erreur… ».

3. **Réponse dupliquée / garbled**
   - Poser une question qui génère une réponse un peu longue (ex. bien-être, conseils).
   - Vérifier qu’il n’y a pas deux phrases consécutives quasi identiques (une correcte et une avec « pourvus », « foule », etc.).

4. **TTS**
   - Vérifier que la synthèse vocale se déclenche après la réponse et que le délai entre affichage du texte et début de la voix est raisonnable (sans garantie sur le tout premier appel Piper).

### 3.2 Tests automatisés suggérés

- **`tests/test_llm_agent_chat.py`** : appeler `llm_agent.chat(message)` **sans** `max_tokens` et vérifier qu’aucune exception `TypeError` (NoneType * int) n’est levée.
- **`utils/text_processor.py`** : test unitaire pour `_remove_duplicate_consecutive_sentences()` avec un texte contenant deux phrases très similaires ; vérifier qu’une seule est conservée.
- **`interface/components/streaming_text.py`** : test que `replace_current_message("(16:15) QAIA: Bonjour")` n’insère pas « (16:15) QAIA: » en double (le texte inséré doit être « Bonjour »).

### 3.3 Checklist après déploiement

- [ ] Redémarrer l’application après modification du code (pour charger `llm_agent`, `text_processor`, `streaming_text`, `qaia_interface`).
- [ ] Vérifier que `config/system_config.py` contient bien `"max_tokens": 512` (ou une valeur entière) sous `"llm"`.
- [ ] Tester au moins une conversation complète (texte + vocal) sans erreur affichée et sans doublon de préfixe.

---

## 4. Fichiers modifiés (résumé)

| Fichier | Modifications |
|---------|----------------|
| `agents/llm_agent.py` | Initialisation défensive de `max_tokens` dans `chat()` et `chat_stream()` (évite NoneType * int). |
| `interface/qaia_interface.py` | `_on_llm_error()` : en streaming, remplacer le message en cours au lieu d’ajouter un nouveau bloc ; TTS lancé avant `replace_current_message` dans `_on_llm_complete()`. |
| `interface/components/streaming_text.py` | `replace_current_message()` : suppression du préfixe « (HH:MM) QAIA: » en début de `new_text` avant insertion. |
| `utils/text_processor.py` | `_remove_duplicate_consecutive_sentences()` ; appel dans `process_streamed_text()`. |

---

## 5. Références

- **Prompt système (préfixes)** : `agents/llm_agent.py` (règles « NE JAMAIS inclure (HH:MM) QAIA: »).
- **Filtrage streaming** : `agents/callbacks/streaming_callback.py` (buffer + `filter_streaming_token`), `utils/text_processor.py` (`remove_prefix_patterns`, `process_streamed_text`).
- **Config LLM** : `config/system_config.py` → `MODEL_CONFIG["llm"]["max_tokens"]`.
