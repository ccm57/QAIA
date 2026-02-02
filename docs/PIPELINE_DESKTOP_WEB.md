# Pipeline QAIA : Desktop et Web

Ce document décrit les deux modes d’exécution QAIA (desktop et web), leur état opérationnel et comment les lancer / valider.

---

## Vue d’ensemble

| Mode    | Point d’entrée              | Interface              | LLM | RAG | STT/TTS | Déploiement        |
|---------|-----------------------------|------------------------|-----|-----|---------|--------------------|
| Desktop | `python3 launcher.py`       | CustomTkinter (V2)     | Oui | Oui | Oui     | Local (venv)        |
| Web     | FastAPI `chat_service`     | Page HTML `/qaia-ui`   | Oui | Oui | Non*    | Docker / Minikube   |

\* TTS web : endpoint `/tts` présent mais renvoie 501 (prévu pour une évolution ultérieure).

---

## Mode Desktop (opérationnel)

### Lancement
```bash
cd /media/ccm57/SSDIA/QAIA
source .venv/bin/activate   # ou activer l’environnement virtuel
python3 launcher.py
```

### Fonctionnalités
- Interface graphique CustomTkinter (streaming, monitoring, logs, états agents).
- Noyau QAIACore : LLM (Phi-3), RAG (Chroma embarqué), STT (Wav2Vec2), TTS (Piper).
- Détection d'intentions : pour les entrées texte/vocale, QAIACore utilise IntentDetector + DialogueManager pour adapter la réponse (salutations, fin de conversation, confirmations). L'intention COMMAND déclenche le pipeline commandes système (sécurité + exécution contrôlée).
- Fallback RAG : si Chroma est indisponible, QAIA démarre sans RAG (pas de crash).
- Variables : `QAIA_DATA_DIR`, `QAIA_VECTOR_DB_DIR` (voir [CONFIG_CHROMA_RAG.md](CONFIG_CHROMA_RAG.md)).

### Validation rapide
- L’interface s’ouvre, le health/diagnostic affiche RAG ✅ ou ❌.
- Envoyer un message texte et vérifier une réponse du LLM.

---

## Mode Web (opérationnel)

### Architecture
- **Image Docker** `qaia-app` : CMD `uvicorn services.chat_service:app --host 0.0.0.0 --port 8000`.
- **Endpoints** : `GET /health`, `POST /chat`, `GET /qaia-ui` (page de chat), `POST /tts` (501).
- **Réponse /chat** : le JSON peut inclure un champ `intent` (ex. `question`, `greeting`, `command`) et, pour les commandes, `command_executed` ou `command_refused` selon le pipeline commandes.
- **Minikube** : déploiement `qaia`, service `qaia-app` (port 8000), Ingress `qaia-app-ingress` pour `/qaia-ui`, `/health`, `/chat`.

### Lancement (Minikube)
1. Démarrer Minikube et construire les images (inclut la sync du code QAIA) :
   ```bash
   /media/ccm57/SSDIA/DevOps-Center/scripts/minikube/minikube_start.sh
   /media/ccm57/SSDIA/DevOps-Center/scripts/minikube/minikube_build_images.sh
   ```
2. Déployer :
   ```bash
   /media/ccm57/SSDIA/DevOps-Center/scripts/minikube/minikube_deploy.sh
   ```
3. (Optionnel) Synchroniser les modèles LLM si nécessaire :
   ```bash
   /media/ccm57/SSDIA/DevOps-Center/scripts/minikube/minikube_sync_models.sh
   ```

### Accès à l’interface web
- **Port-forward** : `kubectl port-forward svc/qaia-app -n qaia 8081:8000` puis ouvrir `http://localhost:8081/qaia-ui`.
- **Ingress** : ajouter `qaia.local` dans `/etc/hosts` (IP Minikube) puis ouvrir `http://qaia.local/qaia-ui`.

### Validation rapide
- `GET http://localhost:8081/health` (ou via Ingress) → JSON avec `details.vector_db`, `status: ok`.
- Ouvrir `/qaia-ui`, envoyer un message et vérifier la réponse du chat.

### Détails
- Voir [DevOps-Center/docs/MINIKUBE_QAIA.md](/media/ccm57/SSDIA/DevOps-Center/docs/MINIKUBE_QAIA.md) pour les prérequis, logs et nettoyage.

---

## Optimisations en place

- **Chroma/RAG** : une seule initialisation (dans `rag_agent.py`), config unifiée `QAIA_VECTOR_DB_DIR`, fallback propre si Chroma indisponible.
- **Build web** : `minikube_build_images.sh` exécute `sync_qaia_source.sh` avant le build pour embarquer la dernière version du code QAIA.
- **Health / diagnostic** : `vector_db: true/false` exposé dans `/health` et dans l’UI desktop pour refléter le mode RAG actif ou désactivé.

---

## À faire / optionnel

- **TTS web** : implémenter la synthèse vocale côté serveur et lecture audio dans le navigateur (endpoint `/tts` actuellement 501).
- **Tests bout-en-bout** : scénarios automatisés desktop (launcher + un tour de chat) et web (curl/playwright sur `/health` et `/chat`).
