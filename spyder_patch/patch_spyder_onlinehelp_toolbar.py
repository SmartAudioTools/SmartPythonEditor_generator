#!/usr/bin/env python3
"""Patch spyder/plugins/onlinehelp/widgets.py : "Accueil" et les deux zooms quittent la barre du dock
"Aide en ligne" pour son menu burger (options).

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt, arbitrage de l'utilisateur le 26/07/2026.

CONSTAT. La barre porte DIX elements - Retour, Suivant, Actualiser, Arreter, Accueil, une etiquette,
la liste deroulante d'adresse, Agrandir, Reduire, Recherche - alors que le menu burger de ce dock
etait entierement VIDE (il ne contenait que les quatre actions de dock ajoutees d'office par
PluginMainWidget). Le dock n'est pas affiche par defaut sur cette machine mais reste reaffichable par
Affichage > Panneaux.

CHANGEMENT. Trois boutons passent dans le burger, qui recoit ainsi ses premieres entrees propres :
  - "Accueil" : on y va une fois, au debut ;
  - "Agrandir" et "Reduire" : reglage de confort de lecture, pose une fois - et la molette avec Ctrl
    fait deja le meme travail dans la vue web.
La barre garde la navigation reelle (Retour, Suivant, Actualiser, Arreter), l'adresse et la
recherche.

Les actions restent CREEES et enregistrees : on ne change QUE ou elles s'affichent.

Usage : patch_spyder_onlinehelp_toolbar.py <chemin vers onlinehelp/widgets.py installe>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja en place, de sorte
qu'une passe ulterieure puisse ajouter un bloc sans rien defaire. Re-parse avant ecriture, echec
BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # Barre allegee, et menu burger (jusque-la vide) peuple des trois actions retirees.
    (
        "le menu burger de ce dock etait vide",
        '''        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.get_action(WebViewActions.Back),
                     self.get_action(WebViewActions.Forward), refresh_action,
                     stop_action, home_action, self.label, self.url_combo,
                     self.get_action(WebViewActions.ZoomIn),
                     self.get_action(WebViewActions.ZoomOut), find_action,
                     ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=PydocBrowserMainToolbarSections.Main,
            )''',
        '''        # Toolbar
        # SmartOS (patch_spyder_onlinehelp_toolbar.py) : la barre garde la navigation reelle, la
        # barre d'adresse et la recherche. "Accueil" et les deux zooms partent dans le menu burger
        # (cf. juste apres) - le menu burger de ce dock etait vide, il ne contenait que les quatre
        # actions de dock ajoutees d'office par PluginMainWidget.
        toolbar = self.get_main_toolbar()
        for item in [self.get_action(WebViewActions.Back),
                     self.get_action(WebViewActions.Forward), refresh_action,
                     stop_action, self.label, self.url_combo, find_action,
                     ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=PydocBrowserMainToolbarSections.Main,
            )

        options_menu = self.get_options_menu()
        for item in [home_action,
                     self.get_action(WebViewActions.ZoomIn),
                     self.get_action(WebViewActions.ZoomOut)]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section="smartos_onlinehelp_view",
            )''',
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
        print(f"Usage : {sys.argv[0]} <chemin vers onlinehelp/widgets.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"widgets.py illisible ({error}) - patch barre Aide en ligne non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Aide en ligne", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Aide en ligne : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le widgets.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Aide en ligne applique ({applied} bloc(s)) : Accueil et les deux zooms "
          f"deplaces dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
