#!/usr/bin/env python3
"""Ajoute a Spyder une option en ligne de commande "--run-file FICHIER".

    spyder --run-file /chemin/vers/jeu.py
    spyder -r /chemin/vers/jeu.py          (forme courte ; -r etait libre, seuls -p et -w
                                            sont pris par Spyder)

Spyder ouvre alors le fichier dans l'editeur ET l'execute dans sa console IPython, comme
si l'utilisateur avait appuye sur F5, sans qu'aucune frappe soit necessaire.

POURQUOI
--------
Le developpement du greffon Pyxel (Commun/spyder_plugins/spyder_pyxel) bute sur un mur :
verifier qu'un jeu s'affiche bien dans le panneau demande d'appuyer sur F5, et rien ne
permet de simuler une frappe clavier sous Wayland - kdotool ne fait que du controle de
fenetre, il n'existe pas d'equivalent de "xdotool key". Chaque essai imposait donc une
intervention manuelle, y compris pour les allers-retours de mise au point les plus banals.

Les 22 options de Spyder (--workdir, --project, --connect-to-kernel...) n'en offrent
aucune qui execute un script. On l'ajoute donc, ce qui rend la boucle de test entierement
automatisable : lancer, capturer l'ecran, fermer.

CE QUE LE PATCH MODIFIE
-----------------------
Deux fichiers, par ajout et jamais par remplacement :

  app/cli_options.py   declare l'option (juste avant l'argument positionnel "files",
                       qui doit rester le dernier ajoute).
  app/mainwindow.py    a la fin de post_visible_setup(), ouvre le fichier dans l'editeur
                       puis demande a la console de l'executer.

Pourquoi post_visible_setup() : c'est la methode appelee une fois la fenetre affichee et
tous les greffons enregistres. Executer plus tot laisserait la console non encore creee -
c'est exactement l'ecueil rencontre avec l'option de configuration "startup/run_file", qui
ne declenche rien tant qu'aucune console n'existe.

L'execution passe par un QTimer.singleShot : post_visible_setup() s'execute pendant la
mise en place de l'interface, et la console a besoin que la boucle d'evenements tourne
pour terminer le demarrage de son noyau. Le delai laisse ce demarrage se faire ; l'appel
est de toute facon protege, un echec ne doit jamais empecher Spyder de s'ouvrir.

Usage : patch_spyder_run_file.py <cli_options.py> <mainwindow.py>

Localisation des points d'insertion via le module "ast" (structure du code, pas texte
brut). Echoue BRUYAMMENT (code 1) si un point d'ancrage est introuvable, plutot que de
deviner. Idempotent : ne fait rien si le marqueur est deja present.
"""

import ast
import sys

MARKER = "_smartos_run_file"

CLI_PATCH = '''    # Ajout SmartOS (_smartos_run_file) : executer un script au demarrage, sans frappe
    # clavier. Cf. Commun/scripts/patch_spyder_run_file.py
    parser.add_argument(
        '-r', '--run-file',
        type=str,
        dest="run_file",
        default=None,
        help="Ouvrir ce fichier et l'executer dans la console au demarrage"
    )

'''

MAINWINDOW_PATCH = '''
        # Ajout SmartOS (_smartos_run_file) : --run-file <script> ouvre le fichier et
        # l'execute, comme un F5, sans qu'aucune frappe soit necessaire. Sert a tester
        # automatiquement les greffons qui affichent le resultat d'une execution (Pyxel).
        # Cf. Commun/scripts/patch_spyder_run_file.py
        _smartos_target = getattr(self._cli_options, 'run_file', None)
        if _smartos_target:
            from qtpy.QtCore import QTimer as _SmartosTimer

            def _smartos_run_file():
                try:
                    from spyder.api.plugins import Plugins as _SmartosPlugins

                    editor = self.get_plugin(_SmartosPlugins.Editor, error=False)
                    if editor is not None:
                        editor.load(_smartos_target)
                    console = self.get_plugin(
                        _SmartosPlugins.IPythonConsole, error=False)
                    if console is not None:
                        # runfile() est la fonction que Spyder utilise lui-meme pour F5 :
                        # meme repertoire de travail, meme espace de noms.
                        console.execute_code(
                            "runfile({!r}, wdir={!r})".format(
                                _smartos_target,
                                __import__('os').path.dirname(_smartos_target)))
                except Exception:
                    # Une option de confort ne doit jamais empecher Spyder de s'ouvrir.
                    import traceback
                    traceback.print_exc()

            # La console termine le demarrage de son noyau dans la boucle d'evenements :
            # on lui laisse le temps plutot que d'appeler immediatement.
            _SmartosTimer.singleShot(8000, _smartos_run_file)
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
    # L'argument positionnel "files" doit rester le dernier declare : on insere juste
    # avant lui.
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
        print("  spyder --run-file <script.py> ouvre et execute le fichier au demarrage")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
