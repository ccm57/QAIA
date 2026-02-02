#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migration des fichiers de backup vers backups/agents/
"""

# /// script
# dependencies = []
# ///

import os
import shutil
from pathlib import Path

def migrate_backups():
    """Migre tous les fichiers de backup vers backups/agents/"""
    
    # Chemins
    base_dir = Path(__file__).parent.parent
    agents_dir = base_dir / "agents"
    backups_dir = base_dir / "backups" / "agents"
    
    # Créer le dossier de destination
    backups_dir.mkdir(parents=True, exist_ok=True)
    
    # Trouver tous les fichiers de backup
    backup_files = list(agents_dir.glob("*.backup_*"))
    
    if not backup_files:
        print("✅ Aucun fichier de backup trouvé dans agents/")
        return
    
    print(f"📦 Migration de {len(backup_files)} fichiers de backup...")
    
    migrated = 0
    errors = []
    
    for backup_file in backup_files:
        try:
            dest_path = backups_dir / backup_file.name
            shutil.move(str(backup_file), str(dest_path))
            print(f"  ✅ {backup_file.name} → backups/agents/")
            migrated += 1
        except Exception as e:
            error_msg = f"  ❌ Erreur avec {backup_file.name}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    print(f"\n📊 Résumé:")
    print(f"  ✅ Migrés: {migrated}/{len(backup_files)}")
    if errors:
        print(f"  ❌ Erreurs: {len(errors)}")
        for error in errors:
            print(f"    {error}")
    else:
        print("  ✅ Tous les fichiers ont été migrés avec succès!")

if __name__ == "__main__":
    migrate_backups()

