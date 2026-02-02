# Schéma de base de données QAIA

Ce document décrit le schéma complet de la base de données SQLite `qaia.db`.

## Tables principales

### 1. `speakers` (Locuteurs / Identité vocale)

Table pour stocker les profils vocaux des locuteurs identifiés.

| Colonne        | Type   | Description                                    |
|----------------|--------|------------------------------------------------|
| `speaker_id`   | TEXT   | Identifiant unique du locuteur (PRIMARY KEY)   |
| `prenom`       | TEXT   | Prénom du locuteur (optionnel)                 |
| `civilite`     | TEXT   | Civilité (Monsieur, Madame, etc., optionnel)  |
| `metadata`     | TEXT   | Métadonnées additionnelles (JSON string)       |
| `embedding_path` | TEXT | Chemin vers le fichier .npy d'embedding vocal |
| `created_at`   | DATETIME | Date de création du profil                    |
| `updated_at`   | DATETIME | Date de dernière mise à jour                  |

**Notes :**
- Les embeddings vocaux sont stockés dans `data/voice_profiles/` (fichiers `.npy`).
- Les métadonnées peuvent contenir des informations additionnelles (tags, préférences, etc.).

### 2. `conversations` (Historique de conversations)

Table principale pour stocker l'historique des échanges avec QAIA.

| Colonne        | Type   | Description                                    |
|----------------|--------|------------------------------------------------|
| `id`           | INTEGER | Identifiant unique (PRIMARY KEY, AUTOINCREMENT) |
| `timestamp`    | DATETIME | Date/heure de la conversation (DEFAULT CURRENT_TIMESTAMP) |
| `speaker_id`   | TEXT   | Référence vers `speakers.speaker_id` (optionnel, NULL si non identifié) |
| `user_input`   | TEXT   | Texte de l'entrée utilisateur                  |
| `qaia_response`| TEXT   | Réponse générée par QAIA                       |

**Relations :**
- `speaker_id` → `speakers.speaker_id` (FOREIGN KEY, peut être NULL)

**Notes :**
- Si `speaker_id` est NULL, la conversation n'est pas associée à un locuteur identifié.
- Permet de filtrer l'historique par locuteur pour une mémoire conversationnelle personnalisée.

### 3. `conversation_media` (Médias associés aux conversations)

Table pour stocker les fichiers audio associés aux conversations.

| Colonne        | Type   | Description                                    |
|----------------|--------|------------------------------------------------|
| `id`           | INTEGER | Identifiant unique (PRIMARY KEY, AUTOINCREMENT) |
| `conversation_id` | INTEGER | Référence vers `conversations.id` (FOREIGN KEY) |
| `media_type`   | TEXT   | Type de média : 'user_audio' ou 'qaia_audio'   |
| `path`         | TEXT   | Chemin vers le fichier audio                  |
| `duration_ms`  | INTEGER | Durée du fichier audio en millisecondes (optionnel) |
| `created_at`   | DATETIME | Date de création (DEFAULT CURRENT_TIMESTAMP)   |

**Relations :**
- `conversation_id` → `conversations.id` (FOREIGN KEY)

### 4. `settings` (Paramètres de configuration)

Table pour stocker les paramètres de configuration persistants.

| Colonne        | Type   | Description                                    |
|----------------|--------|------------------------------------------------|
| `key`          | TEXT   | Clé du paramètre (PRIMARY KEY)                 |
| `value`        | TEXT   | Valeur du paramètre (sérialisée si nécessaire) |
| `updated_at`   | DATETIME | Date de dernière mise à jour                  |

### 5. `documents` (Documents pour RAG)

Table pour suivre les documents indexés dans la base vectorielle RAG.

| Colonne        | Type   | Description                                    |
|----------------|--------|------------------------------------------------|
| `id`           | INTEGER | Identifiant unique (PRIMARY KEY, AUTOINCREMENT) |
| `filename`     | TEXT   | Nom du fichier                                 |
| `path`         | TEXT   | Chemin vers le fichier                         |
| `added_at`     | DATETIME | Date d'ajout (DEFAULT CURRENT_TIMESTAMP)      |
| `indexed`      | BOOLEAN | Indique si le document est indexé dans ChromaDB (DEFAULT 0) |

---

## Requêtes utiles

### Récupérer l'historique d'un locuteur spécifique

```sql
SELECT id, timestamp, user_input, qaia_response 
FROM conversations 
WHERE speaker_id = 'claude_dupont' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Lister tous les locuteurs avec leur nombre de conversations

```sql
SELECT s.speaker_id, s.prenom, s.civilite, COUNT(c.id) as nb_conversations
FROM speakers s
LEFT JOIN conversations c ON s.speaker_id = c.speaker_id
GROUP BY s.speaker_id
ORDER BY nb_conversations DESC;
```

### Récupérer les conversations récentes avec informations du locuteur

```sql
SELECT c.id, c.timestamp, c.user_input, c.qaia_response, 
       s.prenom, s.civilite
FROM conversations c
LEFT JOIN speakers s ON c.speaker_id = s.speaker_id
ORDER BY c.timestamp DESC
LIMIT 20;
```

---

## Migration et compatibilité

- La colonne `speaker_id` dans `conversations` est ajoutée automatiquement lors de l'initialisation si elle n'existe pas (migration transparente pour les bases existantes).
- Les anciennes conversations auront `speaker_id = NULL` (comportement attendu).

