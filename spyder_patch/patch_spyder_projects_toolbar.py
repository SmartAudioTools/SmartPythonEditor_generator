#!/usr/bin/env python3
"""Patch spyder/plugins/projects/widgets/main_widget.py : haut du panneau "Projets".

Contexte (TODO CachyOS "TODO - Spyder - Projets.txt"). Le panneau Projets etait le SEUL panneau
sans rien en tete : ni barre d'outils, ni selecteur. Tout passait par le menu "Projets" de la barre
de menus, que l'etudiant ne pense pas a ouvrir quand il a le panneau sous les yeux. On lui donne la
meme tete que le panneau Fichiers :

    [ combo du projet courant .................... ] [Nouveau projet] [Ouvrir un projet] [burger]

Trois changements, tous des DEPLACEMENTS ou des branchements d'existant - aucune action nouvelle :
  1. "Nouveau projet..." et "Ouvrir un projet..." (deja creees ici, posees dans le menu Projets par
     le plugin) ajoutees au coin du panneau, a gauche du bouton burger ;
  2. "Fermer le projet" et "Supprimer le projet" ajoutees au menu burger du panneau, en tete ;
  3. un combo de chemin, de la MEME classe que celui du panneau Fichiers (PathComboBox, cf.
     WorkingDirectoryComboBox), listant le projet ouvert, les projets recents et les projets
     trouves dans SMARTOS_PROJECTS_ROOT. Le choisir ouvre le projet.

Spyder n'a qu'UN projet actif a la fois (ouvrir un projet ferme le precedent) : le combo est donc un
selecteur de bascule, pas une liste de projets ouverts simultanement.

La liste est reconstruite a CHAQUE ouverture du popup (showPopup), et chaque entree passe par
is_valid_project() : c'est le "verifier leur existence" du TODO - un projet supprime ou renomme
depuis le dernier scan n'y figure plus, sans avoir a redemarrer Spyder.

Usage : patch_spyder_projects_toolbar.py <chemin vers projects/widgets/main_widget.py installe>

Remplacements de blocs exacts, idempotent (marqueur), re-parse avant ecriture, echec BRUYANT
(code 1) si un bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

MARKER = "patch_spyder_projects_toolbar.py"

# Racine des projets, injectee dans le bloc ci-dessous a la place de @SMARTOS_PROJECTS_ROOT@. Elle
# est ecrite ICI et nulle part ailleurs : patch_spyder_projects_dialog.py l'importe pour en faire le
# repertoire propose par le dialogue de creation, les deux ne peuvent donc pas diverger.
SMARTOS_PROJECTS_ROOT = "/DATA/Python"

# Liste de (ancien, nouveau). Tous doivent matcher exactement et une seule fois.
PAIRS = [
    # 1. Imports : QSize (taille recommandee du combo) et PathComboBox (le combo du dock Fichiers).
    (
        '''from qtpy.QtCore import Qt, Signal, Slot''',
        '''from qtpy.QtCore import QSize, Qt, Signal, Slot''',
    ),
    (
        '''from spyder.plugins.switcher.utils import get_file_icon, shorten_paths''',
        '''from spyder.plugins.switcher.utils import get_file_icon, shorten_paths
from spyder.widgets.comboboxes import PathComboBox''',
    ),
    # 2. Constantes + classe du combo, juste avant la classe du panneau.
    (
        '''class ProjectsOptionsMenuActions:
    SearchInSwitcher = "search_in_switcher"


# ---- Main widget''',
        '''class ProjectsOptionsMenuActions:
    SearchInSwitcher = "search_in_switcher"


# SmartOS (patch_spyder_projects_toolbar.py) : ou chercher des projets a proposer dans le combo, en
# plus du projet ouvert et des projets recents. Un dossier absent est simplement ignore (les autres
# distributions n'ont pas cette arborescence) : le combo se limite alors aux projets recents.
SMARTOS_PROJECTS_ROOT = "@SMARTOS_PROJECTS_ROOT@"


class SmartosProjectComboBox(PathComboBox):
    """
    Combo de selection du projet, calque sur celui du panneau Fichiers (WorkingDirectoryComboBox) :
    meme classe de base, meme elision a gauche, meme infobulle au survol.

    La liste est reconstruite a l'ouverture du popup plutot qu'une fois pour toutes : les projets
    crees, supprimes ou renommes depuis le dernier affichage sont ainsi pris en compte sans
    redemarrer Spyder.
    """

    def __init__(self, parent, refresh):
        super().__init__(
            parent,
            adjust_to_contents=False,
            id_="projects_path_combo",
            elide_text=True,
        )
        self._refresh = refresh
        self.setMinimumWidth(80)

    def sizeHint(self):
        """
        Taille DEMANDEE, pas taille finale : le combo etant en politique Expanding, il recoit
        ensuite toute la largeur que la barre du panneau laisse libre.

        Elle est nettement plus modeste que les 400 px du combo du panneau Fichiers, et c'est
        MESURE : ce combo-la est seul sur sa ligne, celui-ci partage la sienne avec les boutons et
        le burger. Avec 400, le coin du panneau n'avait plus la place d'afficher ses trois boutons
        et Qt repliait le burger dans un chevron "»" (constate en capture le 03/08/2026 ; la regle
        generale est dans CLAUDE_qt.md).
        """
        return QSize(120, 10)

    def enterEvent(self, event):
        """
        Infobulle posee au survol, comme pour le combo du panneau Fichiers : le texte affiche est
        elide a gauche des que le chemin depasse, l'infobulle est le seul endroit ou l'etudiant lit
        le chemin en entier. On la nomme, sans quoi un chemin nu n'apprend pas ce qu'il designe.
        """
        chemin = self.currentText()
        self.setToolTip(
            _("Current project") + (" : " + chemin if chemin else "")
        )

    def showPopup(self):
        """Rafraichir la liste juste avant de la derouler."""
        self._refresh()
        super().showPopup()


# ---- Main widget''',
    ),
    # 3. Menu burger : "Fermer le projet" et "Supprimer le projet" en tete, dans leur propre section
    #    (le menu n'avait que des reglages d'affichage).
    (
        '''        # Options menu
        menu = self.get_options_menu()
        for action in [
            hidden_action,
            single_click_action,
            search_in_switcher_action,
        ]:
            self.add_item_to_menu(
                action,
                menu=menu,
                section=ProjectExplorerOptionsMenuSections.Main
            )''',
        '''        # Options menu
        menu = self.get_options_menu()

        # SmartOS (patch_spyder_projects_toolbar.py) : "Fermer le projet" et "Supprimer le projet"
        # etaient accessibles seulement par le menu Projets de la barre de menus. Section propre, et
        # ajoutee EN PREMIER pour qu'elle apparaisse en tete du menu (l'ordre des sections est celui
        # de leur premiere apparition).
        for action in [self.close_project_action, self.delete_project_action]:
            self.add_item_to_menu(
                action,
                menu=menu,
                section=ProjectExplorerOptionsMenuSections.Project
            )

        for action in [
            hidden_action,
            single_click_action,
            search_in_switcher_action,
        ]:
            self.add_item_to_menu(
                action,
                menu=menu,
                section=ProjectExplorerOptionsMenuSections.Main
            )

        # SmartOS (patch_spyder_projects_toolbar.py) : tete du panneau, calquee sur celle du panneau
        # Fichiers -> [combo du projet courant] [Nouveau projet] [Ouvrir un projet] [burger].
        self.smartos_project_combo = SmartosProjectComboBox(
            self, self._smartos_refresh_project_combo
        )

        # Deux chemins d'activation, comme pour le combo du repertoire courant : open_dir pour une
        # saisie validee par Entree, textActivated pour un choix dans la liste deroulante.
        self.smartos_project_combo.open_dir.connect(self._smartos_switch_project)
        self.smartos_project_combo.textActivated.connect(
            self._smartos_switch_project
        )

        # sig_project_closed a deux signatures : indexer sur str, sinon la surcharge bool passerait
        # aussi par ce slot.
        self.sig_project_loaded.connect(
            lambda path: self._smartos_refresh_project_combo()
        )
        self.sig_project_closed[str].connect(
            lambda path: self._smartos_refresh_project_combo()
        )

        self.add_item_to_toolbar(
            self.smartos_project_combo, toolbar=self.get_main_toolbar()
        )

        for action_name in [
            ProjectsActions.NewProject,
            ProjectsActions.OpenProject,
        ]:
            self.add_corner_widget(
                self.get_action(action_name), before=self._options_button
            )''',
    ),
    # 4. Section de menu dediee au projet lui-meme.
    (
        """class ProjectExplorerOptionsMenuSections:
    Main = 'main'""",
        """class ProjectExplorerOptionsMenuSections:
    # SmartOS (patch_spyder_projects_toolbar.py) : section du menu burger pour les actions portant
    # sur le projet lui-meme (Fermer, Supprimer), separee des reglages d'affichage.
    Project = 'project'
    Main = 'main'""",
    ),
    # 5. Methodes de service du combo, en tete de la section "Private API".
    (
        '''    # ---- Private API
    # -------------------------------------------------------------------------
    def _set_project_dir(self, directory):''',
        '''    # ---- Private API
    # -------------------------------------------------------------------------
    def _smartos_project_candidates(self):
        """
        Projets a proposer dans le combo : le projet ouvert, les projets recents, puis ceux trouves
        dans SMARTOS_PROJECTS_ROOT, sans doublon et dans cet ordre.
        """
        candidates = []
        active = self.get_active_project_path()
        if active:
            candidates.append(active)
        candidates.extend(self.recent_projects)

        try:
            for name in sorted(os.listdir(SMARTOS_PROJECTS_ROOT)):
                candidates.append(osp.join(SMARTOS_PROJECTS_ROOT, name))
        except OSError:
            # Dossier absent (autre distribution) ou illisible : les projets recents suffisent.
            pass

        paths = []
        for path in candidates:
            path = osp.normpath(path)
            # is_valid_project() teste le dossier ET son .spyproject : un projet supprime ou
            # renomme depuis le dernier affichage disparait de la liste.
            if path not in paths and self.is_valid_project(path):
                paths.append(path)

        return paths

    def _smartos_refresh_project_combo(self):
        """Reconstruire la liste du combo, en y affichant le projet ouvert."""
        combo = getattr(self, "smartos_project_combo", None)
        if combo is None:
            return

        active = self.get_active_project_path() or ""

        # Signaux bloques : addItems et set_current_text emettraient textActivated et
        # editTextChanged, donc une reouverture en boucle du projet affiche.
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(self._smartos_project_candidates())
        combo.set_current_text(active)
        combo.selected_text = active
        combo.blockSignals(False)

    def _smartos_switch_project(self, path):
        """Ouvrir le projet choisi dans le combo (item de la liste ou chemin saisi)."""
        if not path:
            return

        path = osp.normpath(path)
        if path == osp.normpath(self.get_active_project_path() or ""):
            return

        if self.is_valid_project(path):
            self.open_project(path=path)
            return

        # Un dossier ordinaire saisi a la main : meme question que "Ouvrir un projet...", jamais de
        # creation silencieuse (open_project() sur un dossier quelconque y deposerait un .spyproject
        # sans rien demander).
        answer = QMessageBox.warning(
            self,
            _("Warning"),
            _("<b>%s</b> is not a Spyder project.<br><br>"
              "Do you want to create a project in this "
              "location?") % path,
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.Yes:
            valid, reason = self._is_valid_location(path)
            if valid:
                self.create_project(path)
                return

            QMessageBox.critical(
                self,
                _("Error"),
                _(
                    "It was not possible to create a project "
                    "in <b>{}</b>. The reason is:<br><br>{}"
                ).format(path, reason)
            )

        # Refus, ou creation impossible : le combo doit revenir au projet reellement ouvert.
        self._smartos_refresh_project_combo()

    def _set_project_dir(self, directory):''',
    ),
]

PAIRS = [
    (old, new.replace("@SMARTOS_PROJECTS_ROOT@", SMARTOS_PROJECTS_ROOT))
    for old, new in PAIRS
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers projects/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch tete du panneau Projets non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch tete du panneau Projets deja applique.")
        return 0

    # Verifier d'abord que TOUS les blocs sont presents et uniques (sinon on n'ecrit rien).
    for old, _new in PAIRS:
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch tete du panneau Projets non applique. "
                  f"Bloc:\n{old[:80]}...", file=sys.stderr)
            return 1

    patched = source
    for old, new in PAIRS:
        patched = patched.replace(old, new)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch tete du panneau Projets applique : combo de projet + Nouveau/Ouvrir dans la barre, "
          f"Fermer/Supprimer dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
