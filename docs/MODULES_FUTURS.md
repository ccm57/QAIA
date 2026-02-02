# Modules préparés pour usage futur

Ce document liste les modules qui ont été créés et leur statut d'intégration dans le flux principal de QAIA.

## Modules dans `agents/`

### `audio_manager.py`
**Statut** : Intégré (Desktop)  
**Description** : Gestionnaire audio centralisé (singleton) avec stratégies d'enregistrement multiples (InputStream+VAD, InputStream+fixe, rec+wait, PyAudio).  
**Utilisation actuelle** : Utilisé par `interface/qaia_interface.py` pour la capture micro et par `agents/wav2vec_agent.py` pour l'enregistrement ; tests dans `tests/test_conversation_flow.py` et `tests/test_audio_manager_integration.py`.  
**Intégration future** : Évolutions possibles (stratégies additionnelles, métriques).

### `context_manager.py`
**Statut** : Intégré (Core)  
**Description** : Gestion mémoire conversationnelle avec résumé automatique (court/moyen/long terme), extraction d'entités, gestion de sujets.  
**Utilisation actuelle** : Instancié dans `qaia_core.QAIACore` et injecté dans `core/dialogue_manager.DialogueManager` pour la mémoire conversationnelle.  
**Intégration future** : Enrichissement des résumés et entités selon besoins.

### `intent_detector.py`
**Statut** : Intégré (Core + Dialogue)  
**Description** : Détection d'intentions utilisateur (question, clarification, confirmation, commande, salutation, fin de conversation, etc.) via règles et patterns regex en français.  
**Utilisation actuelle** : Initialisé dans `QAIACore`, injecté dans `DialogueManager`. Utilisé pour `END_CONVERSATION`, `GREETING`, `CONFIRMATION`. L'intention `COMMAND` est détectée et servira le pipeline commandes système (sécurité + exécution).  
**Intégration future** : Pipeline complet détection → sécurité → exécution pour les commandes système ; extraction verbe/cible (parse_command).

## Modules dans `config/`

### `interface_config.py`
**Statut** : Non utilisé  
**Description** : Configuration de l'interface (thème, couleurs, FPS, buffers, alertes).  
**Utilisation actuelle** : Aucune (pas d'imports trouvés).  
**Intégration future** : Peut être utilisé pour centraliser la configuration UI au lieu de valeurs hardcodées dans `qaia_interface.py`.

## Scripts utilitaires

### `save_qaia.py`
**Statut** : Script utilitaire standalone  
**Description** : Menu interactif pour sauvegarde rapide ou complète de QAIA.  
**Utilisation** : Script à exécuter manuellement si nécessaire.

## Recommandations

1. **Conserver ces modules** : Ils font partie du flux principal ou représentent des améliorations futures possibles.
2. **Documenter leur statut** : Ce document sert de référence à jour.
3. **Intégration progressive** : Nouvelles fonctionnalités (ex. pipeline commandes) à intégrer avec tests appropriés.
