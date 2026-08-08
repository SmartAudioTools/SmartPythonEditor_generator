#!/usr/bin/env python3
"""Patch spyder/plugins/plots/widgets/main_widget.py : allege la barre du dock "Graphiques" en
deplaçant trois de ses boutons dans son menu burger (options).

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt, arbitrage de l'utilisateur le 26/07/2026.

CONSTAT. Douze elements dans la barre : cinq d'edition (Enregistrer le graphique, Enregistrer TOUS
les graphiques, Copier l'image, Supprimer le graphique, Supprimer TOUS les graphiques) puis le
groupe de zoom et de navigation. Le dock n'est pas affiche par defaut sur cette machine, mais il
reste reaffichable par Affichage > Panneaux.

CHANGEMENT. Trois boutons passent dans le burger :
  - "Enregistrer tous les graphiques..." et "Supprimer tous les graphiques" : les variantes EN MASSE
    des deux boutons voisins, rarement ce qu'on veut, et "supprimer tous" est destructif ;
  - "Copier l'image" : deja accessible par le menu contextuel du graphique (clic droit), qui recoit
    exactement Enregistrer / Copier / Supprimer.
La barre garde "Enregistrer le graphique sous...", "Supprimer le graphique" et tout le groupe de
zoom et de navigation (zoom, ajuster au panneau, precedent/suivant) - ce avec quoi on regarde
reellement une figure.

Les actions restent CREEES et enregistrees (update_actions() les retrouve par get_action) : on ne
change QUE ou elles s'affichent, et le menu contextuel du graphique n'est pas touche.

Usage : patch_spyder_plots_toolbar.py <chemin vers plots/widgets/main_widget.py installe>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja en place, de sorte
qu'une passe ulterieure puisse ajouter un bloc sans rien defaire. Re-parse avant ecriture, echec
BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # 1. Menu burger : accueillir les trois boutons retires de la barre, dans leur propre section.
    (
        "les variantes EN MASSE et la copie d'image",
        '''        for action in [
            self.mute_action,
            self.outline_action,
            self.set_max_plots_action,
        ]:
            self.add_item_to_menu(action, menu=options_menu)''',
        '''        # SmartOS (patch_spyder_plots_toolbar.py) : les variantes EN MASSE et la copie d'image,
        # retirees de la barre. Section propre, declaree en premier : les sections sont rendues dans
        # leur ordre de premiere utilisation, et separees par un trait.
        for action in [save_all_action, copy_action, remove_all_action]:
            self.add_item_to_menu(
                action, menu=options_menu, section="smartos_plots_data"
            )

        for action in [
            self.mute_action,
            self.outline_action,
            self.set_max_plots_action,
        ]:
            self.add_item_to_menu(action, menu=options_menu)''',
    ),
    # 2. Barre : ne garder que Enregistrer et Supprimer dans la section Edit.
    (
        "la section Edit ne garde que le graphique",
        '''        for item in [
            save_action,
            save_all_action,
            copy_action,
            remove_action,
            remove_all_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=PlotsWidgetMainToolbarSections.Edit,
            )''',
        '''        # SmartOS (patch_spyder_plots_toolbar.py) : la section Edit ne garde que le graphique
        # COURANT (enregistrer, supprimer). Les variantes "tous les graphiques" et "Copier l'image"
        # sont passees dans le menu burger (cf. plus haut).
        for item in [
            save_action,
            remove_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=PlotsWidgetMainToolbarSections.Edit,
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
        print(f"Usage : {sys.argv[0]} <chemin vers plots/widgets/main_widget.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Graphiques non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Graphiques", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Graphiques : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Graphiques applique ({applied} bloc(s)) : trois boutons deplaces dans le "
          f"menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
