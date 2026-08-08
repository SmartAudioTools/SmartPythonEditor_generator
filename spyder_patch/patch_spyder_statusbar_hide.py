#!/usr/bin/env python3
"""Patch spyder/plugins/statusbar/plugin.py pour retirer de la barre d'etat trois widgets sans
option de configuration.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "barre de status", demandes de
l'utilisateur). Mem, CPU et l'heure se desactivent proprement par CONFIGURATION (options
statusbar/memory_usage/enable, statusbar/cpu_usage/enable, statusbar/clock/enable, positionnees a
False par installation_SmartPythonEditor.sh via tools/spyder_config_set.py) : leur minuterie est alors reellement
arretee, et l'utilisateur peut les reactiver depuis les Preferences. Les trois widgets ci-dessous
n'ont PAS d'option de configuration ; ce patch est le seul moyen de les retirer.

DEUX BLOCS INDEPENDANTS, chacun avec son propre marqueur d'idempotence (regle du depot : un marqueur
global unique empeche le mode --personnalisations de rejouer un bloc ajoute apres coup). Chaque bloc
ne s'applique que si son marqueur est absent, donc ajouter le second n'oblige pas a reinstaller
Spyder a neuf : "installation_SmartPythonEditor.sh --personnalisations" applique le bloc manquant.

  BLOC 1 - LSP:Python (lsp_status) et RW (read_write_status), juges non essentiels.
    Garde en TETE de StatusBar.add_status_widget qui, pour ces deux ID, fait hide() puis return :
    le widget n'est jamais ajoute a la barre ni memorise. C'est sur POUR CES DEUX widgets car les
    plugins qui les fournissent ne les re-cherchent pas par ID a leur teardown.

  BLOC 2 - pythonenv_status (l'interpreteur de la console), DEPLACE dans la barre d'outils togglable
    "Interpreteur" (greffon spyder_interpreter_toolbar). On ne peut PAS lui appliquer la meme garde :
    le plugin console le re-cherche par ID a son teardown (ipythonconsole/plugin.py
    on_statusbar_teardown : get_status_widget puis remove_status_widget) - un return avant
    memorisation ferait lever une SpyderAPIError a la FERMETURE de Spyder. On le laisse donc
    s'enregistrer normalement, mais on le RETIRE de la disposition dans _organize_status_widgets :
    il est alors retire de la barre (removeWidget, qui le masque) et jamais re-affiche
    (le re-ajout + setVisible(True) de cette methode ne le concerne plus), tout en restant present
    dans STATUS_WIDGETS -> get_status_widget/remove_status_widget continuent de fonctionner.

Usage : patch_spyder_statusbar_hide.py <chemin vers plugins/statusbar/plugin.py installe>

Localisation via le module "ast" (structure du code, pas texte brut). Re-parse avant ecriture ;
echoue BRUYAMMENT (code de sortie 1) si un point d'insertion attendu est introuvable - jamais deviner.
"""
import ast
import sys

# ---- BLOC 1 : garde dans add_status_widget (lsp_status, read_write_status) --------------------
MARKER_HIDE = "Widgets de barre de statut masques (SmartOS"
GUARD_HIDE = '''        # Widgets de barre de statut masques (SmartOS). Cf.
        # Commun/scripts/patch_spyder_statusbar_hide.py : LSP:Python et l'indicateur
        # lecture/ecriture (RW), juges non essentiels (demande utilisateur). Ils n'ont pas
        # d'option de configuration, contrairement a Mem/CPU/heure (desactives par config).
        if getattr(widget, "ID", None) in ("lsp_status", "read_write_status"):
            # hide() est indispensable : le widget est deja cree, parente au widget principal de
            # l'editeur ; se contenter d'un "return" (sans l'ajouter a la barre de statut) le
            # laisserait s'afficher en widget orphelin quelque part dans l'editeur. On le cache.
            widget.hide()
            return
'''

# ---- BLOC 2 : exclusion de pythonenv_status dans _organize_status_widgets ---------------------
MARKER_PYENV = "pythonenv_status retire de la disposition (SmartOS"
FILTER_PYENV = '''        # pythonenv_status retire de la disposition (SmartOS, cf.
        # Commun/scripts/patch_spyder_statusbar_hide.py) : l'interpreteur de la console est
        # desormais choisi depuis la barre d'outils togglable "Interpreteur" (greffon
        # spyder_interpreter_toolbar). On le sort de la disposition pour qu'il ne soit ni
        # re-ajoute ni re-affiche ici (setVisible(True) plus bas ne le concerne plus). Il reste
        # enregistre dans STATUS_WIDGETS : le plugin console peut toujours le re-chercher par ID
        # et le retirer proprement a son teardown (ipythonconsole/plugin.py on_statusbar_teardown).
        internal_layout = [_id for _id in internal_layout if _id != "pythonenv_status"]
'''


def find_method(tree, class_name, method_name):
    """Retourne le noeud AST de <class_name>.<method_name>, ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and sub.name == method_name:
                    return sub
    return None


def insertion_apres_docstring(method):
    """Numero de ligne (1-indexe) APRES lequel inserer : fin de la docstring si presente, sinon
    juste avant la premiere instruction du corps."""
    premier = method.body[0]
    if (isinstance(premier, ast.Expr)
            and isinstance(premier.value, ast.Constant)
            and isinstance(premier.value.value, str)):
        return premier.end_lineno  # inserer apres la docstring
    return premier.lineno - 1  # inserer juste avant la premiere instruction


def fin_affectation(method, nom_cible):
    """Numero de ligne (1-indexe) de fin de l'affectation `<nom_cible> = ...` dans <method>, ou
    None. Couvre les litteraux multi-lignes (end_lineno = ligne du crochet fermant)."""
    for node in ast.walk(method):
        if isinstance(node, ast.Assign):
            for cible in node.targets:
                if isinstance(cible, ast.Name) and cible.id == nom_cible:
                    return node.end_lineno
    return None


def appliquer_bloc_hide(source):
    """BLOC 1. Retourne (nouvelle_source, applique)."""
    if MARKER_HIDE in source:
        return source, False
    method = find_method(ast.parse(source), "StatusBar", "add_status_widget")
    if method is None:
        print("StatusBar.add_status_widget introuvable - Spyder a peut-etre restructure son code, "
              "bloc masquage LSP/RW non applique.", file=sys.stderr)
        sys.exit(1)
    ligne = insertion_apres_docstring(method)
    lines = source.splitlines(keepends=True)
    lines.insert(ligne, GUARD_HIDE)
    return "".join(lines), True


def appliquer_bloc_pyenv(source):
    """BLOC 2. Retourne (nouvelle_source, applique)."""
    if MARKER_PYENV in source:
        return source, False
    method = find_method(ast.parse(source), "StatusBar", "_organize_status_widgets")
    if method is None:
        print("StatusBar._organize_status_widgets introuvable - Spyder a peut-etre restructure son "
              "code, bloc masquage pythonenv_status non applique.", file=sys.stderr)
        sys.exit(1)
    fin = fin_affectation(method, "internal_layout")
    if fin is None:
        print("Affectation 'internal_layout' introuvable dans _organize_status_widgets - bloc "
              "masquage pythonenv_status non applique.", file=sys.stderr)
        sys.exit(1)
    lines = source.splitlines(keepends=True)
    lines.insert(fin, FILTER_PYENV)
    return "".join(lines), True


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/statusbar/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"statusbar/plugin.py illisible ({error}) - patch masquage barre de statut non "
              "applique.", file=sys.stderr)
        return 1

    # Bloc 1 d'abord (haut du fichier), puis re-lecture AST pour le bloc 2 (plus bas, decale par
    # l'insertion du bloc 1).
    source, hide_applique = appliquer_bloc_hide(source)
    source, pyenv_applique = appliquer_bloc_pyenv(source)

    if not hide_applique and not pyenv_applique:
        print("Patch masquage barre de statut Spyder deja applique (LSP/RW + pythonenv_status).")
        return 0

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"Le statusbar/plugin.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(source)

    faits = []
    if hide_applique:
        faits.append("LSP:Python + RW masques")
    if pyenv_applique:
        faits.append("pythonenv_status retire (deplace dans la barre d'outils Interpreteur)")
    print(f"Patch masquage barre de statut applique : {' ; '.join(faits)} ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
