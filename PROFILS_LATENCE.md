# Profils d'Optimisation Latence QAIA

**Matériel:** i7-7700HQ, 40GB RAM, CPU only  
**Latence actuelle:** ~50-55s par question

## Analyse Temps Actuels

| Composant | Temps | Optimisable |
|-----------|-------|-------------|
| STT | 2-5s | ❌ Déjà optimal |
| **LLM** | **48s** | ✅ OUI |
| TTS | 1-2s | ❌ Déjà optimal |

---

## Profil 1: VITESSE MAXIMALE ⚡
**Objectif:** ~20-25s par question (-50% latence)

### Paramètres
```python
"n_ctx": 1024,          # ÷2 (moins de contexte)
"max_tokens": 60,       # ÷2.5 (réponses courtes)
"n_batch": 512,         # maintenu
"temperature": 0.5,     # plus déterministe
```

### Impact
- ✅ **Gain:** 25-30s de latence en moins
- ⚠️ **Compromis:** 
  - Réponses plus courtes (2-3 phrases)
  - Moins de contexte conversation
  - Moins de nuances

### Cas d'usage
- Questions simples et directes
- Conversations rapides
- Tests et développement

---

## Profil 2: ÉQUILIBRÉ ⚖️
**Objectif:** ~30-35s par question (-35% latence)

### Paramètres
```python
"n_ctx": 1536,          # -25% contexte
"max_tokens": 100,      # -33% tokens
"n_batch": 512,
"temperature": 0.6,
```

### Impact
- ✅ **Gain:** 15-20s de latence en moins
- ✅ **Compromis acceptable:**
  - Réponses de qualité (3-4 phrases)
  - Contexte conversation suffisant
  - Bonne balance vitesse/qualité

### Cas d'usage
- Usage quotidien recommandé
- Conversations naturelles
- Questions moyennement complexes

---

## Profil 3: QUALITÉ ⭐
**Objectif:** ~45-50s par question (-10% latence)

### Paramètres
```python
"n_ctx": 2048,          # maintenu
"max_tokens": 120,      # -20% tokens
"n_batch": 512,
"temperature": 0.7,     # maintenu
```

### Impact
- ✅ **Gain:** 5-10s de latence en moins
- ✅ **Qualité maximale:**
  - Réponses détaillées (4-5 phrases)
  - Contexte conversation complet
  - Nuances préservées

### Cas d'usage
- Questions complexes
- Analyses détaillées
- Qualité prioritaire

---

## Profil 4: ULTRA-RAPIDE 🚀 (EXPÉRIMENTAL)
**Objectif:** ~15-20s par question (-65% latence)

### Paramètres
```python
"n_ctx": 512,           # ÷4 (minimal)
"max_tokens": 40,       # ÷3.75 (très court)
"n_batch": 256,         # réduit pour stabilité
"temperature": 0.3,     # très déterministe
```

### Impact
- ✅ **Gain:** 30-35s de latence en moins
- ⚠️ **Compromis important:**
  - Réponses très courtes (1-2 phrases)
  - Presque pas de contexte
  - Réponses factuelles uniquement

### Cas d'usage
- Tests rapides
- Questions yes/no
- Démonstrations

---

## Comparaison

| Profil | Latence | Qualité | Contexte | Recommandé |
|--------|---------|---------|----------|------------|
| **Actuel** | 50-55s | ⭐⭐⭐⭐⭐ | 2048 | Non |
| **Ultra** | 15-20s | ⭐⭐ | 512 | Tests |
| **Vitesse** | 20-25s | ⭐⭐⭐ | 1024 | Dev |
| **Équilibré** | 30-35s | ⭐⭐⭐⭐ | 1536 | ✅ OUI |
| **Qualité** | 45-50s | ⭐⭐⭐⭐⭐ | 2048 | Analyses |

---

## Recommandation

**→ PROFIL ÉQUILIBRÉ** pour usage quotidien:
- Latence acceptable (~30-35s)
- Qualité préservée
- Contexte suffisant

**→ PROFIL VITESSE** pour sessions interactives:
- Latence réduite (~20-25s)
- Qualité encore correcte
- Bon compromis

---

## Limitations Matérielles

**CPU i7-7700HQ:**
- Génération: ~3 tokens/s
- Impossible d'aller en-dessous de ~15s avec qualité
- GPU améliorerait de 5-10x (non disponible)

**Optimisations déjà appliquées:**
- ✅ n_batch: 512 (parallélisation)
- ✅ n_threads: 6 (optimal)
- ✅ Prompt minimaliste
- ✅ Modèle Q4_K_M (quantifié)

---

## Mise en Œuvre

### Changer de profil
Modifiez `config/system_config.py`:

```python
# PROFIL ÉQUILIBRÉ (recommandé)
MODEL_CONFIG["llm"] = {
    "n_ctx": 1536,
    "max_tokens": 100,
    "temperature": 0.6,
    # ... autres paramètres
}
```

### Tester le profil
```bash
# Nettoyer cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Relancer
python3 launcher.py
```

### Mesurer la latence
```bash
python3 scripts/benchmark_pipeline.py
```

---

## Conclusion

**Sans GPU, on atteint les limites du CPU i7-7700HQ.**

Options:
1. ✅ **Adopter profil ÉQUILIBRÉ** (30-35s) - RECOMMANDÉ
2. ✅ **Adopter profil VITESSE** (20-25s) - Acceptable
3. ⚠️ **Garder actuel** (50s) - Trop lent
4. 💰 **Ajouter GPU** - Amélioration 5-10x (hors budget)

**Choix optimal:** PROFIL ÉQUILIBRÉ (n_ctx=1536, max_tokens=100)

