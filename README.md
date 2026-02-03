#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""README du projet QAIA – Quality Assistant Intelligent Agent"""

# QAIA – Quality Assistant Intelligent Agent

QAIA est un **assistant intelligent de supervision et de contrôle qualité**, conçu pour :
- analyser en temps réel l’activité (voix, interface, logs) ;
- superviser l’état de santé du système ;
- assister l’utilisateur dans l’exécution de commandes et de scénarios complexes ;
- fournir une interface graphique de monitoring riche (agents, métriques, logs, actions UI).

Le projet est écrit en **Python 3.10+** et s’appuie sur des modèles IA (LLM, STT/TTS, RAG) configurés localement.

---

## 1. Structure générale du projet

Les dossiers principaux :

- `agents/` : agents d’IA (intention, audio, RAG, etc.).
- `core/` : noyau conversationnel et exécution de commandes.
- `interface/` : interface graphique QAIA (fenêtres, composants, événements).
- `ui_control/` : pipeline de contrôle de l’interface (actions UI, sécurité, monitoring).
- `utils/` : outils transverses (logs, métriques, sécurité, mémoire, sauvegardes…).
- `config/` : configuration système et logging.
- `models/` : modèles lourds (TTS, LLM, etc.).
- `data/` : données, caches, bases SQLite.
- `docs/` : documentation détaillée (architecture, pipelines, audits…).
- `tests/` : tests automatisés (intégration, performance, UI, agents).

Le point d’entrée principal est :

- `launcher.py` : lanceur de QAIA.
- `qaia_core.py` : noyau central de l’agent.

---

## 2. Prérequis

- **Système** : Linux (testé sur Linux Mint).
- **Python** : 3.10 ou supérieur.
- **Matériel recommandé** :
  - CPU : Intel i7 ou équivalent ;
  - RAM : ≥ 16 Go (40 Go dans la config de référence) ;
  - GPU : NVIDIA GTX 1050 (2 Go VRAM) ou supérieur pour l’IA accélérée.

---

## 3. Installation rapide

Cloner le dépôt :

```bash
git clone https://github.com/ccm57/QAIA.git
cd QAIA
```

Créer et activer un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installer les dépendances :

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configuration de base

1. Créer un fichier `.env` à la racine du projet (non versionné) pour y mettre :
   - les clés API nécessaires (si utilisation de services externes) ;
   - les chemins locaux pour les modèles (LLM, TTS, STT) ;
   - les paramètres spécifiques à votre machine.

2. Vérifier la configuration dans `config/system_config.py` et les fichiers de logging dans `config/logging_config.py`.

3. S’assurer que les dossiers nécessaires existent (créés automatiquement au besoin) :
   - `logs/`, `data/`, `models/`, `backups/`, etc.

---

## 5. Lancement de QAIA

Pour lancer QAIA avec l’interface de supervision :

```bash
python launcher.py
```

Selon la configuration, cela démarre :
- les agents (audio, RAG, intention, etc.) ;
- l’interface `qaia_interface` (fenêtres de métriques, logs, monitoring, etc.) ;
- le pipeline de contrôle UI si activé.

Consultez `docs/PIPELINE_COMMANDES.md`, `docs/PIPELINE_DESKTOP_WEB.md` et `docs/AUDIT_INTERACTION_VOCALE.md` pour le détail des flux de commandes et de l’interaction vocale.

---

## 6. Tests

Pour exécuter la suite de tests :

```bash
pytest
```

Les tests couvrent notamment :
- l’initialisation des agents ;
- l’intégration audio ;
- le pipeline de commandes ;
- les flux conversationnels ;
- le contrôle d’interface et la supervision.

---

## 7. Contribution et bonnes pratiques

- Tout nouveau code doit :
  - respecter **PEP 8** ;
  - utiliser des **annotations de types** explicites ;
  - inclure des **docstrings en français** (scripts, classes, fonctions) ;
  - éviter toute donnée sensible en dur (utiliser `.env`).

- Les logs doivent être centralisés dans `logs/` via les utilitaires de `config/` et `utils/log_manager.py`.

Avant de pousser :

```bash
pytest
git status
git commit -m "Description en français des changements"
git push
```

---

## 8. Licence

Ce projet est distribué sous licence **MIT** (voir le fichier `LICENSE`).

---

## 9. Ressources internes

Pour une vue détaillée de l’architecture, consulter notamment :

- `docs/AUDIT_ARCHITECTURAL_COMPLET.md`
- `docs/IMPLEMENTATION_ARCHITECTURE_CENTRALISEE.md`
- `docs/AI_INTEGRATION.md`
- `docs/PIPELINE_COMMANDES.md`
- `docs/PIPELINE_DESKTOP_WEB.md`
- `docs/RESUME_IMPLEMENTATION.md`

Ces documents décrivent les décisions d’architecture, les pipelines clés et les évolutions prévues de QAIA.
