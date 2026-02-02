#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Service API de chat conversationnel QAIA (FastAPI)."""

# /// script
# dependencies = [
#   "fastapi>=0.104.1",
#   "uvicorn[standard]>=0.24.0",
# ]
# ///

from pathlib import Path
from typing import Any, Dict, Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from qaia_core import QAIACore


class ChatRequest(BaseModel):
    """Requête de chat QAIA.

    Attributes:
        message (str): Message utilisateur en texte.
        speaker_id (Optional[str]): Identifiant locuteur pour mémoire personnalisée.
    """

    message: str
    speaker_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Réponse de chat QAIA standardisée.

    Attributes:
        response (str): Réponse textuelle de QAIA.
        intent (Optional[str]): Intention détectée, si disponible.
        context (Optional[str]): Contexte additionnel renvoyé par le noyau.
        error (Optional[str]): Message d'erreur éventuel.
    """

    response: str
    intent: Optional[str] = None
    context: Optional[str] = None
    error: Optional[str] = None


class TTSRequest(BaseModel):
    """Requête TTS pour lecture vocale d'un texte.

    Note:
        Dans cette première version, l'endpoint TTS n'est pas encore
        connecté à un retour audio navigateur et sert de point
        d'extension futur.

    Attributes:
        text (str): Texte à vocaliser.
    """

    text: str


logger = logging.getLogger("qaia_chat_service")

app = FastAPI(
    title="QAIA Chat API",
    version="1.0.0",
    description="API de conversation texte avec QAIA (noyau QAIACore).",
)

BASE_DIR = Path(__file__).parent.parent

_qaia_core: Optional[QAIACore] = None


def get_qaia_core() -> QAIACore:
    """Retourne une instance unique de QAIACore (lazy load).

    Returns:
        QAIACore: Noyau QAIA initialisé.
    """

    global _qaia_core
    if _qaia_core is None:
        logger.info("Initialisation du noyau QAIA pour l'API de chat...")
        _qaia_core = QAIACore()
        logger.info("Noyau QAIA initialisé pour l'API de chat.")
    return _qaia_core


@app.get("/health")
def health() -> Dict[str, Any]:
    """Healthcheck complet du service de chat.

    Returns:
        Dict[str, Any]: Détails de santé retournés par QAIACore.
    """

    core = get_qaia_core()
    return core.health_check()


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Traite un message utilisateur et renvoie la réponse de QAIA.

    Args:
        payload (ChatRequest): Données de la requête (message, speaker_id).

    Returns:
        ChatResponse: Réponse structurée provenant de QAIACore.
    """

    core = get_qaia_core()
    result = core.process_message(payload.message, speaker_id=payload.speaker_id)

    if not isinstance(result, dict):
        return ChatResponse(response=str(result))

    if "error" in result:
        return ChatResponse(
            response=result.get("response", "") or "",
            error=str(result.get("error")),
            intent=result.get("intent"),
            context=result.get("context"),
        )

    return ChatResponse(
        response=str(result.get("response", "")),
        intent=result.get("intent"),
        context=result.get("context"),
    )


@app.post("/tts")
def tts(_payload: TTSRequest) -> Dict[str, str]:
    """Point d'extension TTS pour lecture vocale côté serveur.

    Note:
        Actuellement, cette route ne renvoie qu'un message informatif.
        La synthèse vocale complète (fichiers audio servis au navigateur)
        pourra être ajoutée ultérieurement en s'appuyant sur TTS_CONFIG.

    Returns:
        Dict[str, str]: Message indiquant l'état de l'implémentation.
    """

    raise HTTPException(
        status_code=501,
        detail="TTS web non encore implémenté. Utilisez l'interface QAIA locale pour la synthèse vocale.",
    )


@app.get("/qaia-ui")
def qaia_ui() -> FileResponse:
    """Renvoie la page HTML de l'interface de chat QAIA pour le navigateur.

    Returns:
        FileResponse: Page HTML principale de l'interface QAIA web.
    """

    index_path = BASE_DIR / "static" / "chat" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Interface QAIA UI non disponible.")
    return FileResponse(index_path)

