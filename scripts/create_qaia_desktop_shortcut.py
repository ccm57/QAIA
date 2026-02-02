#!/usr/bin/env python
# -*- coding: utf-8 -*-
# \QAIA\

"""Script utilitaire pour générer un raccourci bureau QAIA (.desktop)."""

# /// script
# dependencies = [
# ]
# ///

from pathlib import Path
import shutil


def installer_icone_systeme(qaia_root: Path, icon_name: str = "qaia") -> str:
    """Installe l'icône PNG dans le thème d'icônes utilisateur (~/.local/share/icons).

    Args:
        qaia_root (Path): Racine du projet QAIA.
        icon_name (str): Nom logique de l'icône (sans extension).

    Returns:
        str: Nom logique à utiliser dans le champ Icon= du .desktop.
    """
    source_icon = qaia_root / "assets" / "icons" / "QAIA2.png"
    home = Path.home()
    # Chemin standard Freedesktop pour les icônes utilisateur
    target_dir = home / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_icon = target_dir / f"{icon_name}.png"

    if source_icon.is_file():
        try:
            shutil.copy2(source_icon, target_icon)
        except Exception:
            # En cas d'échec, on retombera sur l'icône par défaut du thème
            return icon_name

    return icon_name


def generer_contenu_desktop(qaia_root: Path) -> str:
    """Génère le contenu du fichier QAIA.desktop en utilisant une icône de thème.

    L'icône QAIA2.png est copiée dans ~/.local/share/icons/hicolor/... et référencée
    par un nom logique (ex: Icon=qaia), ce qui est plus fiable sur Cinnamon/Mint.
    """
    # Utiliser le Python actuellement actif (pyenv/venv) plutôt que un chemin système fixe
    import sys
    python_exec = Path(sys.executable)
    launcher = qaia_root / "launcher.py"

    # Installer l'icône dans le thème utilisateur et récupérer le nom logique
    icon_name = installer_icone_systeme(qaia_root, icon_name="qaia")

    return f"""[Desktop Entry]
Version=1.0
Type=Application
Name=QAIA
Comment=Quality Assistant Intelligent Agent
Exec={python_exec} {launcher}
Path={qaia_root}
Icon={icon_name}
Terminal=false
Categories=Utility;AI;
StartupNotify=false
Encoding=UTF-8
"""


def main() -> None:
    """Point d'entrée du script.

    Le script génère un fichier `QAIA.desktop` :
        - en priorité dans `~/Bureau` si ce répertoire existe,
        - sinon dans `~/Desktop` (certaines distributions),
        - sinon dans le répertoire courant.
    L'utilisateur peut ensuite vérifier qu'il est exécutable.
    """
    qaia_root = Path(__file__).resolve().parent.parent

    # Déterminer le bureau de l'utilisateur
    home = Path.home()
    candidates = [home / "Bureau", home / "Desktop"]
    target_dir = None
    for cand in candidates:
        if cand.is_dir():
            target_dir = cand
            break
    if target_dir is None:
        target_dir = Path.cwd()

    desktop_path = target_dir / "QAIA.desktop"

    contenu = generer_contenu_desktop(qaia_root)
    desktop_path.write_text(contenu, encoding="utf-8")

    try:
        # Rendre le fichier exécutable si possible
        import os

        mode = desktop_path.stat().st_mode
        desktop_path.chmod(mode | 0o111)
    except Exception:
        # Pas bloquant si on ne peut pas changer les permissions
        pass

    print(f"Fichier {desktop_path} généré.")
    print("Si nécessaire, vous pouvez exécuter manuellement :")
    print(f"  chmod +x '{desktop_path}'")


if __name__ == "__main__":
    main()


