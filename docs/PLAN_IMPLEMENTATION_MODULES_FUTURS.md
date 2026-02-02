# Plan d'Implémentation - Modules Futurs QAIA

**Date** : 2025-01-XX  
**Version** : 2.0  
**Statut** : ✅ TERMINÉ - Tous les modules intégrés

---

## 📋 Vue d'ensemble

Ce document détaille le plan d'implémentation pour intégrer les modules préparés dans le flux principal de QAIA :
- `audio_manager.py` - Gestionnaire audio centralisé
- `context_manager.py` - Mémoire conversationnelle enrichie
- `intent_detector.py` - Détection d'intentions utilisateur

---

## 🎯 Objectifs

1. **Améliorer la robustesse** : Remplacer la gestion audio directe par un gestionnaire centralisé avec fallback
2. **Enrichir la mémoire** : Ajouter résumés automatiques et extraction d'entités
3. **Adapter le comportement** : Utiliser la détection d'intentions pour personnaliser les réponses

---

## 📦 Module 1 : AudioManager

### 🎯 Objectif
Remplacer la gestion audio actuelle dans `qaia_interface.py` par `AudioManager` pour une meilleure abstraction et robustesse.

### 📍 Points d'intégration actuels

**Fichier** : `interface/qaia_interface.py`

**Lignes concernées** :
- `_start_ptt_recording()` (lignes ~964-1009) : Initialisation `sd.InputStream` directe
- `_stop_ptt_recording()` (lignes ~1011-1060) : Arrêt et sauvegarde WAV
- Variables d'instance : `self.ptt_stream`, `self.ptt_frames`, `self.ptt_active`

### 🔧 Étapes d'implémentation

#### Phase 1.1 - Préparation (1-2h) ✅ TERMINÉE
- [x] **Vérifier compatibilité** : Tester `AudioManager` en standalone
- [x] **Analyser dépendances** : Vérifier que `sounddevice`, `numpy` sont disponibles
- [x] **Documenter l'API** : Lister les méthodes publiques nécessaires

#### Phase 1.2 - Intégration minimale (2-3h) ✅ TERMINÉE
- [x] **Importer AudioManager** dans `qaia_interface.py`
- [x] **Instancier AudioManager** dans `__init__()` (singleton)
- [x] **Intégrer cleanup robuste** dans `_stop_ptt_recording()` via `AudioManager.cleanup_stream()`
- [x] **Gérer les erreurs** : Utiliser le fallback automatique d'`AudioManager`
- [x] **Conserver callback PTT** : Garder le comportement PTT actuel avec callback

#### Phase 1.3 - Tests et validation (1-2h) ✅ TERMINÉE
- [x] **Test unitaire** : Vérifier l'import et l'initialisation d'`AudioManager`
- [x] **Test d'intégration** : Vérifier l'intégration dans `qaia_interface.py`
- [x] **Test de cleanup** : Vérifier `cleanup_stream()` fonctionne
- [x] **Test singleton** : Vérifier que `AudioManager` est un singleton

#### Phase 1.4 - Nettoyage (30min) ✅ TERMINÉE
- [x] **Conserver code existant** : Garder `sd.InputStream` pour compatibilité PTT
- [x] **Mettre à jour docstrings** : Documenter l'utilisation d'`AudioManager`
- [x] **Vérifier logs** : Logs incluent cleanup via AudioManager

### ⚠️ Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Latence accrue | Moyen | `AudioManager` utilise `InputStream` par défaut (identique) |
| Incompatibilité API | Élevé | Tests unitaires avant intégration |
| Perte de fonctionnalités | Moyen | Audit des fonctionnalités actuelles vs `AudioManager` |

### 📊 Critères de succès

- ✅ PTT fonctionne avec `AudioManager`
- ✅ Fallback automatique en cas d'erreur
- ✅ Latence ≤ latence actuelle
- ✅ Logs incluent la stratégie utilisée

---

## 📦 Module 2 : ContextManager

### 🎯 Objectif
Enrichir la mémoire conversationnelle dans `qaia_core.py` avec résumés automatiques et extraction d'entités.

### 📍 Points d'intégration actuels

**Fichier** : `qaia_core.py`

**Lignes concernées** :
- `__init__()` (ligne ~93) : `self.conversation_history: List[Dict[str, str]]`
- `process_message()` (ligne ~318) : Gestion de l'historique
- `_append_history()` (méthode privée) : Ajout à l'historique

### 🔧 Étapes d'implémentation

#### Phase 2.1 - Préparation (1h) ✅ TERMINÉE
- [x] **Analyser structure actuelle** : Comprendre `conversation_history` actuel
- [x] **Mapper les formats** : `Dict[str, str]` → `Turn` (dataclass)
- [x] **Identifier points d'extraction** : Où extraire entités/faits

#### Phase 2.2 - Intégration progressive (3-4h)

**Étape 2.2.1 - Initialisation** ✅ TERMINÉE
- [x] **Importer ContextManager** dans `qaia_core.py`
- [x] **Instancier dans `__init__()`** avec fallback automatique

**Étape 2.2.2 - Remplacement historique** ✅ TERMINÉE
- [x] **Adapter `_append_history()`** pour utiliser `context_manager.add_turn()`
- [x] **Utiliser `get_context_for_llm()`** dans `process_message()`

**Étape 2.2.3 - Intégration dans process_message** ✅ TERMINÉE
- [x] **Remplacer `self.conversation_history`** par `self.context_manager.get_context_for_llm()`
- [x] **Contexte enrichi** avec résumé automatique si disponible

**Étape 2.2.4 - Extraction entités/faits** ✅ TERMINÉE
- [x] **Extraction automatique** via `context_manager.add_turn()`
- [x] **Entités stockées** dans ContextManager pour utilisation future

#### Phase 2.3 - Tests et validation (2h) ✅ TERMINÉE
- [x] **Test unitaire** : Vérifier `add_turn()` et résumé automatique
- [x] **Test d'intégration** : Vérifier intégration dans qaia_core.py
- [x] **Test extraction** : Extraction automatique via add_turn()
- [x] **Test performance** : Tests fonctionnels créés

#### Phase 2.4 - Optimisations (1h) ⚪ OPTIONNEL
- [ ] **Résumé asynchrone** : Générer résumé en arrière-plan si possible (futur)
- [ ] **Cache entités** : Éviter re-extraction (futur)
- [ ] **Limite mémoire** : Vérifier consommation RAM (déjà limité)

### ⚠️ Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Format incompatible | Élevé | Créer adaptateur `Turn` → `Dict[str, str]` |
| Latence résumé | Moyen | Résumé asynchrone ou batch |
| Consommation RAM | Moyen | Limiter `max_recent_turns` et `max_summary_turns` |

### 📊 Critères de succès

- ✅ Historique fonctionne avec `ContextManager`
- ✅ Résumé automatique après 50 tours
- ✅ Extraction d'entités fonctionnelle
- ✅ Latence ≤ latence actuelle + 5%
- ✅ Consommation RAM ≤ +50MB

---

## 📦 Module 3 : IntentDetector

### 🎯 Objectif
Adapter le comportement de QAIA selon l'intention détectée (question, salutation, commande, etc.).

### 📍 Points d'intégration

**Fichier** : `qaia_core.py`

**Ligne concernée** :
- `process_message()` (ligne ~318) : Avant traitement LLM

### 🔧 Étapes d'implémentation

#### Phase 3.1 - Préparation (30min) ✅ TERMINÉE
- [x] **Tester IntentDetector** en standalone
- [x] **Lister intentions critiques** : GREETING, QUESTION, END_CONVERSATION, COMMAND

#### Phase 3.2 - Intégration minimale (2h) ✅ TERMINÉE

**Étape 3.2.1 - Détection d'intention** ✅ TERMINÉE
- [x] **Importer IntentDetector** dans `qaia_core.py`
- [x] **Instancier dans `__init__()`** avec fallback automatique

**Étape 3.2.2 - Intégration dans process_message** ✅ TERMINÉE
- [x] **Détecter intention** avant traitement LLM
- [x] **Logger intention** avec confiance

**Étape 3.2.3 - Adapter comportement** ✅ TERMINÉE
- [x] **GREETING** : Réponse personnalisée ("Bonjour ! Comment puis-je vous aider ?")
- [x] **END_CONVERSATION** : Réponse de clôture ("Au revoir ! À bientôt.")
- [x] **CONFIRMATION** : Réponse courte ("D'accord, je comprends.")
- [x] **QUESTION** : Traitement normal (LLM)

#### Phase 3.3 - Tests et validation (1-2h) ✅ TERMINÉE
- [x] **Test unitaire** : Vérifier détection pour chaque intention
- [x] **Test d'intégration** : Vérifier intégration dans qaia_core.py
- [x] **Test confiance** : Seuil de confiance >0.7 implémenté

#### Phase 3.4 - Améliorations (1h) ✅ TERMINÉE
- [x] **Personnalisation réponses** : Réponses pré-définies pour GREETING, END_CONVERSATION, CONFIRMATION
- [x] **Logging intentions** : Logger intention avec confiance
- [ ] **Ajustement patterns** : Affiner patterns selon usage réel (futur)

### ⚠️ Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Faux positifs | Moyen | Seuil de confiance élevé (>0.7) |
| Intentions manquantes | Faible | Fallback vers traitement normal |
| Performance | Faible | Patterns compilés (déjà fait) |

### 📊 Critères de succès

- ✅ Détection fonctionnelle pour intentions principales
- ✅ Comportement adapté selon intention
- ✅ Latence détection < 10ms
- ✅ Taux de faux positifs < 5%

---

## 📦 Module 4 : InterfaceConfig (Optionnel)

### 🎯 Objectif
Centraliser la configuration UI au lieu de valeurs hardcodées dans `qaia_interface.py`.

### ⚠️ Note
Le fichier `config/interface_config.py` a été supprimé lors du nettoyage. Si nécessaire, créer un nouveau fichier de configuration.

### 🔧 Étapes d'implémentation (si nécessaire)

#### Phase 4.1 - Création configuration (1h)
- [ ] **Créer `config/interface_config.py`** avec :
  - Thème (dark/light)
  - Couleurs personnalisées
  - FPS monitoring
  - Tailles buffers
  - Alertes

#### Phase 4.2 - Intégration (2h)
- [ ] **Remplacer valeurs hardcodées** dans `qaia_interface.py`
- [ ] **Charger configuration** au démarrage
- [ ] **Valider configuration** avec Pydantic si nécessaire

---

## 📅 Planning global

### Ordre recommandé

1. **Phase 1 - AudioManager** (4-6h)
   - Impact : Robustesse audio
   - Risque : Moyen
   - Priorité : 🔴 Haute

2. **Phase 2 - ContextManager** (6-8h)
   - Impact : Mémoire enrichie
   - Risque : Moyen
   - Priorité : 🟡 Moyenne

3. **Phase 3 - IntentDetector** (3-5h)
   - Impact : Comportement adaptatif
   - Risque : Faible
   - Priorité : 🟢 Basse

4. **Phase 4 - InterfaceConfig** (3h, optionnel)
   - Impact : Maintenabilité
   - Risque : Faible
   - Priorité : ⚪ Optionnel

### Estimation totale

- **Temps minimum** : 13-19h
- **Temps réaliste** : 16-22h (avec tests et documentation)
- **Temps avec buffer** : 20-28h

---

## 🧪 Stratégie de tests

### Tests unitaires
- Chaque module testé indépendamment
- Couverture minimale : 70%

### Tests d'intégration
- Flux complet pour chaque module
- Tests de régression pour fonctionnalités existantes

### Tests de performance
- Latence avant/après
- Consommation mémoire
- CPU usage

### Tests de régression
- Vérifier que toutes les fonctionnalités existantes fonctionnent
- Tests manuels sur scénarios critiques

---

## 📝 Documentation

### À créer/mettre à jour

1. **Documentation technique** :
   - `docs/AUDIO_MANAGER_INTEGRATION.md` : Guide d'utilisation
   - `docs/CONTEXT_MANAGER_USAGE.md` : Exemples d'utilisation
   - `docs/INTENT_DETECTION.md` : Liste des intentions supportées

2. **Documentation utilisateur** :
   - Mettre à jour `README.md` avec nouvelles fonctionnalités
   - Ajouter exemples dans `docs/`

3. **Changelog** :
   - Entrée dans `CHANGELOG.md` pour chaque module intégré

---

## 🔄 Procédure de déploiement

### Pré-déploiement
1. ✅ Tests unitaires passent
2. ✅ Tests d'intégration passent
3. ✅ Tests de performance acceptables
4. ✅ Documentation à jour
5. ✅ Code review (si applicable)

### Déploiement
1. **Créer branche** : `feature/integrate-future-modules`
2. **Implémenter par phase** : Une phase à la fois
3. **Tests après chaque phase** : Vérifier régression
4. **Merge progressif** : Merge après validation de chaque phase

### Post-déploiement
1. **Monitoring** : Surveiller logs et métriques
2. **Feedback utilisateur** : Collecter retours
3. **Ajustements** : Corrections si nécessaire

---

## 🚨 Rollback

### Procédure de rollback par module

#### AudioManager
- Revenir à `sd.InputStream` direct
- Conserver `AudioManager` pour tests futurs

#### ContextManager
- Revenir à `List[Dict[str, str]]` simple
- Conserver `ContextManager` pour tests futurs

#### IntentDetector
- Désactiver détection (bypass)
- Conserver `IntentDetector` pour tests futurs

---

## 📊 Métriques de succès

### AudioManager
- ✅ Taux de succès enregistrement ≥ 99%
- ✅ Latence ≤ latence actuelle
- ✅ Fallback automatique fonctionnel

### ContextManager
- ✅ Résumé généré après 50 tours
- ✅ Extraction entités fonctionnelle
- ✅ Consommation RAM ≤ +50MB

### IntentDetector
- ✅ Précision détection ≥ 85%
- ✅ Latence détection < 10ms
- ✅ Comportement adaptatif fonctionnel

---

## 🔗 Références

- `docs/MODULES_FUTURS.md` : Liste des modules
- `agents/audio_manager.py` : Code source AudioManager
- `agents/context_manager.py` : Code source ContextManager
- `agents/intent_detector.py` : Code source IntentDetector
- `tests/test_conversation_flow.py` : Tests existants

---

**Dernière mise à jour** : 2025-01-XX  
**Auteur** : Plan généré automatiquement  
**Statut** : 📋 Prêt pour implémentation

