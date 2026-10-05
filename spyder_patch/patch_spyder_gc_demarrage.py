#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le ramasse-miettes cyclique est suspendu pendant le demarrage (start.py, mainwindow.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 9, 05/10/2026). Le demarrage cree
plus de 200 000 objets suivis par le ramasse-miettes, presque tous durables (modules, classes,
widgets). Avec les seuils par defaut (700, 10, 10), cela declenche 452 collectes de generation 0,
41 de generation 1 et 3 collectes completes : ~100 a 120 ms mesures par gc.callbacks, pour ne
liberer presque rien (1 645 objets sur les trois collectes completes).

Deux blocs, chacun avec son marqueur :
  - _smartos_gc_demarrage_suspendu (spyder/app/start.py) : gc.disable() juste apres
    `import sys`, donc avant les imports lourds. Le comptage de references, lui, continue de
    liberer tout ce qui n'est pas un cycle.
  - _smartos_gc_demarrage_retabli (spyder/app/mainwindow.py) : gc.enable() trois secondes apres
    sig_setup_finished, une fois l'editeur, le LSP et le noyau prets. Les seuils ne sont jamais
    modifies.

Cout accepte : la premiere collecte apres le retablissement traite d'un coup tout ce qui a ete
cree pendant le demarrage (une collecte de ~50 ms, ~15 000 objets liberes, mesuree ~3 s apres la
fin du demarrage). gc.freeze() l'eviterait, mais ces objets ne seraient alors jamais liberes.

Si la fenetre n'atteint jamais la fin de post_visible_setup (erreur fatale, ou arguments
transmis a une instance deja ouverte), le processus se termine : le ramasse-miettes n'a pas a
etre retabli.

Usage : patch_spyder_gc_demarrage.py <spyder/app/start.py> <spyder/app/mainwindow.py>
Idempotent (un marqueur par bloc), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR_SUSPENDU = "_smartos_gc_demarrage_suspendu"
BLOC_SUSPENDU = '''
# ---- SmartOS (_smartos_gc_demarrage_suspendu) : pas de ramasse-miettes pendant le demarrage ----
# Retabli par mainwindow.py (_smartos_gc_demarrage_retabli). Voir
# spyder_patch/patch_spyder_gc_demarrage.py du generator.
import gc as _smartos_gc_demarrage_suspendu
_smartos_gc_demarrage_suspendu.disable()
'''

MARQUEUR_RETABLI = "_smartos_gc_demarrage_retabli"
ANCRE_RETABLI = "self.sig_setup_finished.emit()"
BLOC_RETABLI = '''
        # Ajout SmartOS (_smartos_gc_demarrage_retabli) : le ramasse-miettes, suspendu par
        # start.py, reprend une fois l'editeur, le LSP et le noyau prets.
        QTimer.singleShot(3000, gc.enable)
'''


def _echec(message, chemin):
    print(f"ERREUR : {message} dans {chemin} - la forme amont a change.", file=sys.stderr)
    return False


def _ecrire(chemin, resultat):
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def patcher_start(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_SUSPENDU in source:
        print(f"Deja patche : {chemin}")
        return True
    lignes = source.splitlines(keepends=True)
    imports = [n for n in ast.parse(source).body if isinstance(n, ast.Import)
               and [a.name for a in n.names] == ["sys"]]
    if len(imports) != 1:
        return _echec("`import sys` (unique, au niveau du module) est introuvable", chemin)
    fin = imports[0].end_lineno
    return _ecrire(chemin, "".join(lignes[:fin]) + BLOC_SUSPENDU + "".join(lignes[fin:]))


def patcher_mainwindow(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_RETABLI in source:
        print(f"Deja patche : {chemin}")
        return True
    arbre = ast.parse(source)
    lignes = source.splitlines(keepends=True)
    noms = {alias.asname or alias.name for n in arbre.body
            if isinstance(n, (ast.Import, ast.ImportFrom)) for alias in n.names}
    methodes = [m for c in arbre.body if isinstance(c, ast.ClassDef) and c.name == "MainWindow"
                for m in c.body if isinstance(m, ast.FunctionDef)
                and m.name == "post_visible_setup"]
    ancres = [n for m in methodes for n in m.body if isinstance(n, ast.Expr)
              and lignes[n.lineno - 1].strip() == ANCRE_RETABLI]
    if len(ancres) != 1 or not {"gc", "QTimer"} <= noms:
        return _echec(f"`{ANCRE_RETABLI}` (unique, dans MainWindow.post_visible_setup, avec gc "
                      "et QTimer importes au niveau du module) est introuvable", chemin)
    fin = ancres[0].end_lineno
    return _ecrire(chemin, "".join(lignes[:fin]) + BLOC_RETABLI + "".join(lignes[fin:]))


def main(argv):
    if len(argv) != 3:
        print(f"Usage : {argv[0]} <spyder/app/start.py> <spyder/app/mainwindow.py>",
              file=sys.stderr)
        return 1
    # Le retablissement d'abord : s'il echoue, la suspension n'est pas posee.
    if not patcher_mainwindow(argv[2]):
        return 1
    return 0 if patcher_start(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
