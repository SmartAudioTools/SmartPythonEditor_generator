#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile a la demande les expressions regulieres des colorations syntaxiques.

Contexte (TODO - Spyder - accélération démarage.txt, etape 6, 05/10/2026) : chaque classe de
coloration de spyder/utils/syntaxhighlighters.py (Python, Cython, C++, OpenCL, Fortran, IDL,
NSIS, gettext, YAML, HTML, Markdown...) compile sa grande expression reguliere `PROG` dans le
CORPS de la classe, donc a l'import du module : 22 compilations, 30 ms mesurees hors profileur
(sur 39 ms d'import), alors qu'un demarrage n'en utilise qu'une ou deux (Python, IPython).

-> `PROG = re.compile(...)` devient `PROG = _SmartosRegexParesseuse(...)` : les ARGUMENTS sont
   evalues comme avant (le texte du motif est construit a l'import, c'est peu), la compilation
   attend la premiere lecture de l'attribut, puis l'objet compile remplace le descripteur dans la
   classe : les lectures suivantes ne coutent rien de plus qu'en amont.

Seuls les attributs `PROG` definis par un appel direct a re.compile dans un corps de classe sont
touches ; les petits motifs (IDPROG, ASPROG...) restent compiles a l'import.

Usage : patch_spyder_regex_coloration_paresseuses.py <spyder/utils/syntaxhighlighters.py>
Idempotent (marqueur _SmartosRegexParesseuse), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_SmartosRegexParesseuse"
AMONT = "re.compile"

BLOC = '''

# ---- SmartOS (_SmartosRegexParesseuse) : motifs de coloration compiles a la demande -------------
# Les compiler tous a l'import coutait 30 ms pour un ou deux motifs utilises. Voir
# spyder_patch/patch_spyder_regex_coloration_paresseuses.py du generator.
class _SmartosRegexParesseuse:
    """Attribut de classe : re.compile(*arguments) a la premiere lecture, puis l'objet compile."""

    def __init__(self, *arguments):
        self.arguments = arguments

    def __set_name__(self, classe, nom):
        self.nom = nom

    def __get__(self, instance, classe):
        motif = re.compile(*self.arguments)
        for parente in classe.__mro__:
            if parente.__dict__.get(self.nom) is self:
                setattr(parente, self.nom, motif)
        return motif
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR in source:
        print(f"Deja patche : {chemin}")
        return True
    arbre = ast.parse(source)
    imports = [n for n in arbre.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    noms = {alias.asname or alias.name for n in imports if isinstance(n, ast.Import)
            for alias in n.names}
    cibles = []  # (ligne base 0, colonne) de chaque `re.compile` a remplacer
    for classe in arbre.body:
        if not isinstance(classe, ast.ClassDef):
            continue
        for n in classe.body:
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "PROG"
                    and isinstance(n.value, ast.Call)
                    and ast.unparse(n.value.func) == AMONT
                    and not n.value.keywords):
                cibles.append((n.value.func.lineno - 1, n.value.func.col_offset))
    if "re" not in noms or len(cibles) < 5:
        print(f"ERREUR : `import re` ou les `PROG = re.compile(...)` des classes de coloration "
              f"sont introuvables dans {chemin} ({len(cibles)} trouves) - la forme amont a "
              f"change.", file=sys.stderr)
        return False
    lignes = source.splitlines(keepends=True)
    for ligne, colonne in cibles:
        # Sources ASCII sur ces lignes : colonne en octets = colonne en caracteres.
        if lignes[ligne][colonne:colonne + len(AMONT)] != AMONT:
            print(f"ERREUR : position inattendue ligne {ligne + 1} de {chemin}.",
                  file=sys.stderr)
            return False
        lignes[ligne] = lignes[ligne][:colonne] + MARQUEUR + lignes[ligne][colonne + len(AMONT):]
    fin_imports = imports[-1].end_lineno
    resultat = "".join(lignes[:fin_imports]) + BLOC + "".join(lignes[fin_imports:])
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche ({len(cibles)} motifs) : {chemin}")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/utils/syntaxhighlighters.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
