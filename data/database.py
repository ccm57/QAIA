#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""
Module base de données QAIA.
Gère les opérations SQLite pour logs, métriques et état.
"""

# /// script
# dependencies = []
# ///

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from config.system_config import DATA_DIR, LOGS_DIR

# Configuration des chemins
DB_PATH = DATA_DIR / "qaia.db"

class Database:
    """Gère les opérations de base de données pour QAIA."""
    
    def __init__(self, db_path=DB_PATH):
        """Initialise la connexion à la base de données.
        
        Args:
            db_path (str): Chemin vers le fichier de base de données SQLite
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self._initialize_tables()
            self.logger.info("Base de données initialisée avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise
    
    def _initialize_tables(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        # Table des locuteurs (speakers) pour l'identité vocale
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS speakers (
            speaker_id TEXT PRIMARY KEY,
            prenom TEXT,
            civilite TEXT,
            metadata TEXT,  -- JSON string pour métadonnées additionnelles
            embedding_path TEXT,  -- Chemin vers le fichier .npy d'embedding
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Table des historiques de conversation (avec speaker_id optionnel)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            speaker_id TEXT,  -- Référence vers speakers.speaker_id (NULL si non identifié)
            user_input TEXT,
            qaia_response TEXT,
            FOREIGN KEY(speaker_id) REFERENCES speakers(speaker_id)
        )
        ''')
        
        # Migration: ajouter colonne speaker_id si elle n'existe pas (pour bases existantes)
        try:
            self.cursor.execute("ALTER TABLE conversations ADD COLUMN speaker_id TEXT")
        except sqlite3.OperationalError:
            # La colonne existe déjà, pas d'erreur
            pass

        # Table des médias associés aux conversations (audio utilisateur/réponse)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            media_type TEXT NOT NULL, -- 'user_audio' | 'qaia_audio'
            path TEXT NOT NULL,
            duration_ms INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
        ''')
        
        # Table des paramètres de configuration
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tables pour la gestion des documents
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            path TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            indexed BOOLEAN DEFAULT 0
        )
        ''')
        
        self.conn.commit()
    
    def add_conversation(self, user_input, qaia_response, speaker_id=None):
        """Ajoute une conversation à l'historique.
        
        Args:
            user_input (str): L'entrée de l'utilisateur
            qaia_response (str): La réponse du système
            speaker_id (str|None): Identifiant du locuteur (optionnel)
            
        Returns:
            int: ID de la conversation enregistrée
        """
        try:
            self.cursor.execute(
                "INSERT INTO conversations (user_input, qaia_response, speaker_id) VALUES (?, ?, ?)",
                (user_input, qaia_response, speaker_id)
            )
            self.conn.commit()
            conv_id = self.cursor.lastrowid
            self.logger.info(
                f"Conversation enregistrée id={conv_id} speaker_id={speaker_id} "
                f"user='{(user_input or '')[:80]}' response_len={len(qaia_response or '')}"
            )
            return conv_id
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout d'une conversation: {e}")
            return None

    def add_conversation_detailed(self, user_input, qaia_response, user_audio_path=None, qaia_audio_path=None, user_audio_duration_ms=None, qaia_audio_duration_ms=None, speaker_id=None):
        """Ajoute une conversation et, si fournis, attache les médias audio.
        
        Args:
            user_input (str): Texte utilisateur
            qaia_response (str): Réponse QAIA
            user_audio_path (str|None): Chemin WAV voix utilisateur
            qaia_audio_path (str|None): Chemin WAV voix QAIA
            user_audio_duration_ms (int|None): Durée audio utilisateur
            qaia_audio_duration_ms (int|None): Durée audio QAIA
            speaker_id (str|None): Identifiant du locuteur (optionnel)
        
        Returns:
            int|None: id de conversation
        """
        conv_id = self.add_conversation(user_input, qaia_response, speaker_id=speaker_id)
        if not conv_id:
            return None
        try:
            if user_audio_path:
                self.cursor.execute(
                    "INSERT INTO conversation_media (conversation_id, media_type, path, duration_ms) VALUES (?, ?, ?, ?)",
                    (conv_id, 'user_audio', user_audio_path, user_audio_duration_ms)
                )
            if qaia_audio_path:
                self.cursor.execute(
                    "INSERT INTO conversation_media (conversation_id, media_type, path, duration_ms) VALUES (?, ?, ?, ?)",
                    (conv_id, 'qaia_audio', qaia_audio_path, qaia_audio_duration_ms)
                )
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout des médias conversation: {e}")
        return conv_id
    
    def get_recent_conversations(self, limit=10, speaker_id=None):
        """Récupère les conversations récentes.
        
        Args:
            limit (int): Nombre maximum de conversations à récupérer
            speaker_id (str|None): Filtrer par speaker_id (optionnel)
            
        Returns:
            list: Liste des conversations
        """
        try:
            if speaker_id:
                self.cursor.execute(
                    "SELECT id, timestamp, speaker_id, user_input, qaia_response FROM conversations WHERE speaker_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (speaker_id, limit)
                )
            else:
                self.cursor.execute(
                    "SELECT id, timestamp, speaker_id, user_input, qaia_response FROM conversations ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des conversations: {e}")
            return []
    
    def add_speaker(self, speaker_id, prenom=None, civilite=None, metadata=None, embedding_path=None):
        """Ajoute ou met à jour un locuteur dans la table speakers.
        
        Args:
            speaker_id (str): Identifiant unique du locuteur
            prenom (str|None): Prénom du locuteur
            civilite (str|None): Civilité (Monsieur, Madame, etc.)
            metadata (dict|None): Métadonnées additionnelles (sérialisées en JSON)
            embedding_path (str|None): Chemin vers le fichier .npy d'embedding
            
        Returns:
            bool: True si l'opération a réussi
        """
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            self.cursor.execute(
                """INSERT OR REPLACE INTO speakers 
                   (speaker_id, prenom, civilite, metadata, embedding_path, updated_at) 
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (speaker_id, prenom, civilite, metadata_json, embedding_path)
            )
            self.conn.commit()
            self.logger.info(f"Locuteur {speaker_id} ajouté/mis à jour dans la BDD")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout du locuteur {speaker_id}: {e}")
            return False
    
    def get_speaker(self, speaker_id):
        """Récupère les informations d'un locuteur.
        
        Args:
            speaker_id (str): Identifiant du locuteur
            
        Returns:
            dict|None: Informations du locuteur (speaker_id, prenom, civilite, metadata, embedding_path) ou None
        """
        try:
            self.cursor.execute(
                "SELECT speaker_id, prenom, civilite, metadata, embedding_path, created_at, updated_at FROM speakers WHERE speaker_id = ?",
                (speaker_id,)
            )
            row = self.cursor.fetchone()
            if row:
                import json
                return {
                    'speaker_id': row[0],
                    'prenom': row[1],
                    'civilite': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {},
                    'embedding_path': row[4],
                    'created_at': row[5],
                    'updated_at': row[6],
                }
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du locuteur {speaker_id}: {e}")
            return None
    
    def list_speakers(self):
        """Liste tous les locuteurs enregistrés.
        
        Returns:
            list: Liste des speaker_id
        """
        try:
            self.cursor.execute("SELECT speaker_id FROM speakers ORDER BY created_at DESC")
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Erreur lors de la liste des locuteurs: {e}")
            return []
    
    def set_setting(self, key, value):
        """Définit un paramètre de configuration.
        
        Args:
            key (str): Clé du paramètre
            value (str): Valeur du paramètre
            
        Returns:
            bool: Succès de l'opération
        """
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                (key, value)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la définition d'un paramètre: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Récupère un paramètre de configuration.
        
        Args:
            key (str): Clé du paramètre
            default: Valeur par défaut si le paramètre n'existe pas
            
        Returns:
            str or default: Valeur du paramètre
        """
        try:
            self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = self.cursor.fetchone()
            return result[0] if result else default
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération d'un paramètre: {e}")
            return default
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def __del__(self):
        """Destructeur pour assurer la fermeture de la connexion."""
        self.close()

# Test unitaire
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = Database()
    print("Test d'enregistrement de conversation...")
    db.add_conversation("Bonjour QAIA", "Bonjour ! Comment puis-je vous aider ?")
    
    print("Test de récupération de l'historique...")
    history = db.get_recent_conversations()
    for id, timestamp, user_input, qaia_response in history:
        print(f"[{timestamp}] Utilisateur: {user_input}")
        print(f"[{timestamp}] QAIA: {qaia_response}")
    
    print("Test de configuration...")
    db.set_setting("model_path", "E:/QAIA/models/phi-3-mini-4k-instruct.Q5_K_M.gguf")
    print(f"Chemin du modèle: {db.get_setting('model_path')}") 