# Audit des fichiers obsolètes - QAIA

Date: 2025-01-XX  
**Statut** : ✅ Suppressions effectuées

## Résumé

Cet audit identifie les fichiers qui ne sont plus utilisés, qui sont dupliqués, ou qui nécessitent une attention particulière.

---

## 📁 utils/ - Fichiers obsolètes

### ❌ `event_system.py` - **OBSOLÈTE**
**Statut** : Non utilisé, remplacé  
**Raison** : Remplacé par `interface/events/event_bus.py`  
**Action recommandée** : **SUPPRIMER** ou archiver dans `docs/archive/`  
**Références** : Aucune importation trouvée dans le code actif

### ⚠️ `backup_manager.py` - **NON UTILISÉ**
**Statut** : Non utilisé actuellement  
**Raison** : Aucune importation trouvée  
**Action recommandée** : **CONSERVER** (peut être utile pour sauvegardes futures) ou archiver  
**Note** : Le script `save_qaia.py` existe mais n'utilise pas ce module

---

## 📁 config/ - Fichiers obsolètes

### ❌ `interface_config.py` - **NON UTILISÉ**
**Statut** : Non utilisé  
**Raison** : Aucune importation trouvée  
**Action recommandée** : **SUPPRIMER** ou archiver  
**Note** : Les valeurs sont hardcodées dans `qaia_interface.py`. Ce fichier pourrait être utilisé pour centraliser la config UI, mais actuellement inutilisé.

### ❌ `config_manager.py` - **NON UTILISÉ**
**Statut** : Non utilisé  
**Raison** : Aucune importation trouvée  
**Action recommandée** : **SUPPRIMER** ou archiver  
**Note** : Contient une classe `ConfigManager` avec configuration GPU, mais non utilisée. La config GPU est gérée dans `system_config.py`.

### ❌ `config_validator.py` - **NON UTILISÉ**
**Statut** : Non utilisé  
**Raison** : Aucune importation trouvée  
**Action recommandée** : **SUPPRIMER** ou archiver  
**Note** : Contient des validations Pydantic pour LLM, Audio, VAD, mais non utilisées.

---

## 📁 tests/ - Fichiers à vérifier

### ⚠️ `test_performance.py` - **ERREUR D'IMPORT**
**Statut** : Contient une référence à un module inexistant  
**Problème** : Ligne 29 : `from config.performance_config import apply_performance_config`  
**Action recommandée** : **CORRIGER** ou supprimer la référence  
**Note** : Le test peut fonctionner avec un try/except, mais la référence est incorrecte.

### ✅ `test_streaming_interface.py` - **VALIDE**
**Statut** : Test valide pour l'Event Bus  
**Action** : **CONSERVER**

### ✅ `test_agents_initialization.py` - **VALIDE**
**Statut** : Test valide pour l'initialisation des agents  
**Action** : **CONSERVER**

---

## 📁 utils/ - Fichiers utilisés (à conserver)

### ✅ Fichiers actifs
- `log_manager.py` - Utilisé partout
- `monitoring.py` - Utilisé pour le monitoring des agents
- `metrics_collector.py` - Utilisé dans `interface/qaia_interface.py`
- `health_monitor.py` - Utilisé dans `tests/test_conversation_flow.py`
- `performance_metrics.py` - Utilisé dans d'autres modules (à vérifier si encore utilisé)
- `memory_manager.py` - Utilisé dans `qaia_core.py`
- `version_manager.py` - Utilisé dans `qaia_core.py`
- `security.py` - Utilisé dans `qaia_core.py`
- `clean_ram.py` - Utilisé dans `agents/__init__.py`
- `encoding_utils.py` - Utilisé dans `qaia_core.py` et `launcher.py`
- `embedding_cache.py` - Utilisé dans `agents/__init__.py`

---

## 📁 config/ - Fichiers utilisés (à conserver)

### ✅ Fichiers actifs
- `system_config.py` - Configuration principale, utilisé partout
- `logging_config.py` - Utilisé dans `interface/qaia_interface.py`
- `setup_logging.py` - Utilisé dans `agents/__init__.py`

---

## 📋 Plan d'action recommandé

### Phase 1 - Suppression immédiate (fichiers clairement obsolètes) ✅ TERMINÉ
1. ✅ **SUPPRIMÉ** `utils/event_system.py` (remplacé par `interface/events/event_bus.py`)
2. ✅ **SUPPRIMÉ** `config/interface_config.py` (non utilisé)
3. ✅ **SUPPRIMÉ** `config/config_manager.py` (non utilisé)
4. ✅ **SUPPRIMÉ** `config/config_validator.py` (non utilisé)

### Phase 2 - Correction ✅ FAIT
1. ✅ Corriger `tests/test_performance.py` (référence à `config.performance_config` supprimée)

### Phase 3 - Archivage optionnel
1. 📦 Archiver `utils/backup_manager.py` dans `docs/archive/` si non utilisé à court terme

---

## 📊 Statistiques

- **Fichiers obsolètes identifiés** : 4 (896 lignes de code)
  - `utils/event_system.py` : 544 lignes ✅ **SUPPRIMÉ**
  - `config/interface_config.py` : 47 lignes ✅ **SUPPRIMÉ**
  - `config/config_manager.py` : 99 lignes ✅ **SUPPRIMÉ**
  - `config/config_validator.py` : 206 lignes ✅ **SUPPRIMÉ**
- **Fichiers à corriger** : 1 ✅ (corrigé)
- **Fichiers à archiver** : 1 (`utils/backup_manager.py`)
- **Fichiers utils/ actifs** : 11
- **Fichiers config/ actifs** : 3

**Total supprimé** : 896 lignes de code obsolète

---

## 🔍 Notes supplémentaires

### Doublons potentiels
- `utils/event_system.py` vs `interface/events/event_bus.py` : **DOUBLON** (event_system est obsolète)
- `config/config_manager.py` vs `config/system_config.py` : **REDONDANCE** (config_manager non utilisé)

### Modules préparés pour usage futur
Voir `docs/MODULES_FUTURS.md` pour les modules dans `agents/` qui sont préparés mais non intégrés.

