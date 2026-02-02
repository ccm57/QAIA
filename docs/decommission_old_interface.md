## Plan de décommission de l’ancienne interface QAIA

Ce document décrit la stratégie de mise hors service progressive de l’ancienne interface
legacy (ancien module `agents.interface_agent.InterfaceAgent`, désormais supprimé)
au profit de l’interface V2 (`interface.qaia_interface.QAIAInterface`).

L’objectif est de garantir une transition contrôlée, réversible et sans régression majeure.

---

### 1. Prérequis à la suppression

Avant toute suppression définitive de l’ancienne interface, les conditions suivantes doivent être satisfaites :

- **Validation complète de l’interface V2**
  - Tous les scénarios de `docs/INTERFACE_V2_VALIDATION.md` sont validés (table de checklist complétée).
  - Aucun crash observé sur au moins 20 sessions complètes (texte + PTT).
  - Les erreurs LLM/audio sont correctement gérées (messages clairs + UI stable).

- **Adoption du mode V2**
  - Le flag `INTERFACE_MODE` (ou la variable d’environnement `QAIA_INTERFACE_MODE`) est utilisé
    en mode `v2` ou `auto` sans besoin récurrent de repasser en `legacy`.
  - Aucun bug critique bloquant ne subsiste dans l’interface V2.

- **Couverture de test minimale**
  - Tests manuels réalisés sous Linux Mint sur la machine de référence.
  - Campagne de tests de régression sur les fonctionnalités principales (texte, PTT, logs, métriques, RAG/vision si activés).

---

### 2. Étapes de décommission

#### Étape 1 – Coexistence (état actuel)

- `INTERFACE_MODE` disponible dans `config/system_config.py` avec valeurs :
  - `legacy` : force l’ancienne interface,
  - `v2` : force la V2,
  - `auto` : tente V2 avec fallback legacy.
- `launcher.py` utilise `INTERFACE_MODE` pour choisir l’interface à lancer.
- Action recommandée :
  - Utiliser principalement `INTERFACE_MODE=auto` pour valider V2 tout en gardant un filet de sécurité legacy.

#### Étape 2 – V2 par défaut (legacy en option)

- Changer la configuration par défaut (documentation + scripts de lancement) pour privilégier V2 :
  - Dans les docs et scripts (README, `launch_qaia.sh`, raccourcis), considérer `INTERFACE_MODE="v2"` comme valeur recommandée.
  - Garder la possibilité de démarrer avec `INTERFACE_MODE="legacy"` pour rollback rapide.
- Vérifier que :
  - les utilisateurs internes n’ont plus besoin de repasser systématiquement en legacy,
  - aucun nouveau bug critique n’apparaît en utilisation quotidienne.

#### Étape 3 – Suppression du code legacy

Une fois les conditions précédentes validées :

- **Code à supprimer en priorité** (après audit d’usage) :
  - (FAIT) `agents/interface_agent.py` (ancienne interface Tkinter),
  - éventuels assets spécifiques à l’ancienne interface non utilisés par V2,
  - branches legacy devenues inatteignables dans `launcher.py`.
- **Nettoyage de configuration** :
  - Retirer la valeur `legacy` de la documentation utilisateur,
  - simplifier `INTERFACE_MODE` si nécessaire (ex: ne garder que `v2` et `auto`).
- **Documentation** :
  - Mettre à jour `CHANGELOG.md` avec une entrée explicite :
    - « Suppression de l’ancienne interface graphique (InterfaceAgent), V2 devenue interface unique. »
  - Mettre à jour `README.md` et `docs/` pour référencer uniquement l’interface V2.

---

### 3. Procédure de rollback (en cas de bug critique V2)

Si un bug critique est découvert après la suppression ou la mise en avant de V2, la procédure suivante permet
de revenir temporairement à l’ancienne interface.

#### 3.1. Rollback avec code legacy encore présent

Si le code legacy n’a pas encore été supprimé (Étape 2) :

1. **Forcer le mode legacy** :
   - Exporter la variable d’environnement :
     ```bash
     export QAIA_INTERFACE_MODE=legacy
     python launcher.py
     ```
   - Ou modifier temporairement `INTERFACE_MODE` dans `config/system_config.py` pour le mettre à `"legacy"`.

2. **Informer dans les logs** :
   - Vérifier que `launcher.log` et `system.log` indiquent bien le mode legacy utilisé.

3. **Ouvrir un ticket interne** décrivant :
   - le scénario qui casse V2,
   - les logs associés,
   - la version/commit concerné.

#### 3.2. Rollback après suppression du code legacy

Si l’ancienne interface a déjà été supprimée du code :

1. **Revenir sur un commit antérieur** (via git) :
   - Identifier le dernier commit avant suppression de legacy (référence dans `CHANGELOG.md`).
   - Faire un checkout de ce commit dans une branche de rollback dédiée.

2. **Restaurer éventuellement les fichiers supprimés** si nécessaire, en s’appuyant sur l’historique git.

3. **Remettre `INTERFACE_MODE` à `legacy` ou `auto`** suivant le niveau de confiance dans V2.

4. **Documenter le rollback** :
   - Ajouter une entrée dans `CHANGELOG.md` :
     - « Rollback temporaire vers l’ancienne interface suite à bug critique V2 (détails dans issue #XYZ). »

> Branche de sauvegarde recommandée (à créer une fois la V2 validée) :
> ```bash
> git checkout -b legacy-ui-backup
> git push origin legacy-ui-backup  # optionnel
> ```

---

### 4. Points de vigilance

- Ne jamais supprimer le code legacy sans :
  - validation complète du document `INTERFACE_V2_VALIDATION.md`,
  - confirmation que `INTERFACE_MODE="v2"` fonctionne de manière stable sur la machine de référence.
- Toujours garder une **branche git** avec l’ancienne interface tant que V2 n’a pas au moins
  quelques semaines d’usage sans incident critique.
- Centraliser les retours utilisateurs (latence, ergonomie, bugs) dans un fichier `CHANGELOG.md`
  ou un outil de suivi afin d’étayer la décision de décommission définitif.


