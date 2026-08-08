#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/main_widget.py : vide la barre de coin du dock
"Console IPython", ses trois boutons partant (ou revenant) dans le menu burger.

Contexte : deuxieme passe du chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder -
cosmetique.txt ("pour chaque plugin, les boutons les moins utiles pourraient aller dans le menu
burger"), inventaire + arbitrage de l'utilisateur le 26/07/2026.

CONSTAT. Le coin portait quatre elements : Interrompre le noyau, Effacer la console, Se reconnecter
au noyau distant, et l'etiquette du temps ecoule. Or DEUX de ces boutons sont des DOUBLONS EXACTS
d'entrees deja presentes dans le menu burger - "Interrompre le noyau" (self.interrupt_action) et
"Se reconnecter au noyau distant" (self.reconnect_action), cette derniere n'ayant en plus de sens
que sur un noyau distant. Ce sont des objets distincts (create_toolbutton pour le coin,
create_action pour le menu) mais la meme commande.

DEUX CHANGEMENTS.
  1. "Effacer la console" rejoint le menu burger. L'action existait deja - self.clear_console_action,
     avec son raccourci clavier, dans le menu contextuel de la console - elle n'etait simplement pas
     dans le burger. On l'y ajoute en tete de la section Edit, devant Interrompre/Redemarrer.
  2. Le coin ne garde que l'etiquette du temps ecoule (et le bouton burger lui-meme). Les trois
     boutons restent CREES : update_actions() continue de piloter stop_button.setEnabled() et
     reconnect_button.setMaximumWidth() sans rien savoir de leur emplacement, et rien ne plante a
     appeler ces methodes sur un widget non affiche.

Usage : patch_spyder_ipython_toolbar.py <chemin vers ipythonconsole/widgets/main_widget.py installe>

Remplacements de blocs exacts, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_ipython_toolbar.py"

# Liste de (ancien, nouveau). Tous doivent matcher exactement et une seule fois.
PAIRS = [
    # 1. Menu burger : "Effacer la console" en tete de la section Edit.
    (
        # ⚠ L'ancre inclut la ligne "menu=options_menu" QUI SUIT la liste : la MEME liste de cinq
        # actions est reutilisee telle quelle un peu plus bas pour le menu contextuel des ONGLETS,
        # et une ancre reduite a la liste seule matchait donc deux fois.
        '''        for item in [
                self.interrupt_action,
                self.restart_action,
                self.reconnect_action,
                self.reset_action,
                self.rename_tab_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,''',
        '''        # SmartOS (patch_spyder_ipython_toolbar.py) : "Effacer la console" rejoint le menu
        # burger, d'ou elle etait absente alors qu'elle occupait un bouton dans le coin. L'action
        # existait deja (menu contextuel de la console, avec raccourci) : on ne la cree pas, on
        # l'ajoute simplement ici.
        for item in [
                self.clear_console_action,
                self.interrupt_action,
                self.restart_action,
                self.reconnect_action,
                self.reset_action,
                self.rename_tab_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,''',
    ),
    # 2. Coin : ne garder que l'etiquette du temps ecoule.
    (
        '''        # --- Add tab corner widgets.
        self.add_corner_widget(self.stop_button)
        self.add_corner_widget(self.clear_button)
        self.add_corner_widget(self.reconnect_button)
        self.add_corner_widget(self.time_label)''',
        '''        # --- Add tab corner widgets.
        # SmartOS (patch_spyder_ipython_toolbar.py) : le coin ne garde que l'etiquette du temps
        # ecoule. "Interrompre le noyau" et "Se reconnecter au noyau distant" etaient des doublons
        # exacts d'entrees deja presentes dans le menu burger (self.interrupt_action et
        # self.reconnect_action) ; "Effacer la console" y a ete ajoutee (cf. plus haut). Les trois
        # boutons restent crees : update_actions() les pilote encore (setEnabled, setMaximumWidth),
        # ce qui ne pose aucun probleme sur un widget non affiche.
        self.add_corner_widget(self.time_label)''',
    ),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers ipythonconsole/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch coin Console IPython non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch coin Console IPython deja applique.")
        return 0

    for old, _new in PAIRS:
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch coin Console IPython non applique. "
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
    print(f"Patch coin Console IPython applique : coin reduit au temps ecoule, Effacer la console "
          f"dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
