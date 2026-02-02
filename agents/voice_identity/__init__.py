#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module d'identité vocale pour QAIA
Architecture en 3 couches : extraction d'empreinte, gestion de profils, service d'intégration
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "torchaudio>=0.10.0",  # Pour resampling audio
#   "transformers>=4.26.0",
#   "numpy>=1.22.0",
#   "soundfile>=0.10.3",
# ]
# ///

from .embedding_extractor import VoiceEmbeddingExtractor
from .profile_manager import VoiceProfileManager
from .identity_service import VoiceIdentityService

__all__ = [
    'VoiceEmbeddingExtractor',
    'VoiceProfileManager',
    'VoiceIdentityService',
]

