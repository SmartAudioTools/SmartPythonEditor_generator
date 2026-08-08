#!/usr/bin/env python3
"""Patch spyder/plugins/profiler/widgets/main_widget.py : allege la barre d'outils ET la barre de
coin du dock "Profileur" en deplaçant des boutons dans son menu burger (options).

Contexte : chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt ("voir dock par
dock quels boutons on peut deplacer dans le menu burger du dock"), inventaire + approbation de
l'utilisateur le 25/07/2026, puis deuxieme passe le 26/07/2026.

CONSTAT. C'est le dock le plus charge de tous : DIX boutons en permanence (barre : Reduire, Etendre,
trois bascules d'affichage, Rechercher, Arreter le profilage ; coin : Enregistrer, Charger, Effacer
la comparaison) pour un menu burger totalement VIDE - il ne contenait que les quatre actions de dock
(Deplacer/Detacher/Ancrer/Fermer) ajoutees d'office par PluginMainWidget.

CHANGEMENTS (1re passe, 25/07/2026).
  - Nouvelle classe ProfilerWidgetOptionsMenuSections (le panneau n'en avait pas : son menu burger
    n'avait aucune entree propre).
  - Les trois BASCULES D'AFFICHAGE quittent la barre pour la section Display du burger : on les
    regle une fois pour choisir sa vue, on n'y revient pas a chaque profilage.
  - Enregistrer / Charger / Effacer la comparaison quittent le COIN pour la section Data du burger :
    trois icones permanentes pour des actions rares (comparaison de deux profilages).

CHANGEMENT (2e passe, 26/07/2026). "Reduire" et "Etendre" - le pliage d'UN niveau d'arbre - quittent
a leur tour la barre pour la section Tree du burger : l'arbre se plie et se deplie aussi a la souris,
directement sur ses propres chevrons.

CHANGEMENT (3e passe, 26/07/2026, item 5 du TODO cosmetique : "supprimer le separateur entre l'outil
loupe et le bouton stop, deplacer le stop dans le menu burger"). "Arreter le profilage" quitte la
barre pour la derniere section du burger. Le separateur disparait de lui-meme : c'etait le trait entre
les sections ChangeView (la loupe) et Stop, et la barre n'a plus qu'une section. L'arret du profilage
reste a un clic par la barre "Stop" du greffon spyder_stop_toolbar, qui arrete tout.

Il ne reste donc qu'UN bouton dans la barre (Rechercher) et plus rien dans le coin a part le bouton
burger lui-meme.

Les actions restent CREEES et enregistrees a l'identique (update_actions() les retrouve par
self.get_action(...), independamment de leur emplacement) : on ne change QUE ou elles s'affichent.

Usage : patch_spyder_profiler_toolbar.py <chemin vers profiler/widgets/main_widget.py installe>

IDEMPOTENCE PAR BLOC. Chaque bloc porte SON marqueur et est saute si ce marqueur est deja dans le
fichier. C'est ce qui permet d'ajouter un bloc lors d'une passe ulterieure et de le voir s'appliquer
sur une installation ou les blocs des passes precedentes sont deja en place, sans rien defaire. Un
marqueur global unique aurait rendu la 2e passe inoperante - piege deja paye sur ce depot. Les blocs
sont appliques DANS L'ORDRE : un bloc peut donc s'ancrer sur le resultat d'un bloc precedent. Chaque
marqueur doit etre une chaine STABLE de son propre texte de remplacement, qu'aucun bloc ulterieur ne
reecrit. Re-parse avant ecriture ; echec BRUYANT (code 1) si un bloc attendu est introuvable ou non
unique - jamais deviner.
"""
import ast
import sys

# Texte pose par le bloc 1, reutilise comme ancre par le bloc 4.
SECTIONS_V1 = '''class ProfilerWidgetMainToolbarSections:
    # BrowseView = "view_section" # To be added later
    ExpandCollapse = "collapse_section"
    ChangeView = "change_view_section"
    Stop = "stop_section"


class ProfilerWidgetOptionsMenuSections:
    """SmartOS (patch_spyder_profiler_toolbar.py) : sections du menu burger du Profileur, qui
    n'en avait aucune - son menu ne contenait que les quatre actions de dock ajoutees d'office
    par PluginMainWidget."""
    Display = "display_section"
    Data = "data_section"'''

# Texte pose par le bloc 4, reutilise comme ancre par le bloc 7.
SECTIONS_V2 = SECTIONS_V1 + '''
    #: SmartOS (2e passe, 26/07/2026) : "Reduire" et "Etendre", retires de la barre.
    Tree = "tree_section"'''

# Texte pose par le bloc 3, reutilise comme ancre par le bloc 6.
MENU_V1 = '''        options_menu = self.get_options_menu()
        for action in [
            slow_local_action,
            toggle_builtins_action,
            callers_or_callees_action,
        ]:
            self.add_item_to_menu(
                action,
                menu=options_menu,
                section=ProfilerWidgetOptionsMenuSections.Display,
            )'''

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # ---- 1re passe (25/07/2026) ----------------------------------------------------------------
    # 1. Sections du menu burger (le panneau n'en avait aucune).
    (
        "class ProfilerWidgetOptionsMenuSections",
        '''class ProfilerWidgetMainToolbarSections:
    # BrowseView = "view_section" # To be added later
    ExpandCollapse = "collapse_section"
    ChangeView = "change_view_section"
    Stop = "stop_section"''',
        SECTIONS_V1,
    ),
    # 2. Barre : ne garder que Rechercher parmi les items de la section ChangeView.
    (
        'seul "Rechercher" reste dans la barre',
        '''        for action in [
            slow_local_action,
            toggle_builtins_action,
            callers_or_callees_action,
            search_action
        ]:
            self.add_item_to_toolbar(
                action,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.ChangeView,
            )''',
        '''        # SmartOS (patch_spyder_profiler_toolbar.py) : seul "Rechercher" reste dans la barre.
        # Les trois bascules d'affichage partent dans le menu burger (cf. plus bas) : ce sont des
        # reglages de vue, choisis une fois, pas des commandes du quotidien.
        for action in [
            search_action
        ]:
            self.add_item_to_toolbar(
                action,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.ChangeView,
            )''',
    ),
    # 3. Coin vide, et menu burger peuple des six actions deplacees.
    (
        "# ---- Menu burger (options)",
        '''        # ---- Corner widget
        for action in [save_action, load_action, clear_action]:
            self.add_corner_widget(action, before=self._options_button)''',
        '''        # ---- Menu burger (options)
        # SmartOS (patch_spyder_profiler_toolbar.py) : tout ce qui a quitte la barre et le coin
        # atterrit ici. Deux sections, donc separees par un trait ; les actions de dock
        # (Deplacer/Detacher/Ancrer/Fermer) restent en dernier, PluginMainWidgetOptionsMenu.render()
        # reservant toujours la section Bottom a celles-la.
''' + MENU_V1 + '''

        for action in [save_action, load_action, clear_action]:
            self.add_item_to_menu(
                action,
                menu=options_menu,
                section=ProfilerWidgetOptionsMenuSections.Data,
            )''',
    ),

    # ---- 2e passe (26/07/2026) -----------------------------------------------------------------
    # 4. Nouvelle section Tree, ajoutee a la classe creee par le bloc 1.
    (
        'Tree = "tree_section"',
        SECTIONS_V1,
        SECTIONS_V2,
    ),
    # 5. Barre : retirer "Reduire" et "Etendre" (elle ne garde que Rechercher et Arreter).
    (
        '"Reduire" et "Etendre" ne sont plus dans la barre',
        '''        for action in [collapse_action, expand_action]:
            self.add_item_to_toolbar(
                action,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.ExpandCollapse,
            )''',
        '''        # SmartOS (2e passe, 26/07/2026) : "Reduire" et "Etendre" ne sont plus dans la barre,
        # ils sont passes dans le menu burger (cf. plus bas). L'arbre se plie et se deplie aussi a
        # la souris, sur ses propres chevrons.''',
    ),
    # 6. Menu burger : "Reduire" et "Etendre" en tete, dans la section Tree.
    (
        "le pliage d'un niveau d'arbre, retire de la barre",
        MENU_V1,
        '''        options_menu = self.get_options_menu()

        # SmartOS (2e passe, 26/07/2026) : le pliage d'un niveau d'arbre, retire de la barre.
        for action in [collapse_action, expand_action]:
            self.add_item_to_menu(
                action,
                menu=options_menu,
                section=ProfilerWidgetOptionsMenuSections.Tree,
            )
''' + MENU_V1.split("\n", 1)[1],
    ),

    # ---- 3e passe (26/07/2026, item 5 du TODO cosmetique) --------------------------------------
    # 7. Nouvelle section StopProfiling du menu burger, ajoutee a la classe des blocs 1 et 4.
    #    ⚠ La VALEUR ne peut pas etre "stop_section" : ProfilerWidgetMainToolbarSections l'emploie
    #    deja, et un marqueur d'idempotence qui matcherait les deux ferait sauter ce bloc.
    (
        'StopProfiling = "stop_profiling_section"',
        SECTIONS_V2,
        SECTIONS_V2 + '''
    #: SmartOS (3e passe, 26/07/2026) : "Arreter le profilage", retire de la barre.
    StopProfiling = "stop_profiling_section"''',
    ),
    # 8. Barre : retirer "Arreter le profilage". Il ne reste que "Rechercher" - donc plus qu'UNE
    #    section, donc plus de separateur : c'est ce trait entre la loupe et le stop que l'item 5
    #    demandait de supprimer.
    (
        '"Arreter le profilage" ne reste pas dans la barre',
        '''        self.add_item_to_toolbar(
            stop_action,
            toolbar=main_toolbar,
            section=ProfilerWidgetMainToolbarSections.Stop,
        )''',
        '''        # SmartOS (3e passe, 26/07/2026) : "Arreter le profilage" ne reste pas dans la barre, il
        # passe dans le menu burger (cf. plus bas). La barre "Stop" du greffon
        # spyder_stop_toolbar porte desormais un bouton global qui arrete aussi le profilage,
        # avec le debogage, l'execution et l'analyse de code : le bouton local devient un secours.
        # Consequence voulue : la barre n'a plus qu'une section (Rechercher), donc plus de
        # separateur - le trait entre la loupe et le stop que l'item 5 demandait de supprimer.''',
    ),
    # 9. Menu burger : "Arreter le profilage" en derniere section, apres les actions de donnees.
    (
        '"Arreter le profilage", retire de la barre par la 3e passe',
        '''        for action in [save_action, load_action, clear_action]:
            self.add_item_to_menu(
                action,
                menu=options_menu,
                section=ProfilerWidgetOptionsMenuSections.Data,
            )''',
        '''        for action in [save_action, load_action, clear_action]:
            self.add_item_to_menu(
                action,
                menu=options_menu,
                section=ProfilerWidgetOptionsMenuSections.Data,
            )

        # SmartOS (3e passe, 26/07/2026) : "Arreter le profilage", retire de la barre par la 3e passe.
        # En derniere section propre au panneau, juste avant les actions de dock.
        self.add_item_to_menu(
            stop_action,
            menu=options_menu,
            section=ProfilerWidgetOptionsMenuSections.StopProfiling,
        )''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0)."""
    applied = 0
    for marqueur, old, new in pairs:
        if marqueur in source:
            continue  # bloc deja en place
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - le code "
                  f"amont a peut-etre ete restructure, patch {nom} non applique. "
                  f"Bloc:\n{old[:80]}...", file=sys.stderr)
            return None, 0
        source = source.replace(old, new)
        applied += 1
    return source, applied


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers profiler/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Profileur non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Profileur", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Profileur : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Profileur applique ({applied} bloc(s)) : bascules d'affichage, actions de "
          f"donnees et pliage d'arbre deplaces dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
