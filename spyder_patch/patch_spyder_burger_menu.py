#!/usr/bin/env python3
"""Patch spyder/plugins/mainmenu/plugin.py pour remplacer la barre de menus classique
(File/Edit/Search/Source/Run/Debug/Consoles/Projects/Tools/Window/Help) par un unique bouton
burger place dans SA PROPRE barre d'outils, cachee par defaut et basculee (montrer/cacher) par
le raccourci Ctrl+M.

Contexte (TODO CachyOS du 19/07/2026, "Burger menu pour Spyder ?", demande explicite de
l'utilisateur : "je souhaite pouvoir supprimer le menu classique pour le remplacer par un menu
burger" - PAS un simple remplacement 1-pour-1 dans la QMenuBar existante, mais une fusion complete
avec la toolbar, barre de menus classique masquee entierement). Evolution du 24/07/2026 (meme
utilisateur) : le burger etait d'abord insere tout a gauche de la barre d'outils "File". Il vit
desormais dans une barre d'outils DEDIEE, cachee par defaut, que Ctrl+M affiche/cache, et la rangee
du haut est reorganisee ainsi : burger tout a gauche, barre Fichiers collee a sa suite, puis une
DragArea (zone vide extensible ET glissable) ; combinee a la DragArea de la barre window_controls
(a droite, avant les boutons de fenetre), elle CENTRE au milieu le groupe des autres barres. Ctrl+M
etait le raccourci "enter array table" (constructeur de tableau NumPy) de l'editeur et de la console
IPython : l'utilisateur a explicitement accepte de l'ecraser, ce raccourci est donc vide dans la
config Spyder deployee (Commun/config_files/spyder_<version>/spyder.ini, [shortcuts], editor/ et
ipython_console/enter array table = <vide> ; egalement pose sur la config live par installation_SmartPythonEditor.sh
via tools/spyder_config_set.py) - sans quoi Qt aurait deux Ctrl+M en concurrence (ambigus) des que
l'editeur ou la console a le focus.

MainMenu.on_initialize() (spyder/plugins/mainmenu/plugin.py) cree les 9 a 11 menus d'application
(File/Edit/.../Help, Consoles et Projects etant conditionnels) et les ajoute un par un a
self.main.menuBar() via create_application_menu() -> self.main.menuBar().addMenu(menu). Ce patch
ajoute deux methodes :

1. _build_burger_menu(), appelee a la fin de on_initialize() (juste apres la creation du dernier
   menu, Help) : retire chaque menu de la barre (menuBar().removeAction) et le rajoute comme
   sous-menu d'un unique QMenu self._burger_menu. QMenu.addMenu(menu) reutilise directement
   l'action existante du menu (menu.menuAction()) au lieu d'en creer une copie : les menus
   File/Edit/... restent les MEMES objets QMenu que ceux peuples/mis a jour par le reste de Spyder
   (sections, items ajoutes dynamiquement par les plugins, rendu differe via menu.render()) -
   aucune duplication de logique, self._burger_menu n'est qu'un conteneur different pour les memes
   menus. Ne touche PAS encore a la toolbar (elle n'est pas garantie exister a ce stade, cf. point
   2 ci-dessous) ni a la visibilite de la barre de menus.

2. _install_burger_menu_button(), appelee a la fin de on_mainwindow_visible() (methode deja
   existante, qui fait deja "for menu in self._APPLICATION_MENUS.values(): menu.render()") :
   cree un QToolButton (icone 'tooloptions' = mdi.menu, deja utilisee partout ailleurs dans Spyder
   pour les boutons d'options/hamburger des panneaux) ayant self._burger_menu comme popup en
   InstantPopup, dans une QToolBar DEDIEE (objectName 'spyder_burger_toolbar'), cachee par defaut.
   Son toggleViewAction() (action Qt cochable qui montre/cache la barre) recoit Ctrl+M en contexte
   ApplicationShortcut, ajoutee a la fenetre principale (main.addAction) pour que le raccourci soit
   actif partout, barre visible ou non. Enfin la barre de menus classique, vide, est masquee.

   DISPOSITION de la rangee du haut (evolution du 24/07/2026) : burger tout a gauche, barre Fichiers
   collee, puis une seconde QToolBar dediee 'spyder_burger_dragarea' contenant une DragArea (le
   widget reutilise du plugin spyder_window_controls : zone vide extensible et poignee de
   deplacement de la fenetre sans decoration ; repli en QWidget extensible si ce plugin manque).
   CENTRAGE : QMainWindow attribue TOUT l'espace libre a la seule barre extensible la plus a droite
   (la DragArea de window_controls), jamais un partage entre deux barres. La largeur de la DragArea
   gauche est donc CALCULEE (_recenter : W/2 - epingle_gauche - groupe/2, epingle_gauche = burger +
   Fichiers) pour que le groupe soit centre ; celle de droite remplit le reste. Recalcule sur
   main.sig_resized et a chaque bascule du burger (dont la largeur change l'epinglage).
   PLACEMENT (_place_left) DIFFERE via QTimer.singleShot (comme spyder_window_controls) : reordonne
   burger / Fichiers / DragArea gauche devant la barre du groupe la plus a gauche, reperee par sa
   GEOMETRIE x (l'ordre de toolbar_plugin.toolbarslist est l'ordre d'AJOUT, pas l'ordre visuel).
   Deux passes (l'ancre par x n'est fiable qu'une fois la rangee reellement disposee).
   burger et dragbar sont des QToolBar NUES (main.addToolBar), pas des barres gerees : on n'utilise
   PAS create_application_toolbar() dont le render() differe pourrait, selon l'ordre des
   on_mainwindow_visible, reconstruire la barre et evincer le widget. Elles sont donc absentes de
   toolbarslist (d'ou leur traitement a part dans _recenter/_place_left). La barre burger recopie
   file_toolbar.isMovable() (meme etat verrouille que les autres barres). Recuperation du plugin
   Toolbar via self.main.get_plugin(Plugins.Toolbar, error=False) ; garde None -> degradation
   gracieuse.
   Cette methode a besoin que le plugin Toolbar ait deja fini son on_initialize() - garanti a ce
   stade car on_mainwindow_visible() n'est appele pour AUCUN plugin avant que on_initialize() ait
   fini pour TOUS les plugins (deux phases globales sequentielles, cf. spyder/app/mainwindow.py).
   D'ou la separation en deux methodes : _build_burger_menu() (qui ne depend que des menus,
   disponibles des on_initialize()) et _install_burger_menu_button() (retardee jusqu'a
   on_mainwindow_visible()).

   Raccourci Ctrl+M : cf. le paragraphe d'en-tete sur le conflit avec "enter array table". Le
   toggle est branche en QAction Qt brute (pas via le registre de raccourcis de Spyder) : il
   n'apparait donc pas dans Preferences > Raccourcis clavier et n'est pas reconfigurable la-bas -
   choix assume pour la simplicite, l'utilisateur ayant demande explicitement Ctrl+M.

Limite connue acceptee : remove_application_menu() (appelee uniquement a la fermeture/desactivation
d'un plugin, ex. Consoles ou Projects desactive depuis Preferences > Plugins - jamais en usage
interactif normal) fait encore "self.main.menuBar().removeAction(menu.menuAction())", qui ne fait
plus rien puisque l'action vit desormais dans self._burger_menu et non plus dans menuBar() -
QWidget.removeAction() sur une action absente est un no-op silencieux (pas de plantage), le pire cas
est une entree desactivee qui reste visible dans le burger menu jusqu'au redemarrage de Spyder. Non
traite ici : cas rarissime, sans consequence fonctionnelle sur le burger menu lui-meme.

Localisation des points d'insertion via le module "ast" (comme patch_spyder_status_menu.py et
patch_spyder_raise_window.py) plutot qu'une recherche exacte de bloc de texte pour les deux
nouvelles methodes (retrouve on_mainwindow_visible par son nom dans la classe MainMenu, quels que
soient les commentaires/docstring autour). Les lignes d'appel aux deux nouvelles methodes sont elles
localisees par recherche exacte de texte (une seule occurrence attendue chacune) : plus simple qu'un
parcours ast pour ajouter une seule ligne en fin de corps de methode, et echoue tout aussi
bruyamment si introuvable.

Idempotent : si le marqueur du patch (nom de la premiere nouvelle methode) est deja present, ne
fait rien.

Usage : patch_spyder_burger_menu.py <chemin vers plugin.py installe (spyder/plugins/mainmenu/plugin.py)>
"""
import ast
import sys

BURGER_MENU_MARKER = "_build_burger_menu"

OLD_LAST_INIT_LINE = (
    '        create_app_menu(ApplicationMenus.Help, _("&Help"))\n'
)
NEW_LAST_INIT_LINES = (
    '        create_app_menu(ApplicationMenus.Help, _("&Help"))\n'
    '\n'
    '        # Regroupe tous les menus ci-dessus dans un unique menu burger (TODO CachyOS du\n'
    '        # 19/07/2026, "Burger menu pour Spyder ?"). Cf. docstring de\n'
    '        # patch_spyder_burger_menu.py pour le detail complet.\n'
    '        self._build_burger_menu()\n'
)

OLD_RENDER_LOOP_LINE = "            menu.render()\n"
NEW_RENDER_LOOP_LINES = (
    "            menu.render()\n"
    "\n"
    "        # Installe le bouton burger dans la toolbar File une fois que TOUS les plugins\n"
    "        # (dont Toolbar) ont fini leur on_initialize() - cf. docstring de\n"
    "        # patch_spyder_burger_menu.py pour le detail complet.\n"
    "        self._install_burger_menu_button()\n"
)

NEW_METHODS = '''    def _build_burger_menu(self):
        """
        Retire tous les menus d'application de la barre de menus et les regroupe comme
        sous-menus d'un unique menu burger, garde en reference sur self._burger_menu (TODO
        CachyOS du 19/07/2026, "Burger menu pour Spyder ?" - demande explicite de l'utilisateur).
        Cf. docstring de patch_spyder_burger_menu.py pour le detail complet.
        """
        menu_bar = self.main.menuBar()
        self._burger_menu = self._create_menu(
            menu_id='burger_menu', parent=self.main, title='☰'
        )
        for menu in list(self._APPLICATION_MENUS.values()):
            menu_bar.removeAction(menu.menuAction())
            self._burger_menu.addMenu(menu)

    def _install_burger_menu_button(self):
        """
        Dispose la rangee du haut : bouton burger dans SA PROPRE barre tout a gauche, barre
        Fichiers collee a sa suite, puis une DragArea qui - combinee a celle de window_controls a
        droite - CENTRE au milieu le groupe des autres barres (les boutons de fenetre restent a
        droite). Le burger est cache par defaut (affiche par Ctrl+M) ; la barre de menus classique,
        desormais vide, est masquee (TODO CachyOS du 19/07/2026 puis 24/07/2026, demande explicite
        de l'utilisateur). Cf. docstring de patch_spyder_burger_menu.py pour le detail complet
        (dont pourquoi cette methode est appelee depuis on_mainwindow_visible et non on_initialize,
        et le conflit Ctrl+M).
        """
        main = self.main
        toolbar_plugin = main.get_plugin(Plugins.Toolbar, error=False)

        try:
            from spyder_window_controls.spyder.widgets import (
                DragArea as _DragArea)
        except Exception:
            _DragArea = None

        burger_button = QToolButton(main)
        burger_button.setPopupMode(QToolButton.InstantPopup)
        burger_button.setIcon(ima.icon('tooloptions'))
        burger_button.setToolTip(_("Menu"))
        burger_button.setMenu(self._burger_menu)

        # Barre d'outils dediee au seul bouton burger, cachee par defaut (affichee par Ctrl+M).
        burger_toolbar = QToolBar(_("Menu"), main)
        burger_toolbar.setObjectName('spyder_burger_toolbar')
        burger_toolbar.setIconSize(QSize(24, 24))
        burger_toolbar.addWidget(burger_button)
        main.addToolBar(burger_toolbar)
        if toolbar_plugin is not None:
            try:  # meme etat verrouille/deverrouille (poignee) que les autres barres
                burger_toolbar.setMovable(
                    toolbar_plugin.get_application_toolbar(
                        ApplicationToolbars.File).isMovable())
            except Exception:
                pass

        # DragArea GAUCHE, entre le burger/Fichiers (epingles a gauche) et le groupe centre.
        # Combinee a la DragArea de window_controls (a droite, avant les boutons de fenetre), elle
        # CENTRE le groupe ; les DEUX vides restent des poignees de deplacement de la fenetre.
        # Repli en QWidget extensible si window_controls (donc DragArea) est absent.
        dragbar = QToolBar(main)
        dragbar.setObjectName('spyder_burger_dragarea')
        dragbar.setMovable(False)
        dragbar.setFloatable(False)
        drag = _DragArea(main) if _DragArea is not None else QWidget(main)
        if _DragArea is None:
            drag.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        dragbar.addWidget(drag)
        main.addToolBar(dragbar)

        # Centrage : QMainWindow donne TOUT l'espace libre a la barre extensible la plus a droite
        # (la DragArea de window_controls), jamais un partage entre deux. On CALCULE donc la largeur
        # de la DragArea gauche pour que le groupe soit centre au milieu ; celle de droite remplit
        # le reste. Le groupe = les barres GEREES du haut sauf window_controls (a droite) et
        # Fichiers (epinglee a gauche). burger et dragbar sont des QToolBar nues, hors toolbarslist.
        # Barres EPINGLEES A GAUCHE, aux cotes de Fichiers : elles ne font pas partie du groupe
        # centre, elles le decalent. La liste est ouverte - un autre patch peut y ajouter la sienne
        # en posant son objectName dans main._smartos_barres_epinglees_gauche (c'est ce que fait
        # patch_spyder_deux_ecrans.py pour la barre « Écrans », a la demande de l'utilisateur du
        # 31/07/2026 : « je veux la barre d'outils pour les deux écrans plutôt à gauche collé à
        # celle des fichiers »). Elle est LUE A CHAQUE APPEL, et non capturee ici : les barres qui
        # se declarent tard - apres tous les on_mainwindow_visible - arrivent apres ce code.
        def _epingles_a_gauche():
            return ('file_toolbar',) + tuple(
                getattr(main, '_smartos_barres_epinglees_gauche', ()))

        def _recenter():
            if toolbar_plugin is None:
                return
            epingles = _epingles_a_gauche()
            group_w = pinned = 0
            for tb in toolbar_plugin.toolbarslist:
                if not (tb.isVisible()
                        and main.toolBarArea(tb) == Qt.TopToolBarArea):
                    continue
                on = tb.objectName()
                if on == 'window_controls_toolbar':
                    continue
                if on in epingles:
                    pinned += tb.width()
                else:
                    group_w += tb.width()
            if burger_toolbar.isVisible():
                pinned += burger_toolbar.width()
            drag.setFixedWidth(
                max(0, main.width() // 2 - pinned - group_w // 2))

        # PUBLIE sur main : la bascule deux ecrans (patch_spyder_deux_ecrans.py) passe par
        # restoreState() SANS redimensionner la fenetre principale (le second ecran a sa propre
        # fenetre), donc ni sig_resized ni la bascule du burger ne rejouent le recentrage - la
        # DragArea gauche garde la largeur figee calculee dans l'autre mode (releve utilisateur
        # du 08/08/2026 : « les boutons du milieu ne retournent pas au milieu »).
        main._smartos_recentrer_barres = _recenter

        # Placement DIFFERE en fin de boucle d'evenements (QTimer.singleShot), apres que le plugin
        # Toolbar a dispose ses barres - meme technique que spyder_window_controls. Ordre vise :
        # burger, Fichiers, DragArea gauche, puis le groupe. L'ancre est la barre du groupe la plus
        # a GAUCHE reperee par sa GEOMETRIE (x) : l'ordre de toolbarslist ne suit pas l'ordre visuel.
        def _place_left():
            if toolbar_plugin is None:
                _recenter()
                return
            file_tb = None
            try:
                file_tb = toolbar_plugin.get_application_toolbar(
                    ApplicationToolbars.File)
            except Exception:
                pass
            epingles = _epingles_a_gauche()
            cands = [tb for tb in toolbar_plugin.toolbarslist
                     if tb.isVisible()
                     and main.toolBarArea(tb) == Qt.TopToolBarArea
                     and tb.objectName() != 'window_controls_toolbar'
                     and tb.objectName() not in epingles]
            if cands:
                anchor = min(
                    cands, key=lambda tb: tb.mapTo(main, QPoint(0, 0)).x())
                main.insertToolBar(anchor, dragbar)
                # Les epinglees additionnelles viennent JUSTE AVANT la DragArea gauche, donc
                # collees a Fichiers ; puis Fichiers devant elles, puis le burger tout a gauche.
                suivante = dragbar
                for nom in reversed(epingles[1:]):
                    tb = next((t for t in toolbar_plugin.toolbarslist
                               if t.objectName() == nom), None)
                    if tb is not None:
                        main.insertToolBar(suivante, tb)
                        suivante = tb
                if file_tb is not None:
                    main.insertToolBar(suivante, file_tb)
                    main.insertToolBar(file_tb, burger_toolbar)
                else:
                    main.insertToolBar(suivante, burger_toolbar)
            _recenter()

        # Deux passes de placement (l'ancre par geometrie n'est fiable qu'une fois la rangee
        # disposee), un recentrage tardif quand les combos ont leur taille finale, puis a chaque
        # redimensionnement de la fenetre.
        QTimer.singleShot(0, _place_left)
        QTimer.singleShot(400, _place_left)
        QTimer.singleShot(700, _recenter)
        try:
            main.sig_resized.connect(lambda *a: _recenter())
        except Exception:
            pass

        burger_toolbar.setVisible(False)  # cache par defaut ; Ctrl+M l'affiche

        toggle_action = burger_toolbar.toggleViewAction()
        toggle_action.setShortcut(QKeySequence("Ctrl+M"))
        toggle_action.setShortcutContext(Qt.ApplicationShortcut)
        toggle_action.toggled.connect(lambda *a: _recenter())
        main.addAction(toggle_action)

        main.menuBar().setVisible(False)

'''

NEW_SPYDER_IMPORTS = (
    "from spyder.plugins.toolbar.api import ApplicationToolbars\n"
    "from spyder.utils.icon_manager import ima\n"
)
NEW_QTPY_IMPORT = (
    "from qtpy.QtCore import Qt, QPoint, QSize, QTimer\n"
    "from qtpy.QtGui import QKeySequence\n"
    "from qtpy.QtWidgets import QSizePolicy, QToolBar, QToolButton, QWidget\n"
)


def _find_method_line_range(content, class_name, method_name):
    """Renvoie (lineno, end_lineno) 1-indexes (inclus) de la methode, ou None si introuvable."""
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ):
                    return item.lineno, item.end_lineno
    return None


def _find_last_import_line(content, predicate):
    """Renvoie le end_lineno (1-indexe) du dernier import de haut niveau verifiant predicate(node),
    ou None si aucun ne correspond."""
    tree = ast.parse(content)
    last_line = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) and predicate(node):
            if last_line is None or node.end_lineno > last_line:
                last_line = node.end_lineno
    return last_line


def _insert_before_method(content, class_name, method_name, new_text):
    method_range = _find_method_line_range(content, class_name, method_name)
    if method_range is None:
        return None
    start, _end = method_range
    lines = content.split("\n")
    lines[start - 1:start - 1] = new_text.rstrip("\n").split("\n") + [""]
    return "\n".join(lines)


def _insert_import(content, new_import_text, predicate):
    """Insere new_import_text juste apres le dernier import de haut niveau verifiant predicate."""
    last_line = _find_last_import_line(content, predicate)
    if last_line is None:
        return None
    lines = content.split("\n")
    lines[last_line:last_line] = new_import_text.rstrip("\n").split("\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage : patch_spyder_burger_menu.py <chemin vers mainmenu/plugin.py>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        content = f.read()

    if BURGER_MENU_MARKER in content:
        return  # deja applique

    # 1) Nouvelle methode _install_burger_menu_button() inseree avant on_mainwindow_visible, et
    #    _build_burger_menu() inseree avant elle (meme bloc NEW_METHODS, dans cet ordre) - les deux
    #    en une seule insertion pour garder l'ordre relatif exact.
    new_content = _insert_before_method(
        content, "MainMenu", "on_mainwindow_visible", NEW_METHODS
    )
    if new_content is None:
        print(
            f"Patch burger_menu : methode MainMenu.on_mainwindow_visible introuvable dans "
            f"{path} - Spyder a peut-etre restructure son code, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    # 2) Appel a _build_burger_menu() en fin de on_initialize()
    if content.count(OLD_LAST_INIT_LINE) != 1:
        print(
            f"Patch burger_menu : ligne de creation du menu Help introuvable (ou presente "
            f"plusieurs fois) dans {path} - Spyder a peut-etre restructure son code, patch non "
            f"applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = content.replace(OLD_LAST_INIT_LINE, NEW_LAST_INIT_LINES)

    # 3) Appel a _install_burger_menu_button() en fin de on_mainwindow_visible()
    if content.count(OLD_RENDER_LOOP_LINE) != 1:
        print(
            f"Patch burger_menu : boucle 'menu.render()' introuvable (ou presente plusieurs "
            f"fois) dans {path} - Spyder a peut-etre restructure son code, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = content.replace(OLD_RENDER_LOOP_LINE, NEW_RENDER_LOOP_LINES)

    # Classe chaque nouvel import dans la bonne section plutot que de les entasser en fin de bloc.
    new_content = _insert_import(
        content, NEW_QTPY_IMPORT, lambda node: isinstance(node, ast.Import)
    )
    if new_content is None:
        print(
            f"Patch burger_menu : aucun import 'import X' de haut niveau trouve dans {path} - "
            "situation inattendue, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    new_content = _insert_import(
        content,
        NEW_SPYDER_IMPORTS,
        lambda node: (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("spyder.")
        ),
    )
    if new_content is None:
        print(
            f"Patch burger_menu : aucun import 'from spyder.xxx import ...' de haut niveau trouve "
            f"dans {path} - situation inattendue, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    with open(path, "w") as f:
        f.write(content)
    print(f"Patch burger_menu applique : {path}")


if __name__ == "__main__":
    main()
