#!/usr/bin/env python3
"""Ajoute a Spyder une option "--profile-file FICHIER" (declenche le profilage au demarrage).

    spyder --profile-file /chemin/vers/jeu.py

Spyder ouvre le fichier puis lance sur lui le run du Line Profiler - qui, depuis le profilage
COMBINE (cf. le fork du greffon spyder-line-profiler (depot SmartPythonEditorPlugins/spyder_line_profiler), WIDGETS_CPROFILE_WRAP), execute cProfile ET
kernprof en une seule fois et alimente les DEUX panneaux (Line Profiler + Profileur integre).

POURQUOI
--------
Meme raison que --run-file (patch_spyder_run_file.py) : sous Wayland, rien ne simule un clic ni
une frappe (kdotool ne fait que du controle de fenetre). Pour tester le profilage combine en
autonomie, il faut pouvoir le declencher depuis la ligne de commande. On declenche directement
le run du Line Profiler (get_widget().analyze), qui est exactement ce que fera le reroutage du
bouton "Profiler le fichier" (point 3) une fois pose.

CE QUE LE PATCH MODIFIE (par ajout, jamais par remplacement ; idempotent via _smartos_profile_file)
  app/cli_options.py   declare --profile-file, juste avant l'argument positionnel "files".
  app/mainwindow.py    a la fin de post_visible_setup(), ouvre le fichier et lance le profilage,
                       via QTimer.singleShot pour laisser la console demarrer son noyau.

Usage : patch_spyder_profile_file.py <cli_options.py> <mainwindow.py>
"""

import ast
import sys

MARKER = "_smartos_profile_file"

CLI_PATCH = '''    # Ajout SmartOS (_smartos_profile_file) : profiler un fichier au demarrage, sans clic.
    # Cf. Commun/scripts/patch_spyder_profile_file.py
    parser.add_argument(
        '--profile-file',
        type=str,
        dest="profile_file",
        default=None,
        help="Ouvrir ce fichier et lancer le profilage combine au demarrage"
    )

'''

MAINWINDOW_PATCH = '''
        # Ajout SmartOS (_smartos_profile_file) : --profile-file <script> ouvre le fichier et
        # lance le run du Line Profiler (profilage combine cProfile + lignes), sans frappe.
        # Sert a tester le profilage combine en autonomie. Cf.
        # Commun/scripts/patch_spyder_profile_file.py
        _smartos_prof_target = getattr(self._cli_options, 'profile_file', None)
        if _smartos_prof_target:
            from qtpy.QtCore import QTimer as _SmartosProfTimer

            def _smartos_profile_file():
                try:
                    import os as _smartos_os
                    from spyder.api.plugins import Plugins as _SmartosPlugins

                    editor = self.get_plugin(_SmartosPlugins.Editor, error=False)
                    if editor is not None:
                        editor.load(_smartos_prof_target)
                    lp = self.get_plugin('spyder_line_profiler', error=False)
                    if lp is not None:
                        lp.get_widget().analyze(
                            _smartos_prof_target,
                            wdir=_smartos_os.path.dirname(_smartos_prof_target))
                except Exception:
                    # Une option de test ne doit jamais empecher Spyder de s'ouvrir.
                    import traceback
                    traceback.print_exc()

            # La console termine le demarrage de son noyau dans la boucle d'evenements : on lui
            # laisse le temps (un peu plus que --run-file, le profilage lancant un sous-processus).
            _SmartosProfTimer.singleShot(10000, _smartos_profile_file)
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
        print("  spyder --profile-file <script.py> profile le fichier au demarrage")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
