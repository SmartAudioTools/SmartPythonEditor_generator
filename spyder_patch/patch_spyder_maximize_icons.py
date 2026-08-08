#!/usr/bin/env python3
"""Patch spyder/plugins/layout/container.py : icones personnalisees pour "Agrandir le volet courant",
et BASCULE de l'icone selon l'etat.

Contexte : demande de l'utilisateur du 26/07/2026 - le bouton doit porter ses deux icones,
Commun/icones/spyder/window_full_screen.svg (deux fleches vers l'EXTERIEUR, volet a agrandir) et
window_collapse.svg (deux fleches vers l'INTERIEUR, volet deja agrandi).

DEUX CHANGEMENTS, dont le second n'est pas cosmetique.
  1. L'icone de l'action passe de 'maximize' (livree par Spyder) a 'window_full_screen'.
     create_icon(nom) resout le nom par le gestionnaire d'images, qui indexe tout fichier trouve sous
     spyder/images/ par son nom sans extension : installation_SmartPythonEditor.sh y copie nos deux SVG (dans
     dark/, cf. Commun/icones/spyder/README.txt), il n'y a donc rien d'autre a declarer.
  2. L'icone BASCULE avec l'etat. Spyder n'en changeait pas : l'action est cochable, Qt la dessine
     enfoncee quand elle est cochee, et c'est tout - une meme fleche "agrandir" restait affichee sur
     un volet deja agrandi. On branche donc le signal toggled pour poser window_collapse quand le
     volet est agrandi et window_full_screen sinon. C'est un AJOUT de comportement, pas seulement un
     changement d'image.

⚠ POURQUOI UNE CONNEXION SEPAREE ET NON UNE MODIFICATION DU toggled EXISTANT. Le toggled d'origine
est "lambda state: self._plugin.maximize_dockwidget()" : il ignore deja son argument, et c'est
maximize_dockwidget() qui fait tout le travail. Y greffer la mise a jour de l'icone melangerait deux
responsabilites dans une lambda, et surtout rendrait le patch dependant de la forme exacte de cette
lambda a chaque montee de version. Une connexion supplementaire, posee juste apres la creation de
l'action, ne touche pas au comportement existant : les deux slots sont appeles, dans l'ordre de
connexion.

⚠ ET POURQUOI ON NE SE FIE PAS A isChecked() DANS LE SLOT. Le signal fournit l'etat en argument ;
le lire sur l'action serait une seconde source de verite, et setChecked() est appele de plusieurs
endroits du greffon Layout (switch_to_plugin, unmaximize_dockwidget...) - autant de moments ou l'etat
de l'action et celui du slot pourraient diverger. On utilise l'argument du signal, point.

Usage : patch_spyder_maximize_icons.py <chemin vers plugins/layout/container.py installe>

Idempotent (marqueur). Re-parse avant ecriture ; echec BRUYANT (code 1) si le bloc attendu est
introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_maximize_icons.py"

OLD = '''        # Maximize current dockable plugin
        self._maximize_dockwidget_action = self.create_action(
            LayoutContainerActions.MaximizeCurrentDockwidget,
            text=_('Maximize current pane'),
            icon=self.create_icon('maximize'),
            toggled=lambda state: self._plugin.maximize_dockwidget(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')'''

NEW = '''        # Maximize current dockable plugin
        # SmartOS (patch_spyder_maximize_icons.py) : icones personnalisees a la place de 'maximize',
        # et bascule de l'icone selon l'etat - Spyder gardait la meme fleche "agrandir" sur un volet
        # deja agrandi. Les deux SVG sont deposes dans spyder/images/dark/ par
        # installation_SmartPythonEditor.sh (cf. Commun/icones/spyder/README.txt) : le gestionnaire d'images
        # les indexe par leur nom de fichier, create_icon suffit donc.
        self._maximize_dockwidget_action = self.create_action(
            LayoutContainerActions.MaximizeCurrentDockwidget,
            text=_('Maximize current pane'),
            icon=self.create_icon('window_full_screen'),
            toggled=lambda state: self._plugin.maximize_dockwidget(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')

        # SmartOS : connexion SUPPLEMENTAIRE, plutot qu'une modification du toggled ci-dessus - on ne
        # veut pas dependre de la forme exacte de cette lambda a chaque montee de version. L'icone
        # posee dit ce que FERA le bouton : fleches vers l'interieur quand le volet est agrandi (le
        # clic suivant le remettra en place), vers l'exterieur sinon.
        # L'etat vient de l'ARGUMENT du signal et non de action.isChecked() : setChecked() est appele
        # depuis plusieurs endroits du greffon Layout, et deux sources de verite finiraient par
        # diverger. ⚠ Une lambda et non une methode : ce bloc est au MILIEU de setup(), y dedenter un
        # "def" couperait la methode en deux et le reste de setup() ne s'executerait plus.
        self._maximize_dockwidget_action.toggled.connect(
            lambda agrandi: self._maximize_dockwidget_action.setIcon(
                self.create_icon(
                    'window_collapse' if agrandi else 'window_full_screen')))'''


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/layout/container.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"container.py illisible ({error}) - patch icones d'agrandissement non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch icones d'agrandissement deja applique.")
        return 0

    n = source.count(OLD)
    if n != 1:
        print(f"Bloc de creation de l'action \"Maximize current pane\" introuvable ou non unique "
              f"(occurrences={n}) dans {path} - Spyder a peut-etre restructure son code, patch "
              f"icones d'agrandissement non applique.", file=sys.stderr)
        return 1

    patched = source.replace(OLD, NEW)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le container.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch icones d'agrandissement applique : window_full_screen / window_collapse, avec "
          f"bascule selon l'etat ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
