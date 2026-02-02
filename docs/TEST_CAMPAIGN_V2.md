## Campagne de tests QAIA V2

Cette campagne décrit les tests à exécuter pour valider l’interface V2, le noyau
`QAIACore` et les agents principaux (LLM, RAG, STT/TTS), avant et après
suppression de l’ancienne interface.

Voir également :
- `docs/INTERFACE_V2_VALIDATION.md`
- `docs/decommission_old_interface.md`

---

### 1. Matrice de tests

| ID  | Scénario                          | Type      | Modules principaux                          | Référence validation                  | Tests auto associés (si existants)        |
|-----|-----------------------------------|----------|---------------------------------------------|---------------------------------------|-------------------------------------------|
| T1  | Lancement (terminal + raccourci) | Manuel   | `launcher.py`, `QAIAInterface`              | INTERFACE_V2_VALIDATION §5.1         | N/A                                       |
| T2  | Conversation texte simple        | Manuel   | `qaia_core`, `QAIAInterface`, LLM           | INTERFACE_V2_VALIDATION §5.2         | `tests/test_conversation_flow.py`        |
| T3  | Conversation PTT                 | Manuel   | `wav2vec_agent`, `speech_agent`, UI PTT    | INTERFACE_V2_VALIDATION §5.3         | `scripts/test_audio_pipeline.py` (part.) |
| T4  | RAG question document            | Manuel   | `rag_agent`, vector DB, `qaia_core`        | INTERFACE_V2_VALIDATION §5.4         | `tests/test_conversation_mode.py`        |
| T5  | UI-control (E2E)                | Manuel   | `ui_control/*`, `ui_control_service`       | `docs/UI_CONTROL_TESTS.md`           | `tests/test_ui_control_pipeline.py`      |
| T6  | Erreur LLM simulée              | Manuel   | `qaia_core`, `QAIAInterface`, logs         | INTERFACE_V2_VALIDATION §5.5         | `tests/test_llm_agent.py`                |
| T7  | Erreur audio / micro            | Manuel   | `wav2vec_agent`, `QAIAInterface`           | INTERFACE_V2_VALIDATION §5.5         | `tests/test_audio_system.py`             |
| T8  | Streaming LLM intensif          | Auto     | Event bus, `StreamingTextDisplay`          | README « Tests de Charge »           | `tests/test_streaming_interface.py`      |
| T9  | Performance globale pipeline    | Auto     | `qaia_core`, agents LLM/RAG/STT/TTS        | `PROFILS_LATENCE.md`                 | `scripts/benchmark_pipeline.py`          |
| T10 | Santé agents & monitoring       | Manuel   | `agents_window`, `monitoring_window`       | INTERFACE_V2_VALIDATION §2 / §4      | `tests/test_agents_initialization.py`    |

Cette matrice peut être complétée/affinée en fonction des besoins (nouveaux
agents, nouveaux scénarios métiers, etc.).

---

### 2. Procédure de campagne

1. **Préparation**
   - Activer l’environnement virtuel.
   - Vérifier que les modèles nécessaires sont présents (`models/`).
   - Lancer un nettoyage des logs précédents si nécessaire (`logs/`).

2. **Tests rapides en ligne de commande**
   - Exécuter la suite principale :
     ```bash
     cd /media/ccm57/SSDIA/QAIA
     pytest tests/
     ```
   - Optionnel : lancer les scripts de diagnostic :
     ```bash
     python scripts/test_audio_pipeline.py
     python scripts/verify_environment.py
     ```

3. **Scénarios UI manuels (basés sur `INTERFACE_V2_VALIDATION.md`)**
   - Suivre les scénarios T1 à T7 en cochant la checklist dans
     `INTERFACE_V2_VALIDATION.md` et en notant les anomalies éventuelles.

4. **Tests de performance / latence**
   - Lancer le benchmark :
     ```bash
     python scripts/benchmark_pipeline.py
     ```
   - Comparer les temps mesurés avec `PROFILS_LATENCE.md`.

5. **Validation finale**
   - Confirmer qu’aucun scénario critique n’est NOK.
   - Si un scénario est NOK, ouvrir un ticket interne et bloquer la suppression
     de l’ancienne interface jusqu’à correction.

---

### 3. Checklist d’exécution de campagne

| Élément                                       | OK / NOK | Commentaire / Référence ticket |
|----------------------------------------------|----------|--------------------------------|
| Pytest `tests/`                              |          |                                |
| Script `test_audio_pipeline.py`              |          |                                |
| Script `verify_environment.py`               |          |                                |
| Scénarios T1–T3 (texte + PTT)                |          |                                |
| Scénarios T4–T5 (RAG + UI-control)           |          |                                |
| Scénarios T6–T7 (erreurs LLM/audio)          |          |                                |
| T8 – Test streaming intensif                 |          |                                |
| T9 – Benchmark pipeline                      |          |                                |
| T10 – Santé agents & monitoring              |          |                                |

---

### 4. Validation comportement LLM (system_prompt v2.2.0)

Mini-checklist pour valider que le nouveau prompt système fonctionne correctement :

| Prompt test | Résultat attendu | OK / NOK | Commentaire |
|------------|------------------|----------|-------------|
| "Qu'est-ce que Python ?" | Réponse factuelle, **sans** "Source : ..." ou liens | | |
| "Explique-moi le machine learning" | Réponse synthétique, **sans** références externes | | |
| "Peux-tu me donner des sources sur X ?" | Réponse avec sources/liens (car demande explicite) | | |
| "Comment installer Python ?" | Réponse courte mais complète, ton professionnel | | |
| "Quelle est la capitale de la France ?" | Réponse directe, sans détails inutiles | | |

**Critères de validation :**
- ✅ Aucune citation de source/lien spontanée (sauf demande explicite)
- ✅ Ton professionnel, courtois, calme
- ✅ Réponses en français correct, phrases complètes
- ✅ Longueur adaptée (courtes mais complètes, ou approfondies si demandé)

---

### 5. Journal d’exécution (à remplir)

Format recommandé :
- Date / heure
- Version git (commit hash court)
- Résumé des résultats (succès/échecs)
- Actions correctives éventuelles

Exemple :

- **2025-12-18 15:42** – commit `abc1234`
  - Pytest OK, T1–T3 OK, T6 NOK (erreur LLM simulée non loguée correctement).
  - Action : ouvrir ticket `BUG-LLM-ERROR-LOG` et corriger avant décommission.


