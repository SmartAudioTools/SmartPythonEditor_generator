#!/usr/bin/env python3
"""Patch pylint/main_widget.py : emettre un signal a la fin d'une analyse pylint.

Demande de l'utilisateur du 26/07/2026 : n'avoir qu'UNE passe de pylint pour les deux affichages - le
panneau « Analyse de code » et la marge de l'editeur. Le panneau reste le seul a lancer pylint ; il
faut donc que quelqu'un puisse apprendre que l'analyse est terminee, pour en reporter les resultats
dans la marge.

POURQUOI UN PATCH ET PAS UN GREFFON. C'est bien la MODIFICATION d'un comportement existant, pas un
ajout : PylintWidget ne prevenait personne de la fin de son travail. Il expose deja deux signaux
(sig_edit_goto_requested, sig_start_analysis_requested), et celui-ci est du meme ordre - « ce que le
panneau a a dire au reste de l'application ». Le greffon SmartOS s'y abonne, cf.
le greffon spyder_code_analysis (depot SmartPythonEditorPlugins).

POURQUOI IL PORTE LE NOM DE FICHIER, ET RIEN D'AUTRE. Les resultats sont deja accessibles par
`get_data(nom_de_fichier)`, l'API publique du panneau, qui rend `(date, note, note_precedente,
resultats)`. Les faire passer aussi par le signal reviendrait a en figer la forme, et Spyder l'a deja
changee par le passe. Le nom de fichier suffit, et il est indispensable : au moment ou le signal
part, l'utilisateur peut avoir change d'onglet, et poser les marques dans le mauvais editeur serait
pire que de ne rien poser.

POURQUOI A LA FIN DE `_finished` ET PAS DANS `set_data`. `set_data` est appele aussi a la
RESTAURATION de l'historique (au demarrage du panneau, pour un fichier qui n'a pas ete analyse dans
cette session) : le signal partirait alors sans qu'aucune analyse n'ait tourne. `_finished` est
appele une fois par analyse REELLEMENT executee, apres que la sortie a ete rangee.

Usage : patch_spyder_pylint_signal_fin.py <chemin vers pylint/main_widget.py installe>

IDEMPOTENCE PAR BLOC : deux blocs, chacun avec SON marqueur, sautes independamment. ⚠ Ce fichier
porte deja les cinq blocs de patch_spyder_pylint_toolbar.py : c'est pourquoi les marqueurs sont
distincts et les ancres choisies dans des zones que l'autre patch ne touche pas (la declaration des
signaux et la fin de `_finished`, alors qu'il travaille sur `setup()`). Un marqueur global unique
rendrait l'un des deux inoperant - piege deja paye sur ce depot. ast.parse avant ecriture, echec
BRUYANT si une ancre manque.
"""
import ast
import sys

PAIRS = [
    # 1. Declaration du signal, a cote des deux autres signaux publics du panneau.
    (
        "[SmartOS signal-fin-analyse-declaration]",
        '''    sig_start_analysis_requested = Signal()
    """
    This signal will request the plugin to start the analysis. This is to be
    able to interact with other plugins, which can only be done at the plugin
    level.
    """''',
        '''    sig_start_analysis_requested = Signal()
    """
    This signal will request the plugin to start the analysis. This is to be
    able to interact with other plugins, which can only be done at the plugin
    level.
    """

    # PATCH SmartOS [SmartOS signal-fin-analyse-declaration] (26/07/2026)
    sig_analysis_finished = Signal(str)
    """
    Emis quand une analyse pylint vient de se terminer et que ses resultats sont ranges.

    Permet a un autre greffon de reporter ces resultats ailleurs - ici, dans la marge de l'editeur
    (greffon spyder_code_analysis), afin que pylint ne tourne qu'UNE fois pour les deux affichages.

    Parameters
    ----------
    filename: str
        Fichier analyse. Indispensable : au moment de l'emission, l'utilisateur peut avoir change
        d'onglet. Les resultats se lisent ensuite par get_data(filename), API publique deja la.
    """''',
    ),
    # 2. Emission, en fin d'analyse reellement executee.
    (
        "[SmartOS signal-fin-analyse-emission]",
        '''        self.output = self.error_output + self.output
        self.show_data(justanalyzed=True)
        self.update_actions()
        self.stop_spinner()''',
        '''        self.output = self.error_output + self.output
        self.show_data(justanalyzed=True)
        self.update_actions()
        self.stop_spinner()

        # PATCH SmartOS [SmartOS signal-fin-analyse-emission] (26/07/2026) : prevenir qui veut que
        # l'analyse est terminee et ses resultats ranges. Emis ICI, et non dans set_data(), qui est
        # aussi appele a la restauration de l'historique - le signal partirait alors sans qu'aucune
        # analyse n'ait tourne.
        self.sig_analysis_finished.emit(filename)''',
    ),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers pylint/main_widget.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"main_widget.py illisible ({erreur}) - patch signal de fin non applique.",
              file=sys.stderr)
        return 1

    appliques = 0
    for marqueur, ancien, nouveau in PAIRS:
        if marqueur in source:
            continue
        n = source.count(ancien)
        if n != 1:
            print(f"Ancre introuvable ou non unique (occurrences={n}) pour {marqueur} dans "
                  f"{chemin} - patch signal de fin non applique.", file=sys.stderr)
            return 1
        source = source.replace(ancien, nouveau, 1)
        appliques += 1

    if appliques == 0:
        print("Patch signal de fin d'analyse : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(source)
    except SyntaxError as erreur:
        print(f"Le main_widget.py patche n'est pas du Python valide ({erreur}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch signal de fin d'analyse applique ({appliques} bloc(s)) : le panneau previent "
          f"desormais de la fin d'une analyse ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
