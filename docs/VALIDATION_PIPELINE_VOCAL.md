# Validation du pipeline vocal (bout en bout)

**Objectif** : Valider la chaîne **WAV → STT → normalisation → intention** avant de considérer les commandes vocales comme fiables.

---

## 1. Test automatisé

Le test `tests/test_stt_pipeline_e2e.py` enchaîne :

1. **Transcription** : fichier WAV → `Wav2VecVoiceAgent.transcribe_audio()` → texte + confiance  
2. **Normalisation** : `normalize_stt_text()` (corrections phonétiques)  
3. **Intention** : `IntentDetector.detect()` sur le texte normalisé  

### Exécution

- **Sans fichier WAV** (chaîne texte → normalisation → intention uniquement, sans charger le modèle STT) :
  ```bash
  cd /chemin/vers/QAIA
  python -m pytest tests/test_stt_pipeline_e2e.py::test_normalize_et_intent_sans_wav -v
  ```

- **Avec fichier WAV** :
  - Option 1 : utiliser un enregistrement réel (recommandé pour validation complète)
    ```bash
    export QAIA_STT_E2E_WAV=/chemin/vers/un/enregistrement.wav
    python -m pytest tests/test_stt_pipeline_e2e.py -v
    ```
  - Option 2 : lancer tous les tests du fichier ; si `QAIA_STT_E2E_WAV` n’est pas défini, un WAV de silence est créé temporairement (le STT peut retourner une chaîne vide ou du bruit, le test vérifie surtout que la chaîne ne lève pas et que les types sont corrects).

- **Inclure le test lent (STT avec modèle)** :
  ```bash
  python -m pytest tests/test_stt_pipeline_e2e.py -v -m slow
  ```
  ou sans marqueur :
  ```bash
  python -m pytest tests/test_stt_pipeline_e2e.py -v
  ```

---

## 2. Vérifications effectuées

- Les sorties STT sont bien `(str, float)` (texte, confiance).  
- La normalisation retourne un `str`.  
- La détection d’intention retourne un `IntentResult` avec `intent` dans l’enum `Intent`.  
- La confiance STT est dans un intervalle cohérent (typiquement [0, 1]).

---

## 3. Recommandation

Avant de valider les commandes vocales en production, exécuter au moins une fois le test avec un **fichier WAV réel** (phrase courte en français) pour s’assurer que le modèle STT et la chaîne complète se comportent correctement sur votre environnement.
