#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les points d'entree des paquets installes sont lus UNE fois pendant le demarrage (start.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 11, 05/10/2026).
importlib.metadata.entry_points() relit a chaque appel les metadonnees de tous les paquets du
venv (5 a 7 ms), et le demarrage l'appelle cinq fois : pygments (greffons de lexers, depuis
spyder.config.utils), spyder.app.find_plugins deux fois, le greffon de completion,
jupyter_client (provisionneurs de noyau). Mesure in situ, hors profileur : 29,8 ms au total.

Le correctif remplace importlib.metadata.entry_points, juste apres `import sys` de
spyder/app/start.py, par une fonction qui lit la liste complete une fois puis y fait la meme
selection (`entry_points(**params)` EST `entry_points().select(**params)` dans importlib.metadata
de Python 3.12). Le memo expire 20 secondes apres le lancement : ensuite chaque appel relit, comme
en amont (un paquet installe en cours de session est donc vu).

Usage : patch_spyder_points_entree_memo.py <spyder/app/start.py>
Idempotent (marqueur _smartos_points_entree_memo), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_smartos_points_entree_memo"
BLOC = '''
# ---- SmartOS (_smartos_points_entree_memo) : points d'entree lus une fois pendant le demarrage --
# Voir spyder_patch/patch_spyder_points_entree_memo.py du generator.
def _smartos_points_entree_memo():
    import importlib.metadata as metadata
    # Pas de « import time » litteral : le sed setproctitle de appliquer_correctifs_spyder.sh
    # vise ce texte dans ce fichier.
    from time import monotonic

    amont = metadata.entry_points
    fin = monotonic() + 20
    memo = []

    def entry_points(**params):
        if monotonic() > fin:
            memo.clear()
            return amont(**params)
        if not memo:
            memo.append(amont())
        return memo[0].select(**params)

    metadata.entry_points = entry_points


if sys.version_info[:2] == (3, 12):
    _smartos_points_entree_memo()
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR in source:
        print(f"Deja patche : {chemin}")
        return True
    lignes = source.splitlines(keepends=True)
    imports = [n for n in ast.parse(source).body if isinstance(n, ast.Import)
               and [a.name for a in n.names] == ["sys"]]
    if len(imports) != 1:
        print(f"ERREUR : `import sys` (unique, au niveau du module) est introuvable dans "
              f"{chemin} - la forme amont a change.", file=sys.stderr)
        return False
    fin = imports[0].end_lineno
    resultat = "".join(lignes[:fin]) + BLOC + "".join(lignes[fin:])
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/app/start.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
