#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module centralisé de post-traitement de texte pour QAIA
Point unique de vérité pour tous les nettoyages, corrections et normalisations

# /// script
# dependencies = [
#   "pyspellchecker>=0.8.0",  # Correcteur orthographique
# ]
# ///
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import du correcteur orthographique
try:
    from utils.spell_checker import correct_spelling
    SPELL_CHECKER_AVAILABLE = True
except ImportError:
    SPELL_CHECKER_AVAILABLE = False
    logger.warning("Correcteur orthographique non disponible, corrections manuelles uniquement")


# ============================================================================
# CONSTANTES
# ============================================================================

# Patterns pour détection et suppression des préfixes indésirables
PATTERN_TIMESTAMP = r'\(\d{2}:\d{2}\)'
PATTERN_QAIA_PREFIX = r'(QAIA|qaia)\s*:'
PATTERN_TIMESTAMP_QAIA = rf'{PATTERN_TIMESTAMP}\s*{PATTERN_QAIA_PREFIX}'
PATTERN_DOUBLE_QAIA = rf'{PATTERN_TIMESTAMP}\s*{PATTERN_QAIA_PREFIX}\s*{PATTERN_QAIA_PREFIX}'

# Balises Phi-3 à supprimer
PHI3_TAGS = ["<|end|>", "<|endoftext|>", "<|system|>", "<|user|>", "<|assistant|>"]

# Tokens de préfixes à filtrer en streaming
STREAMING_PREFIX_TOKENS = [
    r'^\(\d{1,2}:\d{2}\)$',  # Timestamp seul "(17:30)"
    r'^QAIA\s*:?\s*$',       # "QAIA" ou "QAIA:"
    r'^qaia\s*:?\s*$',       # "qaia" ou "qaia:"
    r'^\($',                 # "(" seul (début timestamp)
    r'^\d{1,2}:\d{2}\)$',   # "17:30)" (fin timestamp)
    r'^17:\d{2}\)$',         # Pattern spécifique "17:30)"
    r'^\d{2}:\d{2}\)$',     # Pattern spécifique "17:30)"
]


# ============================================================================
# FONCTIONS DE NETTOYAGE
# ============================================================================

def clean_phi3_artifacts(text: str) -> str:
    """
    Supprime les balises et artefacts spécifiques à Phi-3.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte sans balises Phi-3
    """
    if not text or not isinstance(text, str):
        return text
    
    cleaned = text
    for tag in PHI3_TAGS:
        cleaned = cleaned.replace(tag, "")
    
    # Supprimer répétitions de rôles
    cleaned = cleaned.replace("user\n", "").replace("assistant\n", "")
    
    return cleaned


def remove_prefix_patterns(text: str) -> str:
    """
    Supprime tous les préfixes de type "(HH:MM) QAIA:" ou "QAIA:".
    Application multi-passes pour éliminer toutes les occurrences.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte sans préfixes
    """
    if not text or not isinstance(text, str):
        return text
    
    cleaned = text.strip()
    
    # Pass 1: Supprimer au début de la chaîne (avec timestamps, insensible à la casse)
    cleaned = re.sub(
        rf'^\s*({PATTERN_TIMESTAMP}\s*)?{PATTERN_QAIA_PREFIX}\s*',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # Pass 2: Supprimer toutes les occurrences de "QAIA: " dans le texte (même au milieu)
    cleaned = re.sub(
        rf'\b{PATTERN_QAIA_PREFIX}\s*',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # Pass 3: Supprimer les timestamps isolés au début "(HH:MM)"
    cleaned = re.sub(
        rf'^\s*{PATTERN_TIMESTAMP}\s*',
        '',
        cleaned
    )
    
    # Pass 4: Supprimer les répétitions de préfixes "(HH:MM) QAIA: QAIA:"
    cleaned = re.sub(
        PATTERN_DOUBLE_QAIA,
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    return cleaned.strip()


def normalize_spaces(text: str) -> str:
    """
    Normalise les espaces dans le texte.
    - Supprime les espaces multiples
    - Gère les espaces autour de la ponctuation
    - Assure un espace après les virgules, points, etc.
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte avec espaces normalisés
    """
    if not text or not isinstance(text, str):
        return text
    
    # Remplacer tous les espaces multiples par un seul espace
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Normaliser espaces autour ponctuation (PRÉSERVER espaces entre mots)
    # Espace APRÈS ponctuation (pas avant)
    cleaned = re.sub(r'\s*([.,!?;:])\s*', r'\1 ', cleaned)
    # Pas d'espace autour parenthèses (mais préserver espaces entre mots)
    cleaned = re.sub(r'\s*\(\s*', '(', cleaned)
    cleaned = re.sub(r'\s*\)\s*', ') ', cleaned)
    
    # Supprimer espaces en début/fin
    cleaned = cleaned.strip()
    
    return cleaned


def clean_control_characters(text: str) -> str:
    """
    Supprime les caractères de contrôle problématiques.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte sans caractères de contrôle
    """
    if not text or not isinstance(text, str):
        return text
    
    # Supprimer caractères de contrôle (sauf \n, \t)
    cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    return cleaned


# ============================================================================
# FONCTION PRINCIPALE DE NETTOYAGE LLM
# ============================================================================

def clean_llm_response(text: str, apply_spell_check: bool = True) -> str:
    """
    Nettoie complètement une réponse LLM.
    Point unique de vérité pour le nettoyage des réponses LLM.
    
    Étapes appliquées :
    1. Suppression balises Phi-3
    2. Suppression préfixes "(HH:MM) QAIA:"
    3. Normalisation espaces
    4. Suppression caractères de contrôle
    5. Correction orthographique (optionnel)
    
    Args:
        text: Réponse LLM brute
        apply_spell_check: Si True, applique la correction orthographique
        
    Returns:
        Texte nettoyé et corrigé
    """
    if not text or not isinstance(text, str):
        return text if text else ""
    
    # Étape 1: Supprimer balises Phi-3
    cleaned = clean_phi3_artifacts(text)
    
    # Étape 2: Supprimer préfixes indésirables
    cleaned = remove_prefix_patterns(cleaned)
    
    # Étape 3: Normaliser espaces
    cleaned = normalize_spaces(cleaned)
    
    # Étape 4: Supprimer caractères de contrôle
    cleaned = clean_control_characters(cleaned)
    
    # Étape 5: Correction orthographique (si demandée et disponible)
    if apply_spell_check and SPELL_CHECKER_AVAILABLE:
        try:
            cleaned = correct_spelling(cleaned)
        except Exception as e:
            logger.debug(f"Erreur correction orthographique: {e}")
    
    return cleaned.strip()


# ============================================================================
# FONCTIONS DE FILTRAGE STREAMING
# ============================================================================

def filter_streaming_token(token: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Filtre un token de streaming pour supprimer les préfixes indésirables.
    Utilisé AVANT l'affichage pour éviter les doublons.
    
    CRITIQUE (TODO-4): Détecte et supprime les préfixes même s'ils sont dans un token complet.
    Ex: "(15:33) QAIA: Bonjour" → "Bonjour"
    
    Args:
        token: Token à filtrer
        context: Contexte optionnel (ex: tokens précédents)
        
    Returns:
        Token filtré ou None si token à ignorer
    """
    if not token or not isinstance(token, str):
        return None
    
    token_clean = token.strip()
    
    # Ignorer tokens vides
    if not token_clean:
        return None
    
    # CRITIQUE (TODO-4): Supprimer les préfixes DANS le token complet
    # Ex: "(15:33) QAIA: Bonjour" → "Bonjour"
    prefix_pattern = re.compile(
        rf'^\s*({PATTERN_TIMESTAMP}\s*)?{PATTERN_QAIA_PREFIX}\s*',
        flags=re.IGNORECASE,
    )
    new_token = re.sub(prefix_pattern, '', token_clean)
    if not new_token.strip():
        # Token était uniquement un préfixe
        logger.debug(f"Token filtré (préfixe complet): '{token_clean}'")
        return None
    if new_token != token_clean:
        # Préfixe supprimé, utiliser le reste
        logger.debug(f"Préfixe supprimé du token: '{token_clean}' → '{new_token}'")
        token_clean = new_token
    
    # Vérifier si c'est un token de préfixe isolé à filtrer
    for pattern in STREAMING_PREFIX_TOKENS:
        if re.match(pattern, token_clean, re.IGNORECASE):
            logger.debug(f"Token filtré (préfixe isolé): '{token_clean}'")
            return None
    
    # Vérifier si le token commence par un préfixe indésirable
    # Patterns pour début de préfixes
    prefix_start_patterns = [
        rf'^{PATTERN_TIMESTAMP}',  # Commence par "(17:30)"
        rf'^{PATTERN_QAIA_PREFIX}',  # Commence par "QAIA:"
        r'^\(\d{1,2}:',  # Commence par "(17:"
        r'^\d{1,2}:\d{2}\)',  # Commence par "17:30)"
    ]
    
    for pattern in prefix_start_patterns:
        if re.match(pattern, token_clean, re.IGNORECASE):
            logger.debug(f"Token filtré (commence par préfixe): '{token_clean}'")
            return None
    
    return token


def should_add_space_before_token(token: str, previous_token: Optional[str] = None) -> bool:
    """
    Détermine si un espace doit être ajouté avant un token.
    
    IMPORTANT: Les tokens de llama.cpp sont des sous-mots BPE (BytePairEncoding),
    donc "parle" peut être émis comme "par" + "le" (sans espace entre).
    On ne doit PAS ajouter d'espace entre sous-mots qui forment un mot.
    
    Args:
        token: Token actuel
        previous_token: Token précédent (optionnel)
        
    Returns:
        True si un espace doit être ajouté
    """
    if not token:
        return False
    
    # Si le token commence déjà par un espace, ne pas en ajouter
    if token.startswith(' '):
        return False
    
    if not previous_token:
        return False
    
    # Si le token précédent se termine par un espace, ne pas en ajouter
    if previous_token.endswith(' '):
        return False
    
    # RÈGLE CRITIQUE: Ne PAS ajouter d'espace si les tokens forment un mot (sous-mots BPE)
    # Exemples: "par" + "le" = "parle" (pas d'espace)
    #           "fran" + "çais" = "français" (pas d'espace)
    #           "effic" + "ac" + "ement" = "efficacement" (pas d'espace)
    
    # Détecter si c'est un sous-mot BPE (commence par lettre minuscule ou caractère spécial)
    # Les sous-mots BPE qui continuent un mot ne commencent généralement pas par majuscule
    # sauf après ponctuation
    
    # Si le token précédent se termine par une lettre et le token actuel commence par une lettre minuscule,
    # c'est probablement un sous-mot (pas d'espace)
    if previous_token and len(previous_token) > 0 and len(token) > 0:
        prev_last = previous_token[-1]
        curr_first = token[0]
        
        # Si précédent se termine par lettre et actuel commence par lettre minuscule → sous-mot
        if prev_last.isalpha() and curr_first.isalpha() and curr_first.islower():
            # Exception: si le précédent se termine par ponctuation, c'est un nouveau mot
            if len(previous_token) > 1 and previous_token[-2] in '.,!?;:':
                return True
            # Sinon, probablement un sous-mot → pas d'espace
            return False
        
        # Si précédent se termine par lettre et actuel commence par caractère spécial (apostrophe, etc.)
        # → probablement un sous-mot
        if prev_last.isalpha() and curr_first in "'-":
            return False
    
    # Si le token actuel commence par ponctuation, pas d'espace avant
    if re.match(r'^[.,!?;:()]', token):
        return False
    
    # Si le token précédent se termine par ponctuation, ajouter espace
    if previous_token and previous_token[-1] in '.,!?;:':
        return True
    
    # Par défaut, ajouter un espace entre tokens (mots séparés)
    return True


# ============================================================================
# FONCTIONS DE POST-TRAITEMENT SPÉCIALISÉES
# ============================================================================

def process_text_for_display(text: str) -> str:
    """
    Post-traitement complet pour affichage dans l'interface.
    Applique tous les nettoyages nécessaires pour un affichage propre.
    
    Args:
        text: Texte à traiter
        
    Returns:
        Texte prêt pour affichage
    """
    return clean_llm_response(text, apply_spell_check=True)


def process_text_for_tts(text: str) -> str:
    """
    Post-traitement complet pour synthèse vocale (TTS).
    Applique les mêmes nettoyages que pour l'affichage + normalisations TTS.
    
    IMPORTANT: 
    - Protège la prononciation de mots spéciaux comme "QAIA"
    - Remplace "QAIA" par une prononciation phonétique pour Piper TTS
    - S'assure que les mots français sont correctement prononcés
    
    Args:
        text: Texte à traiter
        
    Returns:
        Texte prêt pour TTS avec prononciations corrigées
    """
    if not text or not isinstance(text, str):
        return text
    
    # ÉTAPE 0: Corriger les problèmes BPE AVANT tout traitement
    # CRITIQUE: "Q A IA" doit être corrigé en "QAIA" avant protection
    corrections_bpe_qaia = {
        r'\bQ\s+A\s+I\s+A\b': 'QAIA',
        r'\bQ\s+A\s+IA\b': 'QAIA',
        r'\bQ\s+AIA\b': 'QAIA',
        r'\bQA\s+I\s+A\b': 'QAIA',
    }
    text_bpe_fixed = text
    for pattern, replacement in corrections_bpe_qaia.items():
        text_bpe_fixed = re.sub(pattern, replacement, text_bpe_fixed, flags=re.IGNORECASE)
    
    # ÉTAPE 1: Supprimer TOUS les préfixes AVANT de protéger QAIA
    # CRITIQUE: Le texte pour TTS ne doit JAMAIS contenir "(HH:MM) QAIA:"
    # Doit être fait AVANT de remplacer QAIA par le placeholder
    cleaned = remove_prefix_patterns(text_bpe_fixed)
    
    # ÉTAPE 2: PROTÉGER QAIA après suppression des préfixes (remplacer temporairement)
    # Maintenant on peut remplacer "QAIA" par le placeholder sans risquer de supprimer les préfixes
    QAIA_PLACEHOLDER = "___QAIA___"
    text_protected = re.sub(r'\bQAIA\b', QAIA_PLACEHOLDER, cleaned, flags=re.IGNORECASE)
    
    # ÉTAPE 3: Appliquer le même nettoyage que pour l'affichage
    cleaned = clean_llm_response(text_protected, apply_spell_check=True)
    
    # ÉTAPE 4: Pass final de suppression des préfixes (au cas où clean_llm_response en aurait ajouté)
    cleaned = remove_prefix_patterns(cleaned)
    
    # ÉTAPE 5: CORRECTION PRONONCIATION pour TTS
    # QAIA → prononciation phonétique française "ka-ia" (pas "kaia" avec K dur)
    # Piper TTS prononce mieux "ka-ia" que "QAIA" (qui devient "kaia" avec K)
    cleaned = re.sub(QAIA_PLACEHOLDER, "ka-ia", cleaned, flags=re.IGNORECASE)
    
    # 2. "intelligent" → s'assurer qu'il reste en français (ne pas le modifier)
    # Si le modèle génère "intelligent" (masculin), le laisser tel quel
    # Piper TTS devrait le prononcer correctement en français
    
    return cleaned


def _remove_duplicate_consecutive_sentences(text: str) -> str:
    """
    Supprime les phrases consécutives quasi-dupliquées (modèle répète avec variantes BPE).
    Ex: "Je suis là pour vous aider." suivi de "Suis là pourvus aider." → garde la première.

    Args:
        text: Texte à traiter

    Returns:
        Texte sans phrases consécutives dupliquées
    """
    if not text or not isinstance(text, str) or len(text.strip()) < 20:
        return text
    # Découper en phrases : après . ! ? avec zéro ou plus d'espaces (pour "?Bonjour" sans espace)
    sentences = re.split(r'(?<=[.!?])\s*', text)
    # Filtrer les vides et garder au moins 2 segments pour dédupliquer
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) < 2:
        return text

    def _word_set(s: str) -> set:
        """Ensemble de mots normalisés (minuscules, sans ponctuation)."""
        return set(re.findall(r'\b\w+\b', s.lower()))

    def _similarity(s1: str, s2: str) -> float:
        """Similarité Jaccard approximative entre deux phrases."""
        w1, w2 = _word_set(s1), _word_set(s2)
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    result = [sentences[0]]
    for i in range(1, len(sentences)):
        prev, curr = result[-1].strip(), sentences[i].strip()
        if not curr:
            continue
        # Si la phrase actuelle est très similaire à la précédente, la considérer comme doublon
        if len(curr) >= 10 and _similarity(prev, curr) >= 0.5:
            logger.debug("Phrase quasi-dupliquée supprimée: %s...", curr[:50])
            continue
        result.append(sentences[i])
    return " ".join(result).strip()


def process_streamed_text(text: str) -> str:
    """
    Post-traitement pour texte accumulé pendant le streaming.
    Utilisé dans _on_llm_complete() pour traiter le texte streamé complet.
    
    IMPORTANT: Nettoie les doublons, préfixes, et corrige les problèmes BPE.
    CRITIQUE: Supprime aussi les fragments d'hallucinations (TODO-1).
    
    Args:
        text: Texte streamé accumulé
        
    Returns:
        Texte nettoyé et normalisé
    """
    if not text or not isinstance(text, str):
        return text
    
    # ÉTAPE 0: Supprimer les fragments d'hallucinations (fragments de prompts)
    # CRITIQUE: Détecter et supprimer les fragments comme "--- ## # Instruction..."
    import re
    hallucination_patterns = [
        r'---\s*##?\s*#?\s*Instruction.*?(?=\n\n|\Z)',  # Fragments markdown + instruction
        r'###\s*Instruction.*?(?=\n\n|\Z)',  # Fragments markdown
        r'Contraintes\s+supplémentaires.*?(?=\n\n|\Z)',  # Fragments de contraintes
        r'Artemis.*?(?=\n\n|\Z)',  # Fragments avec nom d'exemple
        r'N\s+I\s+N\s+A.*?(?=\n\n|\Z)',  # Fragments "N IN A"
        r'conseiller\s+numérique.*?(?=\n\n|\Z)',  # Fragments de prompt
    ]
    for pattern in hallucination_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # ÉTAPE 1: Supprimer les préfixes et doublons AVANT tout autre traitement
    # CRITIQUE: Le modèle génère encore "(18:28) QAIA:" malgré les instructions
    cleaned = remove_prefix_patterns(text)
    # Supprimer toute occurrence de "(HH:MM) QAIA:" n'importe où dans le texte (pas seulement au début)
    cleaned = re.sub(
        r'\s*\(\d{1,2}:\d{2}\)\s*QAIA\s*:?\s*',
        ' ',
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip()

    # Étape 1: Corriger les espaces mal placés dans les mots (BPE)
    # Les tokens BPE peuvent créer des espaces au milieu des mots
    # Exemples: "O ui" → "Oui", "par le" → "parle", "Q A IA" → "QAIA"
    
    # Corrections spécifiques pour cas courants identifiés
    corrections_espaces = {
        # QAIA (CRITIQUE - problème BPE fréquent observé)
        r'\bQ\s+A\s+I\s+A\b': 'QAIA',
        r'\bQ\s+A\s+IA\b': 'QAIA',
        r'\bQ\s+AIA\b': 'QAIA',
        r'\bQA\s+I\s+A\b': 'QAIA',
        r'\bQ\s+A\s+I\b': 'QAI',  # Partiel mais corrige quand même
        # NINA (TODO-5: Problème BPE observé)
        r'\bN\s+I\s+N\s+A\b': 'NINA',
        r'\bN\s+IN\s+A\b': 'NINA',
        r'\bN\s+N\s+A\b': 'NINA',
        # Autres corrections BPE (TODO-5)
        r'\bdin\s+as\b': "d'ailleurs",  # "din as" → "d'ailleurs"
        r'\bDin\s+as\b': "D'ailleurs",
        r'\bO\s+ui\b': 'Oui',
        r'\bo\s+ui\b': 'oui',
        r'\bpar\s+le\b': 'parle',
        r'\bPar\s+le\b': 'Parle',
        r'\bfran\s+çais\b': 'français',
        r'\bFran\s+çais\b': 'Français',
        r'\beffic\s+ac\s+ement\b': 'efficacement',
        r'\bEffic\s+ac\s+ement\b': 'Efficacement',
        r'\bcon\s+ç\s+ue\b': 'conçue',
        r'\bCon\s+ç\s+ue\b': 'Conçue',
        r'\blang\s+ues\b': 'langues',
        r'\bLang\s+ues\b': 'Langues',
        r'\bang\s+lais\b': 'anglais',
        r'\bAng\s+lais\b': 'Anglais',
        r'\bact\s+uelle\b': 'actuelle',
        r'\bAct\s+uelle\b': 'Actuelle',
        # Corrections supplémentaires pour cas observés
        r'\bpar\s+le\s+le\b': 'parle le',  # "par le le" → "parle le"
        r'\bcommun\s+ic\s+ation\b': 'communication',
        r'\bCommun\s+ic\s+ation\b': 'Communication',
    }
    
    corrected = cleaned  # Utiliser le texte déjà nettoyé des préfixes (ÉTAPE 0)
    for pattern, replacement in corrections_espaces.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    # Correction générale : supprimer espaces entre lettres minuscules consécutives
    # (sous-mots BPE qui forment un mot)
    # Pattern: lettre_minuscule espace lettre_minuscule (mais pas entre mots complets)
    # On évite de casser les vrais espaces entre mots
    # Exemple: "par le français" → "parle français" (mais attention à ne pas casser "par le")
    # On applique seulement si les deux parties sont courtes (probablement sous-mots)
    def fix_bpe_spaces(match):
        """Corrige les espaces BPE dans un match."""
        full_match = match.group(0)
        # Si les deux parties sont courtes (< 5 chars), probablement sous-mots
        parts = full_match.split()
        if len(parts) == 2 and len(parts[0]) < 5 and len(parts[1]) < 5:
            # Vérifier si c'est un mot français valide (approximation)
            combined = parts[0] + parts[1]
            # Si le résultat a l'air d'un mot (pas de majuscule au milieu), fusionner
            if combined.islower() or (combined[0].isupper() and combined[1:].islower()):
                return combined
        return full_match
    
    # Appliquer correction générale (avec prudence)
    # Pattern: mot court espace mot court (probablement BPE)
    corrected = re.sub(r'\b([a-z]{1,4})\s+([a-z]{1,4})\b', fix_bpe_spaces, corrected, flags=re.IGNORECASE)
    
    # Étape 1b: Supprimer phrases consécutives quasi-dupliquées (modèle répète avec variantes BPE)
    # Ex: "Je suis là pour vous aider." suivi de "Suis là pourvus aider."
    corrected = _remove_duplicate_consecutive_sentences(corrected)
    
    # Étape 2: Normaliser les espaces multiples
    normalized = normalize_spaces(corrected)
    
    # Étape 3: Appliquer le nettoyage complet (sans re-nettoyer les préfixes déjà supprimés)
    # On utilise clean_llm_response mais sans re-appliquer remove_prefix_patterns
    # car on l'a déjà fait en ÉTAPE 0
    final_cleaned = clean_llm_response(normalized, apply_spell_check=True)
    
    # ÉTAPE 4: Pass final de suppression des préfixes (au cas où clean_llm_response en aurait ajouté)
    final_cleaned = remove_prefix_patterns(final_cleaned)
    
    return final_cleaned


# ============================================================================
# FONCTION DE VALIDATION
# ============================================================================

def validate_processed_text(text: str) -> bool:
    """
    Valide qu'un texte traité est valide.
    
    Args:
        text: Texte à valider
        
    Returns:
        True si le texte est valide
    """
    if not text or not isinstance(text, str):
        return False
    
    # Vérifier qu'il n'y a pas de préfixes indésirables
    if re.search(PATTERN_TIMESTAMP_QAIA, text, re.IGNORECASE):
        logger.warning(f"Texte contient encore des préfixes: {text[:50]}...")
        return False
    
    # Vérifier qu'il n'y a pas de balises Phi-3
    for tag in PHI3_TAGS:
        if tag in text:
            logger.warning(f"Texte contient encore des balises Phi-3: {tag}")
            return False
    
    return True

