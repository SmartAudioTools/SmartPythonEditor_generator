#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PySide6 relit le SOURCE de chaque module importe : lecture brute a la place (mainwindow.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 7, 05/10/2026). Des que PySide6 est
charge, shiboken remplace builtins.__import__ par son crochet (shibokensupport/feature.py), et
pour CHAQUE module importe ensuite il appelle

    pyside_feature_dict[nom] = 0 if _mod_uses_pyside(module) else -1

ou _mod_uses_pyside fait `"PySide6" in inspect.getsource(module)`. C'est ce qui permet a
`from __feature__ import snake_case` de ne s'appliquer qu'aux modules qui utilisent PySide.
Au demarrage de Spyder : 1393 inspect.getsource, donc 1393 fichiers lus, decodes, decoupes en
lignes ET GARDES dans linecache (profil du banc : 153 ms cumules sous cProfile, dont 39 ms de
lecture pure).

Le correctif garde la question et la reponse, et change seulement la facon de lire : le fichier
.py du module est lu en octets et on y cherche b"PySide6". Tout autre cas (pas de __file__, pas
un .py, fichier illisible) repart sur la fonction d'origine. Les sources ne sont plus gardees
dans linecache (qui les relit a la demande pour une trace d'erreur).

Ecart possible, accepte : un source dont le decodage echouait donnait False, et donne maintenant
la reponse de la recherche en octets.

Sans effet sous PyQt (le module shibokensupport.feature n'existe pas) ; rien n'est ecrit dans le
venv : le remplacement se fait en memoire, a chaque lancement, juste apres le premier import de
Qt (requirements.check_qt()).

Usage : patch_spyder_pyside_feature_rapide.py <spyder/app/mainwindow.py>
Idempotent (marqueur _smartos_pyside_feature_rapide), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_smartos_pyside_feature_rapide"
ANCRE = "requirements.check_qt()"

BLOC = '''

# ---- SmartOS (_smartos_pyside_feature_rapide) : PySide6 ne relit plus le source des modules ----
# Son crochet d'import faisait inspect.getsource() sur chaque module importe (1393 au demarrage)
# pour y chercher "PySide6". Meme question, lecture brute du fichier. Voir
# spyder_patch/patch_spyder_pyside_feature_rapide.py du generator.
def _smartos_pyside_feature_rapide():
    feature = sys.modules.get("shibokensupport.feature")
    amont = getattr(feature, "_mod_uses_pyside", None)
    if amont is None or getattr(amont, "_smartos", False):
        return

    def _mod_uses_pyside(module):
        fichier = getattr(module, "__file__", None)
        if not isinstance(fichier, str) or not fichier.endswith(".py"):
            return amont(module)
        try:
            with open(fichier, "rb") as source:
                return b"PySide6" in source.read()
        except OSError:
            return amont(module)

    _mod_uses_pyside._smartos = True
    feature._mod_uses_pyside = _mod_uses_pyside


_smartos_pyside_feature_rapide()
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR in source:
        print(f"Deja patche : {chemin}")
        return True
    arbre = ast.parse(source)
    lignes = source.splitlines(keepends=True)
    ancres = [n for n in arbre.body if isinstance(n, ast.Expr)
              and lignes[n.lineno - 1].strip() == ANCRE and n.lineno == n.end_lineno]
    noms = {alias.asname or alias.name for n in arbre.body
            if isinstance(n, ast.Import) and n.lineno < (ancres[0].lineno if ancres else 0)
            for alias in n.names}
    if len(ancres) != 1 or "sys" not in noms:
        print(f"ERREUR : l'appel `{ANCRE}` (unique, au niveau du module, apres `import sys`) "
              f"est introuvable dans {chemin} - la forme amont a change.", file=sys.stderr)
        return False
    fin = ancres[0].end_lineno
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
        print(f"Usage : {argv[0]} <spyder/app/mainwindow.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
