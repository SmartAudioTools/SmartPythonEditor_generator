#!/usr/bin/env python3
"""Extrait une icone qtawesome (glyphe de police) en fichier SVG MODIFIABLE.

    glyphe_qtawesome_en_svg.py mdi.file sortie.svg [--taille 24] [--couleur "#ffffff"]

POURQUOI CET OUTIL. Les icones de Spyder sont de deux natures, et on ne les remplace pas de la meme
facon :
  - un FICHIER, sous spyder/images/ : il suffit de deposer le sien par-dessus (c'est ce qu'on a fait
    pour l'horloge du profileur) ;
  - un GLYPHE DE POLICE, declare dans le dictionnaire _qtaargs de spyder/utils/icon_manager.py
    (par exemple 'filenew' -> mdi.file). Il n'a AUCUN chemin : il vit dans
    qtawesome/fonts/materialdesignicons*.ttf. Deposer un fichier du meme nom dans images/ ne
    servirait a rien, le gestionnaire consultant son dictionnaire AVANT le dossier d'images.
Pour retoucher une icone du second type, il faut donc d'abord la sortir de la police. C'est ce que
fait ce script.

COMMENT, ET POURQUOI PAS AUTREMENT
  - fontTools donnerait le contour directement, mais il n'est pas installe dans l'environnement de
    Spyder, et l'y ajouter pour cela seul serait disproportionne ;
  - rendre l'icone en PNG puis la vectoriser serait une approximation, avec l'antialiasing pour
    bruit ;
  - dessiner le glyphe en TEXTE dans un SVG donnerait un fichier qui ne s'affiche que si la police
    est installee, et qu'aucun editeur ne laisse deformer.
On passe donc par QPainterPath.addText(), qui rend le CONTOUR exact du glyphe sous forme de chemin,
puis on ecrit ce chemin dans un SVG. Le resultat est un trace ordinaire, modifiable dans Inkscape
comme n'importe quel dessin, et fidele au pixel pres a l'original.

⚠ LE RESULTAT EST NORMALISE dans un viewBox carre : le glyphe est mis a l'echelle et centre sur la
boite englobante de son ENCRE, pas sur les metriques de la police - celles-ci reservent des marges
laterales qui decaleraient le dessin. La part du cadre occupee est reglable (--part), et vaut par
defaut 0,75 : c'est la mesure relevee le 26/07/2026 sur les icones de barre d'outils de Spyder, dont
celle qu'on remplace. Cf. Commun/icones/spyder/README.txt.

⚠ Qt DOIT pouvoir charger la police : le script s'appuie sur qtawesome, qui l'enregistre lui-meme.
Il tourne sans serveur graphique (QT_QPA_PLATFORM=offscreen est pose ici).
"""
import argparse
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def chemin_du_glyphe(nom_qta, taille_police=512):
    """Renvoie (QPainterPath du contour, rectangle de l'encre) pour une icone qtawesome."""
    from qtpy.QtGui import QFont, QPainterPath
    import qtawesome as qta

    prefixe, _, nom = nom_qta.partition(".")
    if not nom:
        raise SystemExit(f"Nom attendu sous la forme 'prefixe.nom' (ex. mdi.file), recu {nom_qta!r}")

    # qta.icon() force le chargement de la police et remplit ses tables ; on lit ensuite le
    # caractere dans la table de correspondance du prefixe demande.
    qta.icon(nom_qta)
    ressource = qta._instance().charmap
    if prefixe not in ressource:
        raise SystemExit(f"Prefixe inconnu : {prefixe!r}. Connus : {sorted(ressource)}")
    if nom not in ressource[prefixe]:
        raise SystemExit(f"Icone inconnue : {nom!r} dans {prefixe!r}")
    caractere = ressource[prefixe][nom]

    # ⚠ fontname est un DICTIONNAIRE, pas une methode - piege paye au premier essai. Il donne le nom
    # de famille reel que Qt a enregistre pour ce prefixe (par exemple "Material Design Icons
    # 5.9.55" pour mdi), et ce nom PORTE LE NUMERO DE VERSION : le coder en dur casserait au premier
    # changement de qtawesome.
    police = QFont(qta._instance().fontname[prefixe])
    police.setPixelSize(taille_police)

    chemin = QPainterPath()
    chemin.addText(0, 0, police, caractere)
    if chemin.isEmpty():
        raise SystemExit(f"Contour vide pour {nom_qta} : la police n'a pas ete chargee par Qt.")
    return chemin, chemin.boundingRect()


def svg_du_chemin(chemin, encre, taille, part, couleur):
    """Ecrit le chemin dans un SVG carre, mis a l'echelle et centre sur son encre."""
    from qtpy.QtCore import QBuffer, QByteArray, QRectF
    from qtpy.QtGui import QPainter, QTransform
    from qtpy.QtSvg import QSvgGenerator

    cible = taille * part
    facteur = cible / max(encre.width(), encre.height())
    # Centrer l'ENCRE dans le cadre : on ramene son coin haut-gauche a l'origine, on met a
    # l'echelle, puis on decale de la moitie du reste.
    t = QTransform()
    t.translate((taille - encre.width() * facteur) / 2.0,
                (taille - encre.height() * facteur) / 2.0)
    t.scale(facteur, facteur)
    t.translate(-encre.x(), -encre.y())
    place = t.map(chemin)

    octets = QByteArray()
    tampon = QBuffer(octets)
    generateur = QSvgGenerator()
    generateur.setOutputDevice(tampon)
    generateur.setSize(_QSize(taille, taille))
    generateur.setViewBox(QRectF(0, 0, taille, taille))
    generateur.setTitle("Glyphe qtawesome extrait en trace")
    peintre = QPainter(generateur)
    peintre.setPen(_Qt.NoPen)
    peintre.setBrush(_QColor(couleur))
    peintre.drawPath(place)
    peintre.end()
    return bytes(octets).decode("utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("icone", help="nom qtawesome, par exemple mdi.file")
    ap.add_argument("sortie", help="fichier .svg a ecrire")
    ap.add_argument("--taille", type=int, default=24,
                    help="cote du viewBox (defaut 24, comme les icones mdi)")
    ap.add_argument("--part", type=float, default=0.75,
                    help="part du cadre occupee par le dessin (defaut 0,75 : la mesure des icones "
                         "de barre d'outils de Spyder)")
    ap.add_argument("--couleur", default="#ffffff",
                    help="couleur de remplissage (defaut blanc, pour le theme sombre)")
    args = ap.parse_args()

    from qtpy.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841 - requis par Qt

    global _QSize, _Qt, _QColor
    from qtpy.QtCore import QSize as _QSize, Qt as _Qt
    from qtpy.QtGui import QColor as _QColor

    chemin, encre = chemin_du_glyphe(args.icone)
    texte = svg_du_chemin(chemin, encre, args.taille, args.part, args.couleur)
    with open(args.sortie, "w", encoding="utf-8") as f:
        f.write(texte)
    print(f"{args.icone} -> {args.sortie}")
    print(f"  encre du glyphe dans la police : {encre.width():.0f} x {encre.height():.0f}")
    print(f"  viewBox {args.taille} x {args.taille}, dessin occupant {args.part:.0%}, "
          f"couleur {args.couleur}")
    print("  a retoucher dans Inkscape ; si des marqueurs ou des contours sont ajoutes, les aplatir")
    print("  avant deploiement (cf. Commun/icones/spyder/README.txt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
