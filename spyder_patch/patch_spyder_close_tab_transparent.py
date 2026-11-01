#!/usr/bin/env python3
"""Croix de fermeture d'onglet de Spyder : fond transparent (hors survol et clic), et position.

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

POSITION (demande de l'utilisateur, 01/11/2026) : « les croix pour fermer les onglets sont un
peu trop hautes (pas aligne en bas avec le text de l'onglet) et trop a droite ». Mesure hors
ecran, a l'echelle 1 : bas de la croix 2 px au-dessus de la ligne de base du texte, 3,7 px de la
croix au bord droit de l'onglet contre 11 px du bord gauche au texte. Les marges de la feuille
de style du bouton passent de 9/-7 (haut/bas) a 10/-8 et de 2/-6 (gauche/droite) a -2/-2 :
croix 1 px plus bas, 4 px plus a gauche (7,7 px du bord, 10,7 px du texte). Seulement 1 px vers
le bas : a l'echelle 1,3 la croix touche deja la ligne de base, 2 px l'y feraient passer
dessous. Ecarte : un decalage calcule sur la metrique de la police, trop de code pour 1 px.

TAILLE (meme jour) : la croix paraissait plus grande une fois deplacee ; l'utilisateur :
« oui, réduis-la à 14 px ». setIconSize passe de 16 a 14 ; le bouton (SIZE) garde ses
dimensions, donc la largeur des onglets ne change pas. L'icone est centree dans le bouton :
reduite de 2 px, son bas remonte de 1 px - d'ou marginTop/marginBottom a 11/-9 et non 10/-8,
pour garder le bas de la croix au meme niveau.

Chaque remplacement est ancre sur des lignes d'origine uniques, idempotent par son marqueur,
en echec bruyant si ni l'ancre ni le marqueur ne sont trouves ; fichier reparse avant ecriture.
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

ANCRE_MARGES = (
    "            marginTop='9px',\n"
    "            marginBottom='-7px',\n"
    "            marginLeft='3px' if MAC else '2px',\n"
    "            marginRight='-7px' if MAC else '-6px',\n"
)
MARQUEUR_MARGES = "# Croix plus basse et plus a gauche (ajout SmartOS"
BLOC_MARGES = (
    "            # Croix plus basse et plus a gauche (ajout SmartOS, cf.\n"
    "            # patch_spyder_close_tab_transparent.py) : bas aligne sur le texte.\n"
    "            marginTop='11px',\n"
    "            marginBottom='-9px',\n"
    "            marginLeft='-1px' if MAC else '-2px',\n"
    "            marginRight='-3px' if MAC else '-2px',\n"
)

ANCRE_TAILLE = "        self.setIconSize(QSize(size, size))\n"
MARQUEUR_TAILLE = "# Croix de 14 px au lieu de 16 (ajout SmartOS"
BLOC_TAILLE = (
    "        # Croix de 14 px au lieu de 16 (ajout SmartOS, cf.\n"
    "        # patch_spyder_close_tab_transparent.py) : le bouton, lui, garde sa taille.\n"
    "        self.setIconSize(QSize(size - 2, size - 2))\n"
)

CORRECTIFS = (
    (ANCRE, MARQUEUR, BLOC, "fond transparent au repos"),
    (ANCRE_MARGES, MARQUEUR_MARGES, BLOC_MARGES, "bas aligne sur le texte, 4 px a gauche"),
    (ANCRE_TAILLE, MARQUEUR_TAILLE, BLOC_TAILLE, "icone de 14 px"),
)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers tabs.py>", file=sys.stderr)
        return 1
    path = sys.argv[1]
    with open(path, encoding='utf-8') as flux:
        source = flux.read()
    patched = source
    for ancre, marqueur, bloc, effet in CORRECTIFS:
        if marqueur in patched:
            print(f"Croix d'onglet Spyder deja faites : {effet}.")
            continue
        if patched.count(ancre) != 1:
            print(f"tabs.py : ancre de CloseTabButton introuvable ({effet}) - patch "
                  "abandonne. Structure du fichier changee ?", file=sys.stderr)
            return 1
        patched = patched.replace(ancre, bloc)
        print(f"Croix d'onglet Spyder : {effet}.")
    if patched != source:
        ast.parse(patched)
        with open(path, 'w', encoding='utf-8') as flux:
            flux.write(patched)
    return 0


if __name__ == '__main__':
    sys.exit(main())
