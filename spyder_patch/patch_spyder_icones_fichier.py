#!/usr/bin/env python3
"""Patch spyder/utils/icon_manager.py : fait passer certaines icones du GLYPHE DE POLICE au FICHIER.

Contexte : chapitre "icones" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt, demande de
l'utilisateur du 26/07/2026 ("utilise l'icone .../Commun/icones/spyder/filenew.svg").

LE MECANISME, ET POURQUOI IL FAUT CE PATCH. Les icones de Spyder sont de deux natures :
  - un FICHIER sous spyder/images/{dark,light}/, indexe par son nom SANS extension
    (ImagePathManager.add_image_path). Le remplacer se fait en deposant le sien par-dessus - c'est
    ce qu'on a fait pour l'horloge du profileur, sans une ligne de patch ;
  - un GLYPHE de police, declare dans le dictionnaire _qtaargs de icon_manager.py (par exemple
    'filenew' -> mdi.file, de materialdesignicons*.ttf). Il n'a AUCUN chemin.
Et IconManager.icon() consulte _qtaargs D'ABORD :

    try:
        args, kwargs = self._qtaargs[name]      # <- le glyphe gagne
        ...
    except KeyError:
        icon = QIcon(self.get_icon(name))       # <- le fichier, seulement en repli

Deposer un fichier nomme filenew.svg dans images/ ne servirait donc a RIEN : l'entree du
dictionnaire le masquerait. D'ou ce patch, dont tout le travail consiste a RETIRER l'entree du
dictionnaire pour que le repli par fichier s'applique. Le fichier n'est pas designe ici : il est
trouve par son NOM, comme n'importe quelle icone livree avec Spyder.

CONSEQUENCE A ACCEPTER, ET ELLE EST VOULUE : une icone de fichier ne suit plus le theme. Un glyphe
etait recolorie a la volee (color=MAIN_FG_COLOR, et COLOR_DISABLED pour l'etat grise) ; un SVG porte
ses couleurs. Le mode grise reste correct - get_icon() peint par-dessus en COLOR_DISABLED - mais un
dessin clair concu pour le theme sombre restera clair sur le theme clair. C'est le prix d'un dessin
sur mesure, et la raison pour laquelle on ne bascule QUE les icones explicitement demandees.

⚠ SI LE FICHIER MANQUE, l'icone n'est pas absente : get_image_path() renvoie son defaut 'not_found'.
Le defaut se VOIT donc, il ne passe pas en silence - c'est le bon comportement, mais cela veut dire
que le deploiement du .svg (installation_SmartPythonEditor.sh) et ce patch vont par paire.

Usage : patch_spyder_icones_fichier.py <chemin vers spyder/utils/icon_manager.py installe>

IDEMPOTENCE PAR NOM D'ICONE : chaque bascule porte son propre marqueur (SmartOS icone-fichier <nom>)
et est sautee si ce marqueur est deja dans le fichier. Ajouter un nom a ICONES_FICHIER suffit donc a
basculer une icone de plus, sans defaire les precedentes ni exiger une reinstallation propre - le
piege du marqueur global unique, deja paye sur ce depot. Re-parse avant ecriture, echec BRUYANT
(code 1) si une entree attendue est introuvable ou non unique : jamais deviner.
"""
import ast
import re
import sys

# Icones dont on veut le FICHIER images/<nom>.svg plutot que le glyphe de police.
#   filenew : dessin "document New" de l'utilisateur, Commun/icones/spyder/filenew.svg (26/07/2026).
ICONES_FICHIER = ("filenew",)


def bascule(source, nom):
    """Retire l'entree <nom> de _qtaargs. Renvoie la source patchee, ou None si l'ancre manque."""
    # Ancrage sur la LIGNE ENTIERE de l'entree, reperee par la cle en debut de ligne : le motif est
    # ainsi insensible a l'alignement des colonnes et au contenu des arguments (le glyphe et la
    # couleur changent d'une version de Spyder a l'autre), tout en restant unique - une cle de
    # dictionnaire ne s'y trouve qu'une fois.
    motif = re.compile(r"^([ \t]*)'%s':[ \t]*\[\(.*\n" % re.escape(nom), re.MULTILINE)
    trouves = motif.findall(source)
    if len(trouves) != 1:
        print(f"Entree '{nom}' introuvable ou non unique (occurrences={len(trouves)}) dans _qtaargs "
              f"- le dictionnaire amont a peut-etre change, bascule non appliquee.", file=sys.stderr)
        return None

    indentation = trouves[0]
    remplacement = (
        f"{indentation}# PATCH SmartOS [SmartOS icone-fichier {nom}] (26/07/2026) : entree RETIREE "
        f"du\n"
        f"{indentation}# dictionnaire des glyphes, a dessein. icon() consultant _qtaargs AVANT le\n"
        f"{indentation}# dossier d'images, c'est son ABSENCE ici qui fait servir le fichier\n"
        f"{indentation}# spyder/images/{{dark,light}}/{nom}.svg (depose par installation_SmartPythonEditor.sh\n"
        f"{indentation}# depuis Commun/icones/spyder/). Cf. patch_spyder_icones_fichier.py.\n"
    )
    return motif.sub(lambda _: remplacement, source, count=1)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers spyder/utils/icon_manager.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"icon_manager.py illisible ({erreur}) - patch icones fichier non applique.",
              file=sys.stderr)
        return 1

    basculees = []
    for nom in ICONES_FICHIER:
        if f"[SmartOS icone-fichier {nom}]" in source:
            continue
        patchee = bascule(source, nom)
        if patchee is None:
            return 1
        source = patchee
        basculees.append(nom)

    if not basculees:
        print("Patch icones fichier : toutes les bascules sont deja en place.")
        return 0

    try:
        ast.parse(source)
    except SyntaxError as erreur:
        print(f"L'icon_manager.py patche n'est pas du Python valide ({erreur}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch icones fichier applique : {', '.join(basculees)} servie(s) depuis "
          f"spyder/images/ et non plus depuis la police ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
