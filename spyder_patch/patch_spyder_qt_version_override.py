#!/usr/bin/env python3
"""Permet d'outrepasser la plage de version Qt figee en dur dans spyder/requirements.py.

    SPYDER_QT_MAX_VERSION=6.99.0 spyder
    SPYDER_QT_MIN_VERSION=6.0.0 SPYDER_QT_MAX_VERSION=6.99.0 spyder
    SPYDER_QT_SKIP_VERSION_CHECK=1 spyder

POURQUOI
--------
spyder/requirements.py:check_qt() refuse de demarrer si la version du binding Qt actif
sort d'une plage figee en dur par binding (ex. PySide6 : >=6.8.0,<6.9.0 - constate en
direct le 25/07/2026 : Spyder 6.1.5 refuse PySide6 6.11.1, installee par defaut par pip,
et n'accepte que 6.8.x). Cette plage n'est pas configurable telle quelle : chaque nouvelle
version de PySide6/PyQt6 a tester obligerait a modifier spyder/requirements.py a la main.
On ajoute donc trois variables d'environnement optionnelles pour piloter la verification
sans toucher au fichier a chaque fois :

  SPYDER_QT_MIN_VERSION         remplace la borne basse pour le binding actif
  SPYDER_QT_MAX_VERSION         remplace la borne haute pour le binding actif
  SPYDER_QT_SKIP_VERSION_CHECK  si "1", ignore entierement la verification

Absentes, le comportement d'origine de Spyder est inchange.

CE QUE LE PATCH MODIFIE (par ajout, jamais par remplacement ; idempotent via
_smartos_qt_version_override)
  app/../requirements.py (spyder/requirements.py) : juste apres la ligne qui lit
  `package_name, required_ver = qt_infos[qtpy.API]` dans check_qt().

Localisation du point d'insertion via le module "ast" (structure du code, pas texte
brut). Echoue BRUYAMMENT (code 1) si l'ancre est introuvable, plutot que de deviner.

Usage : patch_spyder_qt_version_override.py <requirements.py>
"""

import ast
import sys

MARKER = "_smartos_qt_version_override"

PATCH = '''
        # Ajout SmartOS (_smartos_qt_version_override) : permet d'outrepasser la plage de
        # version figee en dur ci-dessus via des variables d'environnement, sans avoir a
        # repatcher ce fichier a chaque nouvelle version de binding Qt testee. Cf.
        # Commun/scripts/patch_spyder_qt_version_override.py
        import os as _smartos_os
        if _smartos_os.environ.get("SPYDER_QT_SKIP_VERSION_CHECK") == "1":
            return
        _smartos_min = _smartos_os.environ.get("SPYDER_QT_MIN_VERSION")
        _smartos_max = _smartos_os.environ.get("SPYDER_QT_MAX_VERSION")
        if _smartos_min or _smartos_max:
            required_ver = (
                _smartos_min or required_ver[0],
                _smartos_max or required_ver[1],
            )
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


def find_anchor_statement(source, function, needle):
    """Trouve l'instruction la plus SPECIFIQUE (pas un bloc englobant type try/except)
    dont le code source correspond exactement au besoin - sinon l'insertion se retrouve
    apres tout un bloc try/except au lieu de juste apres la ligne visee (bug constate le
    25/07/2026 sur ce patch meme : l'ancre reperait le Try entier, pas l'Assign a
    l'interieur, et le code insere finissait par s'executer APRES le show_warning())."""
    candidates = [
        node for node in ast.walk(function)
        if isinstance(node, ast.stmt)
        and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (ast.get_source_segment(source, node) or "").strip() == needle
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda node: len(ast.get_source_segment(source, node)))


def patch_requirements(path):
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : {path} illisible ({error})", file=sys.stderr)
        return False

    function = find_function(tree, "check_qt")
    if function is None:
        print(f"ERREUR : check_qt() introuvable dans {path}", file=sys.stderr)
        return False

    anchor = find_anchor_statement(
        source, function, "package_name, required_ver = qt_infos[qtpy.API]")
    if anchor is None:
        print(
            "ERREUR : ligne d'ancrage "
            "'package_name, required_ver = qt_infos[qtpy.API]' introuvable "
            f"dans check_qt() de {path}",
            file=sys.stderr,
        )
        return False

    end_line = getattr(anchor, "end_lineno", anchor.lineno)

    lines = source.splitlines(keepends=True)
    result = "".join(lines[:end_line]) + PATCH + "".join(lines[end_line:])
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
        print(f"Usage : {argv[0]} <requirements.py>", file=sys.stderr)
        return 1
    ok = patch_requirements(argv[1])
    if ok:
        print(
            "  SPYDER_QT_MAX_VERSION=6.99.0 spyder  outrepasse la borne haute\n"
            "  SPYDER_QT_SKIP_VERSION_CHECK=1 spyder  ignore la verification"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
