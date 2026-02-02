#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script principal de sauvegarde QAIA
Permet de choisir entre sauvegarde rapide et complète
Utilise utils/backup_manager.py pour les opérations de sauvegarde
"""

# /// script
# dependencies = []
# ///

import sys
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Importer le gestionnaire de sauvegarde
try:
    from utils.backup_manager import QAIBackupManager, create_backup
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assurez-vous que utils/backup_manager.py existe")
    sys.exit(1)

def show_menu():
    """Affiche le menu de sauvegarde"""
    print("🚀 SAUVEGARDE QAIA")
    print("=" * 30)
    print("1. Sauvegarde rapide (fichiers essentiels, sans ZIP)")
    print("2. Sauvegarde complète (tout QAIA + ZIP)")
    print("3. Test du module de sauvegarde")
    print("4. Quitter")
    print()

def quick_backup():
    """
    Lance la sauvegarde rapide (sans ZIP, fichiers essentiels uniquement)
    """
    print("🔄 Lancement de la sauvegarde rapide...")
    try:
        # Créer le gestionnaire de sauvegarde
        backup_manager = QAIBackupManager()
        
        # Sauvegarde complète mais sans ZIP pour aller plus vite
        print("📁 Sauvegarde des fichiers essentiels...")
        success = backup_manager.full_backup(create_zip=False)
        
        if success:
            print("\n✅ Sauvegarde rapide terminée avec succès!")
            print(f"📁 Emplacement: {backup_manager.backup_dir}")
        else:
            print("\n❌ Échec de la sauvegarde rapide!")
        
        return success
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def full_backup():
    """
    Lance la sauvegarde complète (avec ZIP)
    """
    print("🔄 Lancement de la sauvegarde complète...")
    try:
        # Utiliser la fonction utilitaire
        success = create_backup(create_zip=True)
        
        if success:
            print("\n✅ Sauvegarde complète terminée avec succès!")
        else:
            print("\n❌ Échec de la sauvegarde complète!")
        
        return success
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backup():
    """
    Teste le module de sauvegarde (vérification de l'initialisation)
    """
    print("🔄 Test du module de sauvegarde...")
    try:
        # Créer une instance du gestionnaire
        backup_manager = QAIBackupManager()
        
        print(f"✅ Répertoire source: {backup_manager.source_dir}")
        print(f"✅ Répertoire de sauvegarde: {backup_manager.backup_dir}")
        
        # Vérifier que le répertoire source existe
        if not backup_manager.source_dir.exists():
            print(f"❌ Répertoire source introuvable: {backup_manager.source_dir}")
            return False
        
        # Vérifier les informations de sauvegarde
        info = backup_manager.get_backup_info()
        if "error" not in info:
            print(f"✅ Informations de sauvegarde disponibles")
            print(f"   Dernière sauvegarde: {info.get('timestamp', 'N/A')}")
        else:
            print("ℹ️  Aucune sauvegarde précédente trouvée")
        
        print("\n✅ Test terminé avec succès!")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale"""
    while True:
        show_menu()
        
        try:
            choice = input("Votre choix (1-4): ").strip()
            
            if choice == "1":
                print("\n" + "="*50)
                success = quick_backup()
                if success:
                    print("\n✅ Sauvegarde rapide terminée avec succès!")
                else:
                    print("\n❌ Échec de la sauvegarde rapide!")
                input("\nAppuyez sur Entrée pour continuer...")
                
            elif choice == "2":
                print("\n" + "="*50)
                print("⚠️  ATTENTION: La sauvegarde complète va copier tout QAIA")
                print("   Cela peut prendre du temps et utiliser beaucoup d'espace disque.")
                confirm = input("Voulez-vous vraiment continuer ? (o/N): ").strip().lower()
                
                if confirm in ['o', 'oui', 'y', 'yes']:
                    success = full_backup()
                    if success:
                        print("\n✅ Sauvegarde complète terminée avec succès!")
                    else:
                        print("\n❌ Échec de la sauvegarde complète!")
                else:
                    print("❌ Sauvegarde complète annulée")
                input("\nAppuyez sur Entrée pour continuer...")
                
            elif choice == "3":
                print("\n" + "="*50)
                success = test_backup()
                if success:
                    print("\n✅ Test terminé avec succès!")
                else:
                    print("\n❌ Échec du test!")
                input("\nAppuyez sur Entrée pour continuer...")
                
            elif choice == "4":
                print("\n👋 Au revoir!")
                break
                
            else:
                print("❌ Choix invalide. Veuillez choisir 1, 2, 3 ou 4.")
                input("\nAppuyez sur Entrée pour continuer...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()
