#!/usr/bin/env python3
"""Patch spyder/plugins/layout/plugin.py : un bouton "Agrandir le volet" A DROITE de l'en-tete des
panneaux qui en ont l'usage, a la place de la barre d'outils globale.

Contexte : demande de l'utilisateur du 26/07/2026, precisee en trois fois - "cache par defaut cette
barre d'outils de redimensionnement en haut de la fenetre, on va ajouter ce bouton a chaque panneau
qui en a vraiment besoin" ; puis "ne remets pas les burgers s'ils sont vides, et mets l'outil a
DROITE" ; puis "quand le panneau contient des onglets, le bouton doit etre A COTE DU BURGER
PREEXISTANT".

CRITERE DES PANNEAUX (arbitre avec l'utilisateur, pas devine) : ceux dont le CONTENU gagne a occuper
toute la fenetre - Editeur, Pyxel, Pyxel Studio, Python Tutor, VizTracer, Graphiques, le panneau
Claude depuis le 27/07/2026 et le panneau Terminal depuis le 31/07/2026. Ecartes : Console IPython,
Fichiers, Organisation du code, Analyse de code, etroits par nature.
⚠ LA LISTE FAIT FOI DANS LE CODE, pas ici : SMARTOS_PANNEAUX_AGRANDISSABLES, plus bas. Le compte
rendu de fin l'en extrait plutot que de la recopier — il annoncait encore six panneaux le jour ou le
septieme a ete ajoute.

⚠ LES PANNEAUX A TERMINAUX SONT UN CAS A PART, et c'est ce qui les a fait ajouter : chez eux,
l'agrandissement ne se contente pas d'agrandir, il CHANGE l'affichage — les onglets s'etalent en
mosaique (mosaique.py de chaque greffon, accroche sur set_maximized_state). Sans ce bouton, la
mosaique n'etait atteignable que par la barre d'outils globale, justement masquee : l'utilisateur ne
pouvait pas la declencher du tout. « Je ne peux pas verifier la mosaique », 27/07/2026 pour Claude ;
meme demande le 31/07/2026 pour le Terminal, qui venait de recevoir la mosaique en devenant un
greffon independant — elle y etait donc deja, mais inatteignable.

⚠ L'EDITEUR EST SORTI DE CETTE LISTE LE 27/07/2026, et son bouton est desormais cree par
EditorStack lui-meme (Commun/scripts/patch_spyder_editor_split_buttons.py). Raison mesuree : il n'a
pas UNE barre d'onglets mais UNE PAR VOLET, et les volets naissent et meurent au fil des scissions.
Pose ici une fois pour toutes, le bouton ne servait que le volet ne du demarrage, et disparaissait
avec lui. Ce qui suit ne vaut donc plus que pour les autres panneaux ; le releve d'origine est
conserve tel quel, parce que c'est lui qui a departage les deux emplacements.

DEUX EMPLACEMENTS, ET C'EST UNE MESURE QUI LES A DEPARTAGES
Une sonde a inventorie, panneau par panneau, la barre principale, la barre de coin, les widgets a
onglets, leur barre d'onglets et leur coin haut-droit, avec la GEOMETRIE de chacun (releve du
26/07/2026, HGIGNORED/sonde_entetes.py) :
  - EDITEUR : barre d'onglets visible, 44 px, coin haut-droit dote d'un layout et portant deja
    editor_stack_options_button - le burger preexistant. Notre bouton se pose a sa gauche, donc a
    cote de lui et a droite de l'en-tete ;
  - PYXEL STUDIO : barre d'onglets visible, 29 px, mais coin haut-droit vide et de taille nulle. On
    lui en pose un ;
  - PYXEL (panneau du jeu) : widget a onglets present mais barre d'onglets MASQUEE - y placer le
    bouton l'aurait mis dans une ligne invisible. Cas general ;
  - PYTHON TUTOR, VIZTRACER, GRAPHIQUES : pas d'onglets. Cas general.
Le critere codé ci-dessous est donc la VISIBILITE DE LA BARRE D'ONGLETS. Deux criteres plus simples
ont ete essayes et pris en defaut : "le panneau a-t-il des onglets" (envoyait Pyxel dans une ligne
invisible) et "le coin d'onglets porte-t-il deja un bouton a menu" (excluait Pyxel Studio, que
l'utilisateur cite nommement).

QUATRE PIEGES, chacun paye avant d'etre compris :

  1. LA CIBLE DE L'AGRANDISSEMENT EST CHOISIE PAR LE FOCUS. maximize_dockwidget() parcourt les
     greffons ancrables et retient celui qui est ANCETRE de QApplication.focusWidget() ; a defaut il
     se rabat sur l'EDITEUR. Or un bouton de barre d'outils ne prend PAS le focus au clic. Sans
     precaution, cliquer le bouton de Pyxel aurait agrandi l'Editeur, de facon reproductible et
     silencieuse. D'ou la connexion au signal `pressed`, qui part AVANT que l'action ne bascule, et
     qui donne le focus au panneau proprietaire - seulement si rien n'est encore agrandi, sinon le
     clic veut dire "reviens en arriere" et switch_to_plugin() aurait des effets de bord.

  2. UN BOUTON POSE DANS UN COIN INVISIBLE NE SE VOIT PAS, et rien ne le signale.
     patch_spyder_dock_actions.py masque le bouton burger des panneaux dont le menu d'options est
     vide ; le coin n'ayant alors plus rien a montrer, Qt ne l'affiche pas. La premiere version de ce
     patch posait le bouton et s'en tenait la : la sonde disait "present", l'utilisateur ne voyait
     rien - elle verifiait l'EXISTENCE dans le registre, jamais la geometrie.

  3. LE CALAGE A DROITE N'EST PAS ACQUIS, ET L'ESPACEUR VA DANS LE BON WIDGET. La barre de coin est
     normalement poussee a droite par la barre d'outils principale du panneau, qui occupe le reste de
     la largeur. Les panneaux SANS barre principale (Pyxel, Python Tutor) n'ont rien pour la pousser.
     Un espaceur place dans la BARRE de coin ne suffit pas : le releve montrait alors le widget de
     coin large de 440 px, ses deux boutons calés a son bord GAUCHE. L'espaceur doit aller DANS le
     widget de coin (MainCornerWidget), pas dans la barre qui le contient.

  4. NE JAMAIS FIGER LA TAILLE D'UN WIDGET SUR CELLE D'UN VOISIN PAS ENCORE MIS EN PAGE. La premiere
     version faisait setFixedSize(voisin.size()) pour s'aligner sur le burger de la barre d'onglets :
     a cet instant le voisin mesurait 44x0, et le bouton s'est retrouve HAUT DE ZERO PIXEL - present,
     "visible" au sens de Qt, et invisible a l'ecran. On ne reprend donc du voisin que sa taille
     d'ICONE, et on laisse le layout dimensionner le reste.

ON REUTILISE L'ACTION EXISTANTE, ON N'EN CREE PAS UNE PAR PANNEAU : l'icone et sa bascule
sortante/rentrante, l'etat coche (un seul panneau agrandi a la fois, donc une seule source de verite)
et le raccourci clavier viennent alors gratuitement.

POURQUOI DANS LE GREFFON LAYOUT : c'est lui qui detient l'agrandissement et son action. Un patch par
panneau en aurait fait autant a maintenir, dont plusieurs sur nos propres greffons. Le travail est DIFFERE
d'un tour de boucle pour passer apres les on_mainwindow_visible de tous les greffons.

Usage : patch_spyder_pane_maximize_button.py <chemin vers plugins/layout/plugin.py installe>

⚠ DEPEND de patch_spyder_hide_docks.py, applique AVANT : le bloc s'ancre sur la fin du sien.
IDEMPOTENT, ET AUTO-SUPPLANTANT : plutot que d'enumerer les textes de ses versions precedentes, le
patch RETIRE tout bloc SmartOS deja pose - il est delimite de facon sure, de son commentaire d'entete
jusqu'au "# ---- Private API" qui suit dans le fichier d'origine - puis reecrit le bloc courant. Une
retouche du bloc s'applique ainsi sur une installation deja patchee, sans avoir a maintenir la liste
de ses etats anterieurs. Re-parse avant ecriture ; echec BRUYANT (code 1) si l'ancre est introuvable.
"""
import ast
import re
import sys

MARKER = "_smartos_poser_bouton_agrandir"

ANCRE = '            self.set_conf("smartos_docks_hidden_v2", True)\n'

# Delimiteurs du bloc SmartOS deja pose, pour pouvoir le remplacer quelle que soit sa version.
DEBUT_BLOC = "\n        # SmartOS (patch_spyder_pane_maximize_button.py)"
FIN_ORIGINE = "\n    # ---- Private API"

BLOC = '''
        # SmartOS (patch_spyder_pane_maximize_button.py) : poser le bouton "Agrandir le volet" a
        # DROITE de l'en-tete des panneaux qui en ont l'usage, la barre d'outils globale etant
        # masquee. DIFFERE d'un tour de boucle : les panneaux doivent tous exister et avoir
        # construit leur en-tete.
        from qtpy.QtCore import QTimer as _SmartosQTimer
        _SmartosQTimer.singleShot(0, self._smartos_add_pane_maximize_buttons)

    #: SmartOS : panneaux dont le CONTENU gagne a occuper toute la fenetre (critere valide par
    #: l'utilisateur le 26/07/2026). La console, les fichiers, l'organisation du code et l'analyse
    #: de code en sont volontairement absents : ils sont etroits par nature.
    #: ⚠ "editor" N'Y EST PAS : l'Editeur n'a pas UNE barre d'onglets mais UNE PAR VOLET, et les
    #: volets naissent et meurent au fil des scissions - un bouton pose une fois pour toutes ne peut
    #: pas suivre (releve du 27/07/2026 : il ne servait que le volet du haut). C'est donc
    #: EditorStack qui cree le sien, cf. Commun/scripts/patch_spyder_editor_split_buttons.py.
    SMARTOS_PANNEAUX_AGRANDISSABLES = (
        "pyxel_game",
        "pyxel_studio",
        "python_tutor",
        "viztracer_profiler",
        "plots",
        # Ajoute le 27/07/2026, a la demande de l'utilisateur : « peux-tu ajouter le bouton
        # d'agrandissement pour le panneau Claude ? car la je ne peux pas verifier la mosaique ».
        # Il entre dans le critere sans discussion — c'est meme le seul panneau dont l'agrandissement
        # CHANGE le contenu : au-dela d'une session, il etale ses onglets en mosaique.
        "claude_pane",
        # Ajoute le 31/07/2026, meme demande pour le panneau Terminal : « comme pour le panneau
        # Claude, peux-tu ajouter un bouton d'agrandissement au panneau Terminal, qui permet de
        # l'agrandir et de passer en vue onglet ou mosaique ? »
        # ⚠ IL N'Y AVAIT RIEN A ECRIRE D'AUTRE QUE CETTE LIGNE, et c'est le seul point a
        # comprendre : la mosaique et sa bascule ont ete recopiees dans ce panneau le meme jour,
        # quand les deux greffons sont devenus independants. Elles etaient donc deja la, mais
        # INATTEIGNABLES — la mosaique ne s'affiche que dans un panneau agrandi, et ce panneau
        # n'avait aucun moyen de l'etre. Le bouton ne l'ajoute pas, il l'ouvre.
        "native_terminal",
    )

    def _smartos_add_pane_maximize_buttons(self):
        """
        Poser l'action d'agrandissement dans l'en-tete de chaque panneau retenu, calee a droite, et
        sur la ligne des titres d'onglets quand le panneau en a.
        Cf. Commun/scripts/patch_spyder_pane_maximize_button.py pour le detail et les pieges.
        """
        action = self.get_container()._maximize_dockwidget_action

        for _nom in self.SMARTOS_PANNEAUX_AGRANDISSABLES:
            try:
                plugin = self.get_plugin(_nom, error=False)
                if plugin is None:
                    continue
                widget = plugin.get_widget()
                if getattr(widget, "_smartos_bouton_agrandir", None) is not None:
                    continue  # deja pose (methode rejouee)

                bouton = self._smartos_poser_bouton_agrandir(widget, action)
                if bouton is None:
                    continue
                widget._smartos_bouton_agrandir = bouton

                # ⚠ FOND GRISE A L'ETAT COCHE (panneau agrandi) : meme demande de l'utilisateur,
                # meme jour, que pour le bouton "Mode deux ecrans" - garder un fond transparent.
                # Cf. patch_spyder_deux_ecrans.py pour la meme regle, ET pour le meme piege : un
                # type-selecteur nu (QToolButton:checked) perd face a la feuille de style plus
                # SPECIFIQUE que Spyder pose au niveau de l'application - releve de l'utilisateur,
                # le fond restait gris malgre ce style. Nom d'objet UNIQUE par panneau, cible par
                # selecteur d'ID (specificite maximale). Une SEULE action partagee
                # (`_maximize_dockwidget_action`) alimente les 7 boutons de ce patch : la regle
                # doit donc etre reposee sur CHACUN d'eux, pas une seule fois.
                bouton.setObjectName(f"smartos_bouton_agrandir_{_nom}")
                bouton.setStyleSheet(
                    f"QToolButton#smartos_bouton_agrandir_{_nom}"
                    " { background-color: transparent; border: none; } "
                    f"QToolButton#smartos_bouton_agrandir_{_nom}:checked"
                    " { background-color: transparent; border: none; } "
                    f"QToolButton#smartos_bouton_agrandir_{_nom}:hover"
                    " { background-color: transparent; border: none; } "
                    f"QToolButton#smartos_bouton_agrandir_{_nom}:pressed"
                    " { background-color: transparent; border: none; }"
                )

                # ⚠ maximize_dockwidget() choisit sa cible par QApplication.focusWidget(), qui n'a
                # pas le temps de refleter un changement survenu dans le MEME clic (synchrone) que
                # le `toggled` qui suit `pressed` et invoque maximize_dockwidget() - decouvert le
                # 01/08/2026 (TODO - Spyder - General.txt, bug rapporte sur le mode deux ecrans) :
                # sans repli, ce focus perime fait retomber l'agrandissement sur l'Editeur (mono
                # fenetre) ou sur la MAUVAISE FENETRE (mode deux ecrans). On retient donc
                # explicitement, ICI, QUEL panneau vient d'etre presse - cf.
                # _smartos_bouton_agrandir_presse plus bas.
                bouton.pressed.connect(
                    lambda _p=plugin, _a=action: self._smartos_bouton_agrandir_presse(_p, _a)
                )
            except Exception:
                # Un panneau recalcitrant ne doit pas priver les autres de leur bouton, ni casser le
                # demarrage pour un ajout cosmetique.
                logger.debug("Bouton d'agrandissement non pose sur %s", _nom, exc_info=True)

            # Hors du try qui precede : que le bouton ait pu etre pose ou non, un burger vide ne doit
            # pas rester affiche. C'est une demande a part entiere de l'utilisateur, elle ne doit pas
            # tomber avec l'echec de l'autre.
            try:
                self._smartos_masquer_burger_vide(widget)
            except Exception:
                logger.debug("Burger vide non masque sur %s", _nom, exc_info=True)

    def _smartos_bouton_agrandir_presse(self, plugin, action):
        """
        Reagir au clic sur UN bouton d'agrandissement precis (`pressed`, avant que l'action ne
        bascule). Retient explicitement CE panneau (`_smartos_bouton_agrandir_cible`), consomme en
        UNE FOIS par `maximize_dockwidget()` (patch_spyder_deux_ecrans_maximize.py) a la place d'un
        focus Qt pas encore a jour. None quand l'action est deja cochee (le clic veut dire "revenir
        en arriere") : ce cas ne doit pas influencer une future selection.

        `switch_to_plugin(force_focus=True)` RESTE NECESSAIRE ICI, et ce n'est PAS ce qui causait le
        bug "Hierarchie" releve par l'utilisateur le 01/08/2026 - hypothese emise a l'epoque (son
        appel a `maximize_dockwidget()` avant celui du bouton, dans le meme clic, semblait un
        candidat plausible), RETIREE puis VERIFIEE FAUSSE par un test A/B en direct
        (HGIGNORED/scenario_test_switch_to_plugin_hypothese.json) : avec l'appel, un panneau deja
        agrandi ailleurs est proprement desagrandi puis le bon panneau est agrandi ; SANS l'appel,
        cliquer ce bouton alors qu'autre chose est deja agrandi ne fait plus RIEN DU TOUT (le clic
        retombe sur la restauration de l'ancien agrandissement, jamais sur le nouveau) - une
        regression reelle, plus genante que le bug qu'on croyait corriger. La cause du bug Hierarchie
        etait ailleurs (disposition de fenetre corrompue par des essais anterieurs, cf. DONE - Spyder
        - cosmetique et disposition.txt).
        """
        self._smartos_bouton_agrandir_cible = None if action.isChecked() else plugin
        if not action.isChecked():
            plugin.switch_to_plugin(force_focus=True)

    @staticmethod
    def _smartos_ligne_des_onglets(widget):
        """
        Le coin haut-droit d'une barre d'onglets VISIBLE, ou None.

        L'utilisateur veut le bouton "a la meme hauteur que les titres d'onglets" quand il y en a.
        Le critere est donc la VISIBILITE DE LA BARRE D'ONGLETS, et non la seule existence d'un
        widget a onglets : Pyxel (panneau du jeu) en contient un dont la barre est masquee - y poser
        le bouton l'aurait mis dans une ligne invisible. Releve du 26/07/2026 : barre visible pour
        l'Editeur (44 px) et Pyxel Studio (29 px), masquee pour Pyxel.

        ⚠ NE PAS Y AJOUTER DE DRAPEAU « ce panneau refuse cet emplacement ». Essaye le 27/07/2026
        pour le panneau Claude, dont la barre d'onglets disparait en mode mosaique : le drapeau
        FONCTIONNAIT (cette methode rendait bien None) et ne changeait RIEN au resultat — le repli
        `add_corner_widget` mene au MEME MainCornerWidget, celui que Spyder place lui-meme dans la
        barre d'onglets des qu'un panneau contient un `Tabs`. Il n'y en a qu'un. Mesure : bouton a
        44x43 dans MainCornerWidget, avec le drapeau comme sans lui. C'etait donc du code mort,
        retire a la passe de simplification. Un panneau dont la barre d'onglets disparait doit
        porter son propre bouton la ou il reste visible (cf. spyder_claude/mosaique.py), pas
        esperer un autre emplacement de celui-ci.
        """
        from qtpy.QtCore import Qt as _SmartosQt
        from qtpy.QtWidgets import QHBoxLayout as _SmartosQHBoxLayout
        from qtpy.QtWidgets import QTabWidget as _SmartosQTabWidget
        from qtpy.QtWidgets import QWidget as _SmartosQWidget

        for _tw in widget.findChildren(_SmartosQTabWidget):
            if not _tw.isVisible() or not _tw.tabBar().isVisible():
                continue
            _coin = _tw.cornerWidget(_SmartosQt.TopRightCorner)
            if _coin is not None and _coin.layout() is not None:
                return _coin
            # Pas de coin exploitable : en poser un. C'est le cas de Pyxel Studio, dont le coin
            # existe mais mesure 0x0 et n'accueille rien.
            _neuf = _SmartosQWidget(_tw)
            _boite = _SmartosQHBoxLayout(_neuf)
            _boite.setContentsMargins(0, 0, 0, 0)
            _boite.setSpacing(0)
            _tw.setCornerWidget(_neuf, _SmartosQt.TopRightCorner)
            return _neuf
        return None

    def _smartos_poser_bouton_agrandir(self, widget, action):
        """
        Poser le bouton et renvoyer le QToolButton cree, ou None.

        Deux emplacements, cf. l'en-tete du patch : sur la ligne des titres d'onglets quand le
        panneau en a une, dans la barre de coin du panneau sinon. Dans les deux cas, a DROITE.
        """
        from qtpy.QtWidgets import QToolButton as _SmartosQToolButton

        _coin = self._smartos_ligne_des_onglets(widget)
        if _coin is not None:
            # ⚠ UN COIN PEUT ETRE UNE BARRE D'OUTILS, ET ON N'EMPILE PAS UN WIDGET DANS LE LAYOUT
            # D'UNE BARRE D'OUTILS. `MainCornerWidget`, le coin que Spyder pose sur la barre
            # d'onglets de certains panneaux, HERITE DE QToolBar : son layout est un QToolBarLayout,
            # qui n'a ni insertWidget ni un addWidget qui range quoi que ce soit. On lui donne donc
            # l'ACTION, et Qt fabrique le bouton, le place et le dimensionne.
            #
            # Mesure du 27/07/2026, panneau Claude, en deux temps — les deux tentatives ratees sont
            # gardees parce qu'elles ont chacune une signature reconnaissable :
            #   1. `layout().insertWidget(0, b)` -> AttributeError sur un QLayout generique,
            #      exception avalee par l'appelant, AUCUN bouton et aucun message ;
            #   2. `layout().addWidget(b)` -> le bouton existe, mais HORS LAYOUT : dessine en
            #      100x30 (taille par defaut d'un widget jamais mis en page) au milieu de voisins
            #      en 44x44. C'est exactement le piege des boutons orphelins deja paye trois fois
            #      sur ce depot.
            # Et une ACTION, contrairement a un bouton, ne laisse rien derriere elle si on la
            # deplace un jour.
            from qtpy.QtWidgets import QToolBar as _SmartosQToolBar
            if isinstance(_coin, _SmartosQToolBar):
                _coin.addAction(action)
                return _coin.widgetForAction(action)

            bouton = _SmartosQToolButton(_coin)
            bouton.setDefaultAction(action)
            bouton.setAutoRaise(True)
            # ⚠ NE PAS FIGER LA TAILLE SUR CELLE D'UN VOISIN : mesure trop tot, elle valait 44x0 et
            # le bouton etait invisible tout en etant "present" (releve du 26/07/2026). On ne fixe
            # que la taille d'icone et on laisse le layout dimensionner le reste.
            _voisins = [_b for _b in _coin.findChildren(_SmartosQToolButton) if _b is not bouton]
            if _voisins:
                bouton.setIconSize(_voisins[0].iconSize())
            # En TETE du layout : le burger preexistant reste le dernier element, donc le plus a
            # droite, et notre bouton se place juste a sa gauche - "a cote du burger", comme demande.
            #
            # ⚠ insertWidget N'EXISTE QUE SUR UN QBoxLayout, et le coin d'un panneau n'en a pas
            # forcement un. Mesure du 27/07/2026 sur le panneau Claude : son coin est le
            # MainCornerWidget de Spyder, dont layout() rend un QLayout generique — l'appel levait
            # « 'PySide6.QtWidgets.QLayout' object has no attribute 'insertWidget' », l'exception
            # etait avalee par le try de l'appelant et journalisee en debug, donc AUCUN bouton et
            # AUCUN message. Le cas ne s'etait jamais presente parce que cette branche n'avait plus
            # qu'un seul utilisateur, l'Editeur, sorti de la liste le matin meme : du code sans
            # appelant, qui se degrade en silence. Les autres panneaux passent par le `_neuf` de
            # _smartos_ligne_des_onglets, un QHBoxLayout que nous construisons — d'ou insertWidget
            # disponible chez eux et pas ici.
            _layout = _coin.layout()
            if hasattr(_layout, "insertWidget"):
                _layout.insertWidget(0, bouton)
            else:
                # Pas de QBoxLayout : on ajoute en fin, ce qui met le bouton le plus a DROITE.
                # C'est l'emplacement demande par l'utilisateur, et le burger de ces panneaux-la
                # est de toute facon masque quand son menu est vide.
                _layout.addWidget(bouton)
            return bouton

        # Cas general : la barre de coin du panneau.
        widget.add_corner_widget(action)
        bouton = widget.get_corner_widget(action.name)
        if bouton is not None:
            self._smartos_caler_le_coin_a_droite(widget, bouton)
        return bouton

    @staticmethod
    def _smartos_caler_le_coin_a_droite(widget, bouton):
        """
        Rendre le coin visible et y caler le contenu A DROITE.

        Deux defauts constates, chacun mesure :
          - le coin peut etre invisible : patch_spyder_dock_actions.py masque le burger des panneaux
            au menu vide, et un coin sans rien a montrer n'est pas affiche par Qt. Le bouton etait
            alors pose sans etre visible, et rien ne le signalait ;
          - le contenu se cale a GAUCHE dans les panneaux SANS barre d'outils principale (Pyxel,
            Python Tutor) : rien ne pousse le coin, qui prend toute la largeur. L'espaceur va DANS
            le widget de coin (MainCornerWidget), et non dans la barre de coin qui le contient :
            mesure du 26/07/2026, un espaceur place dans la barre laissait encore les boutons a
            gauche d'un widget de coin large de 440 px.
        """
        from qtpy.QtWidgets import QSizePolicy as _SmartosQSizePolicy
        from qtpy.QtWidgets import QWidget as _SmartosQWidget

        bouton.setVisible(True)
        for _attr in ("_corner_widget", "_corner_toolbar"):
            _zone = getattr(widget, _attr, None)
            if _zone is not None:
                _zone.setVisible(True)

        _coin = getattr(widget, "_corner_widget", None)
        if _coin is not None and not getattr(_coin, "_smartos_cale_a_droite", False):
            _coin._smartos_cale_a_droite = True
            _espaceur = _SmartosQWidget(_coin)
            _espaceur.setSizePolicy(
                _SmartosQSizePolicy.Expanding, _SmartosQSizePolicy.Preferred)
            _actions = _coin.actions()
            if _actions:
                _coin.insertWidget(_actions[0], _espaceur)
            else:
                _coin.addWidget(_espaceur)

    @staticmethod
    def _smartos_masquer_burger_vide(widget):
        """
        Masquer le bouton burger d'un panneau dont le menu d'options n'a aucune entree.

        ⚠ IL FAUT MASQUER L'ACTION, PAS LE WIDGET. Le burger est tenu par une barre d'outils Qt (le
        MainCornerWidget en est une), via une QWidgetAction. Or QToolBarLayout REAFFICHE le widget de
        chaque action dont l'ACTION est visible des que la barre redevient visible - ce que fait
        justement _smartos_caler_le_coin_a_droite juste avant. Un setVisible(False) pose sur le seul
        bouton etait donc annule aussitot : releve du 26/07/2026, trois panneaux a zero entree de menu
        et burger pourtant affiche, alors que les deux panneaux passes par la ligne d'onglets - ou la
        barre n'est pas re-affichee - respectaient la consigne. C'est ce contraste qui a mis le doigt
        dessus.
        Meme cause pour patch_spyder_dock_actions.py, qui porte la meme regle et paraissait inoperant :
        il masque bien le bouton au demarrage, mais nous ressuscitions le burger en rendant le coin
        visible. La regle est donc rejouee ici, sur l'action.
        """
        _burger = getattr(widget, "_options_button", None)
        _menu = getattr(widget, "_options_menu", None)
        if _burger is None or _menu is None:
            return
        _menu._dirty = True
        _menu.render()
        _garder = any(not _a.isSeparator() for _a in _menu.actions())

        _burger.setVisible(_garder)
        _coin = getattr(widget, "_corner_widget", None)
        if _coin is not None:
            for _act in _coin.actions():
                try:
                    if _coin.widgetForAction(_act) is _burger:
                        _act.setVisible(_garder)
                except Exception:
                    continue
'''

def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/layout/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"layout/plugin.py illisible ({error}) - patch bouton d'agrandissement non applique.",
              file=sys.stderr)
        return 1

    if source.count(ANCRE) != 1:
        print(f"Ancre introuvable ou non unique dans {path} : ce patch s'ancre sur le bloc de "
              f"patch_spyder_hide_docks.py, qui doit etre applique AVANT. Patch bouton "
              f"d'agrandissement non applique.", file=sys.stderr)
        return 1

    # Retirer un bloc SmartOS deja pose, quelle que soit sa version (cf. l'en-tete).
    debut = source.find(DEBUT_BLOC)
    if debut != -1:
        fin = source.find(FIN_ORIGINE, debut)
        if fin == -1:
            print(f"Bloc SmartOS present dans {path} mais sa fin (\"# ---- Private API\") est "
                  f"introuvable - je n'y touche pas plutot que de couper au hasard.",
                  file=sys.stderr)
            return 1
        if MARKER in source and source[debut:fin].count(BLOC.rstrip("\n")) == 1:
            print("Patch bouton d'agrandissement par panneau deja applique.")
            return 0
        source = source[:debut] + source[fin:]

    patched = source.replace(ANCRE, ANCRE + BLOC)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le layout/plugin.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    # ⚠ LA LISTE EST RELUE DANS LE BLOC QU'ON VIENT D'ECRIRE, jamais recopiee ici. Elle l'etait,
    # et elle avait cesse d'etre vraie a la premiere addition : le message annoncait encore six
    # panneaux quand le Terminal venait d'etre ajoute (31/07/2026). Un compte rendu faux est pire
    # que pas de compte rendu — c'est lui qu'on croit quand on vient verifier.
    panneaux = re.findall(r'^\s+"([a-z_]+)",\s*$',
                          BLOC[BLOC.index("SMARTOS_PANNEAUX_AGRANDISSABLES"):
                               BLOC.index("def _smartos_add_pane_maximize_buttons")],
                          re.M)
    print(f"Patch bouton d'agrandissement par panneau applique a {len(panneaux)} panneaux : "
          f"{', '.join(panneaux)} ({path}). L'Editeur est servi par "
          f"patch_spyder_editor_split_buttons.py, un bouton par volet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
