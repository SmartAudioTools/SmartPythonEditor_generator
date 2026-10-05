#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memorise les deux fonctions PURES que qstylizer recalcule a chaque regle de style.

Contexte (TODO - Spyder - accélération démarage.txt, etape 1c, 05/10/2026) : chaque
qstylizer.style.StyleRule - c'est-a-dire chaque regle, chaque sous-regle ET chaque propriete
d'une feuille de style - appelle dans son __init__ `get_attributes()` puis `get_attr_options()`.
Ce sont deux classmethods de StyleRuleParent qui reparcourent les classes de base et
reconstruisent un dictionnaire de ~200 descripteurs, alors que leur resultat ne depend QUE de la
classe. Le profil du 20/07/2026 comptait 103 818 appels a get_attributes() pour 7 415 regles
creees par les seuls menus.

Le cache des menus (patch_spyder_menu_stylesheet_cache.py) evite de reconstruire UNE feuille
identique ; celui-ci rend la construction de TOUTES les feuilles moins chere (docks, onglets,
listes deroulantes, editorstack...), sans avoir a prouver feuille par feuille qu'elle est
partageable : memoriser une fonction pure ne change aucun resultat.

Ce qui est memorise, et pourquoi c'est sur :
  - StyleRuleParent.get_attributes / get_attr_options, par classe. Le dictionnaire et l'ensemble
    rendus sont alors PARTAGES entre toutes les instances d'une classe : valable parce que
    qstylizer ne fait que les lire (`in`, `[...]`, style.py) - verifie par lecture de qstylizer
    0.2.4, et le bloc pose refuse de s'activer sur une autre version majeure/mineure ;
  - StyleRule._sanitize_key (et sa surcharge), pour un argument de type str exactement : une
    fonction de chaine vers chaine, qui passe par les expressions regulieres d'inflection.

Le bloc est pose dans spyder/utils/stylesheet.py, juste apres `import qstylizer.style` : c'est
le premier module de Spyder a s'en servir, et modifier les classes de qstylizer une fois suffit
pour tous les autres. Rien n'est ecrit dans le venv.

Usage : patch_spyder_qstylizer_memo.py <spyder/utils/stylesheet.py>
Idempotent (marqueur _smartos_qstylizer_memo), echoue bruyamment si l'import est introuvable.
"""

import ast
import sys

MARKER = "_smartos_qstylizer_memo"

PATCH = '''

# ---- SmartOS (_smartos_qstylizer_memo) : fonctions pures de qstylizer memorisees ---------------
# Chaque regle de style recalculait, dans son __init__, la liste de ses attributs possibles, qui
# ne depend que de sa classe. Voir spyder_patch/patch_spyder_qstylizer_memo.py du generator.
def _smartos_qstylizer_memo():
    import functools
    import importlib.metadata
    from qstylizer.descriptor.stylerule import StyleRuleParent

    # Le partage des resultats suppose que qstylizer ne les modifie pas : verifie pour 0.2.x.
    if not importlib.metadata.version("qstylizer").startswith("0.2."):
        return

    def par_classe(nom):
        originale = StyleRuleParent.__dict__[nom].__func__
        cache = {}

        @functools.wraps(originale)
        def memorisee(cls):
            try:
                return cache[cls]
            except KeyError:
                resultat = cache[cls] = originale(cls)
                return resultat

        setattr(StyleRuleParent, nom, classmethod(memorisee))

    def cle_assainie(classe):
        originale = classe.__dict__["_sanitize_key"].__func__
        en_cache = functools.lru_cache(maxsize=None)(originale)

        @functools.wraps(originale)
        def memorisee(key):
            if type(key) is str:
                return en_cache(key)
            return originale(key)

        classe._sanitize_key = staticmethod(memorisee)

    par_classe("get_attributes")
    par_classe("get_attr_options")
    for classe in list(vars(qstylizer.style).values()):
        if (isinstance(classe, type)
                and isinstance(classe.__dict__.get("_sanitize_key"), staticmethod)):
            cle_assainie(classe)


try:
    _smartos_qstylizer_memo()
except Exception:
    # Une optimisation ne doit jamais empecher Spyder de s'ouvrir.
    import traceback
    traceback.print_exc()
'''


def patch_stylesheet(path):
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : {path} illisible ({error})", file=sys.stderr)
        return False

    anchor = None
    for node in tree.body:
        if isinstance(node, ast.Import) and any(
                alias.name == "qstylizer.style" and alias.asname is None
                for alias in node.names):
            anchor = node.end_lineno
    if anchor is None:
        print(f"ERREUR : `import qstylizer.style` introuvable dans {path}", file=sys.stderr)
        return False

    lines = source.splitlines(keepends=True)
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
        print(f"Usage : {argv[0]} <spyder/utils/stylesheet.py>", file=sys.stderr)
        return 1
    return 0 if patch_stylesheet(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
