#!/usr/bin/env python3
"""Patch spyder/plugins/workingdirectory/container.py : reduit la barre "repertoire courant" au
seul combo de chemin.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt" + retours utilisateur du 22/07/2026). La
barre "repertoire courant" est deplacee en haut du dock Fichiers
(cf. patch_spyder_workingdir_in_files.py). On la degarnit de ses deux boutons :
  - "Aller au repertoire parent" (parent_action) : DOUBLON du "Parent" de la barre de l'Explorer
    (memes remontees, cwd et explorateur synchronises) -> supprime.
  - "Selectionner un repertoire de travail" (browse_action) : DEPLACE dans la barre de l'Explorer,
    avant "Parent" (fait au deplacement, cf. patch_spyder_workingdir_in_files.py) -> retire d'ici.
Il ne reste donc que le combo de chemin (pathedit), pleine largeur, en tete du dock Fichiers.

Les deux actions restent CREEES (parent_action/browse_action referencees par update_actions et par
le deplacement) : on ne les ajoute simplement plus a cette barre.

Usage : patch_spyder_workingdir_bar_trim.py <chemin vers workingdirectory/container.py installe>

Remplacement de bloc exact, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT (code 1)
si le bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "SmartOS: barre repertoire courant reduite au combo"

OLD_BLOCK = '''        for item in [
            spacer,
            self.pathedit,
            self.browse_action,
            self.parent_action,
        ]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=WorkingDirectoryToolbarSections.Main,
            )'''

NEW_BLOCK = '''        # SmartOS: barre repertoire courant reduite au combo (cf.
        # Commun/scripts/patch_spyder_workingdir_bar_trim.py). "Aller au repertoire parent" retire
        # (doublon du "Parent" de l'Explorer) ; "Selectionner un repertoire de travail" deplace dans
        # la barre de l'Explorer (avant Parent, au deplacement). Les deux actions restent creees.
        for item in [
            spacer,
            self.pathedit,
        ]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=WorkingDirectoryToolbarSections.Main,
            )'''


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers workingdirectory/container.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"container.py illisible ({error}) - patch barre repertoire courant non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch barre repertoire courant deja applique.")
        return 0

    if source.count(OLD_BLOCK) != 1:
        print(f"Bloc de la barre repertoire courant introuvable ou non unique dans {path} - Spyder a "
              "peut-etre restructure son code, patch non applique.", file=sys.stderr)
        return 1

    patched = source.replace(OLD_BLOCK, NEW_BLOCK)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le container.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre repertoire courant applique : reduite au combo de chemin ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
