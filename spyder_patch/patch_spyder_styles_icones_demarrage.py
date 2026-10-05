#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trois recalculs repetes au demarrage : icones SVG, listes deroulantes, feuilles des panneaux.

Contexte (TODO - Spyder - accélération démarage.txt, etape 5, 05/10/2026). Comptages faits sur
un demarrage complet du banc (sonde posee dans une copie de l'arbre) :

  1. ICONES (_smartos_icones_memo, spyder/utils/icon_manager.py) - IconManager.get_icon() rend
     l'image SVG en 512x512, deux fois (etat normal, etat desactive), a CHAQUE appel : 129 appels
     pour 44 icones distinctes (« dock » 25 fois, les icones de recherche 7 a 10 fois chacune).
     -> le QIcon construit est garde par (nom, resample, chemin de l'image) ; l'appelant en
        recoit une COPIE (partage implicite de Qt : la copie ne coute rien, et la modifier ne touche pas l'original).
        Le theme d'icones ne change pas sans redemarrage ; le chemin dans la cle couvre le
        greffon qui enregistre son dossier d'images apres un premier appel.

  2. LISTES DEROULANTES (_smartos_combobox_feuille, spyder/api/widgets/comboboxes.py) - Qt appelle
     hidePopup() pendant la construction d'une liste (23 fois au demarrage), et SpyderComboBox y
     repose a chaque fois sa feuille de style, alors qu'aucune liste n'a ete ouverte. 20 de ces
     23 poses changeaient reellement la feuille : celle de __init__ ne portait pas les coins
     arrondis du bas que hidePopup() ajoute.
     -> le constructeur commun (_SpyderComboBoxMixin.__init__) pose d'emblee, pour SpyderComboBox, 
        la feuille « liste fermee » (celle que hidePopup() aurait posee), et hidePopup() ne
        repose la feuille que si elle differe de celle en place.

  3. FEUILLES DES PANNEAUX (_smartos_to_string_unique, spyder/utils/stylesheet.py) -
     SpyderStyleSheet.to_string() convertit la feuille en texte DEUX fois par appel (une pour
     tester si elle est vide, une pour la rendre) : 114 appels au demarrage.
     -> une seule conversion.

Trois blocs, trois marqueurs, chacun idempotent et independant ; echec bruyant si la forme amont
a change.

Usage : patch_spyder_styles_icones_demarrage.py <racine contenant spyder/>
"""

import ast
import os
import sys

MARQUEUR_ICONES = "_smartos_icones_memo"
MARQUEUR_COMBOBOX = "_smartos_combobox_feuille"
MARQUEUR_TO_STRING = "_smartos_to_string_unique"

BLOC_ICONES = '''

# ---- SmartOS (_smartos_icones_memo) : icones SVG rendues une seule fois ------------------------
# get_icon() rendait la meme image a chaque appel (129 appels pour 44 icones au demarrage). Voir
# spyder_patch/patch_spyder_styles_icones_demarrage.py du generator.
def _smartos_icones_memo():
    from spyder.utils.image_path_manager import IMAGE_PATH_MANAGER

    construire = IconManager.get_icon
    chemins = IMAGE_PATH_MANAGER.IMG_PATH
    gardees = {}

    def get_icon(self, name, resample=False):
        try:
            # Le chemin fait partie de la cle : un greffon peut enregistrer plus tard un dossier
            # d'images qui fournit (ou remplace) cette icone.
            cle = (name, resample, chemins.get(name))
            icone = gardees[cle]
        except KeyError:
            icone = gardees[cle] = construire(self, name, resample)
        except TypeError:  # nom non hachable : comme en amont
            return construire(self, name, resample)
        return QIcon(icone)

    get_icon.__doc__ = construire.__doc__
    IconManager.get_icon = get_icon


_smartos_icones_memo()
'''

INIT_AMONT = "self._css = self._generate_stylesheet()"
INIT_AJOUT = '''
{i}# SmartOS (_smartos_combobox_feuille) : la feuille « liste fermee » des la construction,
{i}# pour que les hidePopup() que Qt appelle a l'initialisation n'aient rien a reposer.
{i}# Reserve a SpyderComboBox : la liste des polices, qui partage ce constructeur, ne les pose pas.
{i}if not sys.platform == "darwin" and isinstance(self, SpyderComboBox):
{i}    self._css.QComboBox.setValues(
{i}        borderBottomLeftRadius=SpyderPalette.SIZE_BORDER_RADIUS,
{i}        borderBottomRightRadius=SpyderPalette.SIZE_BORDER_RADIUS,
{i}    )
'''
POSE_AMONT = "self.setStyleSheet(self._css.toString())"
POSE_SMARTOS = '''{i}_smartos_feuille = self._css.toString()  # SmartOS (_smartos_combobox_feuille)
{i}if _smartos_feuille != self.styleSheet():
{i}    self.setStyleSheet(_smartos_feuille)
'''

TO_STRING_AMONT = '''        if self._stylesheet.toString() == "":
            self.set_stylesheet()
        return self._stylesheet.toString()
'''
TO_STRING_SMARTOS = '''        feuille = self._stylesheet.toString()  # SmartOS (_smartos_to_string_unique)
        if feuille == "":
            self.set_stylesheet()
            feuille = self._stylesheet.toString()
        return feuille
'''


def _ecrire(chemin, resultat):
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def patcher_icones(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_ICONES in source:
        print(f"Deja patche (icones) : {chemin}")
        return True
    arbre = ast.parse(source)
    classe = next((n for n in arbre.body
                   if isinstance(n, ast.ClassDef) and n.name == "IconManager"), None)
    methode = classe and next((n for n in classe.body if isinstance(n, ast.FunctionDef)
                               and n.name == "get_icon"), None)
    arguments = [a.arg for a in methode.args.args] if methode else []
    noms = {alias.asname or alias.name for n in arbre.body
            if isinstance(n, ast.ImportFrom) for alias in n.names}
    if arguments != ["self", "name", "resample"] or "QIcon" not in noms:
        print(f"ERREUR : IconManager.get_icon(self, name, resample) ou l'import de QIcon "
              f"introuvable dans {chemin} - la forme amont a change.", file=sys.stderr)
        return False
    return _ecrire(chemin, source.rstrip("\n") + "\n" + BLOC_ICONES)


def patcher_combobox(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_COMBOBOX in source:
        print(f"Deja patche (listes deroulantes) : {chemin}")
        return True
    arbre = ast.parse(source)
    def methode_de(nom_classe, nom):
        classe = next((n for n in arbre.body
                       if isinstance(n, ast.ClassDef) and n.name == nom_classe), None)
        return classe and next((n for n in classe.body if isinstance(n, ast.FunctionDef)
                                and n.name == nom), None)

    lignes = source.splitlines(keepends=True)

    def ligne_de(methode, texte):
        """Numero (base 0) de l'unique instruction `texte` de la methode, ou None."""
        if not methode:
            return None
        trouvees = [n.lineno - 1 for n in ast.walk(methode)
                    if isinstance(n, (ast.Expr, ast.Assign)) and n.lineno == n.end_lineno
                    and lignes[n.lineno - 1].strip() == texte]
        return trouvees[0] if len(trouvees) == 1 else None

    init = ligne_de(methode_de("_SpyderComboBoxMixin", "__init__"), INIT_AMONT)
    pose = ligne_de(methode_de("SpyderComboBox", "hidePopup"), POSE_AMONT)
    if (init is None or pose is None or init >= pose or "SpyderPalette" not in source
            or "\nimport sys\n" not in source):
        print(f"ERREUR : _SpyderComboBoxMixin.__init__ / SpyderComboBox.hidePopup n'ont plus la forme attendue "
              f"dans {chemin} - la forme amont a change.", file=sys.stderr)
        return False

    def retrait(numero):
        return lignes[numero][:len(lignes[numero]) - len(lignes[numero].lstrip())]

    lignes[pose] = POSE_SMARTOS.format(i=retrait(pose))
    lignes[init] = lignes[init] + INIT_AJOUT.format(i=retrait(init)).lstrip("\n")
    return _ecrire(chemin, "".join(lignes))


def patcher_to_string(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_TO_STRING in source:
        print(f"Deja patche (to_string) : {chemin}")
        return True
    if source.count(TO_STRING_AMONT) != 1:
        print(f"ERREUR : SpyderStyleSheet.to_string n'a plus la forme attendue dans {chemin} "
              f"- la forme amont a change.", file=sys.stderr)
        return False
    return _ecrire(chemin, source.replace(TO_STRING_AMONT, TO_STRING_SMARTOS))


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <racine contenant spyder/>", file=sys.stderr)
        return 1
    racine = argv[1]
    # Les trois sont tentes meme si l'un echoue : chaque bloc est independant.
    resultats = [
        patcher_icones(os.path.join(racine, "spyder/utils/icon_manager.py")),
        patcher_combobox(os.path.join(racine, "spyder/api/widgets/comboboxes.py")),
        patcher_to_string(os.path.join(racine, "spyder/utils/stylesheet.py")),
    ]
    return 0 if all(resultats) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
