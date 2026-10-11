"""Banc du focus des volets (patch_spyder_focus_volet.py + regles de patch_spyder_colors.py).

Un BaseTabs portant un CodeEditor, a cote d'un QTreeView, sous la feuille d'application de
Spyder. Donne le focus a l'editeur puis a l'arbre, et verifie :
  - focus editeur : fond de l'editeur eclairci, bord de l'onglet actif bleu (COLOR_ACCENT_3) ;
  - focus arbre   : fond de l'arbre eclairci, editeur et bord d'onglet revenus a la normale.
Rend 0 si tout tient, 1 sinon, et imprime chaque releve.

A lancer HORS ECRAN, avec un HOME separe (jamais la configuration reelle de l'utilisateur) :
    env HOME=$TMPDIR/home QT_API=pyside6 QT_QPA_PLATFORM=offscreen <python de l'env> banc_focus_volet.py
Sans le patch (PYTHONPATH vers un arbre spyder non patche), il doit echouer.
"""
import sys
import warnings

warnings.filterwarnings("ignore")
from qtpy.QtGui import QColor  # noqa: E402
from qtpy.QtWidgets import QApplication, QHBoxLayout, QTreeView, QWidget  # noqa: E402

app = QApplication(sys.argv)
from spyder.utils.palette import SpyderPalette  # noqa: E402
from spyder.utils.stylesheet import APP_STYLESHEET  # noqa: E402
from spyder.widgets.tabs import BaseTabs  # noqa: E402
from spyder.plugins.editor.widgets.codeeditor import CodeEditor  # noqa: E402

app.setStyleSheet(str(APP_STYLESHEET))
fenetre = QWidget()
disposition = QHBoxLayout(fenetre)
onglets = BaseTabs(fenetre)
editeur = CodeEditor(onglets)
editeur.setup_editor(language="python", color_scheme="spyder/dark", linenumbers=True)
editeur.set_text("x = 1\n")
onglets.addTab(editeur, "a.py")
onglets.addTab(QWidget(), "b.py")
arbre = QTreeView(fenetre)
disposition.addWidget(onglets)
disposition.addWidget(arbre)
fenetre.resize(800, 300)
fenetre.show()
app.processEvents()

BLEU = QColor(SpyderPalette.COLOR_ACCENT_3).name()


def releve():
    image = fenetre.grab().toImage()
    ratio = image.devicePixelRatio()

    def pixel(widget, x, y):
        point = widget.mapTo(fenetre, widget.rect().topLeft())
        return image.pixelColor(int((point.x() + x) * ratio),
                                int((point.y() + y) * ratio)).name()

    # Le bord de l'onglet actif est decale par sa marge : on cherche le bleu sur toute la
    # ligne mediane de l'onglet plutot qu'en un point.
    barre = onglets.tabBar()
    zone = barre.tabRect(barre.currentIndex())
    ligne = {pixel(barre, x, zone.center().y()) for x in range(zone.left(), zone.right() + 1)}
    vue = editeur.viewport()
    return {
        "editeur": pixel(vue, vue.width() - 10, vue.height() - 10),
        "arbre": pixel(arbre.viewport(), 10, arbre.viewport().height() - 10),
        "onglet_bleu": BLEU in ligne,
    }


echecs = 0


def verifier(condition, message):
    global echecs
    print(("OK    " if condition else "ECHEC ") + message)
    echecs += not condition


editeur.setFocus()
app.processEvents()
focus_editeur = releve()
arbre.setFocus()
app.processEvents()
focus_arbre = releve()
print("focus editeur :", focus_editeur)
print("focus arbre   :", focus_arbre)

verifier(focus_editeur["onglet_bleu"], "bord d'onglet bleu quand l'editeur a le focus")
verifier(not focus_arbre["onglet_bleu"], "bord d'onglet redevenu non bleu quand l'arbre a le focus")
verifier(QColor(focus_editeur["editeur"]).lightness() > QColor(focus_arbre["editeur"]).lightness(),
         "editeur plus clair avec le focus que sans")
verifier(QColor(focus_arbre["arbre"]).lightness() > QColor(focus_editeur["arbre"]).lightness(),
         "arbre plus clair avec le focus que sans")
sys.exit(1 if echecs else 0)
