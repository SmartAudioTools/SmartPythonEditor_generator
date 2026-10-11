"""Banc du conge concave au pied de l'onglet actif (patch_spyder_arrondi_onglet.py).

Un BaseTabs a trois onglets portant un CodeEditor (focus donne a l'editeur : contour bleu),
sous la feuille d'application de Spyder. Pour chaque flanc de l'onglet actif, lit le pixel du
coin interieur du conge (juste a l'exterieur du flanc, sur la derniere ligne de la barre) :
  - flanc avec conge  : la couleur de l'onglet (fond d'editeur eclairci) ;
  - flanc sans conge  : autre chose (le cadre du volet ou le fond, qui se voient a travers la
    barre transparente).
Verifie : onglet du milieu, deux conges ; premier onglet, pas de conge a gauche ; dernier onglet
avec un volet reduit a la largeur des onglets, pas de conge a droite ; dernier onglet dans un
volet large, conge a droite. Rend 0 si tout tient, 1 sinon.
Avec un chemin en argument, enregistre une capture agrandie (x4) de chaque etat, nommee
<chemin>_<etat>.png.

A lancer HORS ECRAN, avec un HOME separe (jamais la configuration reelle de l'utilisateur) :
    env HOME=$TMPDIR/home QT_API=pyside6 QT_QPA_PLATFORM=offscreen <python de l'env> \
        banc_arrondi_onglet.py [prefixe des captures]
Sans le patch (PYTHONPATH vers un arbre spyder non patche), il doit echouer.
"""
import sys
import warnings

warnings.filterwarnings("ignore")
from qtpy.QtGui import QColor  # noqa: E402
from qtpy.QtWidgets import QApplication, QHBoxLayout, QWidget  # noqa: E402

app = QApplication(sys.argv)
from spyder.utils.stylesheet import (  # noqa: E402
    APP_STYLESHEET, SMARTOS_ECLAIRCISSEMENT, smartos_editor_background)
from spyder.widgets.tabs import BaseTabs  # noqa: E402
from spyder.plugins.editor.widgets.codeeditor import CodeEditor  # noqa: E402

app.setStyleSheet(str(APP_STYLESHEET))
fenetre = QWidget()
disposition = QHBoxLayout(fenetre)
disposition.setContentsMargins(0, 0, 0, 0)
onglets = BaseTabs(fenetre)
onglets.setDocumentMode(True)  # comme l'editeur et la console IPython, les volets vises
editeur = CodeEditor(onglets)
editeur.setup_editor(language="python", color_scheme="spyder/dark", linenumbers=True)
editeur.set_text("x = 1\n")
onglets.addTab(editeur, "a.py")
onglets.addTab(QWidget(), "b.py")
onglets.addTab(QWidget(), "c.py")
disposition.addWidget(onglets)
LARGE = 600
fenetre.resize(LARGE, 200)
fenetre.show()
editeur.setFocus()
app.processEvents()

FOND_ONGLET = QColor(smartos_editor_background()).lighter(SMARTOS_ECLAIRCISSEMENT).name()
prefixe = sys.argv[1] if len(sys.argv) > 1 else None
barre = onglets.tabBar()
echecs = 0


def pixel(x, y):
    """Couleur du pixel (x, y) de la barre, lue sur une capture de la fenetre."""
    image = fenetre.grab().toImage()
    ratio = image.devicePixelRatio()
    point = barre.mapTo(fenetre, barre.rect().topLeft())
    return image.pixelColor(int((point.x() + x) * ratio), int((point.y() + y) * ratio)).name()


def flancs(index, etat):
    """Couleur au coin interieur du conge de chaque flanc de l'onglet `index`, actif."""
    onglets.setCurrentIndex(index)
    app.processEvents()
    zone = barre.tabRect(index)
    y = barre.height() - 1
    if prefixe:
        image = fenetre.grab()
        r = image.devicePixelRatio()
        largeur = min(fenetre.width(), 300)
        image.copy(0, 0, int(largeur * r), int(50 * r)).scaled(
            int(largeur * r) * 4, int(50 * r) * 4).save(f"{prefixe}_{etat}.png")
    # Bornes : l'onglet au bord n'a rien a l'exterieur, on lit alors sa propre colonne de bord.
    return (pixel(max(zone.left() - 1, 0), y),
            pixel(min(zone.right() + 1, barre.width() - 1), y))


def verifier(condition, message):
    global echecs
    print(("OK    " if condition else "ECHEC ") + message)
    echecs += not condition


gauche, droite = flancs(1, "milieu")
verifier(gauche == FOND_ONGLET and droite == FOND_ONGLET,
         f"onglet du milieu : conge des deux cotes ({gauche}, {droite}, attendu {FOND_ONGLET})")
gauche, droite = flancs(0, "premier")
verifier(gauche != FOND_ONGLET and droite == FOND_ONGLET,
         f"premier onglet : pas de conge a gauche, conge a droite ({gauche}, {droite})")
gauche, droite = flancs(2, "dernier_large")
verifier(gauche == FOND_ONGLET and droite == FOND_ONGLET,
         f"dernier onglet, volet large : conge des deux cotes ({gauche}, {droite})")
# Volet reduit pile a la largeur des onglets : le dernier touche le bord droit.
bord_droit = barre.mapTo(onglets, barre.tabRect(2).topRight()).x() + 1
fenetre.resize(bord_droit, 200)
app.processEvents()
gauche, droite = flancs(2, "dernier_au_bord")
touche = barre.mapTo(onglets, barre.tabRect(2).topRight()).x() + 1 >= onglets.width()
verifier(touche and gauche == FOND_ONGLET and droite != FOND_ONGLET,
         f"dernier onglet au bord droit du volet : conge a gauche seulement "
         f"(touche={touche}, {gauche}, {droite})")
sys.exit(1 if echecs else 0)
