#!/usr/bin/env python3
"""Conge concave entre l'onglet actif et le cadre de son volet (onglets 'pane-tabbar').

Contexte (demandes de l'utilisateur, 11/10/2026) : « serait-il possible d'avoir un arrondi du
contour entre le titre et la fenetre, du coup vers l'exterieur ? », puis « pour l'onglet tout a
gauche ou tout a droite, je ne veux pas d'arrondi du cote exterieur (tout a droite s'il touche le
bord droit de la fenetre) ».

CE QUI EST PATCHE (spyder/widgets/tabs.py, deux insertions, un marqueur)
    Une fonction de module _smartos_peindre_conges(barre, peintre) et un TabBar.paintEvent qui
    appelle celui de QTabBar puis la fonction : au pied de chaque flanc de l'onglet actif, un
    quart de disque concave de rayon SMARTOS_RAYON_CONGE, rempli de la couleur de l'onglet (celle
    que PanesTabBarStyleSheet lui donne : fond de l'editeur, eclairci quand le volet a le focus) et
    borde d'un arc de la couleur du contour (COLOR_ACCENT_3 avec le focus, COLOR_BACKGROUND_4
    sinon - les memes que la feuille). Rien n'est peint a l'exterieur du conge : la barre reste
    transparente, c'est le fond du volet qui se voit, comme avant.
    Pas de conge sur le flanc gauche du premier onglet, ni sur le flanc droit d'un onglet dont le
    bord droit atteint celui du QTabWidget (coordonnees du parent de la barre, pas de la fenetre
    principale : un volet ancre a gauche a son propre bord droit, et un conge qui le depasserait
    serait coupe). Un onglet pousse hors de la zone visible par les boutons de defilement a un
    tabRect au-dela du bord : traite comme touchant, donc sans conge.
    TabBar est la barre de TOUS les BaseTabs (fichiers de l'editeur, consoles, graphiques...) :
    tous ont le conge. Les onglets de docks empiles (QMainWindow) ne passent pas par cette classe.
    Ecarte : tout faire en feuille de style - Qt ne sait pas peindre un arrondi CONCAVE (un
    border-radius ne fait que des coins convexes), verifie au banc avant d'ecrire ceci. Une marge
    gauche de 5 px sur ::tab:first pour loger le conge du premier onglet, essayee dans le
    prototype : inutile depuis que ce conge-la est supprime.

    Raccord au pixel (12/10/2026, « le countour des onglet et de fenetre ne coincide pas bien, les
    arrondis externet non plus. ce n'est pas popre ») : l'arc est tangent au flanc (colonne
    tabRect.left()+2 a gauche, marge de qdarkstyle ; tabRect.right() a droite) et au trait haut du
    cadre (derniere ligne de la barre), centre sur le milieu des pixels de ces traits ; le fond de
    l'onglet recouvre l'angle des deux traits, bouts compris, avant de tracer l'arc. Ecartes,
    constates au banc : laisser les bouts de traits intacts (ils se croisent en angle droit et
    cachent l'arc) ; un arc sur coordonnees entieres (bave sur deux pixels, trait flou) ; l'ancien
    flanc gauche a tabRect.left() (conge decale de 1 a 2 px). Les coins du cadre sous un flanc sans
    conge (premier onglet, onglet au bord droit) sont rendus carres et alignes par
    patch_spyder_colors.py (QAbstractScrollArea, ::pane), pas ici.
    Onglet tire (19/10/2026, « lors du deplacement d'onglet, l'arrondi exterieur ne suit pas »,
    barres setMovable : dock Claude en vue onglets) : pendant le glisser, Qt peint l'onglet dans
    un widget enfant prive (QMovableTabWidget) qui suit la souris, et tabRect reste a l'ancienne
    place - le conge y restait. Le conge prend la geometrie de ce widget (moins
    PM_TabBarTabOverlap de chaque cote ; Qt 5 y peint l'onglet en OnlyOneTab, marge gauche 1px).
    Peint APRES la barre, ce widget recouvrait aussi le pied des arcs de ses flancs droits : un
    masque lui retire, sous le depart des arcs, la bande exterieure a chaque flanc dote d'un conge.
    Ecartes : suivre la souris soi-meme (mousePress/MoveEvent) - Qt borne et anime le deplacement,
    on recopierait sa logique ; lire le dragOffset de Qt - prive, inaccessible depuis Python ;
    faire peindre le conge par ce widget - il n'a pas de classe Python a surcharger.
    Banc : outils/banc_arrondi_onglet.py (rend 1 sans ce patch ; aussi avec QT_SCALE_FACTOR=2).

    Points d'insertion localises par ast (la classe TabBar et la fin de son __init__), idempotent
    par marqueur, echec bruyant si la classe ou la methode manquent, fichier reparse avant ecriture.
"""

import ast
import sys

MARQUEUR = "# Conge concave au pied de l'onglet actif (ajout SmartOS"

BLOC_MODULE = '''\
# Conge concave au pied de l'onglet actif (ajout SmartOS, cf.
# patch_spyder_arrondi_onglet.py) : peint par TabBar.paintEvent APRES celui de QTabBar,
# dans la bande sous les onglets, avec les couleurs de PanesTabBarStyleSheet.
from qtpy import QT5
from qtpy.QtCore import QRectF
from qtpy.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion
from qtpy.QtWidgets import QStyle
from spyder.utils.stylesheet import (
    SMARTOS_ECLAIRCISSEMENT, smartos_editor_background)

SMARTOS_RAYON_CONGE = 5


def _smartos_onglet_tire(barre):
    # Pendant un glisser (setMovable), Qt peint l'onglet tire dans un widget enfant prive
    # (QMovableTabWidget, sans meta-objet propre : classe 'QWidget') qui suit la souris,
    # tandis que tabRect reste a la place d'origine. Rend ce widget, ou None hors glisser.
    # Les boutons d'onglet ont leur propre classe (CloseButton de Qt, CoinDOnglet du greffon
    # Claude). QWidget : deja importe en tete de tabs.py.
    for enfant in barre.children():
        if (isinstance(enfant, QWidget) and enfant.isVisible()
                and enfant.metaObject().className() == 'QWidget'):
            return enfant
    return None


def _smartos_peindre_conges(barre, peintre):
    # SpyderPalette : deja importe en tete de tabs.py.
    i = barre.currentIndex()
    if i < 0:
        return
    zone = barre.tabRect(i)
    # Flanc gauche sur la colonne de la bordure de l'onglet, decalee de la marge gauche de la
    # feuille (2px de qdarkstyle ; le premier onglet n'a pas de conge gauche).
    marge = 2
    tire = _smartos_onglet_tire(barre)
    if tire is not None:
        # L'onglet tire est l'onglet actif (la pression le selectionne). Qt le peint dans son
        # widget avec PM_TabBarTabOverlap de jeu de chaque cote, a la largeur qu'il avait a la
        # pression (tabRect peut changer ensuite) ; Qt 5 le peint en OnlyOneTab, donc avec la
        # marge 1px de ::tab:only-one (patch_spyder_colors.py). Mesure au banc, Qt 5 et 6.
        jeu = barre.style().pixelMetric(QStyle.PM_TabBarTabOverlap, None, barre)
        zone = tire.geometry().adjusted(jeu, 0, -jeu, 0)
        if QT5:
            marge = 1
    focus = bool(barre.property('smartos_focus'))
    bord = QColor(SpyderPalette.COLOR_ACCENT_3 if focus
                  else SpyderPalette.COLOR_BACKGROUND_4)
    fond = QColor(smartos_editor_background())
    if focus:
        fond = fond.lighter(SMARTOS_ECLAIRCISSEMENT)
    rayon = SMARTOS_RAYON_CONGE
    # Le trait haut du cadre du volet est la derniere ligne de la barre (pane top:-1px) ; le
    # flanc droit est sur la derniere colonne de l'onglet, aucune marge a droite. Un
    # trait de 1px a son centre au milieu du pixel : l'arc part et arrive sur ces centres
    # (+ 0.5), sinon il bave sur deux pixels au lieu de prolonger les traits nets.
    ligne_cadre = barre.height() - 1
    gauche = zone.left() + marge
    droite = zone.right()
    parent = barre.parentWidget()
    touche_le_bord_droit = (
        parent is not None
        and barre.mapTo(parent, zone.topRight()).x() + 1 >= parent.width())
    cotes = [cote for cote in (-1, 1)
             if not ((cote < 0 and i == 0) or (cote > 0 and touche_le_bord_droit))]
    if tire is not None:
        # Le widget de l'onglet tire est peint APRES la barre : ses flancs descendraient tout
        # droit sur le pied des conges. On lui retire, sous le depart des arcs, la bande qui va
        # de son bord a chaque flanc dote d'un conge (flanc compris) : la barre y peint seule.
        haut = ligne_cadre - rayon + 1 - tire.y()
        masque = QRegion(tire.rect())
        for cote in cotes:
            x = (gauche if cote < 0 else droite) - tire.x()
            masque -= QRegion(0 if cote < 0 else x, haut,
                              x + 1 if cote < 0 else tire.width() - x, tire.height())
        # setMask repeint la barre : sans ce test, chaque paintEvent en relance un (mesure).
        if masque != tire.mask():
            tire.setMask(masque)
    peintre.setRenderHint(QPainter.Antialiasing)
    peintre.setPen(QPen(bord, 1))
    for cote in cotes:
        flanc = gauche if cote < 0 else droite
        # Disque tangent au flanc et au trait du cadre, a l'exterieur de l'onglet : le fond de
        # l'onglet recouvre le coin entre l'arc et ces deux traits, bouts de traits compris
        # (sinon ils continuent tout droit et l'arc reste cache dans leur angle), puis l'arc.
        centre_x = flanc + 0.5 + cote * rayon
        centre_y = ligne_cadre + 0.5 - rayon
        cercle = QRectF(centre_x - rayon, centre_y - rayon, 2 * rayon, 2 * rayon)
        coin = QPainterPath()
        coin.addRect(QRectF(centre_x if cote < 0 else flanc, centre_y,
                            rayon + 0.5, rayon + 0.5))
        disque = QPainterPath()
        disque.addEllipse(cercle)
        peintre.fillPath(coin.subtracted(disque), fond)
        peintre.drawArc(cercle, (270 if cote < 0 else 180) * 16, 90 * 16)

'''

BLOC_METHODE = '''\

    def paintEvent(self, event):
        super().paintEvent(event)
        # Conge concave au pied de l'onglet actif (ajout SmartOS).
        peintre = QPainter(self)
        _smartos_peindre_conges(self, peintre)
        peintre.end()
'''


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <spyder/widgets/tabs.py>", file=sys.stderr)
        return 1
    path = sys.argv[1]
    with open(path, encoding='utf-8') as flux:
        source = flux.read()
    if MARQUEUR in source:
        print("tabs.py : conge des onglets deja applique.")
        return 0
    arbre = ast.parse(source)
    classes = [n for n in arbre.body if isinstance(n, ast.ClassDef) and n.name == 'TabBar']
    inits = [n for c in classes for n in c.body
             if isinstance(n, ast.FunctionDef) and n.name == '__init__']
    if len(classes) != 1 or len(inits) != 1:
        print("tabs.py : classe TabBar ou son __init__ introuvable - patch abandonne. "
              "Structure du fichier changee ?", file=sys.stderr)
        return 1
    lignes = source.splitlines(keepends=True)
    # La methode d'abord (plus bas dans le fichier) pour ne pas decaler l'indice de la classe.
    lignes.insert(inits[0].end_lineno, BLOC_METHODE)
    lignes.insert(classes[0].lineno - 1, BLOC_MODULE)
    source = ''.join(lignes)
    ast.parse(source)
    with open(path, 'w', encoding='utf-8') as flux:
        flux.write(source)
    print("tabs.py : conge des onglets applique.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
