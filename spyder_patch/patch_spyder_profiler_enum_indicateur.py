#!/usr/bin/env python3
"""Patch profiler/widgets/profiler_data_tree.py : l'arbre du profileur plantait sous PySide6.

BUG AMONT DE SPYDER, revele par le passage a PySide6 6.11. Signale par l'utilisateur le 26/07/2026 :
lancer le profileur sur un fichier leve

    File ".../spyder/plugins/profiler/widgets/profiler_data_tree.py", line 848, in populate_tree
        child_item.ShowIndicator
    AttributeError: 'TreeWidgetItem' object has no attribute 'ShowIndicator'

et l'arbre des resultats reste vide.

CAUSE RACINE. Le code lit une ENUMERATION Qt SUR L'INSTANCE :

    child_item.setChildIndicatorPolicy(child_item.ShowIndicator)

C'etait tolere par les anciens bindings, qui exposaient les membres d'enumeration comme attributs de
l'objet. PySide6 ne les expose plus que sur la CLASSE. Mesure faite avant d'ecrire une ligne, avec le
PySide6 installe :

    item.ShowIndicator ................................ AttributeError
    QTreeWidgetItem.ShowIndicator .................... <ChildIndicatorPolicy.ShowIndicator: 0>
    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator <ChildIndicatorPolicy.ShowIndicator: 0>

CE QUE FAIT LE PATCH. Il ecrit la forme PLEINEMENT SCOPEE,
`QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator`, et non l'alias plat de la classe qui marche
aujourd'hui : cet alias est precisement ce que Qt supprime peu a peu. La classe est deja importee dans
le fichier, il n'y a donc pas d'import a ajouter.

CE QUI DECLENCHE LE DEFAUT : une fonction profilee ayant des PETITS-ENFANTS dans l'arbre d'appels.
C'est la seule branche qui pose un indicateur d'expansion, ce qui explique qu'il ne se voie pas sur
tous les fichiers.

⚠ CE N'EST PAS LE MEME CHANTIER que les correctifs marques [SmartOS pyside611-signaux-completion] :
ceux-la portent sur des SIGNAUX tues par la lecture d'un attribut d'instance pendant la construction.
Ici il s'agit d'une ENUMERATION, dans un autre fichier. La parente est reelle - les deux viennent du
durcissement de PySide6 - mais le correctif et le perimetre sont distincts.

COMMENT SAVOIR SI C'EST ENCORE NECESSAIRE : relire `populate_tree()`. Si l'amont y ecrit desormais
l'enumeration sur la CLASSE, le patch peut disparaitre. Test de bout en bout : profiler un fichier dont
une fonction profilee en appelle une autre qui en appelle une troisieme, et verifier que l'arbre
s'affiche avec ses fleches d'expansion.

Usage : patch_spyder_profiler_enum_indicateur.py <chemin vers profiler_data_tree.py installe>

IDEMPOTENCE : saute si son marqueur est deja present. Ancrage sur un motif UNIQUE, ast.parse avant
ecriture, echec BRUYANT (code 1) si l'ancre manque - jamais deviner.
"""
import ast
import sys

MARQUEUR = "[SmartOS enum-indicateur-scopee]"

ANCIEN = """                    child_item.setChildIndicatorPolicy(
                        child_item.ShowIndicator
                    )"""

NOUVEAU = """                    # PATCH SmartOS %s (26/07/2026) : l'enumeration
                    # est lue sur la CLASSE, et sous sa forme pleinement scopee. La lire sur
                    # l'INSTANCE (child_item.ShowIndicator) leve AttributeError sous PySide6, qui
                    # n'expose plus les membres d'enumeration sur les objets - l'arbre du profileur
                    # restait alors vide. On evite aussi l'alias plat QTreeWidgetItem.ShowIndicator,
                    # qui fonctionne encore mais que Qt supprime peu a peu.
                    child_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )""" % MARQUEUR


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers profiler_data_tree.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"profiler_data_tree.py illisible ({erreur}) - patch enumeration non applique.",
              file=sys.stderr)
        return 1

    if MARQUEUR in source:
        print("Patch enumeration de l'indicateur : deja en place.")
        return 0

    n = source.count(ANCIEN)
    if n != 1:
        print(f"Ancre introuvable ou non unique (occurrences={n}) dans {chemin} - populate_tree() a "
              f"peut-etre change, patch enumeration non applique.", file=sys.stderr)
        return 1

    patchee = source.replace(ANCIEN, NOUVEAU, 1)
    if "QTreeWidgetItem," not in patchee and "QTreeWidgetItem" not in patchee.split("class ")[0]:
        print(f"QTreeWidgetItem n'est pas importe dans {chemin} - patch enumeration non applique "
              "plutot que d'ajouter un import a l'aveugle.", file=sys.stderr)
        return 1

    try:
        ast.parse(patchee)
    except SyntaxError as erreur:
        print(f"Le profiler_data_tree.py patche n'est pas du Python valide ({erreur}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(patchee)
    print(f"Patch enumeration de l'indicateur applique : l'arbre du profileur ne plante plus "
          f"({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
