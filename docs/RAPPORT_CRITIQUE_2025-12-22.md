# Rapport Critique - 22 Décembre 2025

**Date** : 2025-12-22 18:42  
**Statut** : 🔴 PROBLÈMES CRITIQUES NON RÉSOLUS  
**Priorité** : 🔴 URGENTE

---

## 📊 ANALYSE OBJECTIVE DES LOGS

### Logs Observés (18:42-18:43)

```
2025-12-22 18:43:28,507 - TTS UI (streaming): déclenchement, longueur=109
2025-12-22 18:43:29,258 - TTS UI (streaming): lancé (non bloquant)
2025-12-22 18:43:31,475 - TTS UI (streaming): déclenchement, longueur=109
2025-12-22 18:43:32,412 - TTS UI (streaming): lancé (non bloquant)
2025-12-22 18:43:34,774 - TTS UI (streaming): déclenchement, longueur=109
2025-12-22 18:43:35,289 - TTS UI (streaming): lancé (non bloquant)
```

**CONSTAT** : Le TTS est déclenché **3 fois** avec la même longueur (109 caractères).

---

## 🔴 PROBLÈMES IDENTIFIÉS

### 1. TTS DÉCLENCHÉ 3 FOIS (CRITIQUE)

**Symptôme** : Le TTS est appelé 3 fois pour la même réponse  
**Cause probable** : `_on_llm_complete()` est appelé plusieurs fois OU plusieurs événements `llm.complete` sont émis  
**Impact** : Répétition vocale, confusion utilisateur  
**Fichier concerné** : `interface/qaia_interface.py` ligne 548-582

**Hypothèses** :
1. Plusieurs événements `llm.complete` émis par le RAG agent
2. `_on_llm_complete()` appelé plusieurs fois (abonnements multiples ?)
3. TTS déclenché à la fois dans `_on_llm_complete()` ET ailleurs

**Code problématique** :
```python
# interface/qaia_interface.py:548
def _on_llm_complete(self, event_data: dict):
    # ...
    if cleaned_streamed:
        threading.Thread(target=_speak_streamed, args=(cleaned_streamed,), daemon=True).start()
```

---

### 2. DOUBLONS "(18:42) QAIA:" PERSISTANTS (CRITIQUE)

**Symptôme** : `(18:42) QAIA: (18:42) QAIA: Bonjour Claude...`  
**Cause** : Les corrections dans `process_streamed_text()` ne sont PAS appliquées correctement  
**Impact** : Texte illisible, TTS répète les préfixes  
**Fichier concerné** : `utils/text_processor.py`

**Analyse** :
- Les corrections ont été ajoutées dans `process_streamed_text()`
- MAIS le texte affiché contient encore les doublons
- **HYPOTHÈSE** : Le texte n'est pas passé par `process_streamed_text()` avant affichage

**Vérification nécessaire** :
- Le texte streamé est-il nettoyé AVANT d'être affiché dans `StreamingTextDisplay` ?
- `_on_llm_token()` applique-t-il le nettoyage ?

---

### 3. PRÉSENTATION RÉPÉTÉE 3 FOIS (CRITIQUE)

**Symptôme** : "Bonjour, je suis QAIA..." répété 3 fois  
**Cause** : 
1. Présentation au démarrage (bienvenue)
2. Présentation dans la première réponse LLM
3. Présentation répétée dans les réponses suivantes

**Impact** : Verbosité excessive, frustration utilisateur  
**Fichiers concernés** :
- `interface/qaia_interface.py` ligne 1536 (bienvenue)
- `agents/llm_agent.py` ligne 169-179 (prompt système)
- `qaia_core.py` ligne 96-502 (flag `_first_interaction`)

**Problème identifié** :
- Le flag `_first_interaction` n'est PAS réinitialisé à la fermeture
- L'historique de conversation n'est PAS vidé à la fermeture
- À la réouverture, le système pense que c'est encore la première interaction

---

### 4. NETTOYAGE INCOMPLET À LA FERMETURE (CRITIQUE)

**Symptôme** : L'historique et les flags ne sont pas réinitialisés  
**Cause** : `_on_closing()` ne nettoie pas l'historique ni `_first_interaction`  
**Impact** : État persistant entre les sessions, bugs accumulés  
**Fichier concerné** : `interface/qaia_interface.py` ligne 637-678

**Code actuel** :
```python
def _on_closing(self):
    # ...
    # ❌ MANQUE : Réinitialisation _first_interaction
    # ❌ MANQUE : Vidage conversation_history
    # ❌ MANQUE : Appel qaia.clear_conversation()
```

**Code manquant** :
```python
if qaia is not None:
    qaia.clear_conversation()  # ❌ MANQUE
    qaia._first_interaction = True  # ❌ MANQUE (pour prochaine session)
```

---

## 🔍 ANALYSE TECHNIQUE DÉTAILLÉE

### Flux de Génération LLM

```
1. qaia_core.process_message()
   └─> llm_agent.chat(is_first_interaction=self._first_interaction)
       └─> rag_agent.process_query()
           └─> StreamingCallback.on_llm_new_token()
               └─> Event Bus 'llm.token'
                   └─> qaia_interface._on_llm_token()
                       └─> StreamingTextDisplay.append_token()
           └─> StreamingCallback.on_llm_end()
               └─> Event Bus 'llm.complete'
                   └─> qaia_interface._on_llm_complete()
                       └─> TTS déclenché (PROBLÈME ICI)
```

**Question** : Pourquoi `_on_llm_complete()` est-il appelé 3 fois ?

**Hypothèses** :
1. **Plusieurs abonnements** : `event_bus.subscribe('llm.complete', ...)` appelé plusieurs fois ?
2. **Plusieurs événements** : Le RAG agent émet plusieurs événements `llm.complete` ?
3. **TTS multiple** : Le TTS est déclenché ailleurs aussi (dans `_process_text_thread()` ?)

---

### Flux de Nettoyage Texte

```
1. LLM génère: "(18:42) QAIA: (18:42) QAIA: Bonjour..."
2. StreamingCallback.on_llm_new_token()
   └─> filter_streaming_token() (filtre les préfixes)
   └─> Event Bus 'llm.token'
       └─> _on_llm_token()
           └─> append_token() (AFFICHE SANS NETTOYAGE ?)
3. StreamingCallback.on_llm_end()
   └─> Event Bus 'llm.complete'
       └─> _on_llm_complete()
           └─> get_streamed_text() (récupère texte brut)
           └─> process_streamed_text() (NETTOIE)
           └─> TTS avec texte nettoyé
```

**PROBLÈME** : Le texte est affiché AVANT nettoyage dans `append_token()`

---

## ✅ CORRECTIONS NÉCESSAIRES

### 1. Empêcher TTS Multiple

**Action** : Ajouter un flag pour empêcher les appels TTS multiples

```python
def _on_llm_complete(self, event_data: dict):
    if getattr(self, '_tts_already_triggered', False):
        return  # Déjà déclenché
    self._tts_already_triggered = True
    # ... reste du code ...
    # Réinitialiser après TTS
    self._tts_already_triggered = False
```

### 2. Nettoyer Texte AVANT Affichage

**Action** : Appliquer `filter_streaming_token()` dans `append_token()`

```python
def append_token(self, token: str):
    from utils.text_processor import filter_streaming_token
    filtered = filter_streaming_token(token)
    if filtered:
        # Afficher
```

### 3. Réinitialiser État à la Fermeture

**Action** : Ajouter dans `_on_closing()`

```python
if qaia is not None:
    qaia.clear_conversation()
    qaia._first_interaction = True  # Pour prochaine session
```

### 4. Vérifier Abonnements Multiples

**Action** : Vérifier que `event_bus.subscribe()` n'est pas appelé plusieurs fois

---

## 📋 TODO LISTE PRIORITAIRE

### 🔴 URGENT (Bloquant)

1. **Empêcher TTS multiple** : Ajouter flag `_tts_already_triggered`
2. **Nettoyer texte avant affichage** : Appliquer `filter_streaming_token()` dans `append_token()`
3. **Réinitialiser état à la fermeture** : Ajouter `clear_conversation()` et `_first_interaction = True`
4. **Vérifier abonnements** : S'assurer qu'il n'y a qu'un seul abonnement à `llm.complete`

### 🟡 IMPORTANT (Non bloquant mais critique)

5. **Logs détaillés** : Ajouter logs pour tracer les appels TTS
6. **Tests** : Créer tests pour vérifier qu'il n'y a qu'un seul appel TTS
7. **Documentation** : Documenter le flux complet de génération

---

## 🎯 RÉSULTAT ATTENDU

Après corrections :
- ✅ **1 seul appel TTS** par réponse
- ✅ **Texte sans doublons** dans l'interface
- ✅ **Présentation unique** au démarrage uniquement
- ✅ **État réinitialisé** à chaque fermeture

---

**Date** : 2025-12-22  
**Auteur** : Audit automatique  
**Statut** : 🔴 EN ATTENTE DE CORRECTIONS

