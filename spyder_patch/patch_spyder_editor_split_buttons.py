#!/usr/bin/env python3
"""Boutons de VOLET dans le coin de la barre d'onglets de CHAQUE panneau d'edition : separation
horizontale, fermer ce volet, agrandir le volet.

Contexte : CachyOS/Documentation/TODO - Spyder - cosmetique.txt, section "icones" -
  - "icone de reduction / agrandissement editeur pas au bon endroit quand vue scindee" ;
  - "ajouter icones de scindage de fenetre : separation horizontale et ferme ce volet".

⚠ LA SEPARATION VERTICALE N'A PAS DE BOUTON, ET C'EST VOULU. Les deux avaient d'abord ete posees,
l'item ne nommant que "separation horizontale" alors que ces deux mots ne designent pas la meme
chose selon qu'on parle du TRAIT ou du SPLITTER. L'utilisateur a tranche apres essai, le 27/07/2026 :
"la separation verticale doit etre dans le menu burger, je n'utilise que la separation horizontale
frequemment". Elle y est deja - __setup_menu() met les trois actions de scission dans le burger de
cette meme barre d'onglets - il n'y avait donc rien a ajouter, seulement un bouton a retirer.

LE DEFAUT, MESURE AVANT D'ETRE CORRIGE (sonde --actions du 27/07/2026, la session de
l'utilisateur etant DEJA scindee ; releve dans HGIGNORED/sonde_split.json). Geometrie ECRAN des
coins haut-droit, apres une scission supplementaire :

    volet du haut (906x806)   coin a x=1185 : [Agrandir le volet] [Options]
    volet du bas  (906x214)   coin a x=1235 :                     [Options]

Le bouton d'agrandissement n'existe donc QUE dans un volet - celui qui existait au demarrage.
CAUSE : patch_spyder_pane_maximize_button.py le pose une fois pour toutes, depuis le greffon
Layout, dans le PREMIER widget a onglets trouve sous le panneau Editeur. Or l'Editeur n'a pas une
barre d'onglets, il en a UNE PAR VOLET, et les volets naissent et meurent au fil des scissions :
un bouton pose une seule fois ne peut pas suivre. Pire, fermer le premier volet le faisait
disparaitre completement.

CORRECTIF : ce n'est pas le greffon Layout qui pose le bouton dans l'Editeur, c'est
EditorStack.setup_editorstack() qui le cree pour lui-meme, en meme temps que son burger. Chaque
volet - y compris ceux qui naitront d'une scission future - est alors servi par construction, et
au meme endroit. "editor" est retire en consequence de SMARTOS_PANNEAUX_AGRANDISSABLES dans
patch_spyder_pane_maximize_button.py (sinon deux boutons dans le volet du haut).

ON REUTILISE L'ACTION DU GREFFON LAYOUT, ON N'EN CREE PAS UNE : l'icone qui bascule
(agrandir / restaurer, cf. patch_spyder_maximize_icons.py), l'etat coche - un seul panneau agrandi
a la fois, donc une seule source de verite - et le raccourci clavier viennent gratuitement.

TROIS PIEGES, deux herites de patch_spyder_pane_maximize_button.py et un propre a l'Editeur :

  1. LA CIBLE DE L'AGRANDISSEMENT EST CHOISIE PAR LE FOCUS. maximize_dockwidget() retient le
     greffon ancetre de QApplication.focusWidget(), et un bouton de barre d'outils ne prend PAS le
     focus au clic. `_last_plugin` n'etant jamais remis a None, un panneau agrandi precedemment
     resterait la cible. D'ou la connexion au signal `pressed`, qui part AVANT la bascule, et qui
     donne le focus a CE volet - seulement si rien n'est agrandi, sinon le clic veut dire "reviens
     en arriere".

  2. L'ACTION DU GREFFON LAYOUT N'EXISTE PAS ENCORE quand le premier volet se construit (les
     greffons sont crees en sequence, l'Editeur pouvant preceder Layout). Le branchement est donc
     DIFFERE d'un tour de boucle d'evenements ; le bouton reste masque si l'action est introuvable,
     plutot que de proposer un bouton mort.

  3. UNE FENETRE D'EDITION DETACHEE N'A PAS DE VOLET A AGRANDIR. `new_window` est pose par
     register_editorstack(), donc APRES setup_editorstack() mais avant le tour de boucle differe :
     c'est exactement la fenetre dans laquelle le tester. La sonde du 27/07/2026 a trouve un tel
     panneau dans la session de l'utilisateur - ce n'est pas un cas theorique.

BOUTON "FERMER CE VOLET" : MASQUE PLUTOT QUE GRISE quand il n'y a qu'un volet - un bouton grise en
permanence dans une vue non scindee est de l'encombrement, pas une information.
⚠ ET IL A FALLU CORRIGER UN DEFAUT AMONT POUR QU'IL DISE VRAI. Spyder ne recalcule `is_closable`
qu'a l'ENREGISTREMENT d'un panneau (register_editorstack), jamais a son retrait : apres avoir
referme une scission, le dernier volet restant gardait is_closable=True. L'entree de menu "Fermer
ce volet" restait donc active alors qu'il n'y a plus rien a fermer - defaut deja present sans nous,
mais qu'un BOUTON toujours visible rendrait voyant. Le recalcul est ajoute a
EditorMainWidget.unregister_editorstack(), fenetre par fenetre : les volets d'une fenetre d'edition
detachee ne sont pas les freres de ceux du dock.

Usage : patch_spyder_editor_split_buttons.py <.../editor/widgets/editorstack/editorstack.py>
                                             <.../editor/widgets/main_widget.py>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja present, pour
qu'une passe ulterieure puisse en ajouter un sans defaire les autres. Re-parse de chaque fichier
avant ecriture, et AUCUN fichier n'est ecrit si l'un des deux echoue. Echec BRUYANT (code 1) si un
texte attendu est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# ---- editorstack.py : creation des boutons dans le coin de la barre d'onglets -------------------

CORNER_OLD = "        corner_widgets = {Qt.TopRightCorner: [menu_btn]}"

CORNER_NEW = '''        # SmartOS (patch_spyder_editor_split_buttons.py) : les boutons de volet sont crees ICI,
        # par le panneau d'edition lui-meme, et non poses de l'exterieur une fois pour toutes -
        # c'est ce qui les fait suivre les scissions. Le burger reste le dernier, donc le plus a
        # droite.
        corner_widgets = {
            Qt.TopRightCorner: self._smartos_creer_boutons_de_volet() + [menu_btn]
        }'''

# ---- editorstack.py : les methodes qui vont avec, ajoutees apres une methode voisine ------------

METHODES_ANCRE = '''    def add_corner_widgets_to_tabbar(self, widgets):
        self.tabs.add_corner_widgets(widgets)'''

# Delimiteurs du bloc de methodes deja pose, pour pouvoir le remplacer QUELLE QUE SOIT SA VERSION
# (meme technique que patch_spyder_pane_maximize_button.py) : plutot que d'enumerer les textes des
# passes precedentes, on retire le bloc et on reecrit le courant. C'est le bloc qui bougera le plus,
# et sans cela une retouche ne s'appliquerait jamais a une installation deja patchee - son marqueur
# etant deja present, elle serait sautee en silence.
METHODES_DEBUT = "\n\n    def _smartos_creer_boutons_de_volet(self):"
METHODES_FIN = "\n\n    @Slot()\n    def close_split(self):"

METHODES_NEW = METHODES_ANCRE + '''

    def _smartos_creer_boutons_de_volet(self):
        """
        Les boutons de volet du coin de la barre d'onglets, de gauche a droite, burger exclu.

        Cf. Commun/scripts/patch_spyder_editor_split_buttons.py pour le releve et les pieges.
        """
        # Variable locale : rien d'autre ne la repilote ensuite, contrairement aux deux suivantes.
        # ⚠ UN SEUL BOUTON DE SCISSION, ET C'EST L'HORIZONTALE (demande de l'utilisateur du
        # 27/07/2026, apres essai des deux : "la separation verticale doit etre dans le menu burger,
        # je n'utilise que la separation horizontale frequemment"). La verticale n'est pas perdue :
        # elle est deja dans le menu burger de cette meme barre d'onglets, ou __setup_menu() met les
        # trois actions de scission - rien a y ajouter.
        scinder_h = self.create_toolbutton(
            "smartos_split_horizontally_button",
            icon=self.create_icon("horsplit"),
            tip=_("Split horizontally this editor window"),
            triggered=lambda: self.sig_split_horizontally.emit(),
            register=False,
        )
        self._smartos_bouton_fermer_volet = self.create_toolbutton(
            "smartos_close_split_button",
            icon=self.create_icon("close_panel"),
            tip=_("Close this panel"),
            triggered=self.close_split,
            register=False,
        )
        # Fermer un volet n'a de sens que s'il y en a plusieurs. MASQUE, et non grise : un bouton
        # grise en permanence dans une vue non scindee est de l'encombrement. set_closable() le
        # remet a jour a chaque scission et a chaque descission.
        self._smartos_bouton_fermer_volet.setVisible(self.is_closable)

        # "Agrandir le volet" : l'action appartient au greffon Layout, qui n'existe pas forcement
        # encore. Branchement DIFFERE d'un tour de boucle ; le bouton reste masque d'ici la.
        self._smartos_bouton_agrandir = self.create_toolbutton(
            "smartos_maximize_pane_button",
            register=False,
        )
        self._smartos_bouton_agrandir.hide()
        QTimer.singleShot(0, self._smartos_brancher_agrandir)

        boutons = [
            scinder_h,
            self._smartos_bouton_fermer_volet,
            self._smartos_bouton_agrandir,
        ]
        # Meme feuille de style que le burger voisin, qui la recoit deux lignes plus haut dans
        # setup_editorstack() : c'est elle qui donne a un bouton de coin sa taille et son fond dans
        # une barre d'onglets.
        for _bouton in boutons:
            _bouton.setStyleSheet(str(PANES_TABBAR_STYLESHEET))
        return boutons

    def _smartos_brancher_agrandir(self):
        """
        Donner au bouton d'agrandissement l'action du greffon Layout - la MEME que celle du menu et
        du raccourci clavier, pour n'avoir qu'une source de verite sur l'etat "agrandi".
        """
        bouton = getattr(self, "_smartos_bouton_agrandir", None)
        if bouton is None or bouton.defaultAction() is not None:
            return

        # Une fenetre d'edition detachee n'a pas de volet a agrandir. `new_window` est pose par
        # register_editorstack(), donc apres setup_editorstack() mais avant ce tour de boucle.
        if self.new_window:
            return

        try:
            from spyder.plugins.layout.container import LayoutContainerActions
            action = self.get_action(
                LayoutContainerActions.MaximizeCurrentDockwidget, plugin=Plugins.Layout
            )
        except Exception:
            # ⚠ CE N'EST PAS UNE PRECAUTION, C'EST LE CAS NORMAL DU PREMIER VOLET, et la mesure du
            # 27/07/2026 le dit sans ambiguite : le bouton restait masque dans ce volet-la, dans lui
            # seul, et un rejeu a la main du branchement aboutissait aussitot
            # (HGIGNORED/sonde_agrandir_diag.json - action introuvable au demarrage, trouvee
            # ensuite). Le QTimer.singleShot(0) du premier volet part pendant un
            # QApplication.processEvents() du demarrage, donc avant que Layout n'ait cree son
            # action ; les volets nes d'une scission, eux, la trouvent du premier coup.
            # On attend le signal que Spyder fournit deja, plutot que de sonder. Le temoin evite de
            # se reconnecter en boucle si l'action manquait pour une autre raison.
            logger.debug("Greffon Layout pas encore pret, branchement reporte", exc_info=True)
            if not getattr(self, "_smartos_attente_layout", False):
                from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
                self._smartos_attente_layout = True
                PLUGIN_REGISTRY.sig_plugin_ready.connect(self._smartos_layout_pret)
            return

        bouton.setDefaultAction(action)
        bouton.show()

        # ⚠ FOND GRISE A L'ETAT COCHE (panneau agrandi) : demande de l'utilisateur du 01/08/2026,
        # meme regle que pour patch_spyder_pane_maximize_button.py et patch_spyder_deux_ecrans.py -
        # garder un fond transparent, ET MEME PIEGE : un type-selecteur nu perd face a la feuille
        # de style plus specifique de Spyder (releve de l'utilisateur, le fond restait gris malgre
        # ce style). Nom d'objet UNIQUE (par volet - `id()`, pas de numero de volet disponible ici)
        # cible par selecteur d'ID. Meme action PARTAGEE, reposee ici pour CE bouton (un par volet).
        _nom_bouton = f"smartos_bouton_agrandir_volet_{id(bouton)}"
        bouton.setObjectName(_nom_bouton)
        bouton.setStyleSheet(
            f"QToolButton#{_nom_bouton}"
            " { background-color: transparent; border: none; } "
            f"QToolButton#{_nom_bouton}:checked"
            " { background-color: transparent; border: none; } "
            f"QToolButton#{_nom_bouton}:hover"
            " { background-color: transparent; border: none; } "
            f"QToolButton#{_nom_bouton}:pressed"
            " { background-color: transparent; border: none; }"
        )

        # ⚠ maximize_dockwidget() choisit sa cible par QApplication.focusWidget(), et un bouton ne
        # prend pas le focus au clic : sans cela, un panneau agrandi precedemment resterait la cible.
        # `pressed` part avant la bascule. Rien a forcer quand l'action est deja cochee : le clic
        # veut alors dire "reviens en arriere".
        bouton.pressed.connect(
            lambda _a=action: None if _a.isChecked() else self.setFocus()
        )

    def _smartos_layout_pret(self, nom_greffon, _omit_conf=False):
        """Rappel de PLUGIN_REGISTRY.sig_plugin_ready. Cf. _smartos_brancher_agrandir()."""
        if nom_greffon != Plugins.Layout:
            return

        from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY

        try:
            PLUGIN_REGISTRY.sig_plugin_ready.disconnect(self._smartos_layout_pret)
        except (RuntimeError, TypeError):
            pass
        self._smartos_brancher_agrandir()'''

# ---- editorstack.py : tenir le bouton "Fermer ce volet" a jour ----------------------------------

CLOSABLE_OLD = '''    def set_closable(self, state):
        """Parent widget must handle the closable state"""
        self.is_closable = state'''

CLOSABLE_NEW = CLOSABLE_OLD + '''
        # SmartOS (patch_spyder_editor_split_buttons.py) : le bouton "Fermer ce volet" du coin de la
        # barre d'onglets suit cet etat. getattr : set_closable() peut etre appele avant que le coin
        # ne soit construit.
        _bouton = getattr(self, "_smartos_bouton_fermer_volet", None)
        if _bouton is not None:
            _bouton.setVisible(state)'''

# ---- editorstack.py : plus d'actions de dock dans le burger de la barre d'onglets ---------------

DOCK_OLD = '''    def __get_main_widget_actions(self):
        actions = []
        if self.parent() is not None:
            main_widget = self.get_main_widget()
        else:
            main_widget = None

        if main_widget is not None:
            if main_widget.windowwidget is not None:
                actions += [main_widget.dock_action]
            else:
                actions += [
                    main_widget.lock_unlock_action,
                    main_widget.undock_action,
                    main_widget.close_action
                ]

        return actions'''

DOCK_NEW = '''    def __get_main_widget_actions(self):
        # SmartOS (patch_spyder_editor_split_buttons.py) : AUCUNE action de dock dans ce menu - ni
        # "Deplacer", ni "Detacher", ni "Fermer", ni "Ancrer" (demande de l'utilisateur du
        # 26/07/2026, "de tous les menus burgers"). patch_spyder_dock_actions.py les avait retirees
        # du menu d'options de PluginMainWidget, qui sert les 22 panneaux ; l'Editeur y echappait,
        # parce que son menu burger est celui de sa BARRE D'ONGLETS et se peuple ici (releve du
        # 27/07/2026 : le menu de l'Editeur les affichait encore, en queue de menu).
        # Pour fermer ou reafficher un panneau : Affichage > Panneaux.
        return []'''

# ---- main_widget.py : recalculer "ce volet est-il fermable" au RETRAIT d'un volet ----------------

UNREGISTER_OLD = '''        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            self.find_widget.set_editor(self.get_current_editor())
            return True'''

UNREGISTER_NEW = '''        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            self.find_widget.set_editor(self.get_current_editor())

            # SmartOS (patch_spyder_editor_split_buttons.py) : Spyder ne recalcule "ce volet est-il
            # fermable" qu'a l'ENREGISTREMENT d'un volet, jamais a son retrait - apres avoir referme
            # une scission, le dernier volet restant gardait is_closable=True, donc un "Fermer ce
            # volet" actif alors qu'il n'y a plus rien a fermer. Fenetre par fenetre : les volets
            # d'une fenetre d'edition detachee ne sont pas les freres de ceux du dock.
            for _fenetre in {_stack.window() for _stack in self.editorstacks}:
                _freres = [_s for _s in self.editorstacks if _s.window() is _fenetre]
                for _frere in _freres:
                    _frere.set_closable(len(_freres) > 1)

            return True'''


# (marqueur, ancien, nouveau) par fichier, appliques DANS CET ORDRE.
PAIRS_EDITORSTACK = [
    ("_smartos_creer_boutons_de_volet() + [menu_btn]", CORNER_OLD, CORNER_NEW),
    ("def _smartos_creer_boutons_de_volet", METHODES_ANCRE, METHODES_NEW),
    ("_smartos_bouton_fermer_volet\", None)", CLOSABLE_OLD, CLOSABLE_NEW),
    ("AUCUNE action de dock dans ce menu", DOCK_OLD, DOCK_NEW),
]

PAIRS_MAIN_WIDGET = [
    ("ne sont pas les freres de ceux du dock", UNREGISTER_OLD, UNREGISTER_NEW),
]


def preparer(path, pairs, supplantable=None):
    """Renvoie (source_patchee | None | False, nb_appliques).

    None + 0 applique = tous les blocs sont deja en place ; False = echec (rien ne doit etre ecrit).
    `supplantable` = (debut, fin, texte_courant) d'un bloc a retirer avant de reecrire, cf.
    METHODES_DEBUT.
    """
    try:
        with open(path, encoding="utf-8") as fichier:
            source = fichier.read()
    except OSError as erreur:
        print(f"{path} illisible ({erreur}) - patch boutons de volet non applique.",
              file=sys.stderr)
        return False, 0

    applied = 0

    # Bloc auto-supplantant : retirer la version deja posee - sauf si c'est deja la version courante,
    # auquel cas il n'y a rien a faire.
    if supplantable is not None:
        debut_texte, fin_texte, texte_courant = supplantable
        debut = source.find(debut_texte)
        if debut != -1 and texte_courant not in source:
            fin = source.find(fin_texte, debut)
            if fin == -1:
                print(f"Bloc SmartOS present dans {path} mais sa fin est introuvable - je n'y "
                      f"touche pas plutot que de couper au hasard.", file=sys.stderr)
                return False, 0
            # Pas de compteur ici : le bloc est immediatement reecrit par la boucle ci-dessous, dont
            # le marqueur vient justement de disparaitre.
            source = source[:debut] + source[fin:]

    for marqueur, old, new in pairs:
        if marqueur in source:
            continue  # bloc deja en place
        if source.count(old) != 1:
            print(f"Le texte attendu n'est pas present exactement une fois dans {path} - Spyder a "
                  f"peut-etre restructure son code, patch boutons de volet non applique. Bloc :\n"
                  f"{old[:80]}...", file=sys.stderr)
            return False, 0
        source = source.replace(old, new)
        applied += 1

    if applied == 0:
        return None, 0

    try:
        ast.parse(source)
    except SyntaxError as erreur:
        print(f"Le {path} patche n'est pas du Python valide ({erreur}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return False, 0
    return source, applied


def main():
    if len(sys.argv) != 3:
        print(f"Usage : {sys.argv[0]} <chemin vers editorstack/editorstack.py> "
              f"<chemin vers editor/widgets/main_widget.py>", file=sys.stderr)
        return 1

    # Les deux fichiers sont prepares AVANT toute ecriture : le patch est un tout, une installation
    # ou seul l'un des deux serait modifie laisserait un bouton "Fermer ce volet" qui ment.
    resultats = []
    for path, pairs, supplantable in (
        (sys.argv[1], PAIRS_EDITORSTACK,
         (METHODES_DEBUT, METHODES_FIN, METHODES_NEW[len(METHODES_ANCRE):])),
        (sys.argv[2], PAIRS_MAIN_WIDGET, None),
    ):
        patched, applied = preparer(path, pairs, supplantable)
        if patched is False:
            return 1
        resultats.append((path, patched, applied))

    if sum(applied for _p, _s, applied in resultats) == 0:
        print("Patch boutons de volet de l'editeur : tous les blocs sont deja en place.")
        return 0

    for path, patched, applied in resultats:
        if patched is None:
            continue
        with open(path, "w", encoding="utf-8") as fichier:
            fichier.write(patched)
        print(f"  {applied} bloc(s) dans {path}")

    print("Patch boutons de volet de l'editeur applique : separation horizontale, fermer ce volet et "
          "agrandir le volet dans le coin de CHAQUE volet d'edition ; plus d'actions de dock dans le "
          "burger de la barre d'onglets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
