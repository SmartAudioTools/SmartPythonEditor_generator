"""Banc du conge concave au pied de l'onglet actif (patch_spyder_arrondi_onglet.py).

Un BaseTabs a trois onglets portant chacun un CodeEditor (focus donne a l'editeur actif : contour bleu),
sous la feuille d'application de Spyder. Pour chaque flanc de l'onglet actif, lit sur une capture :
  - le conge : le pixel juste a l'exterieur du flanc, sur la ligne au-dessus du cadre, porte
    l'arc (il differe du fond de la barre lu plus loin) - ou non, pour un flanc sans conge ;
  - le raccord : la colonne du flanc et le trait haut du cadre restent a la couleur du contour
    jusqu'au depart de l'arc (jusqu'au coin sans conge) ; avec conge, le coin des deux traits est
    recouvert et chaque ligne du conge porte un pixel d'arc. L'ancien conge (11/10/2026) partait
    1 a 2 px a cote du flanc gauche, bavait sur deux pixels et laissait le coin carre visible ;
  - un flanc sans conge (gauche du premier onglet, droit d'un onglet au bord du volet) se
    prolonge tout droit dans le bord du cadre (sans la regle QAbstractScrollArea de
    patch_spyder_colors.py, l'arrondi de 4px du cadre de la page decroche vers l'interieur).
Etats : onglet du milieu, deux conges ; premier onglet, pas de conge a gauche ; dernier onglet
avec un volet reduit a la largeur des onglets, pas de conge a droite ; dernier onglet dans un
volet large, conge a droite ; onglet seul (:only-one), comme le premier. Rend 0 si tout tient, 1 sinon.
Avec un chemin en argument, enregistre une capture agrandie (x6) de chaque etat, nommee
<chemin>_<etat>.png.

Aussi avec QT_SCALE_FACTOR=2 (ecran de l'utilisateur, ratio 2) : les pixels sont lus au
coin haut-gauche de chaque pixel logique.
A lancer HORS ECRAN, avec un HOME separe (jamais la configuration reelle de l'utilisateur) :
    env HOME=$TMPDIR/home QT_API=pyside6 QT_QPA_PLATFORM=offscreen <python de l'env> \
        banc_arrondi_onglet.py [prefixe des captures]
Sans le patch (PYTHONPATH vers un arbre spyder non patche), il doit echouer.
"""
import sys
import warnings

warnings.filterwarnings("ignore")
from qtpy.QtWidgets import QApplication, QHBoxLayout, QWidget  # noqa: E402

app = QApplication(sys.argv)
from spyder.utils.palette import SpyderPalette  # noqa: E402
from spyder.utils.stylesheet import APP_STYLESHEET  # noqa: E402
from spyder.widgets.tabs import SMARTOS_RAYON_CONGE, BaseTabs  # noqa: E402
from spyder.plugins.editor.widgets.codeeditor import CodeEditor  # noqa: E402

app.setStyleSheet(str(APP_STYLESHEET))
fenetre = QWidget()
disposition = QHBoxLayout(fenetre)
disposition.setContentsMargins(0, 0, 0, 0)
onglets = BaseTabs(fenetre)
onglets.setDocumentMode(True)  # comme l'editeur et la console IPython, les volets vises
editeurs = []
for nom in ("a.py", "b.py", "c.py"):  # un cadre de page sous chaque onglet
    editeur = CodeEditor(onglets)
    editeur.setup_editor(language="python", color_scheme="spyder/dark", linenumbers=True)
    editeur.set_text("x = 1\n")
    onglets.addTab(editeur, nom)
    editeurs.append(editeur)
disposition.addWidget(onglets)
LARGE = 600
fenetre.resize(LARGE, 200)
fenetre.show()
app.processEvents()

BORD = SpyderPalette.COLOR_ACCENT_3.lower()  # contour de l'onglet actif, volet au focus
RAYON = SMARTOS_RAYON_CONGE
prefixe = sys.argv[1] if len(sys.argv) > 1 else None
barre = onglets.tabBar()
echecs = 0


def verifier(condition, message):
    global echecs
    print(("OK    " if condition else "ECHEC ") + message)
    echecs += not condition


def ecart(a, b):
    """Distance entre deux couleurs '#rrggbb' (somme des ecarts des trois composantes)."""
    return sum(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (1, 3, 5))


def examiner(index, etat):
    """Active l'onglet `index` ; rend (conge a gauche, conge a droite) et verifie le raccord."""
    onglets.setCurrentIndex(index)
    editeurs[index].setFocus()
    app.processEvents()
    image = fenetre.grab().toImage()
    if prefixe:
        largeur, ratio = min(fenetre.width(), 300), image.devicePixelRatio()
        image.copy(0, 0, round(largeur * ratio), round(70 * ratio)).scaled(
            largeur * 6, 70 * 6).save(f"{prefixe}_{etat}.png")
    origine = barre.mapTo(fenetre, barre.rect().topLeft())
    ratio = image.devicePixelRatio()  # QT_SCALE_FACTOR=2 : 2x2 pixels physiques par pixel

    def pixel(x, y):
        x = min(max(x, 0), barre.width() - 1)
        return image.pixelColor(round((origine.x() + x) * ratio),
                                round((origine.y() + y) * ratio)).name()

    zone = barre.tabRect(index)
    cadre = barre.height() - 1  # trait haut du cadre : derniere ligne de la barre
    flancs = {'gauche': (zone.left() + (1 if index == 0 else 2), -1),
              'droite': (zone.right(), 1)}
    conges = {}
    for cote, (flanc, sens) in flancs.items():
        fond = pixel(flanc + sens * (RAYON + 3), cadre - 1)
        conge = conges[cote] = pixel(flanc + sens, cadre - 1) != fond
        # Avec conge, flanc et trait sont droits jusqu'au depart de l'arc, a RAYON px du coin.
        fin_flanc = cadre - RAYON - 1 if conge else cadre
        colonne = [pixel(flanc, y) for y in range(cadre - 2 * RAYON, fin_flanc + 1)]
        exterieur = [x for x in (flanc + sens * d for d in range(RAYON + 1 if conge else 1,
                                                               2 * RAYON + 1))
                     if 0 <= x < barre.width()
                     and not (index == 0 and sens < 0)]  # pas de cadre a gauche du premier
        trait = [pixel(x, cadre) for x in exterieur]
        verifier(set(colonne) == {BORD} and set(trait) <= {BORD},
                 f"{etat}, flanc {cote} : flanc et trait du cadre droits jusqu'au coin ou a l'arc "
                 f"({sorted(set(colonne + trait))}, attendu {BORD})")
        if conge:
            # L'arc remplace le coin : l'angle des deux traits est recouvert (sinon l'arc reste
            # cache dedans, 12/10/2026), et chaque ligne du conge porte un pixel d'arc (pas de trou).
            lignes_sans_arc = [y for y in range(cadre - RAYON, cadre + 1)
                               if min(ecart(pixel(flanc + sens * d, y), BORD)
                                      for d in range(RAYON + 2)) > 120]
            verifier(pixel(flanc, cadre) != BORD and not lignes_sans_arc,
                     f"{etat}, flanc {cote} : arc continu a la place du coin "
                     f"(coin {pixel(flanc, cadre)}, lignes sans arc {lignes_sans_arc})")
    # Flanc sans conge : il se prolonge tout droit dans le bord du cadre de la page (sans la
    # regle QAbstractScrollArea de patch_spyder_colors.py, l'arrondi de 4px decroche dessous).
    for cote, (flanc, _sens) in flancs.items():
        if not conges[cote]:
            bord = [pixel(flanc, cadre + d) for d in range(1, 6)]
            verifier(set(bord) == {BORD},
                     f"{etat} : le flanc {cote} se prolonge tout droit dans le cadre ({bord})")
    return conges['gauche'], conges['droite']


gauche, droite = examiner(1, "milieu")
verifier(gauche and droite, f"onglet du milieu : conge des deux cotes ({gauche}, {droite})")
gauche, droite = examiner(0, "premier")
verifier(not gauche and droite,
         f"premier onglet : pas de conge a gauche, conge a droite ({gauche}, {droite})")
gauche, droite = examiner(2, "dernier_large")
verifier(gauche and droite,
         f"dernier onglet, volet large : conge des deux cotes ({gauche}, {droite})")
# Volet reduit pile a la largeur des onglets : le dernier touche le bord droit.
bord_droit = barre.mapTo(onglets, barre.tabRect(2).topRight()).x() + 1
fenetre.resize(bord_droit, 200)
app.processEvents()
gauche, droite = examiner(2, "dernier_au_bord")
touche = barre.mapTo(onglets, barre.tabRect(2).topRight()).x() + 1 >= onglets.width()
verifier(touche and gauche and not droite,
         f"dernier onglet au bord droit du volet : conge a gauche seulement "
         f"(touche={touche}, {gauche}, {droite})")
# Onglet seul (cas courant des consoles, de Claude, du Terminal) : Qt le classe :only-one et
# non :first, et la regle de marge du premier onglet ne l'atteignait pas (flanc gauche 1px a
# droite du cadre, signale par l'utilisateur le 12/10/2026).
onglets.removeTab(2)
onglets.removeTab(1)
fenetre.resize(LARGE, 200)
app.processEvents()
gauche, droite = examiner(0, "seul")
verifier(not gauche and droite,
         f"onglet seul : pas de conge a gauche, conge a droite ({gauche}, {droite})")
sys.exit(1 if echecs else 0)
