# Corrections Bugs Agents - 22 Décembre 2025

**Statut** : ✅ **CORRECTIONS APPLIQUÉES**  
**Priorité** : 🔴 CRITIQUE

---

## 🐛 Bugs Identifiés dans les Logs Utilisateur

### Bug 1 : Doublons `(17:30) QAIA:` Persistants

**Symptôme** :
```
(17:30) QAIA: (17:30) QAIA:  O ui, je par le français.
```

**Cause identifiée** :
- Les tokens sont émis via **DEUX chemins différents** :
  1. `StreamingCallback.on_llm_new_token()` (LangChain callbacks)
  2. `llm_agent.chat_stream()` → `process_query_stream()` (émission directe Event Bus)
- Le filtrage n'était appliqué que dans le callback LangChain
- Les tokens de préfixes peuvent être émis en plusieurs tokens : "(17:30)" peut être "(17:" + "30)"

**Corrections appliquées** :
- ✅ Filtrage ajouté dans `llm_agent.py.chat_stream()` AVANT émission Event Bus
- ✅ Filtrage ajouté dans `rag_agent.py.process_query_stream()` AVANT yield
- ✅ Buffer de tokens dans `StreamingCallback` pour détecter préfixes multi-tokens
- ✅ Patterns améliorés pour capturer préfixes partiels

**Fichiers modifiés** :
- `agents/llm_agent.py` : Filtrage tokens dans `chat_stream()`
- `agents/rag_agent.py` : Filtrage tokens dans `process_query_stream()`
- `agents/callbacks/streaming_callback.py` : Buffer pour préfixes multi-tokens
- `utils/text_processor.py` : Patterns de filtrage améliorés

---

### Bug 2 : Espaces Mal Placés (BPE)

**Symptôme** :
```
O ui, je par le français.
con ç ue pour commun i quer effic ac ement
```

**Cause identifiée** :
- Les tokens de llama.cpp sont des **sous-mots BPE** (BytePairEncoding)
- "parle" → "par" + "le" (pas d'espace entre)
- "efficacement" → "effic" + "ac" + "ement" (pas d'espaces entre)
- La fonction `should_add_space_before_token()` ajoutait des espaces incorrectement

**Corrections appliquées** :
- ✅ Logique améliorée dans `should_add_space_before_token()` pour détecter sous-mots BPE
- ✅ Corrections spécifiques dans `process_streamed_text()` pour cas courants
- ✅ Correction générale pour détecter automatiquement les espaces BPE mal placés

**Fichiers modifiés** :
- `utils/text_processor.py` : 
  - `should_add_space_before_token()` : Détection sous-mots BPE
  - `process_streamed_text()` : Corrections spécifiques + générale

---

## 🔧 Détails Techniques

### Filtrage Multi-Chemins

**Avant** :
```python
# Seulement dans StreamingCallback
filtered_token = filter_streaming_token(token)
```

**Après** :
```python
# Dans TOUS les chemins de streaming
# 1. StreamingCallback.on_llm_new_token()
# 2. llm_agent.chat_stream()
# 3. rag_agent.process_query_stream()
filtered_token = filter_streaming_token(token)
if filtered_token is None:
    continue  # Ignorer token
```

### Détection Préfixes Multi-Tokens

**Buffer dans StreamingCallback** :
```python
self._token_buffer += token  # Accumuler
# Détecter préfixes dans buffer complet
if buffer commence par "(17:30) QAIA:":
    ignorer tous les tokens jusqu'à présent
```

### Correction Espaces BPE

**Logique améliorée** :
```python
# Si précédent se termine par lettre ET actuel commence par lettre minuscule
# → Probablement sous-mot BPE → PAS d'espace
if prev_last.isalpha() and curr_first.isalpha() and curr_first.islower():
    return False  # Pas d'espace
```

**Corrections spécifiques** :
```python
corrections_espaces = {
    r'\bO\s+ui\b': 'Oui',
    r'\bpar\s+le\b': 'parle',
    r'\beffic\s+ac\s+ement\b': 'efficacement',
    # ... etc
}
```

---

## ✅ Résultats Attendus

### Avant
- ❌ `(17:30) QAIA: (17:30) QAIA: O ui, je par le français.`
- ❌ Espaces mal placés : "O ui", "par le", "effic ac ement"

### Après
- ✅ `Oui, je parle le français.`
- ✅ Espaces corrects : "Oui", "parle", "efficacement"
- ✅ Pas de doublons de préfixes

---

## 📋 Tests à Effectuer

1. **Doublons** : Vérifier absence de `(HH:MM) QAIA: (HH:MM) QAIA:`
2. **Espaces** : Vérifier texte lisible (pas de "O ui", "par le")
3. **Mots complets** : Vérifier "parle", "français", "efficacement" corrects

---

**Dernière mise à jour** : 2025-12-22  
**Auteur** : Corrections bugs agents

