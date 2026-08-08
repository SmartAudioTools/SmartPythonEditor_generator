#!/usr/bin/env python3
"""Ajoute a Spyder une option "--actions FICHIER.json" (joue un SCENARIO au demarrage).

    spyder --actions /chemin/vers/scenario.json

POURQUOI, ALORS QUE --gui-exec EXISTE DEJA
------------------------------------------
--gui-exec (patch_spyder_gui_exec.py) execute UN script dans le processus GUI, une fois, apres
un delai fixe. Tant qu'un test tenait en une action, ca suffisait. Des qu'il en faut plusieurs -
ouvrir un fichier, attendre que le noyau reponde, profiler, attendre l'artefact, capturer,
fermer - il faut SEQUENCER, donc attendre des conditions sans bloquer la boucle d'evenements de
Qt : un `while ... : time.sleep()` dans --gui-exec gelerait Spyder, donc empecherait justement
l'evenement qu'on attend d'arriver. C'est la raison d'etre de --actions, demande par
l'utilisateur le 24/07/2026 (TODO - Spyder - line profiler.txt, « IDEE UTILISATEUR »).

LE PATCH EST VOLONTAIREMENT MINUSCULE
-------------------------------------
Toute la logique vit dans Commun/scripts/smartos_spyder_actions.py, deploye a cote de Spyder
dans site-packages. Un patch de site-packages est reapplique a chaque mise a jour du paquet et
doit survivre a des changements de code amont : moins il contient de lignes, moins il a de
chances de casser. Ici il se reduit a "importer le moteur et l'appeler" - et le moteur, lui,
est un module Python ordinaire, testable seul (Commun/scripts/test_smartos_spyder_actions.py
tourne SANS Spyder).

CE QUE LE PATCH MODIFIE (par ajout, jamais par remplacement ; idempotent via _smartos_actions)
  app/cli_options.py   declare --actions, juste avant l'argument positionnel "files".
  app/mainwindow.py    a la fin de post_visible_setup(), demarre le moteur de scenario.

Usage : patch_spyder_actions.py <cli_options.py> <mainwindow.py>
"""

import ast
import sys

MARKER = "_smartos_actions"

CLI_PATCH = '''    # Ajout SmartOS (_smartos_actions) : jouer un scenario d'actions au demarrage, sans
    # clic ni frappe. Cf. Commun/scripts/patch_spyder_actions.py
    parser.add_argument(
        '--actions',
        type=str,
        dest="actions",
        default=None,
        help="Jouer ce scenario JSON au demarrage (ouvrir, profiler, attendre, capturer, "
             "fermer) et ecrire un rapport"
    )

'''

MAINWINDOW_PATCH = '''
        # Ajout SmartOS (_smartos_actions) : --actions <scenario.json> joue une suite d'actions
        # dans le processus GUI, en scrutant par QTimer (donc SANS bloquer la boucle
        # d'evenements : une attente qui la bloquerait empecherait ce qu'elle attend d'arriver).
        # Toute la logique est dans le module smartos_spyder_actions, depose a cote de Spyder.
        # Cf. Commun/scripts/patch_spyder_actions.py
        _smartos_actions_target = getattr(self._cli_options, 'actions', None)
        if _smartos_actions_target:
            from qtpy.QtCore import QTimer as _SmartosActionsTimer
            from qtpy.QtWidgets import QApplication as _SmartosActionsApp

            def _smartos_actions_demarrer():
                try:
                    import smartos_spyder_actions as _smartos_actions_moteur
                    _smartos_actions_moteur.demarrer(
                        self, _SmartosActionsApp.instance(), _smartos_actions_target)
                except Exception:
                    # Une option de test ne doit jamais empecher Spyder de s'ouvrir.
                    import traceback
                    traceback.print_exc()

            # Court : le moteur a sa propre temporisation d'amorcage ("depart" du scenario),
            # reglable par scenario - c'est la qu'on attend le noyau, pas ici.
            _SmartosActionsTimer.singleShot(500, _smartos_actions_demarrer)
'''


def find_function(tree, name, class_name=None):
    for node in ast.walk(tree):
        if class_name is not None:
            if not (isinstance(node, ast.ClassDef) and node.name == class_name):
                continue
            children = node.body
        else:
            children = [node]
        for child in children:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and child.name == name:
                return child
    return None


def patch_cli(path):
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    lines = source.splitlines(keepends=True)
    anchor = None
    for index, line in enumerate(lines):
        if "parser.add_argument('files'" in line:
            anchor = index
            break
    if anchor is None:
        print(f"ERREUR : parser.add_argument('files') introuvable dans {path}",
              file=sys.stderr)
        return False

    result = "".join(lines[:anchor]) + CLI_PATCH + "".join(lines[anchor:])
    try:
        ast.parse(result)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    open(path, "w", encoding="utf-8").write(result)
    print(f"Patche : {path}")
    return True


def patch_mainwindow(path):
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : {path} illisible ({error})", file=sys.stderr)
        return False

    function = find_function(tree, "post_visible_setup", "MainWindow")
    if function is None:
        print(f"ERREUR : MainWindow.post_visible_setup introuvable dans {path}",
              file=sys.stderr)
        return False

    last = function.body[-1]
    end_line = getattr(last, "end_lineno", last.lineno)

    lines = source.splitlines(keepends=True)
    result = "".join(lines[:end_line]) + MAINWINDOW_PATCH + "".join(lines[end_line:])
    try:
        ast.parse(result)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    open(path, "w", encoding="utf-8").write(result)
    print(f"Patche : {path}")
    return True


def main(argv):
    if len(argv) != 3:
        print(f"Usage : {argv[0]} <cli_options.py> <mainwindow.py>", file=sys.stderr)
        return 1
    ok = patch_cli(argv[1])
    ok = patch_mainwindow(argv[2]) and ok
    if ok:
        print("  spyder --actions <scenario.json> joue le scenario et ecrit son rapport")
        print("  (le module smartos_spyder_actions.py doit etre depose dans site-packages)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
