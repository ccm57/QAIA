# Configuration Chroma / RAG unifiée

Ce document décrit la configuration unifiée de la base vectorielle (Chroma) et du RAG pour QAIA, valable en exécution locale et en conteneurs.

## Variables d'environnement unifiées

| Variable | Rôle | Local (défaut) | Conteneur (ex. Minikube) |
|----------|------|----------------|---------------------------|
| `QAIA_DATA_DIR` | Répertoire racine des données (documents, vector_db, audio) | `<QAIA>/data` | `/app/data` |
| `QAIA_VECTOR_DB_DIR` | Répertoire de la base Chroma (persistance) | `QAIA_DATA_DIR/vector_db` | `/app/data/vector_db` |

Recommandation : conserver `QAIA_VECTOR_DB_DIR = QAIA_DATA_DIR/vector_db` pour la cohérence entre environnements.

Les variables optionnelles `QAIA_MODELS_DIR` et `QAIA_LOGS_DIR` sont également lues par `config/system_config.py` si définies.

## Mode actuel : Chroma embarqué

QAIA utilise **uniquement** le mode **Chroma embarqué** (persistance sur disque) :

- L'agent RAG (`agents/rag_agent.py`) initialise LangChain `Chroma` avec `persist_directory=str(VECTOR_DB_DIR)`.
- Aucun client HTTP Chroma n'est utilisé : les variables `CHROMA_HOST` et `CHROMA_PORT` **ne sont pas lues** par l'application.
- Le chemin de la base est dérivé de `config.system_config.VECTOR_DB_DIR`, lui-même issu de `QAIA_VECTOR_DB_DIR`.

En conteneur (Docker / Minikube), le ConfigMap doit définir `QAIA_DATA_DIR` et `QAIA_VECTOR_DB_DIR` ; le volume monté sur `/app/data` contient alors `vector_db/` pour Chroma.

## Mode fallback (RAG indisponible)

Si l'initialisation de Chroma ou du RAG échoue (disque, permissions, dépendances) :

- L'agent RAG positionne `vector_db = None` et logue l'erreur.
- QAIA démarre en mode **sans RAG** : réponses sans recherche documentaire, sans crash.
- Le health-check (`/health`) renvoie `"vector_db": false` dans `details`.
- L'interface (diagnostic) affiche la base vectorielle (RAG) comme désactivée.

Aucune action utilisateur requise : le fallback est automatique et documenté dans les logs.

## Évolution future (Chroma serveur distant)

Pour un déploiement avec un conteneur ChromaDB dédié :

- Introduire le support optionnel de `CHROMA_HOST` et `CHROMA_PORT` dans `rag_agent.py`.
- Si ces variables sont définies, utiliser un client HTTP Chroma au lieu de `persist_directory`.
- Aligner les noms de collection / tenant / database côté serveur Chroma et côté client.

Les manifests DevOps peuvent déjà exposer `CHROMA_HOST` / `CHROMA_PORT` pour une future utilisation ; ils ne sont pas utilisés par l'application actuelle.
