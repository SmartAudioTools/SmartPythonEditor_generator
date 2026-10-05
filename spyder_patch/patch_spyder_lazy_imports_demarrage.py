#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend paresseux des imports de tete de module qui ne servent pas au demarrage (SmartOS).

Complement GENERIQUE de patch_spyder_lazy_imports.py (qui traite trois cas a la main) : pour
chaque couple (fichier, module importe) de la table CIBLES, l'instruction d'import de tete est
retiree et recopiee au debut de chaque fonction ou methode qui utilise un des noms qu'elle
liait. Le comportement est inchange, seul l'instant de l'import bouge : au premier appel d'une
fonction qui s'en sert, au lieu du lancement de l'editeur.

La transformation n'est faite que si elle est SURE, sinon le script echoue bruyamment :
  - un nom utilise hors d'un corps de fonction (niveau module, corps de classe, decorateur,
    annotation ou valeur par defaut d'une signature) est evalue a l'import : refus - sauf
    les annotations de signature d'un module `from __future__ import annotations`, jamais
    evaluees ;
  - une instruction d'import introuvable sans le marqueur : refus (l'amont a change).

Mesures et justification de chaque cible : DONE - Spyder - reste.txt, entree du 05/10/2026.

Usage : patch_spyder_lazy_imports_demarrage.py <racine du fork> [--verifier]
  --verifier : n'ecrit rien, dit seulement ce qui serait fait (code de retour 1 si refus).
Idempotent : un marqueur par instruction deplacee (_smartos_lazy_demarrage:<module>).
"""

import ast
import os
import re
import sys

MARKER = "_smartos_lazy_demarrage"

# (fichier relatif a la racine du fork, module dont l'import de tete est differe)
CIBLES = [
    # nbconvert/nbformat : conversion d'un notebook ouvert dans l'editeur.
    ("spyder/plugins/editor/widgets/codeeditor/codeeditor.py", "nbconvert"),
    ("spyder/plugins/editor/widgets/codeeditor/codeeditor.py", "nbformat"),
    # github (+ jwt, cryptography, requests) : envoi d'un rapport d'erreur.
    ("spyder/widgets/github/backend.py", "github"),
    # requests : un simple dictionnaire insensible a la casse pour l'environnement (les deux
    # autres fichiers qui s'en servent sont dans REECRITURES, voir _CASE_INSENSITIVE).
    ("spyder/plugins/pythonpath/widgets/pathmanager.py", "requests.structures"),
    # requests : verification des mises a jour (le greffon ne peut pas etre desactive).
    ("spyder/plugins/updatemanager/workers.py", "requests"),
    ("spyder/plugins/updatemanager/workers.py", "requests.exceptions"),
    # jsonschema : validation du fichier de connexion a un noyau existant.
    ("spyder/plugins/ipythonconsole/widgets/kernelconnect.py", "jsonschema"),
    # jsonschema (+ referencing, attr, rpds : ~20 ms) : validation d'un fichier de snippets
    # importe depuis l'onglet de preferences.
    ("spyder/plugins/completion/providers/snippets/widgets/snippetsconfig.py",
     "jsonschema.exceptions"),
    ("spyder/plugins/completion/providers/snippets/widgets/snippetsconfig.py", "jsonschema"),
    # asyncssh (+ cryptography) et aiohttp : noyaux DISTANTS seulement (ssh, websocket).
    ("spyder/plugins/ipythonconsole/utils/client.py", "asyncssh"),
    ("spyder/plugins/ipythonconsole/utils/websocket_client.py", "aiohttp"),
    ("spyder/plugins/ipythonconsole/utils/websocket_client.py", "aiohttp.client_exceptions"),
    ("spyder/plugins/explorer/widgets/remote_explorer.py", "aiohttp.client_exceptions"),
    # api/ssh.py HERITE d'asyncssh.SSHClient : c'est son import a lui qui est differe.
    ("spyder/plugins/remoteclient/api/manager/ssh.py", "spyder.plugins.remoteclient.api.ssh"),
    ("spyder/plugins/remoteclient/api/manager/jupyterhub.py", "aiohttp"),
    ("spyder/plugins/remoteclient/api/manager/jupyterhub.py", "yarl"),
    ("spyder/plugins/remoteclient/api/manager/ssh.py", "asyncssh"),
    ("spyder/plugins/remoteclient/api/modules/environ.py", "aiohttp"),
    ("spyder/plugins/remoteclient/api/modules/base.py", "aiohttp"),
    ("spyder/plugins/remoteclient/api/modules/base.py", "yarl"),
    ("spyder/plugins/remoteclient/api/modules/file_services.py", "aiohttp"),
    ("spyder/plugins/remoteclient/widgets/connectionpages.py", "asyncssh"),
    ("spyder/plugins/projects/widgets/qcookiecutter.py", "jinja2"),
    ("spyder/plugins/ipythonconsole/widgets/namespacebrowser.py", "cloudpickle"),
    # markdown_it : dialogue d'appel aux dons.
    ("spyder/plugins/application/widgets/appeal.py", "markdown_it"),
]

# Cas que la regle generique refuse a juste titre (le nom importe est consulte a l'import ou
# hors d'une fonction) : reecriture a la main, par remplacement de texte EXACT. Chaque texte
# d'origine doit figurer une fois et une seule, sinon echec bruyant (l'amont a change).
# (fichier, module, [(texte d'origine, texte de remplacement), ...])

# requests.structures.CaseInsensitiveDict n'est construit que sous Windows, mais dans des
# fonctions APPELEES au demarrage sur toutes les plateformes (alter_subprocess_kwargs, env du
# noyau) : la regle generique, qui pose l'import en tete de fonction, faisait donc payer
# requests (+ urllib3, chardet, charset_normalizer : 524 ms mesures le 05/10/2026, -X
# importtime) au premier appel. L'import de tete devient une fonction du meme nom, qui
# n'importe qu'a la construction. Valable parce que le nom n'est qu'APPELE dans ces deux
# fichiers (pas d'isinstance, pas d'heritage) - sinon le texte d'origine ne correspond plus.
_CASE_INSENSITIVE = [
    ("from requests.structures import CaseInsensitiveDict\n",
     "\n\n# Ajout SmartOS (_smartos_lazy_demarrage:requests.structures) : requests n'est importe\n"
     "# qu'a la construction (Windows seulement). Voir patch_spyder_lazy_imports_demarrage.py.\n"
     "def CaseInsensitiveDict(*args, **kwargs):\n"
     "    from requests.structures import CaseInsensitiveDict as _CaseInsensitiveDict\n"
     "    return _CaseInsensitiveDict(*args, **kwargs)\n\n\n"),
]

REECRITURES = [
    # pylsp._utils (+ pylsp, jedi, parso, docstring_to_markdown : 30 ms) n'etait importe que pour
    # une fonction de trois lignes sur les fins de ligne, et differer l'import ne suffisait
    # pas : elle est appelee a l'ouverture du premier fichier. Elle est donc recopiee (meme
    # motif, meme ordre d'alternatives que pylsp._utils.EOL_REGEX ; 05/10/2026).
    ("spyder/utils/sourcecode.py", "pylsp-eol", [
        ("from pylsp._utils import get_eol_chars as _get_eol_chars\n",
         "# Ajout SmartOS (_smartos_lazy_demarrage:pylsp-eol) : copie de\n"
         "# pylsp._utils.get_eol_chars, voir patch_spyder_lazy_imports_demarrage.py.\n"
         "_SMARTOS_EOL_REGEX = re.compile('(\\r\\n|\\r|\\n)')\n\n\n"
         "def _get_eol_chars(text):\n"
         "    match = _SMARTOS_EOL_REGEX.search(text)\n"
         "    return match.group(0) if match else None\n\n"),
    ]),
    ("spyder/utils/programs.py", "requests.structures", _CASE_INSENSITIVE),
    ("spyder/plugins/ipythonconsole/utils/kernelspec.py", "requests.structures",
     _CASE_INSENSITIVE),
    # chardet (45 a 80 ms d'import) : second chemin laisse ouvert par
    # patch_spyder_lazy_imports.py (spyder.utils.encoding -> binaryornot.check -> helpers),
    # et surtout il est APPELE au demarrage (historique, fichiers restaures), donc differer
    # l'import ne suffit pas. Raccourci pour le cas courant, strictement equivalent : sur des
    # octets purement ASCII sans NUL, ESC ni tilde, chardet repond toujours 'ascii'
    # (6002 extraits compares le 05/10/2026, 0 ecart ; ESC et tilde declenchent ses sondes
    # ISO-2022 / HZ, NUL lui fait repondre None). Un fichier accentue l'importe toujours.
    # Doit passer APRES patch_spyder_lazy_imports.py (qui pose l'import dans get_coding).
    ("spyder/utils/encoding.py", "chardet-ascii", [
        ('    import chardet\n    """\n', '    """\n'),
        ("        result = chardet.detect(text)\n",
         "        # Ajout SmartOS (_smartos_lazy_demarrage:chardet-ascii) : voir\n"
         "        # patch_spyder_lazy_imports_demarrage.py.\n"
         "        if (text and text.isascii() and b'\\x00' not in text\n"
         "                and b'\\x1b' not in text and b'~' not in text):\n"
         "            return 'ascii'\n"
         "        import chardet\n"
         "        result = chardet.detect(text)\n"),
    ]),
    ("spyder/utils/external/binaryornot/helpers.py", "chardet-ascii", [
        ("import chardet\nimport logging\n", "import logging\n"),
        ("    detected_encoding = chardet.detect(bytes_to_check)\n",
         "    # Ajout SmartOS (_smartos_lazy_demarrage:chardet-ascii) : voir\n"
         "    # patch_spyder_lazy_imports_demarrage.py.\n"
         "    if (bytes_to_check.isascii() and b'\\x00' not in bytes_to_check\n"
         "            and b'\\x1b' not in bytes_to_check and b'~' not in bytes_to_check):\n"
         "        detected_encoding = {'encoding': 'ascii', 'confidence': 1.0}\n"
         "    else:\n"
         "        import chardet\n"
         "        detected_encoding = chardet.detect(bytes_to_check)\n"),
    ]),
    # Explorateur de fichiers : nbconvert (+ bs4, jinja2, mistune, bleach...) n'etait importe
    # que pour savoir s'il est installe (affichage de l'action "Convertir le notebook").
    # find_spec repond a cette question sans rien importer.
    ("spyder/plugins/explorer/widgets/explorer.py", "nbconvert", [
        ("try:\n"
         "    from nbconvert import PythonExporter as nbexporter\n"
         "except:\n"
         "    nbexporter = None    # analysis:ignore\n",
         "# Ajout SmartOS (_smartos_lazy_demarrage:nbconvert) : temoin de presence seulement,\n"
         "# l'import reel est fait par convert_notebook.\n"
         "try:\n"
         "    import importlib.util\n"
         "    nbexporter = importlib.util.find_spec('nbconvert')\n"
         "except Exception:\n"
         "    nbexporter = None    # analysis:ignore\n"),
        ("            script = nbexporter().from_filename(fname)[0]\n",
         "            from nbconvert import PythonExporter\n"
         "            script = PythonExporter().from_filename(fname)[0]\n"),
    ]),
    # keyring (~9 ms) : patch_spyder_lazy_imports.py l'importe en tete de ConfigurationManager.get,
    # donc au premier CONF.get du lancement ; il ne sert que pour une option `secure`.
    ("spyder/config/manager.py", "keyring-secure", [
        ("    def get(self, section, option, default=NoDefault, secure=False):\n"
         "        import keyring\n",
         "    def get(self, section, option, default=NoDefault, secure=False):\n"),
        ("            if secure:\n"
         "                logger.debug(\n"
         "                    f\"Retrieving option",
         "            if secure:\n"
         "                import keyring  # _smartos_lazy_demarrage:keyring-secure\n"
         "                logger.debug(\n"
         "                    f\"Retrieving option"),
    ]),
    # Themes de coloration : set_color_scheme reecrivait la liste des noms a chaque theme, meme
    # inchangee (21 CONF.set identiques a l'import de spyder.config.gui, 6,6 ms).
    ("spyder/config/gui.py", "noms-themes", [
        ("    names.append(str(name))\n"
         "    CONF.set(section, \"names\", sorted(list(set(names))))\n",
         "    # Ajout SmartOS (_smartos_lazy_demarrage:noms-themes) : ecrit seulement si la liste change.\n"
         "    _smartos_noms = sorted(set(names + [str(name)]))\n"
         "    if _smartos_noms != names:\n"
         "        CONF.set(section, \"names\", _smartos_noms)\n"),
    ]),
    # Pylint : l'analyse tourne dans un sous-processus, l'editeur n'a besoin que de savoir
    # que pylint est installe (PYLINT_VER) et, au moment d'une analyse, de trouver le pylintrc.
    ("spyder/plugins/pylint/main_widget.py", "pylint", [
        ("import pylint\n",
         "# Ajout SmartOS (_smartos_lazy_demarrage:pylint) : version lue dans les metadonnees.\n"
         "import importlib.metadata\n"),
        ("PYLINT_VER = pylint.__version__\n",
         "PYLINT_VER = importlib.metadata.version('pylint')\n"),
    ]),
    ("spyder/plugins/pylint/utils.py", "pylint", [
        ("try:\n"
         "    from pylint import config as pylint_config\n"
         "except Exception:\n"
         "    pylint_config = None\n",
         "# Ajout SmartOS (_smartos_lazy_demarrage:pylint) : import differe dans\n"
         "# _find_pylintrc_path.\n"),
        ("def _find_pylintrc_path(path):\n",
         "def _find_pylintrc_path(path):\n"
         "    try:\n"
         "        from pylint import config as pylint_config\n"
         "    except Exception:\n"
         "        pylint_config = None\n"),
    ]),
]


def _deja_pose(marqueur, source):
    """Le marqueur EXACT est-il pose ? (`...:aiohttp` est un prefixe de
    `...:aiohttp.client_exceptions` : une recherche de sous-chaine les confondait.)"""
    return re.search(re.escape(marqueur) + r"(?![\w.])", source) is not None


def _instruction(tree, module):
    """Instruction d'import de TETE qui importe `module`, ou None."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == module:
            return node
        if isinstance(node, ast.Import) and any(a.name == module for a in node.names):
            if len(node.names) != 1:
                raise ValueError(f"import multiple ligne {node.lineno} : non gere")
            return node
    return None


def _noms_lies(node):
    noms = set()
    for alias in node.names:
        if alias.asname:
            noms.add(alias.asname)
        elif isinstance(node, ast.Import):
            noms.add(alias.name.split(".")[0])
        else:
            noms.add(alias.name)
    return noms


def _usages(tree, noms, instruction):
    """Renvoie (fonctions de premier niveau qui utilisent un nom, lignes d'usage refusees)."""
    fonctions, refus = [], []
    annotations_differees = any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__"
        and any(alias.name == "annotations" for alias in n.names) for n in tree.body)

    def utilise(node):
        return [n for n in ast.walk(node)
                if isinstance(n, ast.Name) and n.id in noms]

    def visiter(conteneur):
        for node in conteneur.body:
            if node is instruction:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Evalue a la definition, donc a l'import : decorateurs et signature.
                hors_corps = list(node.decorator_list)
                if annotations_differees:
                    # `from __future__ import annotations` : les annotations ne sont
                    # jamais evaluees, seules les valeurs par defaut le sont.
                    hors_corps += node.args.defaults
                    hors_corps += [d for d in node.args.kw_defaults if d is not None]
                else:
                    hors_corps.append(node.args)
                    if node.returns is not None:
                        hors_corps.append(node.returns)
                for partie in hors_corps:
                    refus.extend(n.lineno for n in utilise(partie))
                if any(utilise(stmt) for stmt in node.body):
                    fonctions.append(node)
            elif isinstance(node, ast.ClassDef):
                for partie in node.decorator_list + node.bases + node.keywords:
                    refus.extend(n.lineno for n in utilise(partie))
                visiter(node)
            elif isinstance(node, (ast.If, ast.Try, ast.With)) and conteneur is tree:
                refus.extend(n.lineno for n in utilise(node))
            else:
                refus.extend(n.lineno for n in utilise(node))

    visiter(tree)
    return fonctions, refus


def differer(path, module, verifier=False):
    source = open(path, encoding="utf-8").read()
    marqueur = f"{MARKER}:{module}"
    if _deja_pose(marqueur, source):
        print(f"Deja patche : {path} ({module})")
        return True
    try:
        tree = ast.parse(source)
        instruction = _instruction(tree, module)
    except (SyntaxError, ValueError) as error:
        print(f"ERREUR : {path} ({error})", file=sys.stderr)
        return False
    if instruction is None:
        print(f"ERREUR : import de tete de {module} introuvable dans {path}",
              file=sys.stderr)
        return False

    noms = _noms_lies(instruction)
    fonctions, refus = _usages(tree, noms, instruction)
    if refus:
        print(f"ERREUR : {path} utilise {sorted(noms)} a l'import (lignes "
              f"{sorted(set(refus))}) : {module} ne peut pas etre differe",
              file=sys.stderr)
        return False

    lines = source.splitlines(keepends=True)
    texte = "".join(lines[instruction.lineno - 1:instruction.end_lineno])
    texte = " ".join(part.strip() for part in texte.splitlines())  # sur une ligne

    # Insertions de bas en haut, pour que les numeros de ligne restent valides.
    insertions = []
    for fonction in fonctions:
        premier = fonction.body[0]
        if (isinstance(premier, ast.Expr) and isinstance(premier.value, ast.Constant)
                and isinstance(premier.value.value, str) and len(fonction.body) > 1):
            premier = fonction.body[1]
        if premier.lineno == fonction.lineno:
            print(f"ERREUR : {path} ligne {fonction.lineno}, fonction sur une ligne",
                  file=sys.stderr)
            return False
        insertions.append((premier.lineno - 1, " " * premier.col_offset))
    for index, indentation in sorted(insertions, reverse=True):
        lines.insert(index, f"{indentation}{texte}  # {marqueur}\n")
    debut, fin = instruction.lineno - 1, instruction.end_lineno
    lines[debut:fin] = [f"# Ajout SmartOS ({marqueur}) : import differe dans les "
                        f"{len(fonctions)} fonction(s) qui s'en servent.\n"]

    result = "".join(lines)
    try:
        ast.parse(result)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    noms_fonctions = ", ".join(f.name for f in fonctions) or "aucune"
    if verifier:
        print(f"Serait patche : {path} ({module} -> {noms_fonctions})")
        return True
    open(path, "w", encoding="utf-8").write(result)
    print(f"Patche : {path} ({module} -> {noms_fonctions})")
    return True


def reecrire(path, module, remplacements, verifier=False):
    source = open(path, encoding="utf-8").read()
    marqueur = f"{MARKER}:{module}"
    if _deja_pose(marqueur, source):
        print(f"Deja patche : {path} ({module})")
        return True
    result = source
    for origine, remplacement in remplacements:
        if result.count(origine) != 1:
            print(f"ERREUR : {path}, texte attendu {result.count(origine)} fois au lieu "
                  f"d'une : {origine.splitlines()[0]!r}", file=sys.stderr)
            return False
        result = result.replace(origine, remplacement)
    try:
        ast.parse(result)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    if marqueur not in result:
        print(f"ERREUR : {path}, la reecriture ne pose pas {marqueur}", file=sys.stderr)
        return False
    if verifier:
        print(f"Serait reecrit : {path} ({module})")
        return True
    open(path, "w", encoding="utf-8").write(result)
    print(f"Reecrit : {path} ({module})")
    return True


def main(argv):
    verifier = "--verifier" in argv
    args = [a for a in argv[1:] if a != "--verifier"]
    if len(args) != 1:
        print(f"Usage : {argv[0]} <racine du fork> [--verifier]", file=sys.stderr)
        return 1
    ok = True
    for relatif, module in CIBLES:
        ok = differer(os.path.join(args[0], relatif), module, verifier) and ok
    for relatif, module, remplacements in REECRITURES:
        ok = reecrire(os.path.join(args[0], relatif), module, remplacements, verifier) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
