#!/usr/bin/env python3
"""Patch spyder/api/widgets/status.py pour que les widgets cliquables de la barre d'etat
retrouvent un fond TRANSPARENT au repos, au lieu de rester eclaircis apres un clic.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "barre de status" : "certain
bouton deviennent plus clairs une fois qu'on a clique dessus => les remettre a leur couleur par
defaut"). Cause racine : les widgets interactifs (INTERACT_ON_CLICK, c.-a-d. PythonEnvironmentStatus
et MatplotlibStatus) gerent leur fond a la main dans leurs gestionnaires d'evenements Qt, PAS via des
pseudo-etats CSS. Au relachement / a la sortie de survol, Spyder remet leur fond a
SpyderPalette.COLOR_BACKGROUND_4 (#455364, un gris clair). C'etait correct tant que la barre d'etat
elle-meme etait en COLOR_BACKGROUND_4 ; mais depuis que patch_spyder_colors.py recolore la barre de
statut sur le fond SOMBRE de l'editeur (#19232D), ce gris clair d'origine forme une tache claire
persistante autour du widget cliquable. Le fond n'est jamais remis a "transparent" (etat initial),
donc la tache reste.

Correctif : reposer le fond a "transparent" au repos. Un widget transparent laisse voir le fond de
la barre d'etat, quel qu'il soit - correct AVEC et SANS patch_spyder_colors.py, et independant du
theme. Le fond est applique par self.setStyleSheet(self._css.toString()) DIRECTEMENT sur l'instance
du widget : une feuille de style de niveau application (stylesheet.py) ne pourrait pas le contrer, la
regle inline du widget l'emportant. D'ou un patch dans status.py et non dans stylesheet.py.

Deux points, correspondant aux deux moments ou le fond clair pouvait subsister :
- leaveEvent : cas normal (la souris quitte le widget). On remet transparent apres le code de Spyder.
- mouseReleaseEvent, uniquement si un menu est associe : quand le widget ouvre un menu (popup), la
  souris est capturee par le popup et leaveEvent ne se declenche pas - le fond resterait donc au gris
  de survol. On le remet transparent des le relachement dans ce cas.
Les etats de SURVOL (enterEvent) et d'APPUI (mousePressEvent) sont volontairement laisses tels quels
(gris #54687A / #60798B) : ce sont des retours visuels transitoires, visibles seulement pendant
l'interaction, coherents avec la philosophie de patch_spyder_colors.py (garder le retour de survol).

Usage : patch_spyder_status_reset.py <chemin vers api/widgets/status.py installe>

Localisation des points d'insertion via le module "ast" : retrouve StatusBarWidget.leaveEvent et
StatusBarWidget.mouseReleaseEvent par leur nom, et AJOUTE un bloc a la fin de chacune (le code de
Spyder s'execute d'abord, notre remise a transparent a le dernier mot). Echoue BRUYAMMENT (code de
sortie 1) si une methode est introuvable. Idempotent bloc par bloc : chaque bloc porte son propre
marqueur et n'est ajoute que s'il est absent (permet d'ajouter un bloc a un fichier deja patche par
une version anterieure du script, en mode installation_SmartPythonEditor.sh --personnalisations).
"""
import ast
import sys

LEAVE_MARKER = "Fond transparent au repos (SmartOS)"
LEAVE_PATCH = '''
        # Fond transparent au repos (SmartOS). Cf. Commun/scripts/patch_spyder_status_reset.py :
        # plutot que COLOR_BACKGROUND_4, qui forme une tache claire depuis que la barre de statut
        # est sur le fond sombre de l'editeur (cf. patch_spyder_colors.py).
        if self.INTERACT_ON_CLICK:
            self._css.QWidget.setValues(backgroundColor="transparent")
            self.setStyleSheet(self._css.toString())
'''

RELEASE_MARKER = "Menu ouvert : fond transparent (SmartOS)"
RELEASE_PATCH = '''
        # Menu ouvert : fond transparent (SmartOS). Cf.
        # Commun/scripts/patch_spyder_status_reset.py : le popup capture la souris, donc leaveEvent
        # ne se declenchera pas et le fond resterait au gris de survol : on le remet transparent.
        if self.INTERACT_ON_CLICK and self.menu:
            self._css.QWidget.setValues(backgroundColor="transparent")
            self.setStyleSheet(self._css.toString())
'''

TARGETS = [
    ("leaveEvent", LEAVE_MARKER, LEAVE_PATCH),
    ("mouseReleaseEvent", RELEASE_MARKER, RELEASE_PATCH),
]


def find_method(tree, class_name, method_name):
    """Retourne le noeud AST de <class_name>.<method_name>, ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and sub.name == method_name:
                    return sub
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers api/widgets/status.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"status.py illisible ({error}) - patch reset barre de statut non applique.",
              file=sys.stderr)
        return 1

    tree = ast.parse(source)

    # (numero de ligne apres lequel inserer, texte) ; appliques du dernier au premier pour que les
    # numeros de ligne restent valides.
    insertions = []
    for method_name, marker, patch in TARGETS:
        if marker in source:
            continue
        method = find_method(tree, "StatusBarWidget", method_name)
        if method is None:
            print(f"StatusBarWidget.{method_name} introuvable dans {path} - Spyder a peut-etre "
                  "restructure son code, patch reset barre de statut non applique.",
                  file=sys.stderr)
            return 1
        insertions.append((method.body[-1].end_lineno, patch))

    if not insertions:
        print("Patch reset barre de statut Spyder deja applique.")
        return 0

    lines = source.splitlines(keepends=True)
    for ligne, patch in sorted(insertions, reverse=True):
        lines.insert(ligne, patch)
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le status.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch reset barre de statut applique : fond transparent au repos ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
