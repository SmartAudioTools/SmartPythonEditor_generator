#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/status.py : empeche le widget d'interpreteur
(PythonEnvironmentStatus, ID 'pythonenv_status') de se REAFFICHER au demarrage d'un noyau.

Contexte. Le selecteur d'interpreteur a ete deplace dans la barre d'outils togglable "Interpreteur"
(greffon spyder_interpreter_toolbar), et le widget a ete retire de la barre de statut
(patch_spyder_statusbar_hide.py, bloc pythonenv_status : il est exclu de _organize_status_widgets,
donc retire de la barre). PROBLEME constate en direct : a chaque demarrage de noyau, la methode
PythonEnvironmentStatus.on_kernel_start appelle self.show(). Comme le widget n'est plus dans la barre
de statut (il est parente au widget principal de la console), ce show() le fait apparaitre en
ORPHELIN, tronque a une parenthese ")" en bas a gauche.

CORRECTIF : dans on_kernel_start, remplacer le self.show() final par self.hide(). On CONSERVE le
self.set_shellwidget(shellwidget) juste au-dessus : le widget reste connecte au noyau, donc
update_status et son signal sig_interpreter_changed continuent de fonctionner (le plugin console
propage l'info via widget.sig_interpreter_changed -> propagation intacte). On ne fait que ne PAS le
montrer. Le widget reste enregistre dans STATUS_WIDGETS (get_status_widget/remove_status_widget au
teardown du plugin console fonctionnent toujours).

Usage : patch_spyder_pythonenv_keep_hidden.py <chemin vers ipythonconsole/widgets/status.py installe>

Le remplacement est SCOPE a PythonEnvironmentStatus.on_kernel_start (via le module ast) pour ne pas
toucher au self.show() de MatplotlibStatus.on_kernel_start. Idempotent (marqueur). Re-parse avant
ecriture ; echoue BRUYAMMENT (code 1) si la methode ou le self.show() attendu est introuvable.
"""
import ast
import sys

MARKER = "pythonenv_status maintenu masque (SmartOS"
OLD_LINE = "            self.show()\n"
NEW_BLOCK = (
    "            # pythonenv_status maintenu masque (SmartOS, cf.\n"
    "            # Commun/scripts/patch_spyder_pythonenv_keep_hidden.py) : le selecteur\n"
    "            # d'interpreteur est desormais dans la barre d'outils togglable \"Interpreteur\"\n"
    "            # (greffon spyder_interpreter_toolbar) et le widget a ete retire de la barre de\n"
    "            # statut. set_shellwidget (ci-dessus) reste appele -> update_status et\n"
    "            # sig_interpreter_changed fonctionnent toujours ; on ne montre simplement pas le\n"
    "            # widget, sinon il apparait en orphelin (\")\" tronque) hors de la barre de statut.\n"
    "            self.hide()\n"
)


def find_method_range(tree, class_name, method_name):
    """(lineno, end_lineno) 1-indexes inclus de <class_name>.<method_name>, ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and item.name == method_name:
                    return item.lineno, item.end_lineno
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers ipythonconsole/widgets/status.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"status.py illisible ({error}) - patch masquage pythonenv_status non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch maintien masque de pythonenv_status deja applique.")
        return 0

    rng = find_method_range(ast.parse(source),
                            "PythonEnvironmentStatus", "on_kernel_start")
    if rng is None:
        print("PythonEnvironmentStatus.on_kernel_start introuvable dans status.py - Spyder a "
              "peut-etre restructure son code, patch non applique.", file=sys.stderr)
        return 1

    start, end = rng
    lines = source.splitlines(keepends=True)
    # Chercher le self.show() UNIQUEMENT dans la plage de la methode ciblee (le self.show() de
    # MatplotlibStatus.on_kernel_start ne doit pas etre touche).
    cible = None
    for i in range(start - 1, end):
        if lines[i] == OLD_LINE:
            cible = i
            break
    if cible is None:
        print("'self.show()' introuvable dans PythonEnvironmentStatus.on_kernel_start - Spyder a "
              "peut-etre change cette methode, patch non applique.", file=sys.stderr)
        return 1

    lines[cible] = NEW_BLOCK
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le status.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch maintien masque de pythonenv_status applique ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
