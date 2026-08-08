#!/usr/bin/env python3
"""Patch spyder/plugins/help/widgets.py : "Accueil" et "Verrouiller/Deverrouiller" quittent la barre
du dock "Aide" pour son menu burger (options).

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt, arbitrage de l'utilisateur le 26/07/2026.

CONSTAT. La barre porte deux etiquettes, deux listes deroulantes, un champ de saisie - de quoi
choisir la source et l'objet a documenter, c'est le coeur du panneau - puis deux boutons :
"Accueil" (revenir au message d'introduction) et "Verrouiller/Deverrouiller" (figer le panneau sur
l'objet courant plutot que de suivre le curseur). Le dock n'est pas affiche par defaut sur cette
machine mais reste reaffichable par Affichage > Panneaux.

CHANGEMENT. Les deux boutons passent dans la section Other du menu burger, aupres de "Import
automatique" - qui est deja, exactement, un reglage du meme ordre. La barre ne garde que ce qui sert
a designer l'objet documente.

Les actions restent CREEES et enregistrees (self.locked_action est encore pilotee par le code du
panneau) : on ne change QUE ou elles s'affichent.

Usage : patch_spyder_help_toolbar.py <chemin vers help/widgets.py installe>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja en place, de sorte
qu'une passe ulterieure puisse ajouter un bloc sans rien defaire. Re-parse avant ecriture, echec
BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # 1. Menu burger : accueillir les deux boutons, aupres de "Import automatique".
    (
        '"Accueil" et le verrou, retires de la barre',
        '''        self.add_item_to_menu(
            self.auto_import_action,
            menu=menu,
            section=HelpWidgetOptionsMenuSections.Other,
        )''',
        '''        # SmartOS (patch_spyder_help_toolbar.py) : "Accueil" et le verrou, retires de la barre.
        # Ils rejoignent "Import automatique", qui est deja un reglage du meme ordre.
        for item in [self.home_action, self.locked_action,
                     self.auto_import_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=HelpWidgetOptionsMenuSections.Other,
            )''',
    ),
    # 2. Barre : ne garder que de quoi designer l'objet documente.
    (
        "la barre ne garde que de quoi designer l'objet",
        '''        for item in [self.source_label, self.source_combo, self.object_label,
                     self.object_combo, self.object_edit, self.home_action,
                     self.locked_action]:''',
        '''        # SmartOS (patch_spyder_help_toolbar.py) : la barre ne garde que de quoi designer l'objet
        # documente (source, objet). "Accueil" et le verrou sont dans le menu burger, cf. plus haut.
        for item in [self.source_label, self.source_combo, self.object_label,
                     self.object_combo, self.object_edit]:''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0)."""
    applied = 0
    for marqueur, olds, new in pairs:
        if marqueur in source:
            continue  # bloc deja en place
        if isinstance(olds, str):
            olds = (olds,)
        # PREMIER candidat qui matche exactement une fois, les candidats etant donnes DU PLUS
        # SPECIFIQUE AU PLUS GENERAL. Ce n'est pas un detail : le texte pose par une passe
        # precedente CONTIENT en general le texte d'origine de Spyder (elle n'avait fait qu'y
        # ajouter des lignes), donc les deux matchent, et exiger un candidat unique echouerait.
        trouve = next((o for o in olds if source.count(o) == 1), None)
        if trouve is None:
            print(f"Aucun des {len(olds)} textes attendus n'est present exactement une fois dans "
                  f"{path} - le code amont a peut-etre ete restructure, patch {nom} non applique. "
                  f"Bloc:\n{olds[0][:80]}...", file=sys.stderr)
            return None, 0
        source = source.replace(trouve, new)
        applied += 1
    return source, applied


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers help/widgets.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"widgets.py illisible ({error}) - patch barre Aide non applique.", file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Aide", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Aide : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le widgets.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Aide applique ({applied} bloc(s)) : Accueil et le verrou deplaces dans le "
          f"menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
