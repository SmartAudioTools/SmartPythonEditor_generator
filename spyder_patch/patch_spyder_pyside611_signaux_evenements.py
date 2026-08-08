#!/usr/bin/env python3
"""Empeche le SEGFAULT de Spyder sous PySide6 >= 6.9, a l'emission d'un signal typé par CHAINE.

Second defaut rencontre en faisant tourner Spyder 6.1.5 sous PySide6 6.11.1, une fois le
premier corrige (patch_spyder_pyside611_signaux.py). Symptome : plus aucune exception,
mais un plantage brutal du processus pendant `main.show()` —

    Fatal Python error: Segmentation fault
    Current thread ...:
      File ".../spyder/app/mainwindow.py", line 1147 in moveEvent
      File ".../spyder/app/utils.py", line 370 in create_window

CAUSE RACINE, reduite a six lignes SANS Spyder (chaque forme testee dans son propre
processus, puisqu'un segfault emporte l'interprete) :

    class W(QMainWindow):
        sig = Signal("QMoveEvent")     # -> SEGFAULT a l'emission
        sig = Signal(QMoveEvent)       # -> OK
        sig = Signal(object)           # -> OK

Declarer le type d'un signal par son NOM entre guillemets est une forme historique de
PyQt/PySide : le type est alors resolu au moment de l'emission, via le systeme de
meta-types de Qt. Sous PySide6 6.11.1 cette resolution ne se fait plus pour les classes
d'evenements, et l'emission dereference un type nul — d'ou le segfault, sans exception
Python possible. Sous 6.8.3, la meme declaration fonctionnait.

Spyder n'utilise cette forme qu'a SIX endroits, tous pour les memes deux classes
d'evenements (QMoveEvent, QResizeEvent) :

    spyder/app/mainwindow.py          sig_resized, sig_moved
    spyder/api/plugins/new_api.py     sig_mainwindow_resized, sig_mainwindow_moved
    spyder/plugins/tours/widgets.py   sig_resized, sig_moved

Ces signaux sont chaines entre eux (`self.sig_moved.connect(plugin.sig_mainwindow_moved)`),
d'ou une regle : il faut convertir les SIX, sinon les signatures cessent de concorder et
la connexion echoue. Le patch traite un fichier par appel, mais tous doivent etre traites.

CORRECTIF : remplacer la chaine par la CLASSE, importee explicitement. Aucun changement de
comportement — c'est le meme type, resolu a l'import au lieu de l'etre a l'emission.

PORTEE : contournement d'un defaut AMONT (PySide6 >= 6.9 face a une forme que Qt/PySide
documentent toujours), a inscrire dans Contournement_bugs_a_supprimer_quand_corrigés.txt.
Test de peremption : retirer le patch, lancer Spyder ; s'il affiche sa fenetre, c'est fini.

Usage : patch_spyder_pyside611_signaux_evenements.py <fichier .py de Spyder>
"""

import ast
import shutil
import sys

MARQUEUR = "[SmartOS pyside611-signaux-evenements]"

IMPORT = ("from qtpy.QtGui import QMoveEvent as _SmartosQMoveEvent, "
          "QResizeEvent as _SmartosQResizeEvent  # PATCH SmartOS " + MARQUEUR + "\n")

#: Les six declarations, sous leurs deux ecritures (avec et sans annotation de type).
REMPLACEMENTS = (
    ('Signal("QResizeEvent")', "Signal(_SmartosQResizeEvent)"),
    ('Signal("QMoveEvent")', "Signal(_SmartosQMoveEvent)"),
    ("Signal('QResizeEvent')", "Signal(_SmartosQResizeEvent)"),
    ("Signal('QMoveEvent')", "Signal(_SmartosQMoveEvent)"),
)


def _inserer_import(source):
    """Pose l'import juste apres le dernier import de qtpy, pour rester lisible.

    On ne le met pas en tete du fichier : les modules de Spyder commencent par une
    longue en-tete de licence, et un import glisse dedans se lit comme une erreur.
    """
    lignes = source.splitlines(keepends=True)
    dernier = None
    for index, ligne in enumerate(lignes):
        if ligne.startswith("from qtpy") or ligne.startswith("import qtpy"):
            dernier = index
    if dernier is None:
        return None
    # Sauter les lignes de continuation d'un import multi-lignes : on suit le SOLDE des
    # parentheses jusqu'a ce qu'il retombe a zero. Compter ligne a ligne ne suffit pas —
    # une ligne du milieu est equilibree sans que l'import soit termine, et l'import se
    # retrouvait insere au beau milieu (echec du controle de syntaxe, 26/07/2026).
    solde = lignes[dernier].count("(") - lignes[dernier].count(")")
    while solde > 0 and dernier + 1 < len(lignes):
        dernier += 1
        solde += lignes[dernier].count("(") - lignes[dernier].count(")")
    lignes.insert(dernier + 1, IMPORT)
    return "".join(lignes)


def principal(chemin):
    source = open(chemin, encoding="utf-8").read()

    if MARQUEUR in source:
        print("Deja applique (%s) : rien a faire." % MARQUEUR)
        return 0

    trouves = sum(source.count(ancien) for ancien, _neuf in REMPLACEMENTS)
    if trouves == 0:
        print("ECHEC : aucune declaration de signal typee par chaine dans %s" % chemin,
              file=sys.stderr)
        print("        (le defaut a peut-etre ete corrige en amont, ou le fichier a "
              "change : verifier avant de rejouer.)", file=sys.stderr)
        return 1

    nouveau = source
    for ancien, neuf in REMPLACEMENTS:
        nouveau = nouveau.replace(ancien, neuf)

    nouveau = _inserer_import(nouveau)
    if nouveau is None:
        print("ECHEC : aucun import qtpy dans %s, impossible de placer l'import."
              % chemin, file=sys.stderr)
        return 1

    try:
        ast.parse(nouveau)
    except SyntaxError as erreur:
        print("ECHEC : le resultat n'est pas du Python valide : %s" % erreur,
              file=sys.stderr)
        return 1

    shutil.copyfile(chemin, chemin + ".smartos.bak")
    open(chemin, "w", encoding="utf-8").write(nouveau)
    print("Applique %s a %s (%d declaration(s) converties)" % (MARQUEUR, chemin, trouves))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(principal(sys.argv[1]))
