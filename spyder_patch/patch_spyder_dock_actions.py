#!/usr/bin/env python3
"""Retire "Deplacer", "Detacher", "Ancrer" et "Fermer" du menu burger (options) de TOUS les panneaux,
et tire les deux consequences que cela entraine.

Contexte : CachyOS/Documentation/TODO - Spyder - cosmetique.txt, item 2 ("supprimer les
Deplacer / Detacher / Fermer de tous les menu burgers"), demande de l'utilisateur du 26/07/2026.

Ces quatre actions ne sont pas ajoutees panneau par panneau : PluginMainWidget._setup() les met
d'office dans la section Bottom du menu d'options de CHAQUE panneau. Un seul point a modifier, donc,
pour les 22 panneaux de cette installation.

POURQUOI "ANCRER" AUSSI, alors que l'utilisateur n'a cite que les trois autres. Elle a d'abord ete
conservee, puis retiree APRES MESURE (capture du menu du Terminal, 26/07/2026,
HGIGNORED/menu_terminal.png) :
  - elle n'est visible que sur un panneau DETACHE (_update_actions : setVisible(not
    show_dock_actions)), et "Detacher" ayant disparu, plus rien ne peut detacher un panneau : c'est
    une entree morte ;
  - elle est la SEULE de son menu a porter une icone dans plusieurs panneaux (Terminal, Historique,
    Projets...). Qt reserve la colonne de gauche des qu'UNE entree en porte une : son icone se
    retrouvait seule dans une gouttiere vide - c'est-a-dire exactement le "bouton qui flotte dans le
    vide" que l'item 1 du meme TODO demande de corriger ailleurs. La retirer supprime la cause au
    lieu de la deplacer.
Ce qui est perdu : fermer un panneau depuis son propre menu. Le chemin reste Affichage > Panneaux
(cases a cocher), qui liste tous les panneaux et coche les affiches ; et decocher/recocher un panneau
le rendrait a sa place s'il se retrouvait un jour detache par un autre chemin.
Les quatre actions restent CREEES : _update_actions(), _on_top_level_change() et
_on_title_bar_shown() continuent de les piloter sans rien savoir de leur emplacement, et rien ne
plante sur une action qui n'est dans aucun menu. Seul leur emplacement change - ici, disparait.

CINQ CHANGEMENTS, et les quatre derniers ne sont pas cosmetiques : sans eux, retirer des boutons
d'une barre ou d'un menu de panneau DEGRADE l'interface au lieu de l'alleger. Aucun n'a ete devine :
tous viennent de sondes --gui-exec du 26/07/2026 (HGIGNORED/sonde_menus_burger.py,
sonde_geometrie.py, sonde_orphelins.py), qui ont releve le contenu et la GEOMETRIE reels des 22
panneaux dans le Spyder de l'utilisateur.

  1. main_widget.py : plus aucune action de dock dans le menu d'options.
  2. menus.py : retirer les separateurs de FIN dans PluginMainWidgetOptionsMenu.render().
     Cette methode ajoute un separateur apres CHAQUE section, derniere comprise ; tant que la
     section Bottom portait quatre actions, quelque chose suivait toujours ce dernier trait. Elle
     vide, le menu se terminerait par un trait horizontal suivi de RIEN. add_actions()
     (spyder/utils/qthelpers.py) sait deja ignorer un separateur de TETE et les separateurs
     consecutifs, mais pas celui de fin.
  3. main_widget.py : masquer le bouton burger d'un panneau dont le menu d'options est vide. CINQ
     panneaux n'avaient dans ce menu que les actions de dock (Python Tutor, Pyxel, Pyxel Studio,
     Edition collaborative, VizTracer - releve par la sonde) : leur bouton n'aurait plus ouvert qu'un
     rectangle vide. L'Editeur etait un sixieme cas, mais Spyder masque deja lui-meme son bouton
     (editor/widgets/main_widget.py : self._options_button.hide()) au profit de celui de la barre
     d'onglets (editor_stack_options_button), que ce patch ne touche pas.
     Le controle est DIFFERE d'un tour de boucle d'evenements (QTimer.singleShot(0)) : les entrees
     propres a un panneau sont ajoutees par SON setup(), qui tourne apres le _setup() de la classe
     de base ou le controle est branche.
     LIMITE ASSUMEE : un panneau qui peuplerait son menu d'options PLUS TARD (au-dela de ce tour de
     boucle) garderait son bouton masque. Aucun panneau ne le fait - la sonde montre que les 17 menus
     non vides sont tous peuples pendant setup(), et les 5 vides n'ajoutent rien du tout.
  4. main_widget.py : masquer les BOUTONS ORPHELINS du panneau. C'est LE vrai defaut des "boutons qui
     flottent dans le vide" signale par l'utilisateur - et que trois passes precedentes avaient croise
     sans le voir, en se persuadant qu'elles ne changeaient "que l'emplacement" des boutons.
     MECANISME : create_toolbutton() (spyder/utils/qthelpers.py) fait QToolButton(parent) avec le
     PANNEAU pour parent. Un bouton qu'on retire ensuite d'une barre n'est donc PAS retire de
     l'affichage : il reste enfant direct du panneau, sans layout, a la position (0, 0) et a sa taille
     par defaut - 100x30 la ou ses voisins font 44x44 - DESSINE PAR-DESSUS la barre, plus haut
     qu'eux. Il flotte, au sens litteral.
     RELEVE (sonde_orphelins.py, sur les 22 panneaux, caches compris) : CINQ orphelins, tous laisses
     par nos propres patchs, et dans exactement les trois panneaux cites par l'utilisateur -
     outline_explorer "Aller a la position du curseur" ; ipython_console "Interrompre le noyau",
     "Effacer la console", "Se reconnecter au noyau distant" ; terminal "Reload terminal". Les 19
     autres panneaux sont propres : leurs patchs deplacaient des ACTIONS, qui ne laissent pas de
     widget derriere elles.
     POURQUOI UN FILET GENERAL et non un hide() dans chacun des trois patchs : le piege se retend a
     chaque passe d'allegement de barre (il l'a fait trois fois de suite sans etre vu), et le corriger
     dans la classe de base le neutralise aussi pour les panneaux de nos greffons et pour les passes
     futures. Le critere est exact, pas heuristique : un bouton place dans une barre a CETTE BARRE
     pour parent (addWidget reparente), un bouton place par le panneau dans son contenu est gere par
     un layout ; est donc orphelin ce qui est enfant DIRECT du panneau ET hors de tout layout. Verifie
     sur les 22 panneaux : 5 orphelins trouves, 0 faux positif.
     Les boutons restent CREES et pilotables : update_actions() continue d'appeler
     stop_button.setEnabled() et reconnect_button.setMaximumWidth(), ce qui ne pose aucun probleme sur
     un widget masque.
  5. menus.py : meme retrait du separateur de FIN, un cran au-dessus, dans SpyderMenu.get_actions().
     Le changement 2 ne couvre que le menu d'options des PANNEAUX ; le burger de la barre d'onglets
     de l'Editeur est un SpyderMenu ordinaire, dont render() passe par get_actions(). Releve du
     27/07/2026 (sonde --actions, HGIGNORED/sonde_split.json) : ce menu se terminait DEJA par un
     trait suivi de rien, avant meme qu'on lui retire ses actions de dock - ce que fait
     patch_spyder_editor_split_buttons.py, l'Editeur ayant echappe au changement 1.

Usage : patch_spyder_dock_actions.py <chemin vers api/widgets/main_widget.py> <.../api/widgets/menus.py>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja dans le fichier
concerne, ce qui permet a une passe ulterieure d'ajouter ou de SUPPLANTER un bloc sans defaire les
autres (un marqueur global unique l'aurait rendue inoperante - piege deja paye sur ce depot). Un bloc
qui supplante celui d'une passe precedente declare PLUSIEURS textes anciens possibles, DU PLUS
SPECIFIQUE AU PLUS GENERAL : le texte pose par la passe precedente CONTIENT en general celui d'origine
de Spyder, donc les deux matchent, et c'est l'ordre qui designe le bon. Re-parse de chaque fichier
avant ecriture, et AUCUN fichier n'est ecrit si l'un des deux echoue. Echec BRUYANT (code 1) si un
bloc attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# Texte d'origine de Spyder (installation fraiche).
DOCK_MENU_SPYDER = '''        for item in [
            self.lock_unlock_action,
            self.undock_action,
            self.dock_action,
            self.close_action,
        ]:
            self.add_item_to_menu(
                item,
                self._options_menu,
                section=OptionsMenuSections.Bottom,
            )'''

# Texte pose par la 1re passe du 26/07/2026, qui ne gardait qu'"Ancrer" - supplante par le bloc 1.
DOCK_MENU_V1 = '''        # SmartOS (patch_spyder_dock_actions.py) : "Deplacer", "Detacher" et "Fermer" ne sont
        # plus mises dans la section Bottom du menu d'options de CHAQUE panneau (demande de
        # l'utilisateur du 26/07/2026). Les actions restent CREEES ci-dessus : _update_actions(),
        # _on_top_level_change() et _on_title_bar_shown() continuent de les piloter sans rien savoir
        # de leur emplacement. "Ancrer" reste, seule : elle n'est de toute facon visible que sur un
        # panneau detache, et c'est le seul chemin de retour si cela arrivait.
        # Pour fermer un panneau : Affichage > Panneaux.
        for item in [
            self.dock_action,
        ]:
            self.add_item_to_menu(
                item,
                self._options_menu,
                section=OptionsMenuSections.Bottom,
            )'''

DOCK_MENU_NEW = '''        # SmartOS (patch_spyder_dock_actions.py) : AUCUNE action de dock n'est mise dans le menu
        # d'options des panneaux - ni "Deplacer", ni "Detacher", ni "Fermer" (demande de
        # l'utilisateur du 26/07/2026), ni "Ancrer", qui devient une entree morte sans "Detacher" et
        # dont l'icone flottait seule dans la gouttiere des menus qui n'en comptent aucune autre.
        # Les quatre actions restent CREEES ci-dessus : _update_actions(), _on_top_level_change() et
        # _on_title_bar_shown() continuent de les piloter sans rien savoir de leur emplacement.
        # Pour fermer ou reafficher un panneau : Affichage > Panneaux.'''

# Ancrage du bloc 3 (fin de _setup) et textes poses par les versions PRECEDENTES du bloc 3, que
# celui-ci supplante. Les trois candidats vont du plus specifique au plus general (le pristine
# TITLE_ANCHOR est un prefixe des deux autres).
TITLE_ANCHOR = '''        # Update title
        self.setWindowTitle(self.get_title())'''

OPTIONS_BUTTON_V1 = TITLE_ANCHOR + '''

        # SmartOS (patch_spyder_dock_actions.py) : masquer le bouton burger d'un panneau dont le
        # menu d'options ne contient plus aucune entree visible - six panneaux n'y avaient que les
        # actions de dock, desormais retirees (cf. l'en-tete du patch). DIFFERE d'un tour de boucle
        # d'evenements : les entrees propres a un panneau sont ajoutees par SON setup(), qui tourne
        # apres ce _setup() de la classe de base.
        from qtpy.QtCore import QTimer as _SmartosQTimer
        _SmartosQTimer.singleShot(0, self._smartos_update_options_button)

    def _smartos_update_options_button(self) -> None:
        """
        Masquer le bouton burger du panneau si son menu d'options n'a aucune entree visible, le
        montrer sinon. Cf. Commun/scripts/patch_spyder_dock_actions.py.
        """
        if self._options_button is None or self._options_menu is None:
            return

        # Rendu force : sans cela le menu n'a encore aucune action Qt (il n'est rendu qu'a sa
        # premiere ouverture) et le panneau serait TOUJOURS juge vide.
        self._options_menu._dirty = True
        self._options_menu.render()

        self._options_button.setVisible(
            any(
                not action.isSeparator() and action.isVisible()
                for action in self._options_menu.actions()
            )
        )'''

OPTIONS_BUTTON_V2 = TITLE_ANCHOR + '''

        # SmartOS (patch_spyder_dock_actions.py) : masquer le bouton burger d'un panneau dont le menu
        # d'options est VIDE - cinq panneaux n'y avaient que les actions de dock, desormais retirees
        # (cf. l'en-tete du patch), et leur bouton n'aurait plus ouvert qu'un rectangle vide. DIFFERE
        # d'un tour de boucle d'evenements : les entrees propres a un panneau sont ajoutees par SON
        # setup(), qui tourne apres ce _setup() de la classe de base.
        from qtpy.QtCore import QTimer as _SmartosQTimer
        _SmartosQTimer.singleShot(0, self._smartos_update_options_button)

    def _smartos_update_options_button(self) -> None:
        """
        Masquer le bouton burger du panneau si son menu d'options n'a aucune entree, le montrer
        sinon. Cf. Commun/scripts/patch_spyder_dock_actions.py.
        """
        if self._options_button is None or self._options_menu is None:
            return

        # Rendu force : sans cela le menu n'a encore aucune action Qt (il n'est rendu qu'a sa
        # premiere ouverture) et TOUS les panneaux seraient juges vides.
        self._options_menu._dirty = True
        self._options_menu.render()

        # Un menu reduit a des separateurs compte comme vide - il ne devrait plus y en avoir depuis
        # que render() retire ceux de fin, mais le test ne coute rien et ne depend pas de ce patch.
        self._options_button.setVisible(
            any(not action.isSeparator() for action in self._options_menu.actions())
        )'''

OPTIONS_BUTTON_NEW = TITLE_ANCHOR + '''

        # SmartOS (patch_spyder_dock_actions.py) : rangement differe du panneau - masquage du bouton
        # burger devenu inutile et des boutons orphelins. DIFFERE d'un tour de boucle d'evenements :
        # barres et menus propres a un panneau sont peuples par SON setup(), qui tourne apres ce
        # _setup() de la classe de base.
        from qtpy.QtCore import QTimer as _SmartosQTimer
        _SmartosQTimer.singleShot(0, self._smartos_tidy_panel)

    def _smartos_tidy_panel(self) -> None:
        """
        Deux rangements, differes en fin de construction du panneau. Cf.
        Commun/scripts/patch_spyder_dock_actions.py.
        """
        self._smartos_hide_empty_options_button()
        self._smartos_hide_orphan_toolbuttons()

    def _smartos_hide_empty_options_button(self) -> None:
        """
        Masquer le bouton burger du panneau si son menu d'options n'a aucune entree, le montrer
        sinon.
        """
        if self._options_button is None or self._options_menu is None:
            return

        # Rendu force : sans cela le menu n'a encore aucune action Qt (il n'est rendu qu'a sa
        # premiere ouverture) et TOUS les panneaux seraient juges vides.
        self._options_menu._dirty = True
        self._options_menu.render()

        # Un menu reduit a des separateurs compte comme vide - il ne devrait plus y en avoir depuis
        # que render() retire ceux de fin, mais le test ne coute rien et ne depend pas de ce patch.
        self._options_button.setVisible(
            any(not action.isSeparator() for action in self._options_menu.actions())
        )

    def _smartos_hide_orphan_toolbuttons(self) -> None:
        """
        Masquer les boutons ORPHELINS du panneau : ceux que create_toolbutton() a crees mais qu'on
        n'a ajoutes a aucune barre d'outils. Cf. l'en-tete de
        Commun/scripts/patch_spyder_dock_actions.py pour le mecanisme et le releve.
        """
        from qtpy.QtWidgets import QToolButton as _SmartosQToolButton

        def _geres_par_layout(layout, acc):
            """Widgets pris en charge par ce layout, sous-layouts compris."""
            if layout is None:
                return acc
            for _i in range(layout.count()):
                _item = layout.itemAt(_i)
                if _item is None:
                    continue
                _w = _item.widget()
                if _w is not None:
                    acc.add(_w)
                _geres_par_layout(_item.layout(), acc)
            return acc

        # Un bouton place dans une barre d'outils a CETTE BARRE pour parent (addWidget reparente) ;
        # un bouton place par le panneau dans son propre contenu est, lui, gere par un layout. Est
        # donc orphelin ce qui est enfant DIRECT du panneau ET hors de tout layout.
        _geres = _geres_par_layout(self.layout(), set())
        for _bouton in self.findChildren(_SmartosQToolButton):
            if _bouton.parent() is self and _bouton not in _geres:
                _bouton.hide()'''

# (marqueur, ancien(s), nouveau) par fichier, appliques DANS CET ORDRE. "ancien(s)" peut etre un
# tuple, du plus specifique au plus general (cf. l'en-tete).
PAIRS_MAIN_WIDGET = [
    # 1. Plus aucune action de dock dans le menu d'options.
    (
        "AUCUNE action de dock n'est mise dans le menu",
        (DOCK_MENU_V1, DOCK_MENU_SPYDER),
        DOCK_MENU_NEW,
    ),
    # 3 et 4. Rangement differe du panneau : bouton burger vide + boutons orphelins.
    (
        "_smartos_hide_orphan_toolbuttons",
        (OPTIONS_BUTTON_V2, OPTIONS_BUTTON_V1, TITLE_ANCHOR),
        OPTIONS_BUTTON_NEW,
    ),
]

PAIRS_MENUS = [
    # 2. Pas de separateur en fin de menu d'options.
    (
        "retirer les separateurs de FIN",
        '''            # Add bottom actions
            for sec, action in self._actions:
                if sec == bottom:
                    actions.append(action)

            add_actions(self, actions)''',
        '''            # Add bottom actions
            for sec, action in self._actions:
                if sec == bottom:
                    actions.append(action)

            # SmartOS (patch_spyder_dock_actions.py) : retirer les separateurs de FIN. La boucle
            # ci-dessus ajoute un separateur apres CHAQUE section, derniere comprise ; tant que la
            # section Bottom portait Deplacer/Detacher/Ancrer/Fermer, quelque chose suivait toujours
            # ce dernier trait. Ces actions retirees, le menu se terminait par un trait horizontal
            # suivi de rien. add_actions() sait deja ignorer un separateur de TETE et les
            # separateurs consecutifs, mais pas celui de fin.
            while actions and actions[-1] is MENU_SEPARATOR:
                actions.pop()

            add_actions(self, actions)''',
    ),
    # 5. Meme correctif, un cran au-dessus : SpyderMenu.get_actions(). Le bloc 2 ne couvre que le
    #    menu d'options des PANNEAUX ; le burger de la barre d'onglets de l'Editeur, lui, est un
    #    SpyderMenu ordinaire, dont render() passe par get_actions(). Releve du 27/07/2026 : ce menu
    #    se terminait DEJA par un trait suivi de rien, avant meme qu'on lui retire ses actions de
    #    dock (cf. patch_spyder_editor_split_buttons.py).
    (
        "retirer les separateurs de FIN de TOUT menu",
        '''        actions = []
        for section in self._sections:
            for sec, action in self._actions:
                if sec == section:
                    actions.append(action)

            actions.append(MENU_SEPARATOR)
        return actions''',
        '''        actions = []
        for section in self._sections:
            for sec, action in self._actions:
                if sec == section:
                    actions.append(action)

            actions.append(MENU_SEPARATOR)

        # SmartOS (patch_spyder_dock_actions.py) : retirer les separateurs de FIN de TOUT menu. La
        # boucle ci-dessus en ajoute un apres CHAQUE section, derniere comprise, et add_actions()
        # sait ignorer un separateur de TETE et les separateurs consecutifs, mais pas celui de fin.
        # Meme correctif que dans PluginMainWidgetOptionsMenu.render() plus bas, qui n'appelle pas
        # cette methode : il reordonne ses sections et reconstruit sa propre liste.
        while actions and actions[-1] is MENU_SEPARATOR:
            actions.pop()

        return actions''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0)."""
    applied = 0
    for marqueur, olds, new in pairs:
        if marqueur in source:
            continue  # bloc deja en place
        if isinstance(olds, str):
            olds = (olds,)
        # PREMIER candidat present exactement une fois, les candidats etant donnes DU PLUS SPECIFIQUE
        # AU PLUS GENERAL : le texte pose par une passe precedente CONTIENT celui d'origine de
        # Spyder, donc les deux matchent, et exiger un candidat unique echouerait.
        trouve = next((o for o in olds if source.count(o) == 1), None)
        if trouve is None:
            print(f"Aucun des {len(olds)} textes attendus n'est present exactement une fois dans "
                  f"{path} - Spyder a peut-etre restructure son code, patch {nom} non applique. "
                  f"Bloc:\n{olds[0][:80]}...", file=sys.stderr)
            return None, 0
        source = source.replace(trouve, new)
        applied += 1
    return source, applied


def preparer(path, nom, pairs):
    """Renvoie (source_patchee | None | False, nb_appliques).

    None + 0 applique = tous les blocs sont deja en place ; False = echec (rien ne doit etre ecrit).
    """
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"{path} illisible ({error}) - patch actions de dock non applique.", file=sys.stderr)
        return False, 0

    patched, applied = appliquer(source, path, nom, pairs)
    if patched is None:
        return False, 0
    if applied == 0:
        return None, 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le {path} patche n'est pas du Python valide ({error}) - aucune modification ecrite.",
              file=sys.stderr)
        return False, 0
    return patched, applied


def main():
    if len(sys.argv) != 3:
        print(f"Usage : {sys.argv[0]} <chemin vers api/widgets/main_widget.py> "
              f"<chemin vers api/widgets/menus.py>", file=sys.stderr)
        return 1

    main_widget_path, menus_path = sys.argv[1], sys.argv[2]

    # Les deux fichiers sont prepares AVANT toute ecriture : le patch est un tout, une installation
    # ou seul l'un des deux serait modifie afficherait un separateur orphelin en fin de menu.
    resultats = []
    for path, nom, pairs in (
        (main_widget_path, "actions de dock (main_widget)", PAIRS_MAIN_WIDGET),
        (menus_path, "actions de dock (menus)", PAIRS_MENUS),
    ):
        patched, applied = preparer(path, nom, pairs)
        if patched is False:
            return 1
        resultats.append((path, patched, applied))

    if sum(applied for _p, _s, applied in resultats) == 0:
        print("Patch actions de dock : tous les blocs sont deja en place.")
        return 0

    for path, patched, applied in resultats:
        if patched is None:
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(patched)
        print(f"  {applied} bloc(s) dans {path}")

    print("Patch actions de dock applique : Deplacer/Detacher/Ancrer/Fermer retires du menu burger "
          "de tous les panneaux, plus de separateur orphelin, bouton burger masque quand son menu "
          "est vide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
