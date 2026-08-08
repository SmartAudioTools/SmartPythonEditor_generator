#!/usr/bin/env python3
"""Ajoute a Spyder une option "--gui-exec FICHIER" (execute un script dans le PROCESSUS GUI).

    spyder --gui-exec /chemin/vers/sonde.py

POURQUOI
--------
--run-file (patch_spyder_run_file.py) execute le script dans le noyau IPython de la console,
qui tourne dans un PROCESSUS SEPARE (spyder_kernels) : le script n'a donc pas acces a
PLUGIN_REGISTRY ni aux widgets de plugins du processus GUI (verifie le 24/07/2026 : le registre
y est toujours vide). Pour piloter/inspecter les plugins depuis un script autonome (sans clic,
cf. patch_spyder_profile_file.py), il faut executer le code DANS le processus GUI - c'est ce que
fait ce patch, en generalisant le mecanisme de patch_spyder_profile_file.py au lieu de coder en
dur une action.

CE QUE LE PATCH MODIFIE (par ajout, jamais par remplacement ; idempotent via _smartos_gui_exec)
  app/cli_options.py   declare --gui-exec, juste avant l'argument positionnel "files".
  app/mainwindow.py    a la fin de post_visible_setup(), exec() le fichier avec `main` (self) et
                       `app` (QApplication.instance()) dans son namespace, via QTimer.singleShot.

Usage : patch_spyder_gui_exec.py <cli_options.py> <mainwindow.py>
"""

import ast
import sys

MARKER = "_smartos_gui_exec"

CLI_PATCH = '''    # Ajout SmartOS (_smartos_gui_exec) : executer un script dans le processus GUI au
    # demarrage, sans frappe. Cf. Commun/scripts/patch_spyder_gui_exec.py
    parser.add_argument(
        '--gui-exec',
        type=str,
        dest="gui_exec",
        default=None,
        help="Executer ce script Python dans le processus GUI au demarrage "
             "(namespace : main, app)"
    )

'''

MAINWINDOW_PATCH = '''
        # Ajout SmartOS (_smartos_gui_exec) : --gui-exec <script> execute le script DANS le
        # processus GUI (contrairement a --run-file, qui tourne dans le noyau IPython separe),
        # avec acces a `main` (self) et `app`. Sert a inspecter/piloter les plugins en
        # autonomie. Cf. Commun/scripts/patch_spyder_gui_exec.py
        _smartos_gui_exec_target = getattr(self._cli_options, 'gui_exec', None)
        if _smartos_gui_exec_target:
            from qtpy.QtCore import QTimer as _SmartosGuiExecTimer
            from qtpy.QtWidgets import QApplication as _SmartosGuiExecApp

            def _smartos_gui_exec():
                try:
                    with open(_smartos_gui_exec_target, encoding='utf-8') as _f:
                        _code = _f.read()
                    exec(compile(_code, _smartos_gui_exec_target, 'exec'), {
                        'main': self,
                        'app': _SmartosGuiExecApp.instance(),
                        '__name__': '__main__',
                    })
                except Exception:
                    # Une option de test ne doit jamais empecher Spyder de s'ouvrir.
                    import traceback
                    traceback.print_exc()

            _SmartosGuiExecTimer.singleShot(3000, _smartos_gui_exec)
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
        print("  spyder --gui-exec <script.py> execute le script dans le processus GUI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
