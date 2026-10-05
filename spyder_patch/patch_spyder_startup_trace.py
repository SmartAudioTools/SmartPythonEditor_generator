#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Branche le chronometre de demarrage SmartOS dans spyder/app/start.py.

Un seul point d'appel, au debut de main() : si SMARTOS_STARTUP_TRACE=<chemin.json> est
defini, le module smartos_startup_trace (depose a la racine du fork, comme
smartos_spyder_actions.py) pose ses reperes et ecrit la trace. Sans la variable, le cout est
un os.environ.get.

Une variable d'environnement plutot qu'une option de ligne de commande : la trace doit
demarrer AVANT l'analyse des arguments, et se transmet telle quelle a travers le lanceur.

Usage : patch_spyder_startup_trace.py <spyder/app/start.py>
Idempotent (marqueur _smartos_startup_trace), echoue bruyamment si main() est introuvable.
"""

import ast
import sys

MARKER = "_smartos_startup_trace"

PATCH = '''    # Ajout SmartOS (_smartos_startup_trace) : chronometre de demarrage, actif seulement
    # si SMARTOS_STARTUP_TRACE=<chemin.json> est defini (voir smartos_startup_trace.py).
    if os.environ.get('SMARTOS_STARTUP_TRACE'):
        try:
            import smartos_startup_trace as _smartos_startup_trace
            _smartos_startup_trace.demarrer()
        except Exception:
            # Une option de mesure ne doit jamais empecher Spyder de s'ouvrir.
            import traceback
            traceback.print_exc()

'''


def patch_start(path):
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : {path} illisible ({error})", file=sys.stderr)
        return False

    function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            function = node
    if function is None:
        print(f"ERREUR : fonction main() introuvable dans {path}", file=sys.stderr)
        return False

    body = function.body
    first = body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str) and len(body) > 1):
        first = body[1]  # apres la docstring

    lines = source.splitlines(keepends=True)
    anchor = first.lineno - 1
    result = "".join(lines[:anchor]) + PATCH + "".join(lines[anchor:])
    try:
        ast.parse(result)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    open(path, "w", encoding="utf-8").write(result)
    print(f"Patche : {path}")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/app/start.py>", file=sys.stderr)
        return 1
    return 0 if patch_start(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
