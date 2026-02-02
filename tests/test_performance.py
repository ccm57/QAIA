#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de test de performance (restauré, sans téléchargements optionnels)
- Applique une configuration de performance si disponible
- Initialise QAIA
- Envoie quelques messages courts et mesure la latence
"""

# /// script
# dependencies = [
#   "psutil>=5.9.0",
# ]
# ///

import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_conversation_performance():
    os.environ["SKIP_MODEL_DOWNLOAD"] = "1"
    os.environ["DISABLE_OPTIONAL_MODELS"] = "1"

    try:
        # Note: Configuration de performance gérée via system_config.py
        from qaia_core import QAIACore
        qaia = QAIACore()
        logger.info("QAIA initialisé")

        messages = ["Bonjour", "Comment vas-tu ?", "Au revoir"]
        latencies = []
        for msg in messages:
            start = time.time()
            try:
                resp = qaia.process_message(msg)
            except Exception as e:
                logger.error(f"Erreur traitement: {e}")
                resp = {"error": str(e)}
            lat = time.time() - start
            latencies.append(lat)
            logger.info(f"Message: {msg} | latence: {lat:.2f}s | ok: {('error' not in resp)}")

        if latencies:
            logger.info(f"Latence moyenne: {sum(latencies)/len(latencies):.2f}s; min: {min(latencies):.2f}s; max: {max(latencies):.2f}s")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")
        return False

if __name__ == "__main__":
    logger.info("Démarrage du test de performance (restauré)")
    ok = test_conversation_performance()
    logger.info("OK" if ok else "ECHEC")
