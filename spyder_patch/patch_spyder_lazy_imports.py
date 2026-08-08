#!/usr/bin/env python3
"""Rend paresseux trois imports lourds charges au demarrage de Spyder alors qu'ils ne
servent qu'a une fonctionnalite ponctuelle.

    spyder --profile-file  a montre (TODO - Spyder - acceleration demarage.txt) que
    "from spyder.app import mainwindow" a lui seul coute environ 3 s sur cette machine,
    et que les deux tiers de ce temps viennent de trois bibliotheques importees a la
    volee, en cascade, juste pour lire la configuration :

        spyder.utils.encoding            -> chardet                      (~1,06 s)
        spyder.config.appearance         -> sphinxify -> sphinx.application (~0,55 s,
                                             ~0,74 s en comptant sphinxify lui-meme)
        spyder.config.manager            -> keyring                      (~0,20 s)

CE QUE CHACUN SERT REELLEMENT A FAIRE
--------------------------------------
  chardet   : deviner l'encodage d'un fichier ouvert sans declaration "coding=xxx"
              explicite - un seul appel, dans encoding.get_coding().
  sphinx    : construire le rendu HTML riche du panneau Aide (docstring -> page web) -
              seulement quand ce panneau affiche quelque chose, dans sphinxify.py.
  keyring   : lire/ecrire/supprimer une option marquee "secure=True" (mot de passe de
              noyau distant) - trois methodes de ConfigurationManager.

Aucun des trois n'est necessaire pour demarrer Spyder, ouvrir un fichier ou lancer une
console : ce sont des imports de MODULE, executes une fois pour toutes au chargement,
alors que l'usage reel est conditionnel et rare. Les rendre paresseux (import deplace a
l'INTERIEUR de chaque fonction qui s'en sert) ne change aucun comportement observable -
Python met en cache le module des le premier appel reel, le cout est seulement deplace
de "a chaque lancement" a "a la premiere utilisation de cette fonctionnalite precise".

Verifie prealablement par lecture : chardet n'est utilise QUE dans get_coding() ; les
quatre imports tiers de sphinxify.py (docutils.utils.SystemMessage, jinja2.Environment/
FileSystemLoader, sphinx, sphinx.application.Sphinx) ne sont utilises QUE dans les
fonctions listees ci-dessous ; keyring et NoKeyringError ne sont utilises QUE dans get(),
set() et remove_option() de ConfigurationManager (config/manager.py deja precedent
qtpy en local dans set(), pour la meme raison : "This file must not have top-level Qt
imports").

Usage : patch_spyder_lazy_imports.py <encoding.py> <sphinxify.py> <manager.py>

Localisation des points d'insertion via le module "ast" (structure du code, pas texte
brut). Echoue BRUYAMMENT (code 1) si un point d'ancrage est introuvable, plutot que de
deviner. Idempotent : ne fait rien si le marqueur est deja present dans le fichier.
"""

import ast
import sys

MARKER = "_smartos_lazy_import"


def find_function(tree, name, class_name=None):
    for node in ast.walk(tree):
        if class_name is not None:
            if not (isinstance(node, ast.ClassDef) and node.name == class_name):
                continue
            children = node.body
        else:
            children = tree.body
        for child in children:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and child.name == name:
                return child
    return None


def remove_lines(source, needles):
    """Retire les lignes de import top-niveau correspondant EXACTEMENT a chaque motif
    de `needles` (une seule occurrence attendue par motif)."""
    lines = source.splitlines(keepends=True)
    kept = []
    removed = set()
    for line in lines:
        stripped = line.strip("\n")
        if stripped in needles and stripped not in removed:
            removed.add(stripped)
            continue
        kept.append(line)
    missing = needles - removed
    return "".join(kept), missing


def insert_at_function_start(source, tree, class_name, func_name, import_block):
    function = find_function(tree, func_name, class_name)
    if function is None:
        where = f"{class_name}.{func_name}" if class_name else func_name
        return None, f"fonction introuvable : {where}"
    first = function.body[0]
    start_line = first.lineno
    lines = source.splitlines(keepends=True)
    # Indentation calquee sur la premiere ligne du corps existant.
    indent = " " * (len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip(" ")))
    block = "".join(f"{indent}{stmt}\n" for stmt in import_block)
    result = "".join(lines[:start_line - 1]) + block + "".join(lines[start_line - 1:])
    return result, None


def patch_file(path, module_removals, insertions):
    """module_removals : ensemble de lignes top-niveau a retirer.
    insertions : liste de (class_name_ou_None, func_name, [lignes d'import])."""
    source = open(path, encoding="utf-8").read()
    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : {path} illisible ({error})", file=sys.stderr)
        return False

    # Insertions d'abord (du bas vers le haut, pour ne pas invalider les numeros de
    # ligne des insertions suivantes), puis suppression des imports top-niveau.
    ordered = []
    for class_name, func_name, import_lines in insertions:
        tree = ast.parse(source)
        function = find_function(tree, func_name, class_name)
        if function is None:
            where = f"{class_name}.{func_name}" if class_name else func_name
            print(f"ERREUR : fonction introuvable dans {path} : {where}",
                  file=sys.stderr)
            return False
        ordered.append((function.body[0].lineno, class_name, func_name, import_lines))
    ordered.sort(key=lambda item: item[0], reverse=True)

    marked_first = True
    for _, class_name, func_name, import_lines in ordered:
        tree = ast.parse(source)
        block = list(import_lines)
        if marked_first:
            block = [f"# {MARKER} : import deplace ici, cf."
                     " Commun/scripts/patch_spyder_lazy_imports.py"] + block
            marked_first = False
        source, error = insert_at_function_start(
            source, tree, class_name, func_name, block)
        if error:
            print(f"ERREUR : {path} : {error}", file=sys.stderr)
            return False

    source, missing = remove_lines(source, module_removals)
    if missing:
        print(f"ERREUR : import(s) top-niveau introuvable(s) dans {path} : {missing}",
              file=sys.stderr)
        return False

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    open(path, "w", encoding="utf-8").write(source)
    print(f"Patche : {path}")
    return True


def patch_encoding(path):
    return patch_file(
        path,
        module_removals={"import chardet"},
        insertions=[
            (None, "get_coding", ["import chardet"]),
        ],
    )


def patch_sphinxify(path):
    return patch_file(
        path,
        module_removals={
            "from docutils.utils import SystemMessage as SystemMessage",
            "from jinja2 import Environment, FileSystemLoader",
            "import sphinx",
            "from sphinx.application import Sphinx",
        },
        insertions=[
            (None, "warning", ["from jinja2 import Environment, FileSystemLoader"]),
            (None, "usage", ["from jinja2 import Environment, FileSystemLoader"]),
            (None, "loading", ["from jinja2 import Environment, FileSystemLoader"]),
            (None, "generate_context", ["import sphinx"]),
            (None, "sphinxify", [
                "from docutils.utils import SystemMessage as SystemMessage",
                "from sphinx.application import Sphinx",
            ]),
        ],
    )


def patch_manager(path):
    return patch_file(
        path,
        module_removals={
            "import keyring",
            "from keyring.errors import NoKeyringError",
        },
        insertions=[
            ("ConfigurationManager", "get", ["import keyring"]),
            ("ConfigurationManager", "set", [
                "import keyring",
                "from keyring.errors import NoKeyringError",
            ]),
            ("ConfigurationManager", "remove_option", ["import keyring"]),
        ],
    )


def main(argv):
    if len(argv) != 4:
        print(f"Usage : {argv[0]} <encoding.py> <sphinxify.py> <manager.py>",
              file=sys.stderr)
        return 1
    ok = patch_encoding(argv[1])
    ok = patch_sphinxify(argv[2]) and ok
    ok = patch_manager(argv[3]) and ok
    if ok:
        print("  chardet / sphinx / keyring ne se chargent plus qu'a l'usage reel")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
