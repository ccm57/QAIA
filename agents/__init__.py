"""
Package agents pour QAIA
"""

# /// script
# dependencies = []
# ///

from .speaker_auth import SpeakerAuth
from .rag_agent import DataSources
from .wav2vec_agent import Wav2VecVoiceAgent
from .speech_agent import SpeechAgent
from data.database import Database
from utils.clean_ram import MemoryCleaner, clean_ram
from utils.embedding_cache import EmbeddingCache
from config.setup_logging import setup_logging

__all__ = [
    'SpeakerAuth',
    'DataSources',
    'Wav2VecVoiceAgent',
    'SpeechAgent',
    'Database',
    'clean_ram',
    'MemoryCleaner',
    'EmbeddingCache',
    'setup_logging'
] 