#!/usr/bin/env python3
"""Passe la ligne de bord de l'editeur Spyder (marge PEP8, "edge line") en POINTILLES.

Contexte (TODO CachyOS "TODO - Spyder - line profiler.txt", demande de l'utilisateur) : le
greffon line-profiler ajoute une fine ligne de demarcation PLEINE entre le code et la colonne
des temps. Pour ne pas la confondre avec la ligne de bord (par defaut a 79/88 colonnes, elle
aussi verticale), l'utilisateur veut cette derniere en pointilles.

CE QUI EST PATCHE
    spyder/plugins/editor/panels/edgeline.py, methode EdgeLine.paintEvent. Elle trace la ligne
    avec un stylo plein a la couleur des commentaires. On remplace le stylo par un QPen
    COSMETIQUE (largeur en pixels physiques -> toujours 1 px net, meme sous mise a l'echelle
    fractionnaire KDE) et POINTILLE (motif [6, 2]), et la couleur par
    le fond de l'editeur a peine eclairci (10 %) - meme teinte que le trait de demarcation du
    greffon, pour la coherence. Les colonnes sont inchangees.

METHODE
    Remplace la ligne `painter.setPen(color)` par notre bloc (un commentaire-marqueur stable
    suivi du stylo), et ajoute QPen a l'import qtpy.QtGui. METTEUR A JOUR : si notre bloc est deja
    present (version anterieure du stylo), il est remplace par la version courante - inutile de
    reinstaller le plugin pour changer le motif ou l'epaisseur. Le fichier patche est reparse
    avant ecriture : un edge line casse empecherait tout l'editeur de peindre.

    Comme tout correctif applique dans site-packages, il sera ecrase a la prochaine mise a jour
    du paquet : il est rejoue a chaque execution de installation_SmartPythonEditor.sh.
"""

import ast
import re
import sys


# Bloc d'origine (couleur du commentaire + stylo plein) que l'on remplace la PREMIERE fois.
ANCRE_ORIG = (
    "        color = QColor(self.color)\n"
    "        color.setAlphaF(.5)\n"
    "        painter.setPen(color)\n"
)

# Notre bloc injecte, qui remplace ces trois lignes. Commence par un commentaire-marqueur stable,
# ce qui permet de le RETROUVER et de le remplacer quand on fait evoluer le stylo/la couleur, sans
# avoir a reinstaller le plugin : le patch est alors idempotent ET metteur a jour.
BLOC = (
    "        # Ligne de bord POINTILLEE, discrete et pixel-perfect (ajout SmartOS, cf.\n"
    "        # Commun/scripts/patch_spyder_edgeline_dotted.py) : la distingue de la ligne PLEINE\n"
    "        # de demarcation du greffon line-profiler entre le code et les temps.\n"
    "        # Couleur = fond de l'editeur a peine eclairci (10 %), meme teinte discrete que le\n"
    "        # trait de demarcation, pour la coherence.\n"
    "        # ⚠ setCosmetic(True) : la largeur d'un stylo cosmetique est en pixels PHYSIQUES,\n"
    "        # donc le trait fait toujours pile 1 px net quel que soit le facteur d'echelle KDE\n"
    "        # (fractionnaire compris). Motif [6, 2].\n"
    "        _base = self.editor.palette().base().color()\n"
    "        color = QColor(round(_base.red() * 0.9 + 25.5),\n"
    "                       round(_base.green() * 0.9 + 25.5),\n"
    "                       round(_base.blue() * 0.9 + 25.5))\n"
    "        pen = QPen(color)\n"
    "        pen.setWidth(1)\n"
    "        pen.setCosmetic(True)\n"
    "        pen.setDashPattern([6, 2])\n"
    "        painter.setPen(pen)\n"
)

# Retrouve notre bloc deja injecte (du marqueur jusqu'au setPen final), pour le mettre a jour.
MOTIF_BLOC = re.compile(
    r"        # Ligne de bord POINTILLEE.*?        painter\.setPen\(pen\)\n", re.S)

IMPORT_ANCRE = "from qtpy.QtGui import QPainter, QColor\n"
IMPORT_REMPLACEMENT = "from qtpy.QtGui import QPainter, QColor, QPen\n"


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers edgeline.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding='utf-8') as flux:
            source = flux.read()
    except OSError as error:
        print(f"edgeline.py illisible ({error}) - ligne de bord non modifiee.", file=sys.stderr)
        return 1

    if MOTIF_BLOC.search(source):
        # Deja patche (peut-etre par une version anterieure du stylo) : on remplace le bloc.
        patched = MOTIF_BLOC.sub(lambda _m: BLOC, source)
    elif source.count(ANCRE_ORIG) == 1:
        patched = source.replace(ANCRE_ORIG, BLOC)
    else:
        print("edgeline.py : ni le stylo d'origine ni notre bloc n'ont ete trouves - patch "
              "abandonne. Structure du fichier changee ?", file=sys.stderr)
        return 1

    # QPen doit etre importe. Si l'ancre d'import a change de forme, on echoue bruyamment plutot
    # que d'ecrire un fichier ou QPen n'est pas defini.
    if IMPORT_ANCRE in patched:
        patched = patched.replace(IMPORT_ANCRE, IMPORT_REMPLACEMENT)
    elif 'QPen' not in patched:
        print("edgeline.py : l'import qtpy.QtGui n'a pas la forme attendue et QPen est absent - "
              "patch abandonne pour ne pas laisser QPen indefini.", file=sys.stderr)
        return 1

    if patched == source:
        print("Ligne de bord Spyder deja a jour (pointilles 1 px physique).")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"edgeline.py patche invalide ({error}) - aucune modification ecrite.",
              file=sys.stderr)
        return 1

    with open(path, 'w', encoding='utf-8') as flux:
        flux.write(patched)
    print("Ligne de bord Spyder : pointilles de 1 px physique (stylo cosmetique).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
