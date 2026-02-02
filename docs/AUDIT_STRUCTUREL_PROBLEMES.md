# Audit Structurel - Problèmes Identifiés

**Date** : 2025-12-22  
**Statut** : 🔴 CRITIQUE - Problèmes structurels profonds  
**Priorité** : 🔴 HAUTE

---

## 📋 TODO Liste Professionnelle

### 🔴 CRITIQUE - Problèmes Bloquants

#### 1. **Synchronisation Texte/TTS Cassée**
- **Symptôme** : Le TTS ne finit pas de dire ce qui est écrit
- **Cause** : En mode streaming, le texte complet n'est jamais récupéré pour le TTS
- **Fichiers concernés** :
  - `interface/qaia_interface.py` : `_on_llm_complete()` ne récupère pas le texte complet
  - `interface/components/streaming_text.py` : `StreamingTextDisplay` n'expose pas le texte complet
  - `agents/callbacks/streaming_callback.py` : `on_llm_end()` reçoit la réponse mais ne l'émet pas
- **Impact** : TTS lit seulement une partie du texte affiché
- **Solution** : Stocker le texte complet dans `StreamingTextDisplay` et le récupérer dans `_on_llm_complete()` pour le TTS

#### 2. **Répétition Forcée de la Présentation**
- **Symptôme** : "Je suis QAIA, votre assistante multimodale intelligente et de qualité" répétée avant chaque réponse
- **Cause** : Prompt système ligne 100 dans `config/system_config.py` force cette présentation
- **Fichiers concernés** :
  - `config/system_config.py` : Ligne 100 `"Quand tu te présentes, tu dois dire..."`
  - `agents/llm_agent.py` : Construction du prompt système
- **Impact** : Répétition inutile, verbosité excessive
- **Solution** : Modifier le prompt pour ne se présenter qu'une seule fois (première interaction)

#### 3. **Doublons "(HH:MM) QAIA:" Persistants**
- **Symptôme** : Les doublons `(15:54) QAIA: QAIA:` persistent malgré le nettoyage
- **Cause** : 
  - Le modèle génère ces préfixes dans sa réponse
  - Le nettoyage est appliqué APRÈS la génération, mais le modèle continue de les générer
  - Le prompt système peut encourager cette génération
- **Fichiers concernés** :
  - `agents/rag_agent.py` : Nettoyage après génération
  - `interface/qaia_interface.py` : Nettoyage avant affichage
  - `config/system_config.py` : Prompt système
- **Impact** : Affichage incohérent, confusion utilisateur
- **Solution** : 
  - Modifier le prompt pour interdire explicitement ces préfixes
  - Améliorer le nettoyage pour être plus agressif
  - Ajouter un post-traitement de correction

#### 4. **Fautes d'Orthographe dans les Réponses**
- **Symptôme** : "dran" au lieu de "de", "lorsqueil" au lieu de "lorsqu'il"
- **Cause** : Le modèle Phi-3 génère des erreurs d'orthographe (limitation du modèle)
- **Fichiers concernés** :
  - `agents/rag_agent.py` : Post-traitement des réponses
  - `interface/qaia_interface.py` : Post-traitement avant affichage/TTS
- **Impact** : Qualité de réponse dégradée, professionnalisme affecté
- **Solution** : Ajouter un correcteur orthographique français (pyspellchecker ou language-tool-python)

### 🟡 MOYEN - Problèmes de Qualité

#### 5. **Flux de Traitement Incohérent**
- **Symptôme** : Incohérences entre streaming, affichage et TTS
- **Cause** : Plusieurs chemins de traitement (streaming vs non-streaming) avec logique différente
- **Fichiers concernés** :
  - `qaia_core.py` : `process_message()` retourne la réponse
  - `interface/qaia_interface.py` : `_process_text_thread()` gère l'affichage et TTS
  - `agents/rag_agent.py` : Génération avec/sans RAG
- **Impact** : Comportement incohérent, bugs difficiles à reproduire
- **Solution** : Unifier le flux de traitement avec un seul point de sortie pour affichage/TTS

#### 6. **Post-Traitement des Réponses Incomplet**
- **Symptôme** : Nettoyage appliqué à des endroits différents avec des résultats différents
- **Cause** : Nettoyage dupliqué dans `rag_agent.py` et `qaia_interface.py`
- **Fichiers concernés** :
  - `agents/rag_agent.py` : Nettoyage après génération
  - `interface/qaia_interface.py` : Nettoyage avant affichage
- **Impact** : Incohérences, code dupliqué
- **Solution** : Centraliser le post-traitement dans une fonction unique

---

## 🔍 Analyse Détaillée des Problèmes

### Problème 1 : Synchronisation Texte/TTS

**Flux actuel (CASSÉ)** :
```
LLM génère → StreamingCallback.on_llm_new_token() → Event Bus 'llm.token' 
→ qaia_interface._on_llm_token() → StreamingTextDisplay.append_token()
→ StreamingCallback.on_llm_end() → Event Bus 'llm.complete'
→ qaia_interface._on_llm_complete() → StreamingTextDisplay.complete_generation()
→ qaia_core.process_message() retourne response
→ qaia_interface._process_text_thread() utilise response pour TTS
```

**Problème** : `response` dans `_process_text_thread()` est la réponse finale du LLM, mais si le streaming est actif, le texte affiché dans `StreamingTextDisplay` peut être différent (tokens accumulés). Le TTS utilise `response` qui peut être tronqué ou différent.

**Solution** : 
1. Stocker le texte complet dans `StreamingTextDisplay` pendant le streaming
2. Dans `_on_llm_complete()`, récupérer le texte complet depuis `StreamingTextDisplay`
3. Utiliser ce texte complet pour le TTS

### Problème 2 : Répétition de la Présentation

**Cause** : Ligne 100 dans `system_config.py` :
```python
"Quand tu te présentes, tu dois dire « Je suis QAIA, votre assistante multimodale intelligente et de qualité »."
```

Le modèle interprète "Quand tu te présentes" comme "à chaque fois que tu réponds", pas "une seule fois au début".

**Solution** : Modifier le prompt pour :
- Se présenter UNIQUEMENT lors de la première interaction
- Ne pas répéter la présentation dans les réponses suivantes
- Utiliser un flag de contexte pour savoir si c'est la première interaction

### Problème 3 : Doublons "(HH:MM) QAIA:"

**Cause** : Le modèle Phi-3 génère naturellement des préfixes de formatage. Le nettoyage regex ne capture pas tous les cas.

**Solution** :
1. Ajouter dans le prompt système : "NE JAMAIS inclure de préfixes comme '(HH:MM) QAIA:' ou 'QAIA:' dans tes réponses"
2. Améliorer le nettoyage pour être plus agressif (multi-passes, insensible à la casse)
3. Ajouter un post-traitement qui supprime TOUS les préfixes avant affichage/TTS

### Problème 4 : Fautes d'Orthographe

**Cause** : Limitation du modèle Phi-3 (3.8B) qui génère parfois des erreurs d'orthographe.

**Solution** : Ajouter un correcteur orthographique français :
- Utiliser `pyspellchecker` ou `language-tool-python`
- Appliquer la correction après le nettoyage des préfixes
- Corriger les erreurs courantes : "dran" → "de", "lorsqueil" → "lorsqu'il"

---

## 📝 Plan d'Action

### Phase 1 : Corrections Critiques (Priorité 🔴)

1. **Corriger la synchronisation Texte/TTS**
   - Modifier `StreamingTextDisplay` pour stocker le texte complet
   - Modifier `_on_llm_complete()` pour récupérer le texte complet
   - Utiliser ce texte pour le TTS

2. **Corriger la répétition de la présentation**
   - Modifier le prompt système dans `system_config.py`
   - Ajouter un flag de première interaction dans `qaia_core.py`
   - Adapter le prompt selon le flag

3. **Corriger les doublons "(HH:MM) QAIA:"**
   - Améliorer le prompt pour interdire ces préfixes
   - Renforcer le nettoyage (multi-passes, insensible à la casse)
   - Ajouter un post-traitement final

### Phase 2 : Améliorations Qualité (Priorité 🟡)

4. **Ajouter correcteur orthographique**
   - Installer `pyspellchecker` ou `language-tool-python`
   - Créer une fonction de correction orthographique
   - L'appliquer après le nettoyage des préfixes

5. **Unifier le flux de traitement**
   - Centraliser le post-traitement dans une fonction unique
   - S'assurer que le même texte est utilisé partout (affichage, TTS, logs)

---

## 🎯 Critères de Succès

- ✅ TTS lit exactement le même texte que celui affiché
- ✅ Pas de répétition de la présentation après la première interaction
- ✅ Aucun doublon "(HH:MM) QAIA:" dans les réponses
- ✅ Fautes d'orthographe corrigées automatiquement
- ✅ Flux de traitement cohérent et unifié

---

**Dernière mise à jour** : 2025-12-22  
**Auteur** : Audit structurel automatique

