#!/usr/bin/env python3
"""Patch spyder/plugins/explorer/widgets/main_widget.py : nettoie la barre d'outils du dock Fichiers.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt" + retours utilisateur du 22/07/2026).
Deux changements :
  1. Retirer "Precedent" et "Suivant" de la barre : peu utilises, ils faisaient DEBORDER la barre
     dans le bouton d'extension "..." (place insuffisante). Il reste "Parent" et "Aller au repertoire
     du fichier courant" ; "Selectionner un repertoire de travail" (de la barre repertoire courant)
     est ajoute AVANT Parent au moment du deplacement (cf. patch_spyder_workingdir_in_files.py) ->
     ordre final : Selectionner, Parent, fichier courant.
  2. Deplacer le bouton de FILTRE (toggle) de la barre d'outils vers le MENU hamburger (menu des
     options), pour alleger la barre.

Les actions restent CREEES (previous/next referencees par le treewidget ; filter_button reference
par change_filter_state) : on ne change QUE leur emplacement (barre -> rien / menu).

Usage : patch_spyder_explorer_toolbar.py <chemin vers explorer/widgets/main_widget.py installe>

Remplacements de blocs exacts, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_explorer_toolbar.py"

# Liste de (ancien, nouveau). Tous doivent matcher exactement et une seule fois.
PAIRS = [
    # 1. Barre : retirer Precedent/Suivant.
    (
        '''        for item in [
            self.previous_action,
            self.next_action,
            self.parent_action,
            self.go_to_dir_of_file_in_editor_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ExplorerWidgetMainToolbarSections.Main,
            )''',
        '''        # SmartOS (patch_spyder_explorer_toolbar.py) : Precedent/Suivant retires de la barre
        # (peu utilises, ils faisaient deborder la barre dans le bouton "..."). "Selectionner un
        # repertoire de travail" est ajoute AVANT Parent au deplacement (patch_spyder_workingdir_in_files.py)
        # -> ordre final : Selectionner, Parent, fichier courant.
        for item in [
            self.parent_action,
            self.go_to_dir_of_file_in_editor_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ExplorerWidgetMainToolbarSections.Main,
            )''',
    ),
    # 2. Donner un libelle au bouton de filtre (il apparaitra dans le menu, plus dans la barre).
    (
        '''        self.filter_button = self.create_action(
            ExplorerWidgetActions.ToggleFilter,
            text="",
            icon=ima.icon('filter'),
            toggled=self.change_filter_state
        )''',
        '''        self.filter_button = self.create_action(
            ExplorerWidgetActions.ToggleFilter,
            # Libelle du bouton de filtre dans le menu, TRADUIT via _() comme les autres items.
            # "Filter files" -> "Filtrer les fichiers" (et non "les noms de fichiers" : on filtre
            # aussi par extension). Cette traduction est AJOUTEE au catalogue gettext de Spyder par
            # Commun/scripts/patch_spyder_add_translations.py.
            text=_("Filter files"),
            icon=ima.icon('filter'),
            toggled=self.change_filter_state
        )''',
    ),
    # 3. Corner : retirer le filtre (il part dans le menu, cf. pair 4).
    (
        '''        for action in [
            self.remote_treewidget.upload_file_action,
            self.refresh_action,
            self.filter_button,
        ]:
            self.add_corner_widget(action, before=self._options_button)''',
        '''        for action in [
            self.remote_treewidget.upload_file_action,
            self.refresh_action,
        ]:
            self.add_corner_widget(action, before=self._options_button)''',
    ),
    # 4. Menu options (hamburger) : ajouter le bouton de filtre en tete de la section Common.
    (
        '''        for item in [hidden_action, filters_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Common,
            )''',
        '''        # SmartOS (patch_spyder_explorer_toolbar.py) : le bouton de filtre (toggle) est
        # deplace ici, dans le menu hamburger, au lieu de la barre d'outils.
        for item in [hidden_action, self.filter_button, filters_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Common,
            )''',
    ),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers explorer/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Explorer non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch barre Explorer deja applique.")
        return 0

    # Verifier d'abord que TOUS les blocs sont presents et uniques (sinon on n'ecrit rien).
    for old, _new in PAIRS:
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch barre Explorer non applique. Bloc:\n{old[:80]}...",
                  file=sys.stderr)
            return 1

    patched = source
    for old, new in PAIRS:
        patched = patched.replace(old, new)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Explorer applique : Precedent/Suivant retires, filtre deplace dans le menu "
          f"hamburger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
