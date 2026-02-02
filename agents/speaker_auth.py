"""
Module d'authentification des locuteurs pour QAIA
"""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "torchaudio>=0.10.0", # Ou la version correspondante à torch
#   "numpy>=1.22.0",
#   "soundfile>=0.10.3",
#   "sounddevice>=0.4.5"
# ]
# ///

import os
import logging
from pathlib import Path
import numpy as np
import torch
try:
    import torchaudio
except ImportError as e:
    raise ImportError(
        "torchaudio est manquant. Installez-le (version alignée avec torch) pour utiliser speaker_auth."
    ) from e

from torch import nn
from typing import Optional, Dict, Any

try:
    import soundfile as sf
except ImportError as e:
    raise ImportError("soundfile est manquant. Installez-le pour utiliser speaker_auth.") from e

try:
    import sounddevice as sd
except ImportError as e:
    raise ImportError("sounddevice est manquant. Installez-le pour utiliser speaker_auth.") from e

# Importer la configuration système pour les chemins
from config.system_config import (
    VOICE_PROFILES_DIR as QAIA_VOICE_PROFILES_DIR,
    LOGS_DIR as QAIA_LOGS_DIR,
    MODELS_DIR as QAIA_MODELS_DIR # Au cas où le modèle d'embedding est stocké localement via config
)

# Configuration des chemins (utilise system_config)
# BASE_DIR = Path(__file__).parent.parent.absolute() # Non nécessaire si les chemins spécifiques sont importés
# DATA_DIR = BASE_DIR / "data" # Non nécessaire
# MODELS_DIR = BASE_DIR / "models" # Remplacé par QAIA_MODELS_DIR
# VOICE_PROFILES_DIR = DATA_DIR / "voice_profiles" # Remplacé par QAIA_VOICE_PROFILES_DIR
# LOGS_DIR = BASE_DIR / "logs" # Remplacé par QAIA_LOGS_DIR

# Création des répertoires nécessaires (déjà fait par system_config.py à son import, mais peut être laissé pour robustesse si ce script est autonome)
for directory in [QAIA_MODELS_DIR, QAIA_VOICE_PROFILES_DIR, QAIA_LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(QAIA_LOGS_DIR / "speaker_auth.log"), # Utilise QAIA_LOGS_DIR
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SPEAKER_AUTH")

class SpeakerEmbeddingModel(nn.Module):
    """Modèle d'embedding pour l'authentification des locuteurs."""
    
    def __init__(self):
        """Initialise le modèle d'embedding."""
        super().__init__()
        self.logger = logging.getLogger("SPEAKER_AUTH.Model")
        
        try:
            # Charger un modèle Wav2Vec2 depuis Transformers pour extraire des embeddings
            from transformers import Wav2Vec2Processor, Wav2Vec2Model
            self.model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-french" 
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
            self.model = Wav2Vec2Model.from_pretrained(self.model_name)
            self.model.eval()
            
            if torch.cuda.is_available():
                self.model = self.model.cuda()
            
            self.logger.info("Modèle Wav2Vec2 (Transformers) chargé avec succès pour les embeddings")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modèle Wav2Vec2: {e}")
            raise
            
    def extract_features(self, audio_path: str) -> Optional[torch.Tensor]:
        """Extrait les caractéristiques d'un fichier audio.
        
        Args:
            audio_path (str): Chemin du fichier audio
            
        Returns:
            Optional[torch.Tensor]: Vecteur d'embedding 1D ou None en cas d'erreur
        """
        try:
            # Chargement de l'audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Conversion en mono si nécessaire
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
                
            # Resampling si nécessaire
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
                sample_rate = 16000
                
            # Normalisation simple
            max_abs = torch.max(torch.abs(waveform))
            if max_abs > 0:
                waveform = waveform / max_abs
            
            # Préparation entrée processeur (Transformers attend 1D CPU numpy/torch)
            audio_1d = waveform.squeeze(0).cpu().numpy()
            inputs = self.processor(audio_1d, sampling_rate=sample_rate, return_tensors="pt", padding=True)
            
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Passage dans le modèle pour obtenir les représentations cachées
            with torch.no_grad():
                outputs = self.model(**inputs)
                hidden = outputs.last_hidden_state  # [batch, time, feat]
                # Pooling temporel (moyenne) pour obtenir un vecteur fixe
                embedding = hidden.mean(dim=1).squeeze(0)  # [feat]
            
            return embedding.detach().cpu() if not torch.cuda.is_available() else embedding
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des caractéristiques: {e}")
            return None

class SpeakerAuth:
    """Gère l'authentification des locuteurs."""
    
    def __init__(self, data_dir: str = str(QAIA_VOICE_PROFILES_DIR)): # Utilise QAIA_VOICE_PROFILES_DIR
        """Initialise le gestionnaire d'authentification.
        
        Args:
            data_dir (str): Répertoire des profils vocaux
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("SPEAKER_AUTH")
        
        try:
            self.model = SpeakerEmbeddingModel()
            self.logger.info("Système d'authentification initialisé")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            raise
            
    def verify_speaker(self, audio_path: str, speaker_id: str, threshold: float = 0.8) -> bool:
        """Vérifie l'identité du locuteur.
        
        Args:
            audio_path (str): Chemin du fichier audio
            speaker_id (str): Identifiant du locuteur
            threshold (float): Seuil de similarité
            
        Returns:
            bool: True si le locuteur est authentifié
        """
        try:
            if not os.path.exists(audio_path):
                self.logger.error(f"Fichier audio non trouvé: {audio_path}")
                return False
                
            # Chargement du profil
            profile_path = self.data_dir / f"{speaker_id}.npy"
            if not profile_path.exists():
                self.logger.error(f"Profil non trouvé: {speaker_id}")
                return False
                
            # Extraction des caractéristiques
            features = self.model.extract_features(audio_path)
            if features is None:
                return False
                
            # Chargement du profil de référence
            reference_features = np.load(profile_path)
            
            # Calcul de la similarité
            similarity = self._compute_similarity(features, reference_features)
            
            # Décision
            is_verified = similarity >= threshold
            self.logger.info(f"Vérification {speaker_id}: similarité={similarity:.2f}, seuil={threshold}")
            
            return is_verified
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification: {e}")
            return False
            
    def enroll_speaker(self, audio_path: str, speaker_id: str) -> bool:
        """Enregistre un nouveau profil vocal.
        
        Args:
            audio_path (str): Chemin du fichier audio
            speaker_id (str): Identifiant du locuteur
            
        Returns:
            bool: True si l'enregistrement a réussi
        """
        try:
            if not os.path.exists(audio_path):
                self.logger.error(f"Fichier audio non trouvé: {audio_path}")
                return False
                
            # Extraction des caractéristiques
            features = self.model.extract_features(audio_path)
            if features is None:
                return False
                
            # Sauvegarde du profil
            profile_path = self.data_dir / f"{speaker_id}.npy"
            np.save(profile_path, features.cpu().numpy())
            
            self.logger.info(f"Profil enregistré: {speaker_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement: {e}")
            return False
            
    def _compute_similarity(self, features1: torch.Tensor, features2: np.ndarray) -> float:
        """Calcule la similarité entre deux ensembles de caractéristiques.
        
        Args:
            features1 (torch.Tensor): Premier ensemble de caractéristiques
            features2 (np.ndarray): Deuxième ensemble de caractéristiques
            
        Returns:
            float: Score de similarité
        """
        try:
            # Conversion en numpy si nécessaire
            if isinstance(features1, torch.Tensor):
                features1 = features1.cpu().numpy()
                
            # Normalisation
            features1 = features1 / np.linalg.norm(features1)
            features2 = features2 / np.linalg.norm(features2)
            
            # Calcul de la similarité cosinus
            similarity = np.dot(features1, features2)
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de la similarité: {e}")
            return 0.0
            
    def record_audio(self, duration: float = 5.0, sample_rate: int = 16000) -> Optional[str]:
        """Enregistre un échantillon audio.
        
        Args:
            duration (float): Durée de l'enregistrement en secondes
            sample_rate (int): Taux d'échantillonnage
            
        Returns:
            Optional[str]: Chemin du fichier enregistré ou None en cas d'erreur
        """
        try:
            # Configuration de l'enregistrement
            channels = 1
            dtype = np.float32
            
            self.logger.info(f"Début de l'enregistrement ({duration}s)...")
            
            # Enregistrement
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                dtype=dtype
            )
            sd.wait()
            
            # Sauvegarde
            output_path = self.data_dir / "temp.wav"
            sf.write(output_path, audio, sample_rate)
            
            self.logger.info(f"Enregistrement sauvegardé: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement: {e}")
            return None 