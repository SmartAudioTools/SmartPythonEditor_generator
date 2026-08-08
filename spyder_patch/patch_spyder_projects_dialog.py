#!/usr/bin/env python3
"""Patch spyder/plugins/projects/widgets/projectdialog.py : repertoire par defaut d'un projet neuf.

Le dialogue "Creer un nouveau projet" (page "Selectionner un repertoire") arrive avec son champ
"Repertoire" VIDE : l'etudiant doit saisir ou parcourir jusqu'a l'arborescence des projets a chaque
creation, et le bouton "Parcourir" part de son dossier personnel (select_directory() se rabat sur
get_home_dir() quand le champ n'est pas un dossier existant). On le pre-remplit avec
SMARTOS_PROJECTS_ROOT, la meme racine que celle listee par le combo du panneau Projets.

Deux effets pour un seul reglage : le champ est deja bon si l'etudiant ne fait que saisir un nom de
projet, et le bouton "Parcourir" s'ouvre desormais SUR cette racine.

Seule la page "Selectionner un repertoire" est concernee. La page "Repertoire existant" designe le
projet LUI-MEME (son champ s'appelle "Chemin du projet") : y pre-remplir la racine ferait proposer
la racine entiere comme projet, ce qui est valide pour Spyder et faux pour nous.

Un dossier absent est laisse tel quel (champ vide, comportement d'origine) : les autres
distributions n'ont pas cette arborescence.

Usage : patch_spyder_projects_dialog.py <chemin vers projects/widgets/projectdialog.py installe>

Remplacements de blocs exacts, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# Racine des projets : definie une seule fois, dans le patch du panneau Projets, qui l'injecte dans
# main_widget.py pour alimenter son combo. Ici elle sert de valeur par defaut du dialogue de
# creation - c'est le meme fait, il ne doit pas pouvoir diverger.
from patch_spyder_projects_toolbar import SMARTOS_PROJECTS_ROOT

MARKER = "patch_spyder_projects_dialog.py"

# Liste de (ancien, nouveau). Tous doivent matcher exactement et une seule fois.
PAIRS = [
    # 1. La racine, en tete du module.
    (
        '''# =============================================================================
# ---- Auxiliary functions and classes
# =============================================================================''',
        '''# SmartOS (patch_spyder_projects_dialog.py) : repertoire propose par defaut pour un projet neuf.
# Meme valeur que la racine scannee par le combo du panneau Projets (patch_spyder_projects_toolbar).
SMARTOS_PROJECTS_ROOT = "@SMARTOS_PROJECTS_ROOT@"


# =============================================================================
# ---- Auxiliary functions and classes
# =============================================================================''',
    ),
    # 2. Pre-remplissage du champ "Repertoire" de la page "Selectionner un repertoire".
    (
        '''            status_icon=ima.icon("error"),
        )

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addWidget(docs_reference)''',
        '''            status_icon=ima.icon("error"),
        )

        # SmartOS (patch_spyder_projects_dialog.py) : champ pre-rempli plutot que vide. Il sert
        # aussi de point de depart au bouton "Parcourir", qui repartait sinon du dossier personnel.
        if osp.isdir(SMARTOS_PROJECTS_ROOT):
            self._location.textbox.setText(SMARTOS_PROJECTS_ROOT)

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addWidget(docs_reference)''',
    ),
]

PAIRS = [
    (old, new.replace("@SMARTOS_PROJECTS_ROOT@", SMARTOS_PROJECTS_ROOT))
    for old, new in PAIRS
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers projects/widgets/projectdialog.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"projectdialog.py illisible ({error}) - patch repertoire par defaut non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch repertoire par defaut du dialogue de projet deja applique.")
        return 0

    # Verifier d'abord que TOUS les blocs sont presents et uniques (sinon on n'ecrit rien).
    for old, _new in PAIRS:
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch repertoire par defaut non applique. "
                  f"Bloc:\n{old[:80]}...", file=sys.stderr)
            return 1

    patched = source
    for old, new in PAIRS:
        patched = patched.replace(old, new)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le projectdialog.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch repertoire par defaut du dialogue de projet applique : {SMARTOS_PROJECTS_ROOT} "
          f"({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
