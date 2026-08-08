#!/usr/bin/env python3
"""Patch spyder/plugins/outlineexplorer/main_widget.py : allege la barre d'outils du dock
"Explorateur d'organisation du code" en deplaçant des boutons dans son menu burger (options).

Contexte : chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt ("voir dock par
dock quels boutons on peut deplacer dans le menu burger du dock"), inventaire + approbation de
l'utilisateur le 25/07/2026.

CONSTAT. La barre portait SIX boutons (Aller a la position du curseur, Tout replier, Tout deplier,
Retablir, Replier la sélection, Deplier la sélection) pour un dock qui vit dans la colonne etroite de
gauche : quatre seulement tenaient, les deux derniers etaient relegues dans le bouton d'extension
"..." de Qt (constate en capture d'ecran le 25/07/2026).

DEUX CHANGEMENTS.
  1. "Aller a la position du curseur" est simplement RETIRE de la barre. Rien n'est perdu : le
     panneau cree DEUX objets pour cette meme commande - fromcursor_btn (bouton de barre) et
     fromcursor_act (action de menu, deja presente dans le burger, section DisplayOptions). Seul le
     bouton disparait ; l'entree de menu, elle, existait deja avant ce patch. fromcursor_btn reste
     CREE (create_toolbutton l'enregistre dans le registre du widget) : on ne change que son
     emplacement, comme le patch de l'Explorer l'a fait pour Precedent/Suivant.
  2. "Retablir", "Replier la selection" et "Deplier la selection" passent de la barre au menu burger,
     dans leur propre section (rendue APRES les options d'affichage et AVANT les quatre actions de
     dock Deplacer/Detacher/Ancrer/Fermer - PluginMainWidgetOptionsMenu.render() reserve toujours la
     section Bottom a ces dernieres).

Il reste donc DEUX boutons dans la barre : Tout replier, Tout deplier. Plus de bouton "...".

CORRECTION (2e passe, 26/07/2026, defaut VU A L'ECRAN par l'utilisateur puis photographie).
"Aller a la position du curseur" (fromcursor_act) etait la DERNIERE entree du bloc des options
d'affichage, sept cases a cocher sans icone - et elle, seule, en a une. Qt dessine icone et case a
cocher dans la MEME colonne de gauche : son icone se retrouvait donc plantee dans la colonne des
cases, sous sept cases vides, et "flottait dans le vide". Elle rejoint le bloc du dessous
(Retablir / Replier la selection / Deplier la selection), qui sont toutes des commandes AVEC icone -
ce qui aligne le bloc et remet au passage cette entree la ou est sa place : c'est une commande, pas
une option d'affichage.

Usage : patch_spyder_outline_toolbar.py <chemin vers outlineexplorer/main_widget.py installe>

IDEMPOTENCE PAR BLOC. Chaque bloc porte SON marqueur et est saute si ce marqueur est deja dans le
fichier - c'est ce qui permet a une passe ulterieure de s'appliquer sur une installation deja
patchee, sans rien defaire. Un bloc peut declarer PLUSIEURS textes anciens possibles (tuple) quand
il SUPPLANTE un bloc d'une passe precedente au lieu de s'y ajouter : le texte d'origine de Spyder
(installation fraiche) et celui pose par la passe precedente. Re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc est introuvable ou ambigu - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien(s), nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # 1. Barre : ne garder que Tout replier / Tout deplier.
    (
        'la barre ne garde que "Tout replier" et',
        '''        for item in [fromcursor_btn,
                     self.treewidget.collapse_all_action,
                     self.treewidget.expand_all_action,
                     self.treewidget.restore_action,
                     self.treewidget.collapse_selection_action,
                     self.treewidget.expand_selection_action]:
            self.add_item_to_toolbar(item, toolbar=toolbar,
                                     section=OutlineExplorerSections.Main)''',
        '''        # SmartOS (patch_spyder_outline_toolbar.py) : la barre ne garde que "Tout replier" et
        # "Tout deplier". Les six boutons d'origine ne tenaient pas dans la colonne etroite de
        # gauche : les deux derniers finissaient dans le bouton d'extension "..." de Qt.
        # "Aller a la position du curseur" (fromcursor_btn) est retire sans rien perdre : la MEME
        # commande a deja son entree dans le menu burger (fromcursor_act, plus bas). Les trois
        # autres y sont deplacees (cf. la boucle ajoutee en fin de setup()).
        for item in [self.treewidget.collapse_all_action,
                     self.treewidget.expand_all_action]:
            self.add_item_to_toolbar(item, toolbar=toolbar,
                                     section=OutlineExplorerSections.Main)''',
    ),
    # 2. Menu burger : accueillir les commandes d'arborescence retirees de la barre.
    #    Le bloc de la 1re passe est SUPPLANTE par celui-ci (fromcursor_act s'ajoute a la liste),
    #    d'ou les deux anciens possibles.
    (
        "les quatre commandes d'arborescence",
        # Le texte de la 1re passe EN PREMIER : celui d'origine de Spyder en est un prefixe,
        # donc les deux matchent, et c'est l'ordre qui designe le bon.
        (
            '''        option_menu = self.get_options_menu()
        for action in actions:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.DisplayOptions,
            )

        # SmartOS (patch_spyder_outline_toolbar.py) : les trois actions d'arborescence retirees de
        # la barre atterrissent ici, dans leur propre section (donc precedee d'un separateur). Elle
        # est rendue apres les options d'affichage ci-dessus et avant les actions de dock
        # (Deplacer/Detacher/Ancrer/Fermer), que PluginMainWidgetOptionsMenu.render() place
        # toujours en dernier.
        for action in [self.treewidget.restore_action,
                       self.treewidget.collapse_selection_action,
                       self.treewidget.expand_selection_action]:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.Main,
            )''',
            '''        option_menu = self.get_options_menu()
        for action in actions:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.DisplayOptions,
            )''',
        ),
            '''        option_menu = self.get_options_menu()
        for action in actions:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.DisplayOptions,
            )

        # SmartOS (patch_spyder_outline_toolbar.py) : les quatre commandes d'arborescence, dans leur
        # propre section (donc precedee d'un separateur), rendue apres les options d'affichage
        # ci-dessus et avant les actions de dock - PluginMainWidgetOptionsMenu.render() reserve
        # toujours la fin a celles-la. "Aller a la position du curseur" est ici et NON dans les
        # options d'affichage ci-dessus : elle a une icone, elles n'en ont pas, et Qt place icone et
        # case a cocher dans la meme colonne - son icone flottait donc sous sept cases vides.
        for action in [fromcursor_act,
                       self.treewidget.restore_action,
                       self.treewidget.collapse_selection_action,
                       self.treewidget.expand_selection_action]:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.Main,
            )''',
    ),
    # 3. Options d'affichage : "Aller a la position du curseur" n'y est plus (cf. bloc 2).
    (
        "fromcursor_act n'est plus une option d'affichage",
        '''        actions = [fullpath_act, allfiles_act, group_cells_act,
                   display_variables_act, follow_cursor_act, comment_act,
                   sort_files_alphabetically_act, fromcursor_act]''',
        '''        # SmartOS (2e passe, 26/07/2026) : fromcursor_act n'est plus une option d'affichage,
        # elle rejoint les commandes d'arborescence plus bas - cf. l'explication en tete de fichier.
        actions = [fullpath_act, allfiles_act, group_cells_act,
                   display_variables_act, follow_cursor_act, comment_act,
                   sort_files_alphabetically_act]''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0).

    Le texte ANCIEN d'un bloc peut etre une chaine ou un TUPLE de chaines : un bloc qui SUPPLANTE
    celui d'une passe precedente doit pouvoir remplacer indifferemment le texte d'origine de Spyder
    ou celui deja pose. Exactement un candidat doit matcher, une seule fois.
    """
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
        print(f"Usage : {sys.argv[0]} <chemin vers outlineexplorer/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Outline non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Outline", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Outline : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Outline applique ({applied} bloc(s)) : barre reduite a Tout replier/Tout "
          f"deplier, le reste dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
