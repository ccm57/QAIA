# Pipeline commandes système QAIA

Ce document décrit le flux détection → sécurité → exécution des commandes système, les listes blanche / confirmation, et comment ajouter une nouvelle commande.

---

## Flux

```
Texte utilisateur
       │
       ▼
IntentDetector.detect()  →  intent COMMAND + command_verb, command_target
       │
       ▼
command_guard.evaluate_command(verb, target)
       │
       ├── allowed + require_confirmation  →  Réponse "Souhaitez-vous vraiment … ?"  →  intent: command_confirmation_pending
       │                                          │
       │                                          ▼ (utilisateur dit "oui")
       │                                    process_message(..., confirmation_pending={verb, target})
       │                                          │
       │                                          ▼
       ├── allowed + pas de confirmation  ────────┴──► command_executor.execute_command(verb, target)
       │                                                      │
       │                                                      ▼
       │                                               intent: command_executed ou command_refused
       │
       └── not allowed  →  Réponse verdict.reason  →  intent: command_refused
```

---

## Listes (utils/command_guard.py)

- **WHITELIST_NO_CONFIRM** : paires (verbe, cible) autorisées sans confirmation (risque low). Ex. `("arrete", "enregistrement")`, `("arrete", "micro")`, `("lance", "lecture")`.
- **WHITELIST_CONFIRM** : paires autorisées après confirmation (risque medium). Ex. `("ferme", "application")`, `("lance", "navigateur")`, `("ouvre", "navigateur")`.
- Toute autre paire → `allowed=False`, `risk_level="high"`.

---

## Ajouter une nouvelle commande

1. **Détection** : Si besoin, étendre les patterns dans `agents/intent_detector.py` (`parse_command` : verb_patterns, target_map) pour que le verbe/cible soit extrait.
2. **Sécurité** : Dans `utils/command_guard.py`, ajouter la paire dans `WHITELIST_NO_CONFIRM` ou `WHITELIST_CONFIRM`.
3. **Exécution** : Dans `core/command_executor.py`, soit utiliser le message par défaut déjà enregistré dans `_register_defaults()`, soit dans `qaia_core.py` après `get_command_executor()` appeler `register_action(verb, target, callback)` avec un callable qui exécute l’action et retourne un message (str).

Exemple d’enregistrement d’une action réelle dans `qaia_core.py` :

```python
self.command_executor.register_action("arrete", "enregistrement", self._cmd_stop_recording)
```

avec `_cmd_stop_recording()` qui émet l’événement ou appelle l’API appropriée et retourne une chaîne pour le TTS.

---

## Actions réelles (Phase 3)

Les paires suivantes exécutent une action réelle (enregistrées dans `qaia_core._register_command_actions`) :

| Verbe   | Cible         | Action réelle |
|---------|----------------|---------------|
| arrete  | enregistrement | Émet `command.stop_recording` ; l’interface arrête le PTT (sans lancer la transcription). |
| arrete  | micro          | Idem (même événement). |
| arrete  | lecture        | Appel à `stop_speech()` (arrêt TTS). |
| desactive | micro        | Idem « arrete enregistrement ». |
| lance   | navigateur     | `webbrowser.open("https://www.google.com")`. |
| ouvre   | navigateur     | Idem. |
| active  | micro          | Message informatif (micro géré par le bouton Parler). |

Les autres paires (ferme application, ferme interface, redemarre assistant) restent en message par défaut tant qu’aucun callback n’est enregistré.

---

## Intents exposés

- `command_confirmation_pending` : confirmation demandée (champs `command_verb`, `command_target` dans la réponse).
- `command_executed` : commande exécutée avec succès.
- `command_refused` : commande refusée (verdict guard ou erreur exécution).
- `command_cancelled` : utilisateur a répondu « non » à la confirmation.

---

## Logs et sécurité

- Les tentatives sont journalisées dans `utils/command_guard.py` via `_log_attempt` (verb, target, verdict ; pas de secrets).
- Aucun chemin n’exécute de commande shell brute : pas de `shell=True`, pas d’injection de l’entrée utilisateur dans une ligne de commande.
