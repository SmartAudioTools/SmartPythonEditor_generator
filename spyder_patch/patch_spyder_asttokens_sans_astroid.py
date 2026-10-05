#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""asttokens est importe SANS astroid dans le processus de l'interface (mainwindow.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 10, 05/10/2026). La premiere console
importe IPython.core.interactiveshell -> ultratb -> stack_data -> asttokens, et asttokens importe
astroid s'il est installe (asttokens/astroid_compat.py et util.py, dans des try/except), pour
savoir annoter aussi des arbres astroid. Dans l'interface personne ne lui en donne (stack_data
travaille sur des arbres `ast`), et rien d'autre n'y importe astroid : pylint tourne dans un
autre processus. Mesure isolee : import d'asttokens 36 ms et 201 modules avec astroid, 10 ms et
77 modules sans.

Le correctif importe asttokens des le chargement de mainwindow.py en faisant echouer, le temps
de cet import seulement, `import astroid` (entree None dans sys.modules, retiree aussitot) :
asttokens prend alors le chemin qu'il prevoit pour « astroid absent ». astroid reste importable
normalement ensuite. Si astroid ou asttokens est deja charge, ou si asttokens est absent, le
bloc ne fait rien.

Ecart accepte : dans ce processus, asttokens ne reconnait plus un arbre astroid (NodeNG vaut
None) - a reprendre si un greffon de l'interface en avait un jour besoin.

Usage : patch_spyder_asttokens_sans_astroid.py <spyder/app/mainwindow.py>
Idempotent (marqueur _smartos_asttokens_sans_astroid), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_smartos_asttokens_sans_astroid"
ANCRE = "requirements.check_qt()"

BLOC = '''

# ---- SmartOS (_smartos_asttokens_sans_astroid) : asttokens charge sans astroid (~25 ms) ---------
# Dans l'interface, asttokens ne sert qu'a stack_data (arbres `ast`). Voir
# spyder_patch/patch_spyder_asttokens_sans_astroid.py du generator.
def _smartos_asttokens_sans_astroid():
    if "astroid" in sys.modules or "asttokens" in sys.modules:
        return
    sys.modules["astroid"] = None  # `import astroid` leve ImportError le temps de cet import
    try:
        import asttokens  # noqa: F401
    except Exception:
        sys.modules.pop("asttokens", None)
    finally:
        if sys.modules.get("astroid", 0) is None:
            del sys.modules["astroid"]


_smartos_asttokens_sans_astroid()
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
