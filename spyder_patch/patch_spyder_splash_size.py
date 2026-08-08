#!/usr/bin/env python3
"""Ajuste le canevas de l'ecran de demarrage aux proportions du splash SmartPythonEditor.

create_splash_screen() (spyder/app/utils.py) rend le SVG par QSvgRenderer dans une image de
taille FIXE (526x432, ratio 1,218) : le moteur etire le SVG aux dimensions du canevas, sans
preserver ses proportions. Le splash SmartPythonEditor fourni par l'utilisateur (08/08/2026)
fait 1560x1009 (ratio 1,546) : rendu tel quel, il serait ecrase verticalement.

Ce patch remplace les deux constantes par 526x340 (meme largeur que l'amont, hauteur alignee
sur le ratio du nouveau SVG : 526/1,546 = 340). Si le visuel change de proportions, ajuster
ici - et NULLE PART ailleurs, c'est le seul endroit qui fixe le canevas.

Idempotent (marqueur), echec bruyant si les constantes amont ont change de forme.

Usage : patch_spyder_splash_size.py <chemin de spyder/app/utils.py>
"""

import sys

MARQUEUR = "# [SmartOS splash-size]"

ANCIEN = """        width = 526
        height = 432"""

NOUVEAU = """        width = 526   %(m)s canevas aligne sur le ratio du splash SmartPythonEditor
        height = 340  %(m)s (1560x1009 -> 526x340) ; cf. patch_spyder_splash_size.py""" % {
    "m": MARQUEUR}


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    chemin = sys.argv[1]
    with open(chemin, encoding="utf-8") as flux:
        contenu = flux.read()
    if MARQUEUR in contenu:
        print(f"Deja applique : {chemin}")
        return 0
    if ANCIEN not in contenu:
        print(f"ERREUR : constantes du splash introuvables dans {chemin} - "
              f"la forme amont a change, patch NON applique.", file=sys.stderr)
        return 1
    contenu = contenu.replace(ANCIEN, NOUVEAU, 1)
    with open(chemin, "w", encoding="utf-8") as flux:
        flux.write(contenu)
    print(f"Patch taille du splash applique : canevas 526x340 ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
