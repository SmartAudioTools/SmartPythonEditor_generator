#!/usr/bin/env python3
"""Patch spyder/plugins/application/plugin.py : ordre des boutons de la barre d'outils Fichier.

Contexte (demande utilisateur du 23/07/2026). Par defaut, la barre Fichier place les quatre
boutons dans l'ordre [Nouveau, Ouvrir, Enregistrer, Tout enregistrer]. L'utilisateur veut
[Ouvrir, Nouveau, Enregistrer, Tout enregistrer].

D'OU VIENT L'ORDRE
------------------
Application.on_toolbar_available() (ce fichier) ajoute les quatre actions a la barre Fichier dans
une boucle "for action in [container.new_action, container.open_action, container.save_action,
container.save_all_action]", toutes avec before=EditorWidgetActions.NewCell (l'action "Nouvelle
cellule" ajoutee par l'editeur). L'ordre AFFICHE suit exactement l'ordre de cette liste : dans
SpyderToolbar.add_item (spyder/api/widgets/toolbars.py), les quatre tombent dans la meme section et
chaque insertion "before NewCell" se fait juste avant NewCell, a la suite des precedentes - verifie
en lisant l'algorithme, et independant de l'ordre de disponibilite des plugins Application/Editor
(le cas ou NewCell n'existe pas encore passe par _pending_items, rejoue dans le meme ordre). Il
suffit donc de reordonner la liste ; on la reecrit en [open, new, save, save_all].

CE QUE LE PATCH MODIFIE
  Remplace la methode Application.on_toolbar_available en entier (le decorateur @on_plugin_available
  qui la precede n'est PAS touche : ast situe la methode a sa ligne "def", decorateur exclu).

Localisation par le module "ast" (find_method_range, comme patch_spyder_debug_toolbar_gap.py),
JAMAIS par recherche de texte : cette meme liste de quatre actions reapparait ailleurs dans le
fichier (menu Fichier, on_shutdown), un remplacement textuel global les toucherait a tort.
Idempotent (marqueur). Re-parse avant ecriture ; echoue BRUYAMMENT (code 1) si la methode est
introuvable - jamais deviner.

Usage : patch_spyder_file_toolbar_order.py <chemin vers application/plugin.py installe>
"""
import ast
import sys

MARKER = "patch_spyder_file_toolbar_order.py"

NEW_ON_TOOLBAR = '''    def on_toolbar_available(self):
        # SmartOS (cf. Commun/scripts/patch_spyder_file_toolbar_order.py) : ordre des boutons de la
        # barre Fichier passe de [Nouveau, Ouvrir, Enregistrer, Tout enregistrer] a
        # [Ouvrir, Nouveau, Enregistrer, Tout enregistrer] (demande utilisateur). Les quatre sont
        # ajoutes before=NewCell dans la meme section : l'ordre d'affichage suit l'ordre de cette
        # liste (cf. SpyderToolbar.add_item), il suffit donc de la reordonner.
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        for action in [
            container.open_action,
            container.new_action,
            container.save_action,
            container.save_all_action
        ]:
            toolbar.add_item_to_application_toolbar(
                action,
                toolbar_id=ApplicationToolbars.File,
                before=EditorWidgetActions.NewCell
            )
'''


def find_method_range(tree, class_name, method_name):
    """(lineno, end_lineno) 1-indexes inclus de la methode (ligne "def", decorateur exclu), ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and item.name == method_name:
                    return item.lineno, item.end_lineno
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers application/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"application/plugin.py illisible ({error}) - ordre barre Fichier non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch ordre barre Fichier deja applique.")
        return 0

    tree = ast.parse(source)
    cls = "Application"
    rng = find_method_range(tree, cls, "on_toolbar_available")
    if rng is None:
        print(f"{cls}.on_toolbar_available introuvable dans {path} - Spyder a peut-etre restructure "
              "son code, ordre barre Fichier non applique.", file=sys.stderr)
        return 1

    lines = source.splitlines(keepends=True)
    lines[rng[0] - 1:rng[1]] = [NEW_ON_TOOLBAR]
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le application/plugin.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch ordre barre Fichier applique : [Ouvrir, Nouveau, Enregistrer, Tout enregistrer] "
          f"({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
