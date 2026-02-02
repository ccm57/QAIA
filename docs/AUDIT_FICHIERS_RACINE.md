# Audit des fichiers à la racine - QAIA

Date: 2025-01-XX  
**Statut** : ✅ Audit terminé et actions appliquées

## Résumé

Cet audit identifie les fichiers situés à la racine du projet QAIA et détermine s'ils sont :
- ✅ **À conserver** (fichiers essentiels)
- ⚠️ **À corriger** (fichiers avec problèmes)
- ❌ **Obsolètes** (fichiers à supprimer)
- 📦 **À déplacer** (fichiers à ranger dans des dossiers appropriés)

---

## 📁 Fichiers à la racine

### ✅ Scripts Python essentiels (à conserver)

#### `launcher.py` (12KB)
**Statut** : ✅ **ESSENTIEL**  
**Usage** : Point d'entrée principal de QAIA  
**Action** : **CONSERVER** à la racine  
**Références** : Utilisé par `launch_qaia.sh` et directement

#### `qaia_core.py` (36KB)
**Statut** : ✅ **ESSENTIEL**  
**Usage** : Module principal de QAIA  
**Action** : **CONSERVER** à la racine  
**Références** : Importé par `launcher.py` et tests

---

### ✅ Scripts shell (à conserver)

#### `launch_qaia.sh` (3KB)
**Statut** : ✅ **ESSENTIEL**  
**Usage** : Script de lancement avec gestion d'erreurs  
**Action** : **CONSERVER** à la racine  
**Références** : Mentionné dans README.md et CHANGELOG.md

#### `test_qaia.sh` (4.9KB)
**Statut** : ✅ **ESSENTIEL**  
**Usage** : Script de test rapide (audio, volume, instructions)  
**Action** : **CONSERVER** à la racine  
**Références** : Mentionné dans README.md

---

### ✅ Documentation (à conserver)

#### `README.md` (12KB)
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine

#### `CHANGELOG.md` (4.5KB)
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine

#### `ARBORESCENCE.txt` (4.8KB)
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine (documentation structure projet)

#### `PROFILS_LATENCE.md` (4.4KB)
**Statut** : ✅ **UTILE**  
**Usage** : Documentation des profils d'optimisation de latence  
**Action** : **CONSERVER** ou déplacer dans `docs/`  
**Note** : Pourrait être rangé dans `docs/` mais reste accessible à la racine

---

### ✅ Configuration (à conserver)

#### `requirements.txt` (977 bytes)
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine

#### `LICENSE`
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine

#### `.gitignore`
**Statut** : ✅ **ESSENTIEL**  
**Action** : **CONSERVER** à la racine

---

### ⚠️ Fichiers à corriger

#### `save_qaia.py` (4.4KB)
**Statut** : ⚠️ **PROBLÈME**  
**Problème** : Référence des fichiers inexistants :
- `quick_backup.py` (ligne 27)
- `backup_qaia.py` (ligne 42)
- `test_backup.py` (ligne 57)

**Solution** : 
- Option 1 : **CORRIGER** pour utiliser `utils/backup_manager.py`
- Option 2 : **SUPPRIMER** si non utilisé
- Option 3 : **DÉPLACER** dans `scripts/` et corriger

**Action recommandée** : **CORRIGER** pour utiliser `utils/backup_manager.py` ou **DÉPLACER** dans `scripts/`

---

### ❌ Fichiers obsolètes

#### `project_manager.log` (253KB)
**Statut** : ❌ **OBSOLÈTE**  
**Raison** : 
- Fichier de log ancien (juillet 2025)
- Taille importante (253KB)
- Contient des logs de création de dossiers (Windows: `E:\QAIA`)
- Non utilisé actuellement

**Action recommandée** : **SUPPRIMER** ou archiver dans `logs/archive/`

---

### 📦 Dossiers/fichiers à déplacer

#### `vector_db/` (dossier vide à la racine)
**Statut** : ⚠️ **DOUBLON**  
**Problème** : 
- Dossier vide à la racine
- La base vectorielle est dans `data/vector_db/`
- Peut créer de la confusion

**Action recommandée** : **SUPPRIMER** le dossier vide à la racine (la base est dans `data/vector_db/`)

---

## 📋 Plan d'action recommandé

### ✅ Phase 1 - Nettoyage immédiat (TERMINÉ)
1. ✅ **SUPPRIMÉ** `project_manager.log` (fichier de log obsolète)
2. ✅ **SUPPRIMÉ** `vector_db/` (dossier vide, doublon de `data/vector_db/`)

### ✅ Phase 2 - Correction (TERMINÉ)
1. ✅ **CORRIGÉ** `save_qaia.py` :
   - Utilise maintenant `utils/backup_manager.py` directement
   - `quick_backup()` : Sauvegarde rapide sans ZIP
   - `full_backup()` : Sauvegarde complète avec ZIP
   - `test_backup()` : Test du module intégré

### Phase 3 - Organisation optionnelle (NON APPLIQUÉ)
1. 📦 **DÉPLACER** `PROFILS_LATENCE.md` dans `docs/` (optionnel, peut rester à la racine)

---

## 📊 Statistiques

- **Fichiers essentiels à la racine** : 9
  - Scripts Python : 2 (`launcher.py`, `qaia_core.py`)
  - Scripts shell : 2 (`launch_qaia.sh`, `test_qaia.sh`)
  - Documentation : 4 (`README.md`, `CHANGELOG.md`, `ARBORESCENCE.txt`, `PROFILS_LATENCE.md`)
  - Configuration : 1 (`requirements.txt`)
- **Fichiers à corriger** : 1 (`save_qaia.py`)
- **Fichiers obsolètes** : 1 (`project_manager.log`)
- **Dossiers à supprimer** : 1 (`vector_db/` vide)

---

## 🔍 Notes supplémentaires

### Fichiers manquants référencés par `save_qaia.py`
- `quick_backup.py` - N'existe pas
- `backup_qaia.py` - N'existe pas
- `test_backup.py` - N'existe pas

**Solution** : Le module `utils/backup_manager.py` existe et pourrait être utilisé à la place.

### Structure recommandée
Les fichiers essentiels à la racine sont normaux pour un projet Python :
- `launcher.py` / `qaia_core.py` : Points d'entrée
- `README.md` / `CHANGELOG.md` : Documentation standard
- `requirements.txt` : Dépendances standard
- Scripts shell : Utilitaires de lancement

