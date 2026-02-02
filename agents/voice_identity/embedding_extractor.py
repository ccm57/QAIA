#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Couche 1 : Extracteur d'empreinte vocale
Extrait un vecteur d'embedding à partir d'un fichier audio pour identifier un locuteur.
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

import logging
from pathlib import Path
from typing import Optional
import numpy as np
import torch
import soundfile as sf
from transformers import Wav2Vec2Processor, Wav2Vec2Model
from config.system_config import DEVICE

logger = logging.getLogger(__name__)


class VoiceEmbeddingExtractor:
    """
    Extracteur d'empreinte vocale utilisant Wav2Vec2.
    
    Cette classe extrait un vecteur d'embedding fixe à partir d'un fichier audio
    pour permettre l'identification et la vérification de locuteurs.
    """
    
    def __init__(self, model_name: str = "jonatasgrosman/wav2vec2-large-xlsr-53-french", use_gpu: bool = False):
        """
        Initialise l'extracteur d'empreinte vocale.
        
        Args:
            model_name (str): Nom du modèle Wav2Vec2 à utiliser
            use_gpu (bool): Si True, utilise le GPU si disponible (défaut: False)
        """
        self.logger = logging.getLogger(f"{__name__}.VoiceEmbeddingExtractor")
        self.model_name = model_name
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        
        try:
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
            self.model = Wav2Vec2Model.from_pretrained(self.model_name)
            self.model.eval()
            self.model.to(self.device)
            
            self.logger.info(f"Extracteur d'empreinte vocale initialisé (modèle: {self.model_name}, device: {self.device})")
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modèle Wav2Vec2: {e}")
            raise
    
    def extraire_empreinte(self, audio_path: str, pooling: str = "mean") -> Optional[np.ndarray]:
        """
        Extrait une empreinte vocale (embedding) à partir d'un fichier audio.
        
        Args:
            audio_path (str): Chemin vers le fichier audio (WAV, mono, 16 kHz recommandé)
            pooling (str): Méthode de pooling pour obtenir un vecteur fixe ("mean" ou "attention")
            
        Returns:
            Optional[np.ndarray]: Vecteur d'embedding de dimension fixe (ex: 768 ou 1024), ou None en cas d'erreur
        """
        try:
            # Charger l'audio
            audio, sample_rate = sf.read(audio_path)
            
            # Normaliser si nécessaire (amplitude entre -1.0 et 1.0)
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            if np.abs(audio).max() > 1.0:
                audio = audio / np.abs(audio).max()
            
            # Resample si nécessaire (Wav2Vec2 attend 16 kHz)
            if sample_rate != 16000:
                import torchaudio
                audio_tensor = torch.from_numpy(audio).unsqueeze(0)
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_tensor = resampler(audio_tensor)
                audio = audio_tensor.squeeze(0).numpy()
                sample_rate = 16000
            
            # Traiter avec Wav2Vec2
            inputs = self.processor(audio, sampling_rate=sample_rate, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Extraire les features (shape: [batch, seq_len, hidden_dim])
                features = outputs.last_hidden_state
                
                # Pooling pour obtenir un vecteur fixe
                if pooling == "mean":
                    embedding = features.mean(dim=1).squeeze(0)  # [hidden_dim]
                elif pooling == "attention":
                    # Pooling attention simple (moyenne pondérée)
                    attention_weights = torch.softmax(features.mean(dim=-1), dim=1)
                    embedding = (features * attention_weights.unsqueeze(-1)).sum(dim=1).squeeze(0)
                else:
                    embedding = features.mean(dim=1).squeeze(0)
            
            # Convertir en numpy et normaliser
            embedding_np = embedding.cpu().numpy()
            embedding_np = embedding_np / (np.linalg.norm(embedding_np) + 1e-8)  # Normalisation L2
            
            self.logger.debug(f"Empreinte extraite: shape={embedding_np.shape}, norm={np.linalg.norm(embedding_np):.4f}")
            return embedding_np
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction d'empreinte depuis {audio_path}: {e}")
            return None

