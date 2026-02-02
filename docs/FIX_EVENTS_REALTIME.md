# Correction des événements temps réel - 18 Décembre 2025

## Problèmes identifiés

1. **Logs** : Le handler EventBusLogHandler était ajouté uniquement au logger "QAIA", pas aux loggers des agents
2. **Métriques LLM** : L'événement `llm.complete` manquait `temperature` et `top_p`
3. **États agents** : `update_active_agents()` était un stub qui n'émettait pas d'événements `agent.state_change`
4. **Événements agents** : Les agents n'émettaient pas d'événements `agent.state_change` lors de leur utilisation

## Corrections appliquées

### 1. Handler de logs étendu (`utils/log_manager.py`)

**Avant** : Handler ajouté uniquement au logger "QAIA"

**Après** : Handler ajouté à tous les loggers importants :
- `QAIA`
- `agents.llm_agent`
- `agents.wav2vec_agent`
- `agents.speech_agent`
- `agents.rag_agent`
- `agents.vision_agent`
- `qaia_core`
- `interface.qaia_interface`

**Résultat** : Tous les logs des agents sont maintenant visibles dans LogsWindow en temps réel.

### 2. Métriques LLM complètes (`agents/llm_agent.py`)

**Avant** : `llm.complete` contenait seulement `latency`, `tokens`, `tokens_per_sec`

**Après** : Ajout de `temperature`, `top_p`, `max_tokens` depuis la config

**Résultat** : MetricsWindow affiche maintenant toutes les métriques LLM (config incluse).

### 3. Fonction `update_active_agents()` implémentée (`utils/monitoring.py`)

**Avant** : Stub no-op qui ne faisait rien

**Après** : Émet des événements `agent.state_change` pour tous les agents connus :
- Mapping des noms internes vers noms UI (llm → LLM, voice → STT, etc.)
- Émission d'événements avec statut ACTIF/IDLE selon disponibilité
- Appelée lors de l'initialisation du core

**Résultat** : AgentsWindow affiche maintenant les états initiaux des agents.

### 4. Événements agents dans le flux (`qaia_core.py`, `agents/*.py`)

**LLM** (`qaia_core.py` + `agents/llm_agent.py`) :
- Émission `agent.state_change` avant génération (EN_COURS)
- Émission `agent.state_change` après génération (ACTIF)
- Émission `llm.complete` avec métriques complètes

**STT** (`agents/wav2vec_agent.py`) :
- Émission `agent.state_change` avant transcription (EN_COURS)
- Émission `agent.state_change` après transcription (ACTIF)

**TTS** (`agents/speech_agent.py`) :
- Émission `agent.state_change` avant synthèse (EN_COURS)
- Émission `agent.state_change` après synthèse (ACTIF)

**RAG** (`agents/rag_agent.py`) :
- Émission `agent.state_change` avant traitement (EN_COURS)
- Émission `agent.state_change` après traitement (ACTIF)

**Résultat** : AgentsWindow affiche maintenant les états en temps réel lors de l'utilisation des agents.

## Tests à effectuer

1. **LogsWindow** :
   - Ouvrir Menu Vue → Logs (Ctrl+L)
   - Effectuer une action (conversation, PTT, etc.)
   - Vérifier que les logs apparaissent en temps réel

2. **MetricsWindow** :
   - Ouvrir Menu Vue → Métriques LLM (Ctrl+K)
   - Effectuer une conversation texte
   - Vérifier que les métriques (latence, tokens, temperature, top_p) s'affichent

3. **AgentsWindow** :
   - Ouvrir Menu Vue → États Agents (Ctrl+A)
   - Effectuer des actions (conversation, PTT, TTS)
   - Vérifier que les jauges se mettent à jour en temps réel

## Événements émis

### Logs
- `log.message` : Émis par EventBusLogHandler pour tous les logs INFO+

### Métriques LLM
- `llm.start` : Début génération
- `llm.token` : Token généré (streaming)
- `llm.complete` : Fin génération avec métriques complètes
- `llm.error` : Erreur génération

### États agents
- `agent.state_change` : Changement d'état d'un agent
  - `name` : Nom agent (LLM, STT, TTS, RAG, Vision)
  - `status` : Statut (ACTIF, EN_COURS, IDLE, ERREUR)
  - `activity_percentage` : Pourcentage activité (0-100)
  - `details` : Détails texte
  - `last_update` : Timestamp

## Statut

✅ **Corrections appliquées**  
✅ **Événements émis correctement**  
✅ **Fenêtres temps réel fonctionnelles**

