#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Agent RAG pour QAIA"""

# /// script
# dependencies = [
#   "langchain-community>=0.0.10",
#   "langchain-huggingface>=0.0.1",
#   "torch>=2.0.0",
#   "sentence-transformers>=2.2.2",
#   "chromadb>=0.4.0",
#   "scikit-learn>=1.0.0", # Pour PCA
#   # Doc loaders:
#   "pypdf>=3.0.0", # PyMuPDFLoader est utilisé mais pypdf est une dépendance plus générale
#   "unstructured>=0.7.0",
#   "python-docx>=1.1.0", # Pour Docx2txtLoader (docx2txt -> python-docx)
#   "markdownloader" # vérifier le nom exact du paquet pour UnstructuredMarkdownLoader si besoin
# ]
# ///

import os
import pickle
import hashlib
import logging
from datetime import datetime
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import LlamaCpp
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyMuPDFLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import torch
from pathlib import Path
import shutil
from typing import List, Dict, Any, Optional
import gc
import time
import traceback
import re

# Importer la configuration depuis system_config
from config.system_config import (
    MODEL_CONFIG,
    MODELS_DIR as QAIA_MODELS_DIR,
    LOGS_DIR as QAIA_LOGS_DIR,
    DATA_DIR as QAIA_DATA_DIR,
    VECTOR_DB_DIR,
    RAG_CONFIG
)

# ======================
# CONFIGURATION UTILISANT system_config
# ======================
DOC_DIR = QAIA_DATA_DIR / "documents"
PERSIST_DIR = VECTOR_DB_DIR
CACHE_DIR = QAIA_DATA_DIR / "embeddings"

# Configuration LLM depuis system_config
llm_config_from_system = MODEL_CONFIG.get("llm", {})
MODEL_PATH_STR = llm_config_from_system.get("model_path")

if not MODEL_PATH_STR:
    logging.getLogger(__name__).error("Chemin du modèle LLM non trouvé dans system_config")
    raise ValueError("MODEL_CONFIG['llm']['model_path'] non défini")
else:
    MODEL_PATH = Path(MODEL_PATH_STR)

# Modèle d'embedding depuis system_config
embedding_config_from_system = MODEL_CONFIG.get("embeddings", {})
EMBEDDING_MODEL = embedding_config_from_system.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")

# Configuration threads et GPU
MAX_THREADS = llm_config_from_system.get("n_threads", 6)
GPU_LAYERS = llm_config_from_system.get("n_gpu_layers", 0)

# Détection du GPU (logging informatif)
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # En GB
    
    logger_setup = logging.getLogger("GPU_SETUP")
    logger_setup.info(f"GPU détecté: {gpu_name} avec {gpu_vram:.2f} GB VRAM")
    logger_setup.info(f"Configuration LLM n_gpu_layers: {GPU_LAYERS}") # Affiche la valeur de la config

# ==============
# SETUP LOGGING
# ==============
LOG_DIR = QAIA_LOGS_DIR
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"rag_agent_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Support de formats multiples
LOADERS_MAPPING = {
    ".txt": DirectoryLoader(str(DOC_DIR), glob="**/*.txt"),
    ".pdf": DirectoryLoader(str(DOC_DIR), glob="**/*.pdf", loader_cls=PyMuPDFLoader),
    ".html": DirectoryLoader(str(DOC_DIR), glob="**/*.html", loader_cls=UnstructuredHTMLLoader),
    ".htm": DirectoryLoader(str(DOC_DIR), glob="**/*.htm", loader_cls=UnstructuredHTMLLoader),
    ".md": DirectoryLoader(str(DOC_DIR), glob="**/*.md", loader_cls=UnstructuredMarkdownLoader),
    ".docx": DirectoryLoader(str(DOC_DIR), glob="**/*.docx", loader_cls=Docx2txtLoader),
}

# ====================
# GESTION DES SOURCES
# ====================
class DataSources:
    """Gère les sources de données pour RAG."""
    
    def __init__(self, doc_dir=DOC_DIR):
        """Initialise le gestionnaire de sources de données.
        
        Args:
            doc_dir (str): Répertoire des documents
        """
        self.doc_dir = Path(doc_dir)
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def count_documents(self):
        """Compte le nombre de documents disponibles.
        
        Returns:
            int: Nombre de documents
        """
        try:
            return len(list(self.doc_dir.glob("**/*")))
        except Exception as e:
            self.logger.error(f"Erreur lors du comptage des documents: {e}")
            return 0
            
    def list_documents(self):
        """Liste les documents disponibles.
        
        Returns:
            list: Liste des chemins des documents
        """
        try:
            return [str(p) for p in self.doc_dir.glob("**/*")]
        except Exception as e:
            self.logger.error(f"Erreur lors de la liste des documents: {e}")
            return []
            
    def import_document(self, file_path):
        """Importe un document.
        
        Args:
            file_path (str): Chemin du document à importer
            
        Returns:
            bool: True si l'importation a réussi
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Fichier non trouvé: {file_path}")
                return False
                
            # Copier le fichier dans le répertoire des documents
            shutil.copy2(file_path, self.doc_dir)
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'importation du document: {e}")
            return False

# ====================
# CACHE DES EMBEDDINGS
# ====================
class EmbeddingCache:
    def __init__(self, model):
        self.model = model
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_embedding(self, text: str):
        """Retourne l'embedding d'un texte avec un cache local."""
        try:
            hash_key = hashlib.md5(text.encode()).hexdigest()
            cache_path = os.path.join(CACHE_DIR, f"{hash_key}.pkl")
            
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    logger.debug(f"Cache hit pour: {text[:50]}...")
                    return pickle.load(f)
            
            embedding = self.model.embed_query(text)
            with open(cache_path, "wb") as f:
                pickle.dump(embedding, f)
            
            logger.debug(f"Nouveau cache d'embedding: {text[:50]}...")
            return embedding
            
        except Exception as e:
            logger.error(f"Erreur d'embedding: {str(e)}")
            return None

# =========================
# CHARGEMENT DES DOCUMENTS
# =========================
def load_all_documents():
    """Charge tous les documents de tous les formats supportés."""
    all_documents = []
    
    if not os.path.exists(DOC_DIR) or not os.listdir(DOC_DIR):
        logger.warning("Aucun document trouvé dans 'data/documents/' ! Vérifiez le chemin.")
        return []
    
    extensions_found = set()
    for ext, loader in LOADERS_MAPPING.items():
        try:
            docs = loader.load()
            if docs:
                logger.info(f"Chargé {len(docs)} documents avec l'extension {ext}")
                all_documents.extend(docs)
                extensions_found.add(ext)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des documents {ext}: {e}")
    
    if not extensions_found:
        logger.warning(f"Aucun document supporté trouvé. Formats supportés: {', '.join(LOADERS_MAPPING.keys())}")
    else:
        logger.info(f"Formats de documents chargés: {', '.join(extensions_found)}")
    
    return all_documents

# ==================
# INITIALISATION
# ==================
logger.info("Initialisation des modèles...")

try:
    # Configuration du modèle LLM
    DEFAULT_MODEL_PATH = str(MODEL_PATH)
    LLM_CONFIG = {
    "model_path": MODEL_PATH_STR,
    "n_ctx": MODEL_CONFIG["llm"]["n_ctx"],
    "n_threads": MODEL_CONFIG["llm"]["n_threads"],
    "n_gpu_layers": MODEL_CONFIG["llm"]["n_gpu_layers"],
    "n_batch": MODEL_CONFIG["llm"]["n_batch"],
    "temperature": MODEL_CONFIG["llm"]["temperature"],
    "top_p": MODEL_CONFIG["llm"]["top_p"],
    "max_tokens": MODEL_CONFIG["llm"]["max_tokens"],
    "verbose": False}

    # Détection et configuration GPU
    if torch.cuda.is_available():
        try:
            gpu_name = torch.cuda.get_device_name(0)
            vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024**2)
            logger.info(f"GPU détecté: {gpu_name} avec {vram_mb:.2f} MB VRAM")
            
            # Pour GTX 1050 avec 2GB VRAM - forcer le mode CPU
            # Les couches GPU sont définies comme 0 dans LLM_CONFIG
            if "GTX 1050" in gpu_name or vram_mb < 3000:
                logger.info("GPU avec peu de VRAM détecté, utilisation du CPU uniquement")
            else:
                # Nombre de couches dynamique en fonction de la VRAM disponible
                gpu_layers = min(int(vram_mb / 500), 32)  # ~500MB par couche
                LLM_CONFIG["n_gpu_layers"] = gpu_layers
                logger.info(f"Utilisation de {gpu_layers} couches sur GPU")
        except Exception as e:
            logger.error(f"Erreur lors de la configuration GPU: {e}")
            logger.error(traceback.format_exc())

    # Initialisation du modèle LLM avec traitement d'exceptions amélioré
    logger.info(f"Initialisation du modèle avec {LLM_CONFIG['n_threads']} threads et {LLM_CONFIG['n_gpu_layers']} couches GPU")

    try:
        # Vérifier si le fichier du modèle existe
        model_path = LLM_CONFIG["model_path"]
        if not os.path.exists(model_path):
            logger.error(f"Fichier modèle introuvable: {model_path}")
            raise FileNotFoundError(f"Modèle LLM non trouvé: {model_path}")
        
        # Import du callback streaming
        from agents.callbacks.streaming_callback import StreamingCallback
        
        llm = LlamaCpp(
            model_path=model_path,
            n_gpu_layers=LLM_CONFIG["n_gpu_layers"],
            n_batch=512,  # OPTIMISÉ: Traite 512 tokens en parallèle (accélère génération 5-10×)
            n_ctx=LLM_CONFIG["n_ctx"],
            verbose=LLM_CONFIG["verbose"],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"],
            n_threads=LLM_CONFIG["n_threads"],
            streaming=True,  # ✅ Activé pour streaming temps réel
            stop=[
                "<|end|>", "<|endoftext|>", "\n\n\n",
                "---", "##", "###",  # Arrêter les markdown (fragments d'instructions)
                "<|user|>", "<|assistant|>", "<|system|>",  # Balises Phi-3
                "Instruction", "Contraintes",  # Fragments d'instructions à éviter
                "Artemis", "NINA", "N IN A",  # Noms d'exemple à éviter
            ],  # CRITIQUE: Arrêter génération aux balises Phi-3 et fragments suspects
            callbacks=[StreamingCallback()]  # Callback pour Event Bus
        )
        
        # Forcer la libération de la mémoire CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation : {e}")
        llm = None  # Gestion gracieuse de l'échec

    # 2. Chargement de tous les documents supportés
    documents = load_all_documents()
    logger.info(f"Nombre total de documents chargés: {len(documents)}")

    # 3. Découpage du texte (évite les tokens excessifs)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    texts = text_splitter.split_documents(documents) if documents else []
    
    # 4. Création de la base vectorielle
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Client Chroma persistant explicite (évite tenant/database en conteneur avec Chroma 0.4+)
    _chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    
    # Création ou récupération de la base vectorielle
    if texts:
        logger.info(f"Création/mise à jour de la base vectorielle avec {len(texts)} chunks")
        vector_db = Chroma.from_documents(
            documents=texts,
            embedding=embeddings,
            client=_chroma_client,
        )
        logger.info("Base vectorielle créée dans Chroma")
    else:
        # Si aucun document, tenter de charger une base existante, sinon créer une base vide
        logger.warning("Aucun document à vectoriser, tentative de chargement d'une base existante")
        try:
            vector_db = Chroma(
                client=_chroma_client,
                embedding_function=embeddings,
            )
            logger.info("Base vectorielle existante chargée")
        except Exception as e:
            logger.warning(f"Impossible de charger une base existante: {e}")
            logger.info("Création d'une base vectorielle vide")
            vector_db = Chroma.from_documents(
                documents=[],
                embedding=embeddings,
                client=_chroma_client,
            )

except Exception as e:
    # Ne jamais empêcher QAIA de démarrer si RAG échoue à s'initialiser.
    # On logue l'erreur et on laisse vector_db/llm éventuellement à None.
    logger.error(f"Erreur lors de l'initialisation de l'agent RAG : {str(e)}")
    logger.error(traceback.format_exc())
    vector_db = None

# ==============
# FONCTION PRINCIPALE
# ==============
def process_query(query: str, k_results: int = 3, min_similarity: float = 0.4):
    """
    Effectue une recherche sémantique avec ChromaDB et génère une réponse avec LlamaCpp.
    
    Émet des événements agent.state_change pour RAG.
    
    Args:
        query (str): La requête/prompt de l'utilisateur
        k_results (int): Nombre de documents à récupérer (0 = génération sans RAG)
        min_similarity (float): Seuil de similarité minimum
        
    Returns:
        str: Réponse générée
    """
    # Émettre événement agent.state_change pour RAG (EN_COURS)
    try:
        from interface.events.event_bus import event_bus
        import time
        event_bus.emit('agent.state_change', {
            'name': 'RAG',
            'status': 'EN_COURS',
            'activity_percentage': 50.0,
            'details': f'Traitement requête RAG (k_results={k_results})...',
            'last_update': time.time()
        })
    except Exception:
        pass
    
    try:
        logger.info(f"Traitement requête (k={k_results}): {query[:50]}...")
        
        # CAS 1: Génération sans RAG (k_results=0)
        # Utilisé pour conversation pure sans recherche documentaire
        if k_results == 0:
            logger.info("Mode génération directe (sans RAG)")
            
            if llm is None:
                logger.error("LLM non disponible")
                return "Erreur: LLM non initialisé."
            
            # Génération directe avec le prompt fourni
            # stop_sequences déjà définies dans constructeur LlamaCpp (ligne 306)
            response = llm.invoke(query)
            
            logger.info("Réponse générée (sans RAG)")
            
            # Post-traitement complet via module centralisé
            if isinstance(response, str):
                try:
                    from utils.text_processor import clean_llm_response
                    response = clean_llm_response(response, apply_spell_check=True)
                except Exception as e:
                    logger.warning(f"Erreur post-traitement réponse: {e}, utilisation réponse brute")
                    response = response.strip() if response else ""
            
            final_response = response.strip() if isinstance(response, str) else str(response).strip()
            
            # Émettre événement agent.state_change pour RAG (ACTIF après génération directe)
            try:
                from interface.events.event_bus import event_bus
                import time
                event_bus.emit('agent.state_change', {
                    'name': 'RAG',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Génération directe terminée (réponse: {len(final_response)} caractères)',
                    'last_update': time.time()
                })
            except Exception:
                pass
            
            return final_response
        
        # CAS 2: Génération avec RAG (k_results > 0)
        # Émettre événement agent.state_change pour RAG (EN_COURS)
        try:
            from interface.events.event_bus import event_bus
            import time
            event_bus.emit('agent.state_change', {
                'name': 'RAG',
                'status': 'EN_COURS',
                'activity_percentage': 50.0,
                'details': 'Recherche documentaire en cours...',
                'last_update': time.time()
            })
        except Exception:
            pass
        
        if not vector_db:
            logger.warning("Base vectorielle non initialisée, génération sans RAG")
            if llm is None:
                return "Base de données vectorielle non initialisée."
            response = llm.invoke(query)
            final_response = response.strip() if isinstance(response, str) else str(response).strip()
            # Émettre événement agent.state_change pour RAG (ACTIF)
            try:
                from interface.events.event_bus import event_bus
                import time
                event_bus.emit('agent.state_change', {
                    'name': 'RAG',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Génération sans RAG (base non initialisée, réponse: {len(final_response)} caractères)',
                    'last_update': time.time()
                })
            except Exception:
                pass
            return final_response

        # Vérifier si la base contient des documents
        if vector_db._collection.count() == 0:
            logger.warning("Base vectorielle vide, génération sans RAG")
            if llm is None:
                return "Aucun document n'est indexé dans la base."
            response = llm.invoke(query)
            final_response = response.strip() if isinstance(response, str) else str(response).strip()
            # Émettre événement agent.state_change pour RAG (ACTIF)
            try:
                from interface.events.event_bus import event_bus
                import time
                event_bus.emit('agent.state_change', {
                    'name': 'RAG',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Génération sans RAG (base vide, réponse: {len(final_response)} caractères)',
                    'last_update': time.time()
                })
            except Exception:
                pass
            return final_response

        # Recherche sémantique
        docs = vector_db.similarity_search(query, k=k_results)

        if not docs:
            logger.warning("Aucun document trouvé, génération sans RAG")
            if llm is None:
                return "Aucun document pertinent trouvé."
            response = llm.invoke(query)
            final_response = response.strip() if isinstance(response, str) else str(response).strip()
            # Émettre événement agent.state_change pour RAG (ACTIF)
            try:
                from interface.events.event_bus import event_bus
                import time
                event_bus.emit('agent.state_change', {
                    'name': 'RAG',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Génération sans RAG (aucun document trouvé, réponse: {len(final_response)} caractères)',
                    'last_update': time.time()
                })
            except Exception:
                pass
            return final_response

        # Filtrage par similarité
        context = []
        for d in docs:
            if d.metadata.get("similarity", 1.0) >= min_similarity:
                context.append(d.page_content)

        if not context:
            logger.warning("Aucun document au-dessus du seuil, génération sans RAG")
            if llm is None:
                return "Aucun document pertinent (seuil similarité)."
            response = llm.invoke(query)
            final_response = response.strip() if isinstance(response, str) else str(response).strip()
            # Émettre événement agent.state_change pour RAG (ACTIF)
            try:
                from interface.events.event_bus import event_bus
                import time
                event_bus.emit('agent.state_change', {
                    'name': 'RAG',
                    'status': 'ACTIF',
                    'activity_percentage': 100.0,
                    'details': f'Génération sans RAG (seuil similarité non atteint, réponse: {len(final_response)} caractères)',
                    'last_update': time.time()
                })
            except Exception:
                pass
            return final_response

        # Construction prompt avec contexte RAG
        context_text = "\n".join(context)
        prompt = f"Question: {query}\nContexte: {context_text[:1500]}"

        logger.debug(f"Prompt RAG généré: {prompt[:100]}...")
        
        if llm is None:
            logger.info("LLM indisponible, retour prompt-contexte")
            return prompt
        
        response = llm.invoke(prompt)

        logger.info("Réponse générée avec RAG")
        
        # Post-traitement complet via module centralisé
        if isinstance(response, str):
            try:
                from utils.text_processor import clean_llm_response
                response = clean_llm_response(response, apply_spell_check=True)
            except Exception as e:
                logger.warning(f"Erreur post-traitement réponse RAG: {e}, utilisation réponse brute")
                response = response.strip() if response else ""
        
        final_response = response.strip() if isinstance(response, str) else str(response).strip()
        
        # Émettre événement agent.state_change pour RAG (ACTIF après traitement)
        try:
            from interface.events.event_bus import event_bus
            import time
            event_bus.emit('agent.state_change', {
                'name': 'RAG',
                'status': 'ACTIF',
                'activity_percentage': 100.0,
                'details': f'Requête RAG traitée (réponse: {len(final_response)} caractères, {len(context)} docs)',
                'last_update': time.time()
            })
        except Exception:
            pass
        
        return final_response

    except Exception as e:
        logger.error(f"Erreur process_query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Erreur: {str(e)}"


def process_query_stream(query: str, k_results: int = 3, min_similarity: float = 0.4):
    """
    Version streaming de process_query.
    Effectue recherche sémantique et génère réponse token-par-token.
    
    Args:
        query (str): La requête/prompt de l'utilisateur
        k_results (int): Nombre de documents à récupérer (0 = génération sans RAG)
        min_similarity (float): Seuil de similarité minimum
        
    Yields:
        str: Tokens générés un par un
    """
    try:
        logger.info(f"Traitement streaming requête (k={k_results}): {query[:50]}...")
        
        # Préparer le prompt (même logique que process_query)
        final_prompt = query
        
        if k_results > 0 and vector_db and vector_db._collection.count() > 0:
            # Recherche RAG
            docs = vector_db.similarity_search(query, k=k_results)
            
            if docs:
                context = []
                for d in docs:
                    if d.metadata.get("similarity", 1.0) >= min_similarity:
                        context.append(d.page_content)
                
                if context:
                    context_text = "\n".join(context)
                    final_prompt = f"Question: {query}\nContexte: {context_text[:1500]}"
                    logger.info("Génération streaming avec RAG")
                else:
                    logger.info("Génération streaming sans RAG (seuil non atteint)")
            else:
                logger.info("Génération streaming sans RAG (aucun doc)")
        else:
            logger.info("Génération streaming directe (sans RAG)")
        
        if llm is None:
            logger.error("LLM non disponible pour streaming")
            yield "Erreur: LLM non initialisé."
            return
        
        # Streaming avec llama.cpp
        for token in llm.stream(final_prompt):
            # Nettoyer artefacts (centralisé)
            try:
                from utils.text_processor import clean_phi3_artifacts, filter_streaming_token
                clean_token = clean_phi3_artifacts(token)
            except Exception:
                clean_token = token
                filter_streaming_token = None
            
            if clean_token:  # Ne yield que si non vide après nettoyage
                # Filtrer les tokens de préfixes AVANT yield (évite doublons)
                try:
                    if filter_streaming_token is None:
                        raise RuntimeError("Filtrage streaming indisponible")
                    filtered_token = filter_streaming_token(clean_token)
                    
                    # Si le token est filtré (None), ne pas le yield
                    if filtered_token is None:
                        logger.debug(f"Token filtré et ignoré: '{clean_token}'")
                        continue
                    
                    yield filtered_token
                except Exception as e:
                    logger.debug(f"Erreur filtrage token: {e}, utilisation token original")
                yield clean_token
        
        logger.info("Streaming terminé")
        
    except Exception as e:
        logger.error(f"Erreur process_query_stream: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # CRITIQUE: Ne pas yield d'erreur comme token, émettre événement erreur (TODO-10)
        try:
            from interface.events.event_bus import event_bus
            import time
            event_bus.emit('llm.error', {'error': str(e), 'timestamp': time.time()})
        except Exception:
            pass
        # Ne rien yield pour éviter d'afficher l'erreur comme réponse normale
        return

# =================
# EXECUTION CLI
# =================
if __name__ == "__main__":
    logger.info("Démarrage de l'agent RAG...")
    try:
        while True:
            query = input("\nPosez votre question (ou 'quit' pour sortir): ")
            if query.lower() == 'quit':
                break

            response = process_query(query)
            print(f"\nRéponse : {response}")

    except KeyboardInterrupt:
        logger.info("Arrêt de l'agent RAG...")
    finally:
        logger.info("Agent RAG arrêté.")

# Assurez-vous que les classes sont disponibles pour l'import
__all__ = ["DataSources", "EmbeddingCache", "load_all_documents"]
