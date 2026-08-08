#!/usr/bin/env python3
"""Patch spyder/utils/stylesheet.py pour aligner le fond de la barre d'outils principale, celui des
separateurs de docks et celui de la barre de statut sur le fond de l'editeur de texte.

Contexte (TODO du 20/07/2026, section "Couleurs", demande explicite de l'utilisateur) : avec le
theme "spyder/dark", le fond de l'editeur vaut #19232D (COLOR_BACKGROUND_1 de QDarkStyle) alors que
la barre d'outils principale, les separateurs de docks et la barre de statut utilisent
COLOR_BACKGROUND_4 (#455364), nettement plus clair - la fenetre paraissait donc decoupee en bandes
de gris differents. Ce patch les ramene sur la couleur de fond de l'editeur.

La couleur n'est PAS ecrite en dur : elle est relue a chaque construction de la feuille de style
depuis le theme de coloration syntaxique reellement selectionne (option "appearance/selected", puis
cle "<theme>/background"). Changer de theme dans les Preferences deplace donc aussi la barre
d'outils et les separateurs, ce qui est bien la demande ("de la meme couleur que le fond de
l'editeur de texte") et evite un patch a refaire a chaque changement de theme. Si cette lecture
echoue pour une raison quelconque, on retombe silencieusement sur SpyderPalette.COLOR_BACKGROUND_1
(valeur du theme sombre par defaut) : une couleur legerement fausse est preferable a un Spyder qui
refuse de demarrer sur une exception dans sa feuille de style.

Ce qui n'est deliberement PAS touche :
- l'etat :hover des separateurs (#60798B) et des boutons de la barre d'outils : c'est le seul
  retour visuel indiquant qu'un separateur est saisissable / qu'un bouton est survole ; les
  uniformiser rendrait la fenetre plate au point d'etre moins utilisable.
- les barres d'outils des panneaux (PanesToolbarStyleSheet) : la demande porte sur "la barre
  d'outils", c'est-a-dire la barre principale de l'application.

Usage : patch_spyder_colors.py <chemin vers stylesheet.py installe>

Localisation des points d'insertion via le module "ast" (structure du code, pas texte brut) plutot
qu'une recherche de bloc exact : retrouve les methodes par leur nom dans leur classe, et le dernier
import de haut niveau, quels que soient les commentaires/blancs/l'ordre autour - resiste donc aux
changements de pure forme d'une version de Spyder a l'autre. Le patch AJOUTE des instructions a la
fin des methodes visees au lieu de les remplacer : la logique existante de Spyder est conservee
telle quelle et nos "setValues" ont le dernier mot (qstylizer fusionne les proprietes d'un meme
selecteur, la derniere ecriture gagne). Echoue BRUYAMMENT (code de sortie 1) si une methode ou les
imports ne sont pas trouves comme attendu, plutot que de deviner.

Idempotent morceau par morceau : chaque bloc insere porte sa propre ligne de commentaire, qui sert
de marqueur, et n'est pose que si ce marqueur est absent. Un marqueur GLOBAL unique ne convenait
pas : ajouter un bloc (la barre de statut, le 20/07/2026) a un fichier deja patche par une version
precedente du script aurait ete vu comme "deja fait", et le nouveau bloc n'aurait jamais ete pose
en mode "installation_SmartPythonEditor.sh --personnalisations", qui rejoue les correctifs sur le Spyder en place.
"""
import ast
import sys

HELPER_MARKER = 'def smartos_editor_background('
HELPER = '''

def smartos_editor_background():
    """Couleur de fond de l'editeur de texte (fond du theme de coloration syntaxique actif).

    Ajout SmartOS (cf. Commun/scripts/patch_spyder_colors.py) : sert a aligner la barre d'outils
    principale et les separateurs de docks sur l'editeur. Import local pour ne pas creer d'import
    circulaire avec spyder.config.manager au chargement de ce module.
    """
    try:
        from spyder.config.gui import get_color_scheme
        from spyder.config.manager import CONF
        return get_color_scheme(CONF.get('appearance', 'selected'))['background']
    except Exception:
        return SpyderPalette.COLOR_BACKGROUND_1
'''

# Ajoute a la fin de AppStylesheet._customize_stylesheet : le selecteur existe deja dans la feuille
# QDarkStyle (background-color #455364), on ne fait qu'en redefinir la couleur.
SEPARATORS_MARKER = "# Separateurs de docks a la couleur de fond de l'editeur"
SEPARATORS_PATCH = '''
        # Separateurs de docks a la couleur de fond de l'editeur (ajout SmartOS, cf.
        # Commun/scripts/patch_spyder_colors.py). L'etat :hover reste volontairement distinct.
        css['QMainWindow::separator'].setValues(
            backgroundColor=smartos_editor_background()
        )
'''

# Ajoute lui aussi a la fin de AppStylesheet._customize_stylesheet. QDarkStyle donne a QStatusBar
# "background: #455364" ET "border: 1px solid #455364" : redefinir le seul fond laisserait un
# liseret clair d'un pixel tout autour de la barre, donc les deux sont repris.
# "background" ET "backgroundColor" sont poses tous les deux : qstylizer les traite comme deux
# proprietes distinctes, la regle finale contient donc encore le "background: #455364" d'origine.
# Ne poser que backgroundColor marche - la declaration la plus recente l'emporte, verifie sur la
# feuille reellement produite - mais fait dependre le resultat de l'ordre des declarations dans le
# bloc ; ecraser aussi "background" rend la regle vraie quel que soit cet ordre.
STATUSBAR_MARKER = "# Barre de statut a la couleur de fond de l'editeur"
STATUSBAR_PATCH = '''
        # Barre de statut a la couleur de fond de l'editeur (ajout SmartOS, cf.
        # Commun/scripts/patch_spyder_colors.py), comme la barre d'outils et les separateurs.
        smartos_background = smartos_editor_background()
        css.QStatusBar.setValues(
            background=smartos_background,
            backgroundColor=smartos_background,
            border=f'1px solid {smartos_background}',
        )
'''

# Ajoute a la fin de ApplicationToolbarStylesheet.set_stylesheet, apres le
# "css.QToolBar.setValues(backgroundColor=SpyderPalette.COLOR_BACKGROUND_4)" de Spyder.
TOOLBAR_MARKER = "# Barre d'outils principale a la couleur de fond de l'editeur"
TOOLBAR_PATCH = '''
        # Barre d'outils principale a la couleur de fond de l'editeur (ajout SmartOS, cf.
        # Commun/scripts/patch_spyder_colors.py) au lieu de COLOR_BACKGROUND_4.
        css.QToolBar.setValues(
            backgroundColor=smartos_editor_background()
        )
'''


def find_method(tree, class_name, method_name):
    """Retourne le noeud AST de <class_name>.<method_name>, ou None."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == method_name:
                    return sub
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers stylesheet.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding='utf-8') as f:
            source = f.read()
    except OSError as error:
        print(f"stylesheet.py illisible ({error}) - patch couleurs non applique.",
              file=sys.stderr)
        return 1

    targets = [
        ('AppStylesheet', '_customize_stylesheet', SEPARATORS_MARKER, SEPARATORS_PATCH),
        ('AppStylesheet', '_customize_stylesheet', STATUSBAR_MARKER, STATUSBAR_PATCH),
        ('ApplicationToolbarStylesheet', 'set_stylesheet', TOOLBAR_MARKER, TOOLBAR_PATCH),
    ]

    # (numero de ligne apres laquelle inserer, texte a inserer). Insertions appliquees de la
    # derniere a la premiere pour que les numeros de ligne restent valides.
    insertions = []
    tree = ast.parse(source)

    if HELPER_MARKER not in source:
        # Dernier import de haut niveau : point d'insertion de la fonction utilitaire.
        last_import_line = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import_line = max(last_import_line, node.end_lineno)
        if not last_import_line:
            print("Aucun import de haut niveau trouve dans stylesheet.py - "
                  "patch couleurs abandonne.", file=sys.stderr)
            return 1
        insertions.append((last_import_line, HELPER))

    for class_name, method_name, marker, patch in targets:
        if marker in source:
            continue
        method = find_method(tree, class_name, method_name)
        if method is None:
            print(f"{class_name}.{method_name} introuvable dans stylesheet.py - "
                  "patch couleurs abandonne.", file=sys.stderr)
            return 1
        insertions.append((method.body[-1].end_lineno, patch))

    if not insertions:
        print("Patch couleurs Spyder deja applique.")
        return 0

    lines = source.splitlines(keepends=True)
    for line_number, patch in sorted(insertions, reverse=True):
        lines.insert(line_number, patch)

    patched = ''.join(lines)

    # Filet de securite : ne jamais ecrire un fichier que Python ne sait plus lire.
    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le stylesheet.py patche n'est pas du Python valide ({error}) - "
              "aucune modification ecrite.", file=sys.stderr)
        return 1

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print("Patch couleurs Spyder applique (barre d'outils, separateurs de docks et barre de statut "
          "alignes sur le fond de l'editeur).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
