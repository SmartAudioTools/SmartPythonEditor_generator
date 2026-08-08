#!/usr/bin/env python3
"""Patch spyder/plugins/debugger/widgets/main_widget.py : allege la barre du dock "Debogueur" en
deplaçant cinq de ses boutons dans son menu burger (options).

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt, arbitrage de l'utilisateur le 26/07/2026.

CONSTAT. C'est, en nombre, la barre la plus chargee de Spyder : TREIZE elements. Le dock est masque
par defaut sur cette machine (cf. patch_spyder_hide_docks.py), mais il reste reaffichable par
Affichage > Panneaux, et le nettoyage vaut aussi pour lui.

CHANGEMENT. Cinq boutons passent dans le burger, choisis pour deux raisons distinctes :
  - enter_debug_action, interrupt_and_debug_action, inspect_action (section InteractWithConsole) :
    ce sont des points d'ENTREE dans le debogage - "Demarrer le debogage apres la derniere erreur",
    "Interrompre l'execution et demarrer le debogueur", "Inspecter l'execution" - qu'on declenche
    une fois, depuis le menu Deboguer, pas depuis le panneau de la pile d'appels ;
  - goto_cursor_action ("Afficher le fichier et la ligne ou le debogueur est place") et
    toggle_breakpoints_action ("Afficher les points d'arret") : navigation et bascule d'affichage.

La barre garde les cinq commandes de PAS-A-PAS (Deboguer la ligne courante, Executer jusqu'au
prochain point d'arret, Entrer dans la fonction, Executer jusqu'au retour, Arreter le debogage) et
"Rechercher dans les frames" - c'est-a-dire ce qu'on utilise pendant une session de debogage, quand
la main est justement dans ce panneau. Le STRETCHER reste : il pousse le reste vers la gauche.

Les actions restent CREEES et enregistrees (update_actions() les retrouve par get_action) : on ne
change QUE ou elles s'affichent.

Usage : patch_spyder_debugger_toolbar.py <chemin vers debugger/widgets/main_widget.py installe>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja en place, de sorte
qu'une passe ulterieure puisse ajouter un bloc sans rien defaire. Re-parse avant ecriture, echec
BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # 1. Menu burger : accueillir les cinq boutons retires de la barre, en deux sections.
    (
        "les points d'entree dans le debogage",
        '''        # Options menu
        options_menu = self.get_options_menu()
        for item in [exclude_internal_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=DebuggerWidgetOptionsMenuSections.Display,
            )''',
        '''        # Options menu
        options_menu = self.get_options_menu()

        # SmartOS (patch_spyder_debugger_toolbar.py) : les points d'entree dans le debogage,
        # retires de la barre. On les declenche une fois, et le menu Deboguer les propose deja.
        for item in [
            enter_debug_action,
            interrupt_and_debug_action,
            inspect_action,
        ]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section="smartos_enter_debug",
            )

        # SmartOS : navigation et bascule d'affichage, retirees de la barre elles aussi.
        for item in [goto_cursor_action, toggle_breakpoints_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section="smartos_debugger_view",
            )

        for item in [exclude_internal_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=DebuggerWidgetOptionsMenuSections.Display,
            )''',
    ),
    # 2. Barre : supprimer la section InteractWithConsole.
    (
        "la section InteractWithConsole est vide",
        '''        for item in [
            enter_debug_action,
            interrupt_and_debug_action,
            inspect_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.InteractWithConsole,
            )''',
        '''        # SmartOS (patch_spyder_debugger_toolbar.py) : la section InteractWithConsole est vide,
        # ses trois actions sont passees dans le menu burger (cf. plus haut).''',
    ),
    # 3. Barre : ne garder que "Rechercher dans les frames" et l'etirement dans la section Extras.
    (
        "la section Extras ne garde que la",
        '''        for item in [
            goto_cursor_action,
            search_action,
            stretcher,
            toggle_breakpoints_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.Extras,
            )''',
        '''        # SmartOS (patch_spyder_debugger_toolbar.py) : la section Extras ne garde que la
        # recherche et l'etirement (qui pousse le pas-a-pas vers la gauche) ; "Afficher le fichier
        # et la ligne du debogueur" et "Afficher les points d'arret" sont dans le menu burger.
        for item in [
            search_action,
            stretcher,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.Extras,
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
        print(f"Usage : {sys.argv[0]} <chemin vers debugger/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Debogueur non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Debogueur", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Debogueur : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Debogueur applique ({applied} bloc(s)) : cinq boutons deplaces dans le menu "
          f"burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
