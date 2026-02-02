# Configuration GPU / CUDA pour QAIA

Ce document décrit la procédure d'installation et de configuration de PyTorch avec CUDA pour utiliser le GPU NVIDIA GTX 1050 (2 Go VRAM) avec les modèles audio de QAIA.

## Matériel

- **Carte graphique**: NVIDIA GeForce GTX 1050
- **VRAM**: 2 Go
- **Processeur**: Intel Core i7-7700HQ @ 2.80 GHz
- **RAM**: 40 Go
- **OS**: Linux Mint

## Prérequis

### 1. Vérifier les drivers NVIDIA

```bash
nvidia-smi
```

Si la commande échoue, installer les drivers NVIDIA :

```bash
sudo apt update
sudo apt install nvidia-driver-535  # ou version plus récente selon votre distribution
sudo reboot
```

### 2. Vérifier CUDA Toolkit

```bash
nvcc --version
```

Si CUDA n'est pas installé, installer CUDA Toolkit 11.8 ou 12.1 (compatible GTX 1050) :

```bash
# Pour CUDA 11.8 (recommandé pour compatibilité)
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run
sudo sh cuda_11.8.0_520.61.05_linux.run
```

## Installation PyTorch avec CUDA

### Option 1 : PyTorch avec CUDA 11.8 (recommandé)

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Option 2 : PyTorch avec CUDA 12.1

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Vérification

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
```

Résultat attendu :
```
PyTorch version: 2.x.x+cu118
CUDA available: True
CUDA version: 11.8
GPU device: GeForce GTX 1050
```

## Configuration QAIA

### 1. Activer les flags GPU dans `config/system_config.py`

```python
"gpu_audio": {
    "USE_GPU_FOR_STT": True,              # Activer GPU pour STT
    "USE_GPU_FOR_SPEAKER_AUTH": False,   # Désactiver speaker_auth GPU (priorité STT)
}
```

**Note importante** : Avec 2 Go VRAM, activer un seul modèle audio à la fois pour éviter la saturation mémoire.

### 2. Modifier les agents pour utiliser les flags

Les agents (`wav2vec_agent.py`, `voice_identity/embedding_extractor.py`) doivent vérifier les flags avant d'utiliser le GPU :

```python
from config.system_config import MODEL_CONFIG

use_gpu = MODEL_CONFIG.get("gpu_audio", {}).get("USE_GPU_FOR_STT", False) and torch.cuda.is_available()
device = torch.device("cuda" if use_gpu else "cpu")
```

## Tests de base

### Test 1 : Charger un modèle audio sur GPU

```python
import torch
from transformers import Wav2Vec2Model

if torch.cuda.is_available():
    model = Wav2Vec2Model.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-french")
    model = model.to("cuda")
    model.eval()
    print("✅ Modèle chargé sur GPU")
    
    # Vérifier l'utilisation VRAM
    print(f"VRAM utilisée: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    print(f"VRAM réservée: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
else:
    print("❌ CUDA non disponible")
```

### Test 2 : Mesurer la latence STT

```python
import time
import torch
import numpy as np
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

processor = Wav2Vec2Processor.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-french")
model = Wav2Vec2ForCTC.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-french")

# Activer GPU si disponible
if torch.cuda.is_available():
    model = model.to("cuda")
    device = "cuda"
else:
    device = "cpu"

model.eval()

# Audio de test (3 secondes, 16 kHz)
audio = np.random.randn(48000).astype(np.float32)
inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
inputs = {k: v.to(device) for k, v in inputs.items()}

# Mesurer latence
start = time.time()
with torch.no_grad():
    outputs = model(**inputs)
latency = time.time() - start

print(f"Latence STT ({device}): {latency*1000:.2f} ms")
```

### Test 3 : Vérifier la saturation VRAM

```python
import torch

if torch.cuda.is_available():
    # Charger STT
    model_stt = Wav2Vec2ForCTC.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-french")
    model_stt = model_stt.to("cuda")
    print(f"VRAM après STT: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    
    # Essayer de charger speaker_auth en parallèle
    try:
        model_auth = Wav2Vec2Model.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-french")
        model_auth = model_auth.to("cuda")
        print(f"VRAM après STT + Auth: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
        print("⚠️ Attention: saturation VRAM possible avec 2 Go")
    except RuntimeError as e:
        print(f"❌ Erreur VRAM: {e}")
```

## Recommandations

### Avec 2 Go VRAM (GTX 1050)

1. **Activer un seul modèle audio à la fois** :
   - Soit STT (pour latence réduite)
   - Soit speaker_auth (pour authentification vocale)

2. **Désactiver le GPU pour le LLM** :
   - Le LLM reste en CPU (`n_gpu_layers = 0` dans la config)

3. **Surveiller l'utilisation VRAM** :
   ```python
   torch.cuda.memory_allocated(0) / 1024**2  # MB utilisée
   torch.cuda.memory_reserved(0) / 1024**2   # MB réservée
   ```

4. **Optimiser la taille des batchs** :
   - Traiter les audio un par un (batch_size=1)
   - Limiter la longueur audio (ex: 5-7 secondes max)

## Dépannage

### Problème : `torch.cuda.is_available()` retourne `False`

**Solutions** :
1. Vérifier les drivers NVIDIA : `nvidia-smi`
2. Vérifier la version PyTorch : `pip show torch`
3. Réinstaller PyTorch avec CUDA : `pip install torch --index-url https://download.pytorch.org/whl/cu118`

### Problème : Erreur "CUDA out of memory"

**Solutions** :
1. Désactiver un des modèles GPU (STT ou speaker_auth)
2. Réduire la longueur audio traitée
3. Libérer la mémoire : `torch.cuda.empty_cache()`

### Problème : Latence GPU supérieure à CPU

**Causes possibles** :
- Modèle trop petit pour bénéficier du GPU
- Overhead de transfert CPU→GPU pour petits batchs
- **Solution** : Garder le modèle en CPU si la latence est acceptable

## Références

- [PyTorch CUDA Installation](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- [Transformers GPU Guide](https://huggingface.co/docs/transformers/perf_infer_gpu_one)

