#!/usr/bin/env python3
"""Patch spyder/plugins/findinfiles/widgets/main_widget.py : les trois bascules de la barre du dock
"Recherche" passent dans son menu burger.

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt, arbitrage de l'utilisateur le 26/07/2026 (qui a tranche pour le deplacement apres
que je l'avais deconseille - Expression reguliere et Sensible a la casse se rebasculent en cours de
recherche).

CONSTAT. La barre du dock portait le champ de saisie, le bouton Rechercher et TROIS bascules -
Expression reguliere, Sensible a la casse, Afficher les options avancees - dans un dock deja etroit
qui empile par ailleurs deux autres barres (Exclure, et Rechercher dans). Le menu burger, lui, ne
contenait qu'une seule entree : "Definir le nombre maximum de resultats".

CHANGEMENT. La barre ne garde que le CHAMP DE SAISIE et le bouton Rechercher - de quoi taper une
recherche et la lancer. Les trois bascules rejoignent le burger, en tete et dans leur propre section
(donc separees de "Definir le nombre maximum de resultats"). Elles restent cochables et leur etat
reste persiste dans la configuration : ce sont des actions toggled=True liees a une option
(search_text_regexp, case_sensitive, more_options), rien de cet enchainement ne depend de leur
emplacement.

CONSEQUENCE ASSUMEE : l'etat de ces trois bascules n'est plus visible d'un coup d'oeil, il faut
ouvrir le burger. "Afficher les options avancees" reste toutefois lisible autrement - c'est elle qui
montre ou cache la barre "Exclure".

Usage : patch_spyder_findinfiles_toolbar.py <chemin vers findinfiles/widgets/main_widget.py installe>

Remplacements de blocs exacts, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_findinfiles_toolbar.py"

# Liste de (ancien, nouveau). Tous doivent matcher exactement et une seule fois.
PAIRS = [
    # 1. Barre : ne garder que le champ de saisie et le bouton Rechercher.
    (
        '''        for item in [self.search_text_edit, self.find_action,
                     self.search_regexp_action, self.case_action,
                     self.more_options_action]:''',
        '''        # SmartOS (patch_spyder_findinfiles_toolbar.py) : la barre ne garde que le champ de
        # saisie et le bouton Rechercher. Les trois bascules (Expression reguliere, Sensible a la
        # casse, Afficher les options avancees) partent dans le menu burger, cf. plus bas.
        for item in [self.search_text_edit, self.find_action]:''',
    ),
    # 2. Menu burger : les trois bascules en tete, dans leur propre section.
    (
        '''        menu = self.get_options_menu()
        self.add_item_to_menu(
            self.set_max_results_action,
            menu=menu,
        )''',
        '''        menu = self.get_options_menu()

        # SmartOS (patch_spyder_findinfiles_toolbar.py) : les trois bascules retirees de la barre.
        # Section propre, declaree AVANT celle de "Definir le nombre maximum de resultats" : les
        # sections sont rendues dans leur ordre de premiere utilisation, et separees par un trait.
        for item in [self.search_regexp_action, self.case_action,
                     self.more_options_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section="smartos_search_options",
            )

        self.add_item_to_menu(
            self.set_max_results_action,
            menu=menu,
        )''',
    ),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers findinfiles/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Recherche non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch barre Recherche deja applique.")
        return 0

    for old, _new in PAIRS:
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch barre Recherche non applique. "
                  f"Bloc:\n{old[:80]}...", file=sys.stderr)
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
    print(f"Patch barre Recherche applique : les trois bascules deplacees dans le menu burger "
          f"({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
