#!/usr/bin/env python3
"""Patch spyder/plugins/debugger/widgets/main_widget.py : supprime le VIDE a droite du bouton
"Deboguer le fichier" dans la barre d'outils Debug, hors session de debogage.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt" + retour utilisateur du 22/07/2026).
La barre Debug contient "Deboguer le fichier" puis 5 boutons de controle du debogueur
(Next/Step/Return/Continue/Stop), masques tant qu'aucune session n'est active. Spyder les masque
par widget.setFixedWidth(0) (methodes on_debug_toolbar_rendered et
_set_visible_control_debugger_buttons). PROBLEME : setFixedWidth(0) est mis en echec par la feuille
de style des barres d'application (QToolButton width:47px, qui l'emporte), laissant ~14px de slot
RESERVE par bouton -> un large vide (~70px) a droite de "Deboguer le fichier" au repos.

CORRECTIF : au lieu de redimensionner a 0, on RETIRE reellement les boutons de la barre
(QToolBar.removeAction) au repos, et on les REINTRODUIT (addAction, dans leur ordre d'origine) quand
une session de debogage demarre. Un slot retire ne reserve aucun espace, quel que soit le style.
removeAction ne touche PAS l'entree de menu : c'est la meme QAction, mais le menu est un conteneur
distinct, il garde son entree et son raccourci. Ordre garanti : la barre Debug ne contient que
"Deboguer le fichier" (qui reste) + ces 5 boutons en dernier (verifie sur Spyder 6.1.5,
debugger/plugin.py on_toolbar_available) ; on les retire tous puis on les re-ajoute dans l'ordre
[Next, Step, Return, Continue, Stop], donc apres "Deboguer le fichier".

Robustesse au re-rendu : les boutons restent dans _section_items de la barre, donc un nouveau
SpyderToolbar.render() (bascule/verrouillage de barre) les redessine tous ; mais on_debug_toolbar_rendered
est connecte a sig_is_rendered et rappelle le masquage -> etat coherent.

Usage : patch_spyder_debug_toolbar_gap.py <chemin vers debugger/widgets/main_widget.py installe>

Remplace DEUX methodes via le module "ast" (find_method_range), de bas en haut pour ne pas decaler
les lignes. Idempotent (marqueur). Re-parse avant ecriture ; echoue BRUYAMMENT (code 1) si une
methode est introuvable - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_debug_toolbar_gap.py"

NEW_ON_RENDERED = '''    def on_debug_toolbar_rendered(self):
        """Actions to take when the Debug toolbar is rendered."""
        # SmartOS (cf. Commun/scripts/patch_spyder_debug_toolbar_gap.py) : au repos on RETIRE
        # reellement les boutons de controle du debogueur de la barre (removeAction), au lieu de
        # setFixedWidth(0). Motif : setFixedWidth(0) est mis en echec par la feuille de style
        # (QToolButton width:47px l'emporte), laissant ~14px de slot reserve par bouton -> un large
        # vide a droite de "Deboguer le fichier" hors session. removeAction supprime le slot entier
        # (zero espace reserve) ; l'entree de MENU n'est pas touchee (meme QAction, mais le menu est
        # un conteneur distinct). Les boutons sont reintroduits par
        # _set_visible_control_debugger_buttons(True) quand une session de debogage demarre.
        debug_toolbar = self.get_toolbar(
            ApplicationToolbars.Debug, plugin=Plugins.Toolbar
        )
        self._debug_toolbar = debug_toolbar
        self._control_debugger_actions = [
            self.get_action(action_id)
            for action_id in [
                DebuggerWidgetActions.Next,
                DebuggerWidgetActions.Step,
                DebuggerWidgetActions.Return,
                DebuggerWidgetActions.Continue,
                DebuggerWidgetActions.Stop,
            ]
        ]

        # Aucune session active au (re)rendu de la barre : masquer.
        self._set_visible_control_debugger_buttons(False)
'''

NEW_SET_VISIBLE = '''    def _set_visible_control_debugger_buttons(self, visible: bool):
        """Show/hide control debugger buttons in the Debug toolbar."""
        # SmartOS : afficher = reintroduire les actions dans la barre (retirees d'abord pour garantir
        # leur ordre d'origine [Next, Step, Return, Continue, Stop], apres "Deboguer le fichier" qui
        # reste et est le seul autre item) ; masquer = les retirer (slot supprime -> aucun espace).
        toolbar = getattr(self, "_debug_toolbar", None)
        actions = getattr(self, "_control_debugger_actions", None)
        if toolbar is None or actions is None:
            return

        for action in actions:
            if action in toolbar.actions():
                toolbar.removeAction(action)
        if visible:
            for action in actions:
                toolbar.addAction(action)
'''


def find_method_range(tree, class_name, method_name):
    """(lineno, end_lineno) 1-indexes inclus de la methode, ou None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and item.name == method_name:
                    return item.lineno, item.end_lineno
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers debugger/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch vide barre Debug non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch vide barre Debug deja applique.")
        return 0

    tree = ast.parse(source)
    cls = "DebuggerWidget"
    remplacements = []  # (start, end, texte)
    for method, texte in (
        ("on_debug_toolbar_rendered", NEW_ON_RENDERED),
        ("_set_visible_control_debugger_buttons", NEW_SET_VISIBLE),
    ):
        rng = find_method_range(tree, cls, method)
        if rng is None:
            print(f"{cls}.{method} introuvable dans {path} - Spyder a peut-etre restructure son "
                  "code, patch vide barre Debug non applique.", file=sys.stderr)
            return 1
        remplacements.append((rng[0], rng[1], texte))

    # De bas en haut pour ne pas decaler les lignes des remplacements suivants.
    remplacements.sort(key=lambda r: r[0], reverse=True)
    lines = source.splitlines(keepends=True)
    for start, end, texte in remplacements:
        lines[start - 1:end] = [texte]
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch vide barre Debug applique : boutons de controle du debogueur retires/reintroduits "
          f"(plus de slot reserve au repos) ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
