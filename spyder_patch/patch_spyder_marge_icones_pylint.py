#!/usr/bin/env python3
"""Patch editor/panels/linenumber.py : la marge emploie les MEMES icones que le panneau d'analyse.

Demande de l'utilisateur du 26/07/2026 : « peux-tu utiliser dans la marge les memes icones que dans
le panneau d'analyse de code ? »

CE QUE LA MESURE A MONTRE AVANT D'ECRIRE, et qui reduit le travail de moitie : DEUX des quatre icones
sont DEJA les memes. Le panneau (PylintWidget.CATEGORIES) et la marge (LineNumberArea) puisent au meme
gestionnaire d'icones :
    Erreur ......... 'error'   = mdi.close-circle ... marge ET panneau : IDENTIQUE, rien a faire
    Avertissement .. 'warning' = mdi.alert .......... marge ET panneau : IDENTIQUE, rien a faire
    Convention ..... panneau : 'convention' = mdi.alpha-c-circle (un « C » cercle)
                     marge   : 'information'                     (un « i » cercle)   <- a changer
    Factorisation .. panneau : 'refactor'   = mdi.alpha-r-circle (un « R » cercle)
                     marge   : 'hint'                                                <- a changer

POURQUOI LA MARGE NE POUVAIT PAS DEJA LES METTRE. Elle choisit son icone d'apres la SEVERITE LSP
(erreur / avertissement / information / indice), pas d'apres la famille pylint - qu'elle n'a aucune
raison de connaitre, les diagnostics venant en general d'un serveur de langage quelconque. Or la
famille est LISIBLE dans l'identifiant du message : C0114 est une convention, R0903 une factorisation.
C'est cette lecture que le patch ajoute, et UNIQUEMENT pour les marques de source « pylint » : un
diagnostic d'un autre outil garde les icones habituelles de la marge.

⚠ MESURE FAITE AVANT D'INTEGRER, parce que les deux icones du panneau portent un facteur
d'agrandissement (BIG_ATTR_FACTOR) qui pouvait les rendre plus grosses que leurs voisines - le defaut
exact deja paye sur le carre du bouton Stop. Encre relevee au rendu, cote du cadre :
    error 74 % x 75 %   warning 82 % x 71 %   convention 75 % x 75 %   refactor 74 % x 75 %
Le facteur ne fait que compenser le vide interne du glyphe : les quatre sont homogenes, il n'y a rien
a corriger.

⚠ ORDRE D'APPLICATION : ce patch doit venir APRES patch_spyder_error_margin.py, qui REMPLACE
integralement paintEvent (reperage par ast). Applique avant, il serait efface sans bruit. Les
installation_SmartPythonEditor.sh respectent cet ordre.

Usage : patch_spyder_marge_icones_pylint.py <chemin vers editor/panels/linenumber.py installe>

IDEMPOTENCE PAR BLOC, chacun avec SON marqueur : le chargement des deux icones et leur emploi dans
paintEvent. ast.parse avant ecriture, echec BRUYANT si une ancre manque ou n'est pas unique.
"""
import ast
import sys

PAIRS = [
    # 1. Charger les deux icones du panneau, a cote de celles de la marge.
    (
        "[SmartOS marge-icones-pylint-chargement]",
        """        self.info_icon = ima.icon('information')
        self.hint_icon = ima.icon('hint')""",
        """        self.info_icon = ima.icon('information')
        self.hint_icon = ima.icon('hint')
        # PATCH SmartOS [SmartOS marge-icones-pylint-chargement] (26/07/2026) : les deux icones du
        # panneau « Analyse de code » (PylintWidget.CATEGORIES), pour que la marge montre le meme
        # dessin que lui - un « C » cercle pour une convention, un « R » pour une factorisation. Les
        # deux autres familles, erreur et avertissement, utilisent DEJA la meme icone de part et
        # d'autre : il n'y avait que ces deux-la a ajouter.
        self.convention_icon = ima.icon('convention')
        self.refactor_icon = ima.icon('refactor')""",
    ),
    # 2. Les employer, mais seulement pour les marques venant de pylint.
    (
        "[SmartOS marge-icones-pylint-emploi]",
        """                    for _, _, sev, _ in data.code_analysis:
                        errors += sev == DiagnosticSeverity.ERROR
                        warnings += sev == DiagnosticSeverity.WARNING
                        infos += sev == DiagnosticSeverity.INFORMATION
                        hints += sev == DiagnosticSeverity.HINT

                    if errors:
                        draw_pixmap(1, top, self.error_icon.pixmap(icon_size))
                    elif warnings:
                        draw_pixmap(
                            1, top, self.warning_icon.pixmap(icon_size))
                    elif infos:
                        draw_pixmap(1, top, self.info_icon.pixmap(icon_size))
                    elif hints:
                        draw_pixmap(1, top, self.hint_icon.pixmap(icon_size))""",
        """                    # PATCH SmartOS [SmartOS marge-icones-pylint-emploi] (26/07/2026) : la
                    # marge choisit son icone d'apres la SEVERITE LSP, qui ne dit pas la famille
                    # pylint. Or celle-ci se lit dans l'identifiant du message - C0114 est une
                    # convention, R0903 une factorisation - ce qui permet de montrer le MEME dessin
                    # que le panneau « Analyse de code ». Ne concerne que les marques de source
                    # « pylint » : un diagnostic venu d'ailleurs garde les icones habituelles.
                    convention_pylint = False
                    refactor_pylint = False
                    for _source, _code, sev, _ in data.code_analysis:
                        errors += sev == DiagnosticSeverity.ERROR
                        warnings += sev == DiagnosticSeverity.WARNING
                        infos += sev == DiagnosticSeverity.INFORMATION
                        hints += sev == DiagnosticSeverity.HINT
                        if _source == 'pylint' and isinstance(_code, str):
                            convention_pylint = convention_pylint or _code.startswith('C')
                            refactor_pylint = refactor_pylint or _code.startswith('R')

                    if errors:
                        draw_pixmap(1, top, self.error_icon.pixmap(icon_size))
                    elif warnings:
                        draw_pixmap(
                            1, top, self.warning_icon.pixmap(icon_size))
                    elif infos:
                        draw_pixmap(1, top, (
                            self.convention_icon if convention_pylint else self.info_icon
                        ).pixmap(icon_size))
                    elif hints:
                        draw_pixmap(1, top, (
                            self.refactor_icon if refactor_pylint else self.hint_icon
                        ).pixmap(icon_size))""",
    ),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers editor/panels/linenumber.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"linenumber.py illisible ({erreur}) - patch icones de marge non applique.",
              file=sys.stderr)
        return 1

    appliques = 0
    for marqueur, ancien, nouveau in PAIRS:
        if marqueur in source:
            continue
        n = source.count(ancien)
        if n != 1:
            print(f"Ancre introuvable ou non unique (occurrences={n}) pour {marqueur} dans "
                  f"{chemin}. ⚠ Ce patch doit venir APRES patch_spyder_error_margin.py, qui remplace "
                  f"paintEvent. Patch icones de marge non applique.", file=sys.stderr)
            return 1
        source = source.replace(ancien, nouveau, 1)
        appliques += 1

    if appliques == 0:
        print("Patch icones de marge pylint : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(source)
    except SyntaxError as erreur:
        print(f"Le linenumber.py patche n'est pas du Python valide ({erreur}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch icones de marge pylint applique ({appliques} bloc(s)) : conventions et "
          f"factorisations portent le meme dessin que dans le panneau ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
