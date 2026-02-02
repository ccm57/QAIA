# Tests UI-control (E2E) et KPIs

## Objectif
Valider le pipeline UI-control en mode CPU-only, avec sandbox et journalisation.

## Scénarios E2E recommandés

1. **Navigation simple (URL)**
   - Commande: "ouvre https://example.com"
   - Attendu: plan généré, confirmation demandée, exécution simulée en dry-run.

2. **Action click**
   - Commande: "clique sur Connexion"
   - Attendu: plan de click avec selector label.

3. **Saisie texte**
   - Commande: "écris Bonjour QAIA"
   - Attendu: plan de type `type` avec texte.

4. **Scroll**
   - Commande: "descends"
   - Attendu: plan `scroll` avec direction `down`.

5. **Blocage sécurité**
   - Commande: "faire un paiement"
   - Attendu: plan bloqué par denylist, message explicite.

## KPIs de stabilité (à suivre)

- **Taux de succès d’actions** : actions exécutées / actions tentées.
- **Temps moyen d’exécution** : latence end-to-end par action.
- **Taux de confirmation humaine** : confirmations acceptées / demandes.
- **Taux d’échec de parsing** : commandes sans plan / total commandes.
- **Drift UI** : taux d’échec de selectors ou éléments non trouvés.

## Journaux et traces
- `logs/ui_control/` : événements JSON (plan, exécution, erreurs).
- `data/ui_control/` : captures et schémas.
