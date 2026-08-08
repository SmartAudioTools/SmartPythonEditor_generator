#!/usr/bin/env python3
"""Patch spyder/plugins/explorer/plugin.py : reorganise le HAUT du dock Fichiers.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "Barre d'outils"). Le "repertoire
courant" est fonctionnellement LIE au dock Fichiers (naviguer dans l'explorateur change le cwd, et
inversement ; ouvrir un projet fixe le cwd sur la racine). On regroupe donc tout en tete du dock
Fichiers, avec cette disposition (decidee avec l'utilisateur le 22/07/2026) :

    Ligne 1 (barre de l'Explorer) : Selectionner un repertoire de travail | Parent | Aller au
                                    repertoire du fichier courant | (hamburger)
    Ligne 2                       : combo de chemin (le selecteur de repertoire courant), seul
    puis                          : l'arbre des fichiers

Ce patch fait la partie RUNTIME (inter-plugins) :
  - deplace la barre "repertoire courant" (reduite au combo par patch_spyder_workingdir_bar_trim.py)
    de la zone d'outils de la fenetre vers SOUS la barre de l'Explorer ;
  - ajoute l'action "Selectionner un repertoire de travail" (browse_action, du plugin
    WorkingDirectory) dans la barre de l'Explorer, AVANT "Parent".
Les autres retouches sont statiques : patch_spyder_explorer_toolbar.py (retrait Precedent/Suivant +
filtre dans le hamburger) et patch_spyder_workingdir_bar_trim.py (barre reduite au combo).

MISE EN OEUVRE : on ajoute a la classe Explorer une methode on_mainwindow_visible qui DIFFERE le
travail via QTimer.singleShot(0). Le differe est indispensable : l'ordre des on_mainwindow_visible
entre plugins n'est pas garanti et le plugin Toolbar POSE la barre "repertoire courant" dans la
fenetre pendant SON on_mainwindow_visible ; singleShot(0) s'execute apres tous les
on_mainwindow_visible synchrones, donc la barre est deja posee quand on la deplace. Tout est sous
try/except : un echec laisse les barres en place plutot que de casser le demarrage.

Usage : patch_spyder_workingdir_in_files.py <chemin vers explorer/plugin.py installe>

Idempotent et UPDATE-SAFE (marqueur versionne) : si une version anterieure des methodes est deja
presente, on la REMPLACE (on retire les anciennes methodes puis on reinsere), au lieu de dupliquer.
Re-parse avant ecriture ; echec BRUYANT (code 1) si le point d'insertion est introuvable.
"""
import ast
import sys

# Marqueur VERSIONNE : incremente quand le contenu des methodes change, pour forcer la mise a jour
# des installations deja patchees par une version anterieure.
MARKER = "patch_spyder_workingdir_in_files v3"

NEW_METHODS = '''
    def on_mainwindow_visible(self):
        # SmartOS (patch_spyder_workingdir_in_files v3) : reorganiser le haut du dock Fichiers.
        # Travail DIFFERE via QTimer.singleShot(0) pour passer APRES tous les on_mainwindow_visible
        # synchrones (dont celui du plugin Toolbar qui pose la barre "repertoire courant" dans la
        # fenetre) -> sinon la barre serait reprise juste apres notre deplacement.
        super().on_mainwindow_visible()
        from qtpy.QtCore import QTimer
        QTimer.singleShot(0, self._smartos_reorg_files_dock)

    def _smartos_reorg_files_dock(self):
        # Voir on_mainwindow_visible. Tout sous try/except : un echec laisse les barres en place
        # plutot que de casser le demarrage de Spyder pour une retouche cosmetique.
        try:
            wd = self.get_plugin(Plugins.WorkingDirectory, error=False)
            if wd is None:
                return
            container = wd.get_container()
            toolbar = getattr(container, "toolbar", None)            # barre "repertoire courant" (combo)
            browse_action = getattr(container, "browse_action", None)
            main = self.get_main()
            widget = self.get_widget()
            layout = getattr(widget, "_toolbars_layout", None)
            if toolbar is None or main is None or layout is None:
                return

            # 1. "Selectionner un repertoire de travail" dans la barre de l'Explorer, AVANT "Parent"
            #    -> ordre : Selectionner, Parent, fichier courant.
            if browse_action is not None:
                try:
                    ex_toolbar = widget.get_main_toolbar()
                    if "browse_action" not in getattr(ex_toolbar, "_item_map", {}):
                        ex_toolbar.add_item(browse_action, before="parent_action")
                        # add_item ne redessine pas : on reconstruit la barre proprement.
                        ex_toolbar.clear()
                        ex_toolbar.render()
                except Exception:
                    pass

            # 2. Barre "repertoire courant" (combo) sortie de la fenetre et posee SOUS la barre de
            #    l'Explorer (les boutons au-dessus du combo).
            main.removeToolBar(toolbar)
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            if layout.indexOf(toolbar) == -1:
                layout.addWidget(toolbar)
            toolbar.setVisible(True)

            # 3. Le combo doit REMPLIR la largeur du dock. Dans l'ancienne barre d'outils, un spacer
            #    extensible (WorkingDirectorySpacer) poussait le contenu a droite ; reste dans la
            #    barre migree, il occupe l'espace et le combo garde sa taille naturelle. On retire ce
            #    spacer et on rend le combo extensible horizontalement.
            try:
                from qtpy.QtWidgets import QSizePolicy
                pathedit = getattr(container, "pathedit", None)
                if pathedit is not None:
                    pathedit.setSizePolicy(
                        QSizePolicy.Expanding, QSizePolicy.Preferred
                    )
                toolbar.remove_item("working_directory_spacer")
            except Exception:
                pass
        except Exception:
            pass
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
        print(f"Usage : {sys.argv[0]} <chemin vers explorer/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"explorer/plugin.py illisible ({error}) - patch reorg dock Fichiers non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch reorg dock Fichiers (v3) deja applique.")
        return 0

    # UPDATE-SAFE : retirer d'abord d'eventuelles methodes SmartOS d'une version anterieure, pour ne
    # pas dupliquer (les noms couvrent v1 et v2).
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    old_ranges = []
    for meth in ("on_mainwindow_visible", "_smartos_move_workingdir_to_files",
                 "_smartos_reorg_files_dock"):
        r = find_method_range(tree, "Explorer", meth)
        if r is not None:
            old_ranges.append(r)
    for start, end in sorted(old_ranges, key=lambda r: r[0], reverse=True):
        del lines[start - 1:end]
    source = "".join(lines)

    # Inserer les nouvelles methodes juste apres on_working_directory_available.
    lines = source.splitlines(keepends=True)
    rng = find_method_range(ast.parse(source), "Explorer", "on_working_directory_available")
    if rng is None:
        print(f"Explorer.on_working_directory_available introuvable dans {path} - Spyder a peut-etre "
              "restructure son code, patch reorg dock Fichiers non applique.", file=sys.stderr)
        return 1

    end = rng[1]
    if lines and not lines[end - 1].endswith("\n"):
        lines[end - 1] = lines[end - 1] + "\n"
    lines[end:end] = [NEW_METHODS]
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"L'explorer/plugin.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch reorg dock Fichiers (v3) applique ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
