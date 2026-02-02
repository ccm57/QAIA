## Validation de l’interface QAIA V2

Ce document décrit les critères de validation de la nouvelle interface graphique QAIA V2 ainsi que les scénarios de test minimum à exécuter avant la mise hors service de l’ancienne interface.

### 1. Couverture fonctionnelle

- **Texte**
  - Envoi d’un message texte simple.
  - Envoi d’un message texte long (plusieurs phrases).
  - Historique lisible et correctement horodaté.

- **PTT (Push-To-Talk)**
  - Démarrage / arrêt de l’enregistrement.
  - Gestion du timeout automatique.
  - Affichage de l’état (Enregistrement…, Transcription…).
  - Transcription affichée dans la conversation côté « Vous ».

- **Multimodalité / Agents**
  - LLM: réponse textuelle correcte affichée dans la zone de conversation.
  - RAG: au moins un scénario où des documents sont utilisés (si base configurée).
  - STT/TTS: réponse vocale cohérente avec le texte affiché.

### 2. Ergonomie & UX

- **Lisibilité**
  - Thème, couleurs et contrastes lisibles sur l’écran principal.
  - Police et taille de texte confortables en lecture prolongée.

- **Flux utilisateur**
  - Les boutons principaux sont explicites: envoyer, parler, arrêter, etc.
  - Les erreurs sont expliquées en français clair (micro indisponible, LLM indisponible…).
  - Aucun blocage: l’utilisateur comprend toujours « ce qui se passe ».

### 3. Performance

- **Latence perçue**
  - Temps avant affichage du début de réponse texte acceptable pour des questions simples.
  - Temps d’initialisation de QAIA raisonnable (interface prête à l’usage).

- **Stabilité de la session**
  - Plusieurs échanges consécutifs sans ralentissement excessif ni figeage de l’UI.

### 4. Stabilité & gestion des erreurs

- **Absence de crash**
  - Aucun crash de l’interface après une série de tests fonctionnels complets.

- **Gestion propre des erreurs**
  - LLM non initialisé: message clair + UI toujours utilisable (pas de gel).
  - Micro indisponible / erreur audio: message explicite, retour à un état stable.
  - Agents facultatifs (RAG) désactivés proprement si non disponibles.

### 5. Scénarios de test recommandés

1. **Lancement de QAIA**
   - Lancement par terminal (`python launcher.py`) puis via le raccourci bureau.
   - Vérifier:
     - temps d’affichage de la fenêtre principale,
     - absence de crash/traceback dans la console,
     - état initial `status_label`: « Système prêt » (fond vert clair),
     - présence du message de bienvenue (texte + TTS si activé).

2. **Conversation texte simple**
   - Envoyer 3–5 questions/réponses courtes.
   - Vérifier pour chaque échange:
     - affichage immédiat du message utilisateur côté « Vous »,
     - passage du statut à « QAIA écrit… » pendant la génération,
     - affichage d’une réponse unique (pas de doublon streaming / réponse finale),
     - retour du statut à « Système prêt » en fin de réponse,
     - mise à jour des métriques LLM (latence, tokens, tokens/s) dans la fenêtre Métriques.

3. **Conversation PTT (Push-To-Talk)**
   - Réaliser 3–5 questions/réponses complètes en mode vocal.
   - Vérifier:
     - changement du bouton en « ⏹ Arrêter » pendant l’enregistrement,
     - statut « Enregistrement… » puis « Transcription… »,
     - application du timeout automatique d’enregistrement,
     - transcription correcte affichée côté « Vous »,
     - réponse QAIA cohérente (texte + TTS si activé),
     - absence de blocage UI même si le micro est indisponible (message explicite).

4. **Agent RAG (si activé)**
   - RAG: poser au moins une question nécessitant un document (base configurée).
     - Vérifier qu’une réponse contextualisée est fournie ou qu’un message explicite signale l’absence de documents pertinents.

5. **Scénarios d’erreur contrôlée**
   - Désactiver temporairement l’accès LLM (ou simuler une erreur réseau).
     - Vérifier:
       - affichage d’un message d’erreur clair côté QAIA,
       - statut « Erreur LLM » (fond rouge clair),
       - UI toujours utilisable (possibilité de réessayer / fermer proprement).
   - Rendre le micro indisponible (ou forcer une erreur STT).
     - Vérifier:
       - affichage d’un message explicite dans la conversation,
       - statut « Erreur micro » / « Erreur PTT »,
       - retour à un état stable (pas de boucle infinie d’enregistrement).

### 6. Seuils de validation recommandés

- **Latence LLM**
  - Temps avant premier token:
    - ≤ 3 s pour une question simple en local (machine de référence).
  - Temps total de génération pour une réponse courte:
    - généralement ≤ 8–10 s.
- **Initialisation**
  - Temps entre le lancement de `launcher.py` et l’état « Système prêt »:
    - idéalement ≤ 20–30 s (modèles locaux chargés).
- **Stabilité**
  - Au minimum:
    - 20 sessions complètes (texte + PTT) sans crash de l’interface,
    - aucune fuite mémoire visible après une dizaine de minutes d’utilisation continue.
- **Erreurs**
  - 100 % des erreurs LLM/audio doivent:
    - être loguées dans la fenêtre Logs,
    - mettre à jour `status_label` avec un message explicite,
    - laisser l’application dans un état interactif (boutons toujours cliquables).

### 7. Checklist de validation (à cocher)

| Scénario                              | OK / NOK | Observations                         |
|--------------------------------------|---------|--------------------------------------|
| Lancement terminal + raccourci      |         |                                      |
| Texte simple (3–5 tours)            |         |                                      |
| PTT (3–5 tours)                     |         |                                      |
| RAG (si configuré)                  |         |                                      |
| Erreurs LLM simulées                |         |                                      |
| Erreurs micro / audio simulées      |         |                                      |
| Fenêtre Logs remonte les événements |         |                                      |
| Fenêtre Métriques affiche llm.complete |       |                                      |



