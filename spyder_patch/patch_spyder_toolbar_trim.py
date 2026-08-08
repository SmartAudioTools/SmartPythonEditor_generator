#!/usr/bin/env python3
"""Patch spyder/api/widgets/toolbars.py pour RETIRER REELLEMENT des barres d'outils principales les
boutons juges non essentiels : execution par cellules et par selection/ligne (y compris les variantes
du debogueur et du profileur), creation de cellule, Preferences et gestionnaire de PYTHONPATH.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "Barre d'outils" item 1, + retours
de l'utilisateur des 22/07/2026). L'execution/debogage/profilage du FICHIER est CONSERVEE, de meme
que Nouveau/Ouvrir/Enregistrer un fichier.

Spyder n'offre AUCUN reglage .ini pour choisir bouton par bouton : la config des barres
(toolbar/toolbars_visible, last_visible_toolbars) n'agit que sur des barres ENTIERES. Les boutons
sont ajoutes par code par chaque plugin. D'ou ce patch.

APPROCHE : SUPPRIMER, pas masquer. La demande dit explicitement "pas juste les cacher". On reecrit
SpyderToolbar.render() pour, la PREMIERE fois qu'une barre se rend, retirer les boutons de la liste
noire a la fois de self._item_map (registre) ET de self._section_items (contenu des sections), puis
supprimer toute section devenue vide. Consequences :
  - l'action disparait de la STRUCTURE DE DONNEES : elle ne reapparait a aucun rendu ulterieur, ni
    dans le menu d'extension "More" de la barre (qui se remplit aussi depuis _section_items) ;
  - la section videe est supprimee -> pas de separateur orphelin, donc AUCUN trou ;
  - c'est fait une seule fois (drapeau self._smartos_trimmed), le rendu normal suit inchange.
Pourquoi dans render() et non a l'ajout (add_item_to_application_toolbar) : sauter l'AJOUT mettait en
attente indefinie tout bouton ajoute "before=<item saute>" (Nouveau/Ouvrir/Enregistrer
DISPARAISSAIENT, car ajoutes before=create_new_cell). En retirant APRES coup, les chaines "before"
sont deja resolues. render() est le premier point ou tous les boutons sont presents (ils sont
enregistres des on_plugin_available, avant on_mainwindow_visible qui declenche le premier rendu).

Cette approche remplace la precedente (filtrer au rendu sans muter les donnees, ancien marqueur
"Boutons masques") qui ne faisait que NE PAS DESSINER les boutons : l'action restait en memoire. Ici
elle est reellement retiree.

Identifiants retires (verifies sur Spyder 6.1.5), indexes par self.ID (identifiant de la barre) :
- file_toolbar   : "create_new_cell".
- run_toolbar    : "run cell", "run cell and advance", "run selection and advance" (editeur).
- debug_toolbar  : "run cell in debugger", "run selection in debugger".
- profile_toolbar: "run cell in profiler", "run selection in profiler".
- main_toolbar   : "show_action" (Preferences), "manager_action" (gestionnaire de PYTHONPATH).
Les ids "run <ctx> in <executeur>" suivent la construction f'run {context} in {executor}' du plugin
Run (RunContext.Cell='cell', .Selection='selection' ; NAME 'debugger'/'profiler'). "run file in <x>"
(execution/debogage/profilage du FICHIER) n'est PAS dans la liste : conserve. Un id absent est
ignore. Les barres de panneaux (MainWidgetToolbar), sans self.ID correspondant, ne sont pas touchees.

Usage : patch_spyder_toolbar_trim.py <chemin vers api/widgets/toolbars.py installe>

Localisation/remplacement de SpyderToolbar.render() via le module "ast". Idempotent (marqueur).
Re-parse avant ecriture ; echoue BRUYAMMENT (code de sortie 1) si la methode est introuvable - jamais
deviner. Remplace la methode entiere, donc rejoue correctement par-dessus une version anterieure du
patch (ancien marqueur "Boutons masques").
"""
import ast
import sys

MARKER = "Boutons supprimes des barres d'outils (SmartOS"

NEW_RENDER = '''    def render(self) -> None:
        """
        Render the toolbar taking into account sections and locations.

        Returns
        -------
        None
        """
        # Boutons supprimes des barres d'outils (SmartOS, cf.
        # Commun/scripts/patch_spyder_toolbar_trim.py) : la PREMIERE fois qu'une barre se rend, on
        # RETIRE reellement les boutons de la liste noire de self._item_map ET de self._section_items
        # (pas un simple masquage au rendu), puis on supprime toute section videe (pas de separateur
        # orphelin -> aucun trou). L'action disparait de la structure de donnees : absente de tout
        # rendu ulterieur et du menu d'extension "More". L'execution/debogage/profilage du FICHIER
        # ("run file in <x>") et Nouveau/Ouvrir/Enregistrer restent. Blacklist indexee par self.ID.
        if not getattr(self, "_smartos_trimmed", False):
            self._smartos_trimmed = True
            _blacklist = {
                "file_toolbar": ("create_new_cell",),
                "run_toolbar": ("run cell", "run cell and advance",
                                "run selection and advance"),
                "debug_toolbar": ("run cell in debugger",
                                  "run selection in debugger"),
                "profile_toolbar": ("run cell in profiler",
                                    "run selection in profiler"),
                "main_toolbar": ("show_action", "manager_action"),
            }.get(getattr(self, "ID", None), ())
            if _blacklist:
                for _aid in _blacklist:
                    self._item_map.pop(_aid, None)
                for _sec in list(self._section_items.keys()):
                    self._section_items[_sec] = [
                        _it for _it in self._section_items[_sec]
                        if getattr(_it, "action_id", None) not in _blacklist
                    ]
                    if not self._section_items[_sec]:
                        self._section_items.pop(_sec)

        sec_items = []
        for sec, items in self._section_items.items():
            for item in items:
                sec_items.append([sec, item])

            sep = QAction(self)
            sep.setSeparator(True)
            sec_items.append((None, sep))

        if sec_items:
            sec_items.pop()

        for sec, item in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
            else:
                add_method = super().addWidget

            add_method(item)

            if isinstance(item, QAction):
                widget = self.widgetForAction(item)

                if self._filter is not None:
                    widget.installEventFilter(self._filter)

                text_beside_icon = getattr(item, "text_beside_icon", False)
                if text_beside_icon:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget.setCheckable(True)

        self.sig_is_rendered.emit()
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
        print(f"Usage : {sys.argv[0]} <chemin vers api/widgets/toolbars.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"toolbars.py illisible ({error}) - patch barre d'outils non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch barre d'outils Spyder deja applique.")
        return 0

    rng = find_method_range(ast.parse(source), "SpyderToolbar", "render")
    if rng is None:
        print(f"SpyderToolbar.render introuvable dans {path} - Spyder a peut-etre restructure son "
              "code, patch barre d'outils non applique.", file=sys.stderr)
        return 1

    start, end = rng
    lines = source.splitlines(keepends=True)
    lines[start - 1:end] = [NEW_RENDER]
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le toolbars.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre d'outils applique : boutons cellules/selection/Preferences/PYTHONPATH "
          f"reellement retires de _item_map et _section_items ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
