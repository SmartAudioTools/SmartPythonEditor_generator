#!/usr/bin/env python3
"""Supprime l'ecran de demarrage (splash) au lancement normal de SmartPythonEditor.

Mesure du 05/10/2026 (banc de demarrage, hors ecran) : le premier QSplashScreen.show() de
main() (spyder/app/mainwindow.py) bloque 1,0 s FIXE, reproduit en PySide6 nu avec n'importe quel
QSplashScreen, en offscreen, minimal et vnc. Cause probable, non prouvee : QSplashScreen attend
l'exposition de sa fenetre avec un delai de 1000 ms, qui expire faute de compositeur. Sous
Wayland reel, NON MESURE. Dans le doute, l'utilisateur a demande de masquer le splash « pour
l'instant » : ce patch est REVERSIBLE (le retirer de appliquer_correctifs_spyder.sh suffit) et
se juge a la trace de demarrage, sous Wayland, avant d'etre garde ou retire.

Deux blocs, chacun son marqueur :
  - mainwindow.py, main() : `splash = create_splash_screen()` devient `splash = None`. Le code
    aval de main() et de MainWindow teste deja `splash is not None` (create_splash_screen() rend
    None sous pytest) ;
  - plugins/editor/widgets/recover.py, RecoveryDialog.__init__ : SEUL usage aval qui ne le
    testait pas (`hasattr(parent, 'splash')` puis `self.splash.hide()`) - plantage au demarrage
    des qu'il y a des fichiers de sauvegarde automatique a recuperer, constate au banc.
Le splash du REDEMARRAGE (spyder/app/restart.py, qui ne gere pas None) n'est pas touche.

Idempotent (marqueur par bloc), echec bruyant si une ligne amont a change de forme.

Usage : patch_spyder_splash_off.py <racine de l'arbre, contenant spyder/>
"""

import os
import sys

BLOCS = [
    ("spyder/app/mainwindow.py", "# [SmartOS splash-off]",
     "\n    splash = create_splash_screen()\n",
     "\n    splash = None  # [SmartOS splash-off] ecran de demarrage masque, "
     "cf. patch_spyder_splash_off.py\n"),
    ("spyder/plugins/editor/widgets/recover.py", "# [SmartOS splash-off-recover]",
     "\n        if parent and hasattr(parent, 'splash'):\n",
     "\n        if parent and getattr(parent, 'splash', None) is not None:"
     "  # [SmartOS splash-off-recover]\n"),
]


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    erreur = 0
    for relatif, marqueur, ancien, nouveau in BLOCS:
        chemin = os.path.join(sys.argv[1], relatif)
        with open(chemin, encoding="utf-8") as flux:
            contenu = flux.read()
        if marqueur in contenu:
            print(f"Deja applique : {chemin}")
            continue
        if contenu.count(ancien) != 1:
            print(f"ERREUR : motif amont introuvable ou ambigu dans {chemin} - "
                  f"la forme amont a change, bloc NON applique.", file=sys.stderr)
            erreur = 1
            continue
        with open(chemin, "w", encoding="utf-8") as flux:
            flux.write(contenu.replace(ancien, nouveau, 1))
        print(f"Patch splash masque applique : {chemin}")
    return erreur


if __name__ == "__main__":
    sys.exit(main())
