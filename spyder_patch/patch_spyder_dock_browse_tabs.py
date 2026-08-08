#!/usr/bin/env python3
"""Patch spyder/widgets/tabs.py pour masquer le bouton "Browse tabs" (naviguer entre les onglets)
present sur TOUS les docks/panneaux a onglets de Spyder, y compris ceux des plugins.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "Docks", demande explicite de
l'utilisateur) : chaque panneau a onglets affiche, dans le coin haut-gauche de sa barre d'onglets,
un bouton "Browse tabs" (icone 'browse_tab' = mdi.tab, infobulle "Browse tabs") qui ouvre un menu
listant tous les onglets pour y sauter. L'utilisateur ne s'en sert pas et veut le supprimer partout.

Ce bouton (self.browse_button) est cree dans BaseTabs.__init__ (spyder/widgets/tabs.py) et ajoute
au coin haut-gauche. BaseTabs est la classe de base de tous les widgets a onglets de Spyder (editeur
via EditorStack, console IPython, historique, et tout plugin dont le widget principal contient un
Tabs) : le masquer ICI le masque partout d'un coup - "sur tous les dock (dont les plugins)".

Ce N'EST PAS le bouton d'options (self._options_button, icone 'tooloptions', le "hamburger" a
droite), qui reste en place, ni les fleches de defilement < > que Qt ajoute a la barre d'onglets des
docks empiles en cas de debordement (celles-la sont dans widgets/dock.py, un autre mecanisme).

Le bouton est masque (hide()) plutot que supprime : le widget existe deja et son code de mise a jour
(update_browse_tabs_menu, branche sur aboutToShow) reste inerte tant qu'il est cache ; un widget
cache dans un layout de coin ne prend aucune place. On garde ainsi la modification minimale et sans
effet de bord sur le reste de la logique de BaseTabs.

Usage : patch_spyder_dock_browse_tabs.py <chemin vers widgets/tabs.py installe>

Localisation du point d'insertion via le module "ast" (structure du code, pas texte brut) : retrouve
BaseTabs.__init__ par son nom, quels que soient les commentaires/blancs/l'ordre autour. Le patch
AJOUTE une instruction a la fin de la methode (self.browse_button, attribut d'instance pose plus
haut dans cette meme methode, existe donc a coup sur a ce point). Echoue BRUYAMMENT (code de sortie
1) si la methode n'est pas trouvee. Idempotent : ne fait rien si le marqueur est deja present.
"""
import ast
import sys

MARKER = 'Bouton "Browse tabs" masque'
PATCH = '''
        # Bouton "Browse tabs" masque (ajout SmartOS, cf.
        # Commun/scripts/patch_spyder_dock_browse_tabs.py) : navigation entre onglets jugee
        # inutile, retiree de tous les panneaux a onglets d'un coup (demande utilisateur).
        if hasattr(self, "browse_button"):
            self.browse_button.hide()
'''


def find_method(tree, class_name, method_name):
    """Retourne le noeud AST de <class_name>.<method_name>, ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and sub.name == method_name:
                    return sub
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers widgets/tabs.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"tabs.py illisible ({error}) - patch bouton Browse tabs non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch bouton Browse tabs Spyder deja applique.")
        return 0

    tree = ast.parse(source)
    method = find_method(tree, "BaseTabs", "__init__")
    if method is None:
        print(f"BaseTabs.__init__ introuvable dans {path} - Spyder a peut-etre restructure son "
              "code, patch bouton Browse tabs non applique.", file=sys.stderr)
        return 1

    lines = source.splitlines(keepends=True)
    lines.insert(method.body[-1].end_lineno, PATCH)
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le tabs.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch bouton Browse tabs applique : bouton masque sur tous les panneaux ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
