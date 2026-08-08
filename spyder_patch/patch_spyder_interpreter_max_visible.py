#!/usr/bin/env python3
"""Patch spyder/plugins/maininterpreter/confpage.py : agrandit la liste deroulante du combobox
"Recent custom interpreters" des Preferences (page Interpreteur principal).

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", "le menu pour selectionner les
interpreteurs n'est pas assez grand pour qu'ils soient tous visibles") : Qt limite par defaut
maxVisibleItems a 10 lignes avant de faire apparaitre un ascenseur dans la liste deroulante d'un
QComboBox. Sur cette machine, custom_interpreters_list contient 14 entrees (versions pyenv +
alias SmartPython) : la moitie reste hors vue sans faire defiler. Meme correctif que
Commun/spyder_plugins/spyder_interpreter_toolbar/.../combobox.py, cote greffon, pour la barre
d'outils "Interpreteur" qui a remplace ce menu en pratique.

Usage : patch_spyder_interpreter_max_visible.py <chemin vers maininterpreter/confpage.py installe>

Localisation par ancrage de TEXTE EXACT (unique). Idempotent (marqueur). Re-parse avant ecriture ;
echoue BRUYAMMENT (code de sortie 1) si l'ancre manque - jamais deviner.
"""
import ast
import sys

MARKER = "maxVisibleItems porte a 30 (SmartOS"
ANCHOR = (
    "        self.cus_exec_combo.setStyleSheet(\"margin-left: 3px\")\n"
    "        self.cus_exec_combo.combobox.setMinimumWidth(400)\n"
)
REPLACEMENT = (
    "        self.cus_exec_combo.setStyleSheet(\"margin-left: 3px\")\n"
    "        self.cus_exec_combo.combobox.setMinimumWidth(400)\n"
    "        # maxVisibleItems porte a 30 (SmartOS, cf.\n"
    "        # Commun/scripts/patch_spyder_interpreter_max_visible.py) : le defaut Qt (10) force un\n"
    "        # ascenseur des que la liste d'interpreteurs personnalises depasse 10 entrees.\n"
    "        self.cus_exec_combo.combobox.setMaxVisibleItems(30)\n"
)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers maininterpreter/confpage.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"confpage.py illisible ({error}) - patch maxVisibleItems non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch maxVisibleItems interpreteur Spyder deja applique.")
        return 0

    if source.count(ANCHOR) != 1:
        print(f"Patch maxVisibleItems interpreteur : ancre introuvable ou ambigue dans {path} "
              f"(occurrences : {source.count(ANCHOR)}) - Spyder a peut-etre change la construction "
              "de ce combobox, patch non applique.", file=sys.stderr)
        return 1

    patched = source.replace(ANCHOR, REPLACEMENT, 1)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le confpage.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch maxVisibleItems interpreteur applique : liste deroulante jusqu'a 30 lignes "
          f"({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
