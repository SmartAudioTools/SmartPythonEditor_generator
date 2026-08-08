#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/status.py pour retirer le prefixe "Personnalise:"
(Custom:) affiche devant le nom de l'interpreteur dans la barre de statut.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", demande de l'utilisateur du 22/07/2026 :
"pour le widget permettant de selectionner l'interpreteur, je ne veux pas qu'il commence par
'Personnalise:'"). Spyder construit le texte du widget sous la forme
"<type>: <nom> (Python <version>)", ou <type> vaut "Conda"/"Pyenv"/"Pixi" ou, a defaut, "Custom"
(traduit "Personnalise"). Les environnements SmartPython (pyenv) ne sont pas reconnus comme Pyenv par
Spyder, ils tombent donc sur "Custom". Ce patch retire simplement ce prefixe de type : le texte
devient "<nom> (Python <version>)".

Usage : patch_spyder_interpreter_prefix.py <chemin vers ipythonconsole/widgets/status.py installe>

Localisation par ancrage de TEXTE EXACT sur l'assemblage du texte (unique). Idempotent (marqueur).
Re-parse avant ecriture ; echoue BRUYAMMENT (code de sortie 1) si l'ancre manque - jamais deviner.
"""
import ast
import sys

MARKER = 'Prefixe "Custom:"/"Personnalise:" retire (SmartOS'
ANCHOR = (
    "            env_type\n"
    '            + ": "\n'
    '            + env_info["name"]\n'
)
REPLACEMENT = (
    '            # Prefixe "Custom:"/"Personnalise:" retire (SmartOS, cf.\n'
    "            # Commun/scripts/patch_spyder_interpreter_prefix.py) - demande utilisateur.\n"
    '            env_info["name"]\n'
)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers ipythonconsole/widgets/status.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"status.py illisible ({error}) - patch prefixe interpreteur non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch prefixe interpreteur Spyder deja applique.")
        return 0

    if source.count(ANCHOR) != 1:
        print(f"Patch prefixe interpreteur : ancre introuvable ou ambigue dans {path} "
              f"(occurrences : {source.count(ANCHOR)}) - Spyder a peut-etre change la construction "
              "du texte, patch non applique.", file=sys.stderr)
        return 1

    patched = source.replace(ANCHOR, REPLACEMENT, 1)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le status.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch prefixe interpreteur applique : plus de prefixe 'Personnalise:' ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
