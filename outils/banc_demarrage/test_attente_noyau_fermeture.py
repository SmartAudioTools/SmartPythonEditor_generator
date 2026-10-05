#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KernelComm._wait ne doit pas boucler quand l'application est en train de quitter.

Reproduit, sans noyau ni fenetre, la course trouvee le 05/10/2026 : un appel bloquant au noyau
lance alors que QApplication.quit() a deja ete demande. Sans le correctif
(spyder_patch/patch_spyder_attente_noyau_fermeture.py), _wait tourne a vide : son
QEventLoop.exec() rend -1 aussitot et le minuteur de delai ne tombe jamais.

Usage, depuis un arbre Spyder (le repertoire courant choisit l'arbre teste) :
    QT_QPA_PLATFORM=offscreen QT_API=pyside6 <python du venv> <ce fichier>
Sortie : « OK » et code 0 si _wait abandonne ; « BOUCLE » et code 1 s'il tourne a vide.
"""

import os
import sys

# Lance comme script, sys.path[0] est le dossier de ce fichier : sans cette ligne, c'est le
# Spyder INSTALLE qui serait teste, pas l'arbre courant.
sys.path.insert(0, os.getcwd())

from qtpy.QtCore import QObject, QTimer, Signal
from qtpy.QtWidgets import QApplication

from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm

TOURS_MAX = 20000


class _Battement(QObject):
    kernel_died = Signal()


class _FauxClient:
    def __init__(self):
        self.hb_channel = _Battement()

    def is_alive(self):
        return True


def main():
    app = QApplication(sys.argv)
    comm = KernelComm()
    comm.kernel_client = _FauxClient()
    resultat = {}

    def essai():
        app.quit()    # la fermeture est demandee, la boucle principale n'est pas encore sortie
        tours = [0]

        def condition():
            tours[0] += 1
            return tours[0] > TOURS_MAX    # borne du test : la vraie reponse ne vient jamais

        try:
            comm._wait(condition, comm._sig_got_reply, "delai", 30)
            resultat["verdict"] = "BOUCLE" if tours[0] > TOURS_MAX else "OK"
        except RuntimeError as erreur:
            resultat["verdict"] = "OK (%s)" % erreur
        resultat["tours"] = tours[0]

    QTimer.singleShot(0, essai)
    app.exec()
    import spyder
    print(resultat.get("verdict", "essai non lance"), "- tours :", resultat.get("tours"),
          "- arbre :", os.path.dirname(spyder.__file__))
    return 0 if resultat.get("verdict", "").startswith("OK") else 1


if __name__ == "__main__":
    sys.exit(main())
