#!/usr/bin/env python3
"""Declare PySide6 comme dependance pip PAR DEFAUT du fork SmartPythonEditor.

L'amont sait deja viser PySide6 (variable SPYDER_QT_BINDING lue par setup.py), mais son
DEFAUT est pyqt5 et sa plage pyside6 est trop lache ('pyside6>=6.5,<7') : pip installerait
une 6.11 que le controle d'execution de Spyder 6.1.x refuse (requirements.py:check_qt exige
<6.9). Consequence sans ce patch : "pip install ." tire PyQt5, et chaque installeur doit
desinstaller/reinstaller le binding apres coup.

Ce patch, applique au setup.py du fork (JAMAIS a un site-packages - setup.py n'y existe
pas, l'appelant garde ce cas) :
  1. passe le defaut de get_qt_requirements a 'pyside6' ;
  2. remplace la liste pyside6 par la plage EXACTE acceptee par ce Spyder (arguments min et
     max, lus par l'appelant dans qt_bindings_Spyder-<version>.txt du fork), avec repli
     PyQt6 par marqueur d'environnement pour aarch64 (PySide6 n'y publie aucune roue).

Idempotent (marqueur), echec bruyant si la forme amont a change.

Usage : patch_spyder_pyside6_deps.py <chemin de setup.py> <pyside6 min> <pyside6 max>
"""

import sys

MARQUEUR = "# [SmartOS pyside6-deps]"


def main():
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    chemin, mini, maxi = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(chemin, encoding="utf-8") as flux:
        contenu = flux.read()
    if MARQUEUR in contenu:
        print(f"Deja applique : {chemin}")
        return 0

    ancien_defaut = "install_requires = get_qt_requirements(qt_requirements, default='pyqt5')"
    nouveau_defaut = ("install_requires = get_qt_requirements(qt_requirements, "
                      f"default='pyside6')  {MARQUEUR}")
    ancienne_liste = """    'pyside6': [
        'pyside6>=6.5,<7',"""
    nouvelle_liste = f"""    'pyside6': [
        {MARQUEUR} plage EXACTE acceptee par check_qt() (l'amont dit <7 mais refuse
        {MARQUEUR} >=6.9 a l'execution) ; repli PyQt6 sur aarch64 (pas de roue PySide6).
        'pyside6>={mini},<{maxi}; platform_machine != "aarch64"',
        'pyqt6>=6.5,<7; platform_machine == "aarch64"',
        'pyqt6-webengine>=6.5,<7; platform_machine == "aarch64"',"""

    for motif in (ancien_defaut, ancienne_liste):
        if motif not in contenu:
            print(f"ERREUR : motif introuvable dans {chemin} - la forme amont a change,\n"
                  f"         patch NON applique. Motif : {motif.strip().splitlines()[0]}",
                  file=sys.stderr)
            return 1
    contenu = contenu.replace(ancien_defaut, nouveau_defaut, 1)
    contenu = contenu.replace(ancienne_liste, nouvelle_liste, 1)
    with open(chemin, "w", encoding="utf-8") as flux:
        flux.write(contenu)
    print(f"Patch dependances PySide6 applique : defaut pyside6, plage {mini}-{maxi}, "
          f"repli PyQt6 aarch64 ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
