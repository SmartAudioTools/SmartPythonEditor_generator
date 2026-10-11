#!/usr/bin/env python3
"""Rend transparent le fond des croix de fermeture d'onglet de Spyder (hors survol et clic).

Contexte (demande de l'utilisateur, 11/10/2026) : « il faut mettre transparent le fond des croix
pour fermer les onglets, mais aussi pour les titres des onglets non selectionnes ». Les onglets
eux-memes sont rendus transparents par patch_spyder_colors.py (TABS_PATCH) ; la croix
(`CloseTabButton`, spyder/widgets/tabs.py) peint en revanche son PROPRE carre de fond, aux gris
BG5 (onglet actif) et BG4 (inactif) : elle restait un carre gris sur un onglet devenu transparent.

CE QUI EST PATCHE
    Les deux couleurs de repos de CloseTabButton.__init__. Le survol et le clic gardent leurs
    gris : c'est le retour visuel du bouton. Les deux valeurs sont deux ECRITURES differentes du
    transparent, pas la meme chaine : Spyder distingue l'onglet actif de l'inactif en comparant
    `_tab_color` a `_selected_tab_color` (enterEvent, leaveEvent, mousePressEvent) ; deux chaines
    egales feraient prendre a tout onglet le gris de survol de l'onglet actif.

    Remplacement de texte ancre sur les deux lignes d'origine (uniques dans le fichier),
    idempotent par marqueur, echec bruyant si ni l'ancre ni le marqueur ne sont trouves, fichier
    reparse avant ecriture.
"""

import ast
import sys

ANCRE = (
    "        self._selected_tab_color = SpyderPalette.COLOR_BACKGROUND_5\n"
    "        self._not_selected_tab_color = SpyderPalette.COLOR_BACKGROUND_4\n"
)
MARQUEUR = "# Croix d'onglet a fond transparent (ajout SmartOS"
BLOC = (
    "        # Croix d'onglet a fond transparent (ajout SmartOS, cf.\n"
    "        # patch_spyder_close_tab_transparent.py) : deux ecritures du transparent, pour que la\n"
    "        # comparaison _tab_color == _selected_tab_color distingue encore actif et inactif.\n"
    "        self._selected_tab_color = 'transparent'\n"
    "        self._not_selected_tab_color = 'rgba(0, 0, 0, 0)'\n"
)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers tabs.py>", file=sys.stderr)
        return 1
    path = sys.argv[1]
    with open(path, encoding='utf-8') as flux:
        source = flux.read()
    if MARQUEUR in source:
        print("Croix d'onglet Spyder deja transparentes.")
        return 0
    if source.count(ANCRE) != 1:
        print("tabs.py : couleurs de CloseTabButton introuvables - patch abandonne. "
              "Structure du fichier changee ?", file=sys.stderr)
        return 1
    patched = source.replace(ANCRE, BLOC)
    ast.parse(patched)
    with open(path, 'w', encoding='utf-8') as flux:
        flux.write(patched)
    print("Croix d'onglet Spyder : fond transparent au repos.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
