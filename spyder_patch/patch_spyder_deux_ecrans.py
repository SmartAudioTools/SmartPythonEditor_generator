#!/usr/bin/env python3
"""Mode DEUX ECRANS : un bouton bascule les panneaux de droite dans une seconde fenetre de la MEME
instance, et rend a chacune des deux fenetres sa propre disposition.

Contexte : CachyOS/Documentation/TODO - Spyder - Multi-Screen.txt, demande de l'utilisateur du
27/07/2026 :

    « je ne souhaite pas utiliser 2 instance. je veux rester sur une seule avec un nouveau bouton
    dans une nouvelle barre d'outils permetant de passer en mode 2 écrans , avec une nouvelle
    fenetre pour la meme istance sur le deuxième ecran et des paramètrage de position de dock mis
    à jour pour les deux fenetres . il y aura donc deux configuration de disposition de pannels :
    une pour le mono-écran et une pour le double écran »

⚠ CE N'EST PAS EN CONTRADICTION avec son refus, le meme jour, de retablir « Detacher » : ce qu'il
refuse, c'est de sortir les panneaux UN A UN a la main et de recomposer la disposition a chaque
session. Ce qui suit est l'inverse - une bascule globale, en un bouton, et memorisee.

CE QUI A ETE MESURE AVANT D'ECRIRE (sonde du 27/07/2026, HGIGNORED/sonde_deux_fenetres.json et
fenetre_ecran2.png), parce que Spyder n'a jamais fait vivre ses panneaux dans deux fenetres :
  - `addDockWidget()` sur une seconde QMainWindow REPARENTE le dock, qui reste vivant et
    utilisable : la capture montre l'arborescence des Fichiers qui repond et l'Organisation du
    code affichant le vrai contenu du fichier ouvert ;
  - le retour marche aussi : `main.addDockWidget()` puis `main.restoreState(etat)` rend exactement
    la disposition de depart ;
  - chaque fenetre a son PROPRE `saveState()`. Les deux configurations demandees sont donc
    fournies par Qt - il n'y a pas de format a inventer.

TROIS PIEGES, tous payes pendant la mesure :

  1. `addDockWidget()` NE MONTRE PAS LE DOCK. Il garde son etat d'affichage anterieur ; sans
     `show()` explicite il est reparente et invisible. Premier relevé : « docks invisibles apres
     deplacement » - c'etait cela.

  2. LA FEUILLE DE STYLE NE SUIT PAS. Une QMainWindow neuve n'herite pas de celle de
     l'application : la seconde fenetre s'affichait en theme CLAIR alors que Spyder est en sombre.
     Elle est donc recopiee explicitement.

  3. ⚠ ON NE PEUT PAS PLACER LA FENETRE SUR LE SECOND ECRAN, et il ne faut pas faire croire le
     contraire. Sous Wayland un client ne positionne pas sa propre fenetre : mesure du 27/07/2026,
     `move()` demande (300, 300), `pos()` annonce (300, 300), `windowHandle().position()` reste
     (0, 0). On DESIGNE donc l'ecran par `windowHandle().setScreen()` quand il y en a plusieurs -
     c'est une indication au compositeur, pas un ordre - et on s'arrete la. Le placement fiable
     reste une regle de fenetre KWin, hors de Spyder.
     ⚠ COROLLAIRE POUR TOUTE SONDE : `QWidget.pos()` d'une fenetre de premier niveau est la
     position DEMANDEE, pas la position REELLE. Mesurer par `windowHandle().position()`.

CE QUI S'EST CASSE A LA PREMIERE UTILISATION REELLE, le 31/07/2026, n'est PAS raconte ici : le
recit complet - six defauts, ce qui a ete essaye puis ecarte, et la mesure de chacun - est dans
CachyOS/Documentation/DONE/DONE - Spyder - cosmetique et disposition.txt, entree « Mode DEUX
ECRANS ». Chaque contrainte qui en decoule est commentee A SON POINT D'USAGE dans le code
ci-dessous, la ou elle risque d'etre defaite. Le recopier ici en ferait deux versions a maintenir,
et la premiere a devenir fausse serait celle que personne ne relit.

LES PANNEAUX DEPLACES sont ceux qui etaient A DROITE DE L'EDITEUR le 27/07/2026, critere donne par
l'utilisateur. Ils sont ecrits en dur ci-dessous parce que c'est une AMORCE : des la premiere
bascule, c'est l'etat enregistre de chaque fenetre qui gouverne, ce qui laisse l'utilisateur
reorganiser librement.
⚠ La liste a ete relevee, pas devinee, et les deux criteres evidents sont FAUX : un dock en onglet
qui n'est pas l'onglet actif est mappe HORS ECRAN (abscisse negative alors qu'il se dit visible),
et `dockWidgetArea()` repond « gauche » pour tous les panneaux, y compris ceux qui sont a droite.
La bonne methode est de regrouper par `tabifiedDockWidgets()` et de juger le groupe sur son onglet
actif - c'est ce qui a fait passer le relevé de deux panneaux a dix.

Usage : patch_spyder_deux_ecrans.py <chemin vers plugins/layout/plugin.py installe>

IDEMPOTENT ET AUTO-SUPPLANTANT, comme patch_spyder_pane_maximize_button.py : le bloc deja pose est
retire (il est delimite de son commentaire d'en-tete jusqu'a la methode d'origine qui le suit) puis
reecrit. Une retouche s'applique ainsi sur une installation deja patchee. Re-parse avant ecriture ;
echec BRUYANT (code 1) si l'ancre est introuvable.
"""
import ast
import sys

# Ancre : la methode d'origine devant laquelle le bloc s'insere. Choisie parce qu'elle est au coeur
# du greffon Layout et n'a pas bouge depuis Spyder 5.
ANCRE = "    def maximize_dockwidget(self, restore=False):"

# ⚠ DELIMITEUR COMPLET, ET NON UN PREFIXE. La premiere version valait
# "    # SmartOS (patch_spyder_deux_ecrans.py)" : cette chaine est CONTENUE dans la ligne du point
# d'entree, indentee de huit espaces, que `find` a donc trouvee EN PREMIER. La coupe partait de la
# et allait jusqu'a l'ancre : 190 lignes du greffon Layout supprimees, dont close_current_dockwidget,
# quick_layout_switch et les blocs de patch_spyder_hide_docks.py et patch_spyder_pane_maximize_button.py.
# Spyder ne demarrait plus. Coût : reinstallation du paquet. 31/07/2026.
# ⚠ ET SANS SAUT DE LIGNE EN TETE, pour la raison inverse, payee le meme jour : la version d'apres
# l'ancrait sur "\n" pour se garantir un debut de ligne, si bien qu'un bloc COLLE a la ligne
# precedente - ce que produisait justement le retrait d'alors - devenait introuvable. Le patch
# n'enlevait plus rien et s'ajoutait une seconde fois : 1754 lignes puis 2007. On repere donc le
# commentaire, et on recule sur son indentation (cf. _debut_du_bloc).
DEBUT_BLOC = "# SmartOS (patch_spyder_deux_ecrans.py) : mode DEUX ECRANS"

# Point d'entree : sans lui, les methodes ci-dessus ne seraient appelees par rien - c'est le piege
# du « contournement a deux moities » du CLAUDE.md, dont une seule est branchee. DIFFERE d'un tour
# de boucle pour passer apres les on_mainwindow_visible de tous les greffons, comme le fait deja
# patch_spyder_pane_maximize_button.py.
ANCRE_APPEL = "        # Update panes and toolbars lock status\n        self.toggle_lock(self._interface_locked)\n"

APPEL = ANCRE_APPEL + '''
        # SmartOS (patch_spyder_deux_ecrans.py) : poser la barre « Écrans » et son bouton de
        # bascule, puis rendre le mode s'il etait actif a la fermeture precedente.
        from qtpy.QtCore import QTimer as _SmartosQTimerEcrans
        _SmartosQTimerEcrans.singleShot(0, self._smartos_installer_deux_ecrans)
'''

# SEULE retouche du code d'origine. maximize_dockwidget() cache TOUS les
# docks avant de reparenter sa cible dans la zone centrale de la fenetre PRINCIPALE : sans cette
# garde, agrandir quoi que ce soit vide la seconde fenetre, et agrandir un panneau qui s'y trouve
# l'arrache a elle. Ecarter ces panneaux de la boucle regle les deux : ils ne sont plus caches, et
# ils ne peuvent plus devenir _last_plugin (le repli sur l'Editeur prend alors le relais).
HIDE_OLD = """            for plugin in self.get_dockable_plugins():
                plugin.dockwidget.hide()
"""
HIDE_NEW = """            for plugin in self.get_dockable_plugins():
                # SmartOS (patch_spyder_deux_ecrans.py) : un panneau parti sur le second ecran n'est
                # ni cache (cela viderait sa fenetre) ni candidat a l'agrandissement.
                if self._smartos_dock_dans_ecran2(plugin.dockwidget):
                    continue
                plugin.dockwidget.hide()
"""

BLOC = '''    # SmartOS (patch_spyder_deux_ecrans.py) : mode DEUX ECRANS. Cf. l'en-tete du patch pour
    # le releve des panneaux et ce qui n'est pas faisable sous Wayland.

    #: Panneaux qui partent sur le second ecran : ceux qui sont A DROITE de l'editeur, calcule EN
    #: DIRECT a chaque entree dans le mode (plus une liste figee dans le code, cf. plus bas) -
    #: demande de l'utilisateur du 01/08/2026, apres avoir du faire retirer "find_in_files" a la
    #: main quand il l'a deplace a gauche dans SA disposition : suivre sa disposition reelle evite
    #: cette friction pour tout futur reamenagement.
    #:
    #: Identifiant de la barre d'application qui porte le bouton de bascule.
    SMARTOS_BARRE_ECRANS = "smartos_toolbar_ecrans"

    #: Options de configuration ou sont memorisees les deux dispositions.
    #:
    #: ⚠ POURQUOI LA CLE EST VERSIONNEE, ET CE QUE CELA NE DIT PAS. `saveState()` est MONOLITHIQUE :
    #: il enregistre les panneaux ET les barres d'outils. Une disposition enregistree pendant que la
    #: rangee etait cassee la restitue donc fidelement a chaque bascule - et la sortie du mode la
    #: reenregistre telle quelle. Cela ressemble a une boucle qui s'aggrave ; ce n'en est pas une.
    #: MESURE DU 31/07/2026, cinq bascules d'affilee en partant d'une cle vierge : ecart du groupe au
    #: centre de 0 pixel, dix relevés. Aucune derive. Un etat SAIN se reenregistre sain ; c'est un
    #: etat HERITE qui se perpetue.
    #: (Un residu de -8 px subsistait avant que la barre « Écrans » ne recopie l'etat verrouille des
    #: autres : c'etait la largeur de sa poignee de deplacement, que j'avais mise sur le compte d'un
    #: arrondi. Une explication commode vaut moins qu'une mesure de plus.)
    #: Il n'y avait donc rien a corriger dans le mecanisme, et surtout rien a lui retirer - deux
    #: correctifs ont ete ecrits puis jetes avant de le comprendre (forcer la barre de centrage a se
    #: reajuster, rejouer le calcul apres restauration : mesures sans effet, l'espace libere etant
    #: aussitot repris par la zone de gauche). Il fallait REPARTIR PROPRE, et rien d'autre.
    #: v2 avait ete polluee de la meme facon quelques heures apres sa creation, par une version
    #: encore cassee essayee entre-temps : changer de nom ne protege que si l'on change de nom APRES
    #: que le defaut est corrige.
    SMARTOS_CONF_MODE = "smartos_mode_deux_ecrans"
    #: ⚠ CETTE CLE A ETE VERSIONNEE (v1 a v4) PENDANT LE DEVELOPPEMENT DE CE PATCH - PLUS
    #: MAINTENANT. Tant que la rangee de barres changeait, la cle changeait avec elle : l'etat
    #: memorise fige la POSITION des barres autant que celle des panneaux, et deplacer la barre
    #: « Écrans » sans renommer la cle la faisait revenir a son ancienne place a la premiere
    #: bascule (constate deux fois le 31/07/2026, v2 puis v3 polluees dans l'heure par une session
    #: lancee entre la creation de la cle et la retouche suivante). Renommee en anglais et
    #: DEVERSIONNEE le 01/08/2026 (demande explicite de l'utilisateur : les numeros de version
    #: etaient utiles pendant le developpement, plus dans la solution finale). Consequence a
    #: assumer pour toute retouche future de la rangee de barres : reinitialiser la cle a la main
    #: (`set_conf(SMARTOS_CONF_ETATS, {})`) plutot que de lui donner un nouveau nom.
    SMARTOS_CONF_ETATS = "window_state_screens"

    def _smartos_creer_fenetre_ecran2(self):
        """La seconde fenetre, prete a recevoir des panneaux."""
        from qtpy.QtWidgets import QMainWindow as _SmartosQMainWindow

        fenetre = _SmartosQMainWindow()
        fenetre.setObjectName("smartos_fenetre_ecran2")
        fenetre.setWindowTitle(_("Spyder — second écran"))

        # ⚠ LA TAILLE SE MEMORISE, LA POSITION NON, et il ne faut pas laisser croire le contraire.
        # `restoreGeometry` rend la taille ET l'etat maximise/plein ecran, ce qui est l'essentiel de
        # ce que l'utilisateur regle a la main - releve du 31/07/2026, « la deuxieme fenetre
        # n'enregistre pas son emplacement ». Sa POSITION, elle, reste decidee par le compositeur :
        # sous Wayland un client ne place pas sa propre fenetre (mesure du 27/07/2026 rappelee en
        # tete de ce fichier), et aucune option de Qt n'y changera rien. 1200x900 n'est que le repli
        # de la toute premiere ouverture.
        _geometrie = self.get_conf(self.SMARTOS_CONF_ETATS, default={}).get("double_geometry")
        if not (_geometrie and fenetre.restoreGeometry(
                QByteArray().fromHex(str(_geometrie).encode("utf-8")))):
            fenetre.resize(1200, 900)

        # ⚠ Une QMainWindow neuve n'herite PAS de la feuille de style de l'application : sans ceci
        # la fenetre s'affiche en theme clair au milieu d'un Spyder sombre (mesure du 27/07/2026).
        fenetre.setStyleSheet(self.main.styleSheet())

        # ⚠ NI DE SES OPTIONS DE DOCK, et c'est ce qui interdisait la MOSAIQUE. Mesure du
        # 31/07/2026 : la fenetre principale porte AnimatedDocks|AllowNestedDocks|AllowTabbedDocks,
        # une fenetre neuve seulement AnimatedDocks|AllowTabbedDocks. Sans AllowNestedDocks, deux
        # panneaux ne peuvent que s'empiler ou se mettre en onglets, jamais se poser cote a cote -
        # releve de l'utilisateur, « je voudrais pouvoir reorganiser les dock dans la 2nd fenetre,
        # avec des dock lateraux, pour pouvoir faire une mosaique ». On RECOPIE celles de la fenetre
        # principale plutot que d'en ecrire une liste : si Spyder en change un jour, la seconde
        # fenetre suit sans qu'on ait a le savoir.
        fenetre.setDockOptions(self.main.dockOptions())

        # ⚠ SANS CECI LA FENETRE N'EST NI DEPLACABLE, NI REDIMENSIONNABLE, NI FERMABLE : la regle
        # KWin qui supprime la barre de titre vise le TITRE ("^Spyder [-—] .*", cf. TODO cosmetique,
        # "Fenetres pop-up SANS CADRE") - cette fenetre s'appelle "Spyder — second ecran", donc
        # matche aussi et perd son cadre natif. C'est le greffon qui equipe - ses boutons, ses
        # glyphes, son calage - et non nous. Garde les boutons SmartOS plutot que de compter sur le
        # cadre KWin : la demande utilisateur du 01/08/2026 est de garder la possibilite d'ajouter
        # d'autres boutons a cette barre plus tard, ce qu'un cadre natif n'offre pas.
        _controles = self.get_plugin("window_controls", error=False)
        if _controles is not None:
            _controles.equip_window(fenetre)
        else:
            logger.debug("Greffon window_controls absent : seconde fenetre sans ses controles")

        # Fermer la fenetre revient a quitter le mode : sinon les panneaux resteraient dans une
        # fenetre detruite, donc invisibles et injoignables.
        # ⚠ PASSER PAR L'ACTION (`setChecked`), PAS PAR UN APPEL DIRECT A
        # `_smartos_quitter_deux_ecrans()` (fait dans une version precedente, demande de
        # l'utilisateur du 01/08/2026) : un appel direct quitte bien le mode mais laisse le bouton
        # de la barre « Écrans » coche comme si le mode etait toujours actif - `_smartos_basculer_
        # deux_ecrans()`, qui recale aussi l'icone et le texte du bouton
        # (`_smartos_rendre_le_bouton`), n'est alors jamais appele. `setChecked(False)` emet
        # `toggled`, deja connecte a `_smartos_basculer_deux_ecrans` : une seule source de verite,
        # comme le reste de ce mode. Sans effet de bord si la fenetre est fermee PAR ce meme
        # bouton (l'action est deja decochee a ce moment-la, `setChecked` ne re-emet rien).
        fenetre.closeEvent = lambda evenement: (
            self._smartos_action_ecrans.setChecked(False), evenement.accept()
        )

        self._smartos_fen2 = fenetre
        return fenetre

    def _smartos_panneaux_a_droite_de_editeur(self):
        """
        Quels panneaux ancrables sont ACTUELLEMENT a droite de l'editeur dans la fenetre
        principale, releve PAR LA GEOMETRIE REELLE plutot que par une liste figee dans le code -
        remplace SMARTOS_GROUPES_ECRAN2 (retiree le 01/08/2026, demande de l'utilisateur : il avait
        du me faire retirer "find_in_files" a la main apres l'avoir deplace a gauche, ce calcul
        suit desormais sa disposition sans intervention).

        ⚠ DEUX CRITERES PLUS SIMPLES SE SONT REVELES FAUX (releve du 27/07/2026, cf. l'en-tete du
        patch) : `dockWidgetArea()` repond "gauche" pour TOUS les panneaux, meme ceux a droite ; et
        la position d'un panneau en onglet NON actif est mappee hors ecran (abscisse negative)
        alors qu'il se dit visible. La bonne methode, deja eprouvee a l'epoque : regrouper par
        `tabifiedDockWidgets()` (des onglets d'un meme groupe partagent une position), puis juger
        le groupe sur la geometrie de son onglet ACTIF (celui dont `visibleRegion()` n'est pas
        vide).
        """
        editeur = self.get_plugin(Plugins.Editor, error=False)
        if editeur is None or getattr(editeur, "dockwidget", None) is None:
            return ()
        _editeur_x = editeur.dockwidget.mapToGlobal(editeur.dockwidget.rect().topLeft()).x()

        _plugin_par_dock = {}
        for _p in self.get_dockable_plugins():
            _d = getattr(_p, "dockwidget", None)
            if _d is not None and _p is not editeur:
                _plugin_par_dock[_d] = _p

        _deja_vus = set()
        _groupes = []
        for _dock, _plugin in _plugin_par_dock.items():
            if _dock in _deja_vus:
                continue
            _compagnons = [_dock] + [
                _d for _d in self.main.tabifiedDockWidgets(_dock) if _d in _plugin_par_dock
            ]
            _deja_vus.update(_compagnons)
            _actif = next(
                (_d for _d in _compagnons if not _d.visibleRegion().isEmpty()), _compagnons[0]
            )
            _actif_x = _actif.mapToGlobal(_actif.rect().topLeft()).x()
            if _actif_x > _editeur_x:
                _groupes.append(tuple(_plugin_par_dock[_d].NAME for _d in _compagnons))
        return tuple(_groupes)

    def _smartos_groupes_dans_fenetre(self, fenetre):
        """
        Les panneaux ACTUELLEMENT dans `fenetre`, regroupes par `tabifiedDockWidgets()` - pour le
        retour du second ecran vers la fenetre principale, ou TOUT ce qui s'y trouve doit revenir
        (pas de tri par geometrie a faire, contrairement a l'aller).
        """
        from qtpy.QtWidgets import QDockWidget as _SmartosQDockWidget

        _plugin_par_dock = {
            _p.dockwidget: _p
            for _p in self.get_dockable_plugins()
            if getattr(_p, "dockwidget", None) is not None
        }
        _docks_ici = [
            _d for _d in fenetre.findChildren(_SmartosQDockWidget) if _d in _plugin_par_dock
        ]

        _deja_vus = set()
        _groupes = []
        for _dock in _docks_ici:
            if _dock in _deja_vus:
                continue
            _compagnons = [_dock] + [
                _d for _d in fenetre.tabifiedDockWidgets(_dock) if _d in _plugin_par_dock
            ]
            _deja_vus.update(_compagnons)
            _groupes.append(tuple(_plugin_par_dock[_d].NAME for _d in _compagnons))
        return tuple(_groupes)

    def _smartos_poser_groupes(self, fenetre, zone, groupes):
        """
        Poser `groupes` (tuple de tuples de noms de panneaux) dans `fenetre`, EN ONGLETS.

        ⚠ LE REGROUPEMENT VAUT DANS LES DEUX SENS, et c'est la meme mesure qui l'impose. Poses un
        par un, dix panneaux s'empilent en colonne : a l'aller ils faisaient une centaine de pixels
        chacun, illisibles (capture HGIGNORED/bascule_ecran2.png) ; au retour, leur hauteur minimale
        cumulee force Qt a AGRANDIR la fenetre principale, et le `restoreState` qui suit ne rend que
        la disposition, jamais la geometrie - d'ou la fenetre « trop grande verticalement » relevee
        par l'utilisateur le 31/07/2026.

        ⚠ UN PANNEAU DEJA VISIBLE AVANT LA BASCULE PEUT DEVENIR INVISIBLE APRES (releve de
        l'utilisateur le 01/08/2026, PAS l'inverse - une premiere hypothese le disait absent plutot
        qu'invisible, ecartee par sa correction). `addDockWidget()` + `.show()` change l'affichage
        Qt du dock mais PAS le suivi interne de Spyder (celui qui repond a
        Fenetre > Panneaux) - les deux se desynchronisent des que le dock change de fenetre
        parente, et le panneau reste marque "visible" en interne sans l'etre reellement a l'ecran.
        Seul un aller-retour MANUEL par le menu Fenetre le corrigeait, en repassant par le vrai
        chemin de code de Spyder. On rejoue ici ce meme aller-retour programmatiquement
        (`toggle_view`, la methode que ce menu appelle lui-meme) plutot que d'inventer une
        resynchronisation maison.
        """
        for _groupe in groupes:
            _premier = None
            for _nom in _groupe:
                _greffon = self.get_plugin(_nom, error=False)
                _dock = None if _greffon is None else getattr(_greffon, "dockwidget", None)
                if _dock is None:
                    continue
                fenetre.addDockWidget(zone, _dock)
                if _premier is None:
                    _premier = _dock
                else:
                    fenetre.tabifyDockWidget(_premier, _dock)
                # ⚠ addDockWidget NE MONTRE PAS : le dock garde son etat d'affichage anterieur.
                _dock.show()
                # Resynchronise le suivi interne de Spyder (cf. docstring) - meme aller-retour que
                # le menu Fenetre > Panneaux, qui appelle cette meme methode.
                try:
                    _greffon.toggle_view(False)
                    _greffon.toggle_view(True)
                except Exception:
                    logger.debug(
                        "Resynchronisation de visibilite impossible pour %s", _nom, exc_info=True)
            if _premier is not None:
                # Le premier de chaque groupe devient l'onglet actif, comme dans la disposition
                # d'origine.
                _premier.raise_()

    def _smartos_dock_dans_ecran2(self, dock):
        """Vrai si ce dock vit dans la seconde fenetre."""
        fenetre = getattr(self, "_smartos_fen2", None)
        return fenetre is not None and dock is not None and fenetre.isAncestorOf(dock)

    def _smartos_noms_panneaux_ecran2(self):
        """
        Noms des panneaux ACTUELLEMENT dans le second ecran, releves par ancrage plutot que par
        une liste figee - remplace SMARTOS_PANNEAUX_ECRAN2 (retiree le 01/08/2026 avec
        SMARTOS_GROUPES_ECRAN2, meme raison : suivre la disposition reelle plutot qu'une liste a
        maintenir a la main). Vide si le mode n'est pas actif.
        """
        fenetre = getattr(self, "_smartos_fen2", None)
        if fenetre is None:
            return ()
        return tuple(
            _p.NAME for _p in self.get_dockable_plugins()
            if self._smartos_dock_dans_ecran2(getattr(_p, "dockwidget", None))
        )

    def _smartos_basculer_deux_ecrans(self, actif):
        """Entrer dans le mode deux ecrans, ou en sortir."""
        try:
            if actif:
                self._smartos_entrer_deux_ecrans()
            else:
                self._smartos_quitter_deux_ecrans()
            self._smartos_rendre_le_bouton(actif)
        except Exception:
            # Un mode d'affichage ne doit jamais emporter Spyder avec lui.
            logger.exception("Bascule du mode deux ecrans impossible")
        self._smartos_recentrer_rangee()

    def _smartos_recentrer_rangee(self):
        """
        Rejouer le centrage du groupe du milieu (publie sur main par patch_spyder_burger_menu.py).

        La bascule passe par restoreState() SANS redimensionner la fenetre principale (le second
        ecran a sa PROPRE fenetre) : sig_resized ne tire donc pas, et la DragArea gauche garderait
        la largeur figee calculee dans l'autre mode - les boutons du milieu ne revenaient pas au
        milieu en sortant du mode deux ecrans (releve utilisateur du 08/08/2026). Deux passes
        differees, comme au demarrage : les largeurs des barres ne sont definitives qu'une fois la
        rangee reposee par la boucle d'evenements.
        """
        recentrer = getattr(self.main, "_smartos_recentrer_barres", None)
        if recentrer is None:
            return
        from qtpy.QtCore import QTimer as _SmartosQTimerEcrans
        _SmartosQTimerEcrans.singleShot(0, recentrer)
        _SmartosQTimerEcrans.singleShot(400, recentrer)

    def _smartos_entrer_deux_ecrans(self):
        from qtpy.QtCore import Qt as _SmartosQt
        from qtpy.QtGui import QGuiApplication as _SmartosQGuiApplication

        if getattr(self, "_smartos_fen2", None) is not None:
            return

        # Memoriser la disposition mono-ecran AVANT de la defaire : c'est elle qu'on rendra en
        # sortant, et c'est la moitie « mono » des deux configurations demandees.
        etats = dict(self.get_conf(self.SMARTOS_CONF_ETATS, default={}))
        etats["mono"] = qbytearray_to_str(self.main.saveState(version=WINDOW_STATE_VERSION))

        fenetre = self._smartos_creer_fenetre_ecran2()
        self._smartos_poser_groupes(
            fenetre, _SmartosQt.LeftDockWidgetArea, self._smartos_panneaux_a_droite_de_editeur()
        )

        # ⚠ _last_plugin SURVIT d'un agrandissement a l'autre : s'il designe un panneau qui vient de
        # partir, le prochain agrandissement le tirerait dans la fenetre principale.
        if self._last_plugin is not None and self._smartos_dock_dans_ecran2(
                getattr(self._last_plugin, "dockwidget", None)):
            self._last_plugin = None

        # ⚠ DESIGNER L'ECRAN AVANT LE PREMIER AFFICHAGE, ET NON APRES. On ne PLACE pas la fenetre -
        # sous Wayland move() est ignore, c'est mesure - mais on peut dire sur QUEL ECRAN elle doit
        # naitre. Encore faut-il le dire au bon moment : le compositeur en tient compte a la
        # CREATION de la surface, et `setScreen` sur une fenetre deja mappee est au mieux une
        # suggestion qu'il ignore. La premiere version appelait show() puis setScreen() ; l'ordre
        # est desormais inverse, et c'est QWidget.setScreen qui s'en charge - il recree la fenetre
        # si besoin, ce que la poignee brute ne fait pas.
        #
        # ⚠ ET PAS DE showFullScreen. Il etait pose ici « puisqu'on a un ecran dedie » ; il rendrait
        # inutile la taille memorisee ci-dessus, que l'utilisateur a demandee le meme jour. Le
        # plein ecran reste a un clic, et restoreGeometry le memorise comme le reste.
        _ecrans = _SmartosQGuiApplication.screens()
        if len(_ecrans) > 1:
            _autres = [e for e in _ecrans if e is not self.main.screen()]
            if _autres:
                fenetre.setScreen(_autres[0])
        fenetre.show()

        # Restaurer la disposition double-ecran si on en a deja une.
        if etats.get("double_screen_1"):
            self.main.restoreState(
                QByteArray().fromHex(str(etats["double_screen_1"]).encode("utf-8")),
                version=WINDOW_STATE_VERSION,
            )
        if etats.get("double_screen_2"):
            fenetre.restoreState(
                QByteArray().fromHex(str(etats["double_screen_2"]).encode("utf-8"))
            )

        # ⚠ REMONTER LES POIGNEES DE REDIMENSIONNEMENT, ICI, SANS ATTENDRE D'EVENEMENT. Le greffon
        # window_controls les remonte au-dessus du contenu par un filtre d'evenements de la
        # fenetre ; poser dix panneaux d'un coup les recouvre, et le filtre ne rattrape qu'au tour
        # de boucle suivant. Mesure du 31/07/2026, la seule qui tranche : SANS cette relance, six
        # poignees sur huit restent sous les onglets ; avec, huit sur huit, sur trois essais.
        _poignees = getattr(fenetre, "_window_controls_grips", None)
        if _poignees is not None:
            _poignees.reposition()


        self.set_conf(self.SMARTOS_CONF_ETATS, etats)
        self.set_conf(self.SMARTOS_CONF_MODE, True)

    def _smartos_quitter_deux_ecrans(self):
        from qtpy.QtCore import Qt as _SmartosQt

        fenetre = getattr(self, "_smartos_fen2", None)
        if fenetre is None:
            return

        # Memoriser la disposition double-ecran AVANT de la defaire : c'est l'autre moitie.
        etats = dict(self.get_conf(self.SMARTOS_CONF_ETATS, default={}))
        etats["double_screen_1"] = qbytearray_to_str(
            self.main.saveState(version=WINDOW_STATE_VERSION)
        )
        etats["double_screen_2"] = qbytearray_to_str(fenetre.saveState())
        etats["double_geometry"] = qbytearray_to_str(fenetre.saveGeometry())

        # Relever AVANT de couper la reference : _smartos_groupes_dans_fenetre lit `fenetre`
        # directement (variable locale), mais autant le faire pendant que tout est encore en place.
        _groupes = self._smartos_groupes_dans_fenetre(fenetre)

        # closeEvent rappelle cette methode : couper la reference AVANT de reposer les panneaux,
        # sinon _smartos_dock_dans_ecran2 les croirait encore de l'autre cote.
        self._smartos_fen2 = None

        self._smartos_poser_groupes(self.main, _SmartosQt.RightDockWidgetArea, _groupes)

        if etats.get("mono"):
            self.main.restoreState(
                QByteArray().fromHex(str(etats["mono"]).encode("utf-8")),
                version=WINDOW_STATE_VERSION,
            )

        fenetre.closeEvent = lambda evenement: evenement.accept()
        fenetre.close()
        fenetre.deleteLater()

        self.toggle_lock(self._interface_locked)

        self.set_conf(self.SMARTOS_CONF_ETATS, etats)
        self.set_conf(self.SMARTOS_CONF_MODE, False)

    def _smartos_poser_barre_deux_ecrans(self):
        """
        La « nouvelle barre d'outils » demandee, avec son bouton de bascule.

        ⚠ UNE BARRE D'APPLICATION DECLAREE AU GREFFON Toolbar, ET SURTOUT PAS UNE QToolBar NUE.
        Les deux premieres versions en posaient une a la main, et les deux ont casse la rangee du
        haut - c'est le releve de l'utilisateur du 31/07/2026, « les outils se retrouvent a droite
        au lieu d'etre centres et la fenetre est trop grande verticalement ». La raison tient en
        une ligne : le centrage de cette rangee est CALCULE par patch_spyder_burger_menu.py
        (largeur de la DragArea gauche = W/2 - epingle a gauche - groupe/2), et ce calcul ne
        parcourt que `toolbarslist`, la liste des barres DECLAREES. Une barre nue occupe donc de la
        place sans etre comptee, et pousse tout le groupe.
        La parade evidente - addToolBarBreak, une rangee a soi - a ete essayee et MESUREE, elle est
        pire : _place_left reordonne la rangee par insertToolBar, et les controles de fenetre
        descendent avec la nouvelle rangee (releve du 31/07/2026, barre window_controls_toolbar a
        y=50 au lieu de y=0). Se declarer est la seule voie qui ne demande a corriger personne.

        Deux consequences de faire cela TARD (ce travail est differe d'un tour de boucle pour
        passer apres tous les on_mainwindow_visible) :
          - le container a deja rendu les barres : il faut appeler render() nous-memes ;
          - la barre s'ajoute en bout de rangee, donc apres les controles de fenetre : on l'insere
            juste avant eux, pour qu'ils restent l'element le plus a droite.
        """
        if getattr(self, "_smartos_barre_ecrans", None) is not None:
            return

        greffon_barres = self.get_plugin(Plugins.Toolbar, error=False)
        if greffon_barres is None:
            logger.debug("Greffon Toolbar absent : barre « Écrans » non posee")
            return

        action = self.create_action(
            "smartos_toggle_two_screens",
            text=_("Mode deux écrans"),
            tip=_("Déplacer les panneaux de droite dans une fenêtre pour le second écran"),
            toggled=self._smartos_basculer_deux_ecrans,
            register_action=False,
        )

        barre = greffon_barres.create_application_toolbar(
            self.SMARTOS_BARRE_ECRANS, _("Écrans")
        )
        greffon_barres.add_item_to_application_toolbar(
            action, toolbar_id=self.SMARTOS_BARRE_ECRANS, omit_id=True
        )
        barre.render()

        # ⚠ FOND GRISE QUAND LE BOUTON EST COCHE : cf. `_smartos_rendre_transparent` plus bas pour
        # le detail et les deux pieges deja payes. Applique ICI une premiere fois, mais ce n'est
        # PAS SUFFISANT A SOI SEUL (releve de l'utilisateur le 01/08/2026, toujours gris malgre ce
        # premier appel) - `_smartos_rendre_le_bouton`, rejouee a chaque bascule, la reapplique.
        self._smartos_rendre_transparent(barre.widgetForAction(action))

        # ⚠ ET RECOPIER L'ETAT VERROUILLE D'UNE BARRE EXISTANTE. Le verrouillage de l'interface
        # n'est pas une propriete que Qt propage : le greffon Toolbar le REJOUE sur les barres qu'il
        # connait, et il l'a fait avant que la notre existe. Elle nait donc MOBILE et affiche sa
        # poignee de deplacement, seule de la rangee - releve de l'utilisateur le 31/07/2026.
        # C'est le troisieme etat, apres la visibilite et le centrage, qu'une barre declaree tard
        # doit aller chercher elle-meme. patch_spyder_burger_menu.py fait deja exactement cela pour
        # sa propre barre nue.
        for _autre in greffon_barres.toolbarslist:
            if _autre is barre:
                continue
            barre.setMovable(_autre.isMovable())
            break

        # ⚠ A GAUCHE, COLLEE A « Fichiers », et pas seulement deplacee la : demande de l'utilisateur
        # du 31/07/2026. Une barre posee a gauche sans le DIRE serait comptee dans le groupe centre
        # par patch_spyder_burger_menu.py, qui la ferait alors decaler de sa propre largeur. On
        # s'annonce donc comme EPINGLEE A GAUCHE - la liste est ouverte, l'autre patch la relit a
        # chaque calcul - et c'est lui qui place la barre au bon endroit de la rangee.
        _epingles = tuple(getattr(self.main, "_smartos_barres_epinglees_gauche", ()))
        if self.SMARTOS_BARRE_ECRANS not in _epingles:
            self.main._smartos_barres_epinglees_gauche = _epingles + (self.SMARTOS_BARRE_ECRANS,)

        # ⚠ TROISIEME CONSEQUENCE, ET LA PLUS SOURNOISE : la barre nait CACHEE. Mesure du
        # 31/07/2026 - elle existe, elle est rendue, elle est placee, sa geometrie vaut 72x50 en
        # x=876, et `isVisible()` rend False. Un bouton parfaitement construit et invisible, soit
        # exactement ce dont l'utilisateur s'est plaint la veille : « je ne peux rien confirmer, si
        # je n'ai aucun bouton ». C'est load_last_visible_toolbars() qui cache tout ce qui n'est pas
        # dans `last_visible_toolbars`, et elle passe APRES nous : notre travail est differe d'un
        # tour de boucle, mais le demarrage de Spyder appelle processEvents(), si bien que ce tour
        # de boucle tombe AVANT le on_mainwindow_visible du greffon Toolbar.
        #
        # D'ou les deux moities, une par ordre d'execution possible - et il en faut bien deux,
        # aucune ne couvrant les deux cas : la conf si le greffon Toolbar passe apres nous (c'est
        # LUI qui montrera la barre, par son propre mecanisme), le setVisible s'il est deja passe.
        _noms = list(self.get_conf("last_visible_toolbars", default=[], section="toolbar"))
        if self.SMARTOS_BARRE_ECRANS not in _noms:
            _noms.append(self.SMARTOS_BARRE_ECRANS)
            self.set_conf("last_visible_toolbars", _noms, section="toolbar")
        barre.setVisible(True)

        self._smartos_barre_ecrans = barre
        self._smartos_action_ecrans = action
        self._smartos_rendre_le_bouton(False)

    def _smartos_rendre_transparent(self, bouton):
        """
        Forcer un fond transparent, y compris a l'etat coche, sur CE bouton precis.

        ⚠ DEUX PIEGES, chacun paye avant de comprendre. 1) Un selecteur de type nu
        (`QToolButton:checked`) ne suffit pas : Spyder pose sa propre feuille de style au niveau
        de l'application, avec un selecteur plus SPECIFIQUE qui l'emporte quel que soit l'ordre
        d'application - releve de l'utilisateur le 01/08/2026, fond gris persistant malgre ce
        style. Nom d'objet UNIQUE + selecteur d'ID (`#nom:checked`), qui l'emporte en specificite
        CSS. 2) POSER LE STYLE UNE SEULE FOIS, A LA CREATION DU BOUTON, N'A PAS SUFFI NON PLUS -
        toujours gris malgre le selecteur d'ID. Diagnostic en direct : le bouton qu'on style au
        moment de creer la barre (`_smartos_poser_barre_deux_ecrans`) n'a NI objectName NI
        styleSheet quand on l'inspecte ensuite - `render()` est rejoue plus tard par le greffon
        Toolbar lui-meme (deja documente juste au-dessus : « la conf si le greffon Toolbar passe
        apres nous »), qui RECONSTRUIT le QToolButton depuis l'action, effacant tout ce qu'on avait
        pose sur l'ancien. D'ou cette methode SEPAREE, REJOUEE a chaque bascule par
        `_smartos_rendre_le_bouton` (qui tourne de toute facon a chaque clic) plutot qu'une seule
        fois a la creation - le bouton, quel qu'il soit a cet instant, est alors forcement le bon.
        """
        if bouton is None:
            return
        bouton.setObjectName("smartos_bouton_deux_ecrans")
        bouton.setStyleSheet(
            "QToolButton#smartos_bouton_deux_ecrans"
            " { background-color: transparent; border: none; } "
            "QToolButton#smartos_bouton_deux_ecrans:checked"
            " { background-color: transparent; border: none; } "
            "QToolButton#smartos_bouton_deux_ecrans:hover"
            " { background-color: transparent; border: none; } "
            "QToolButton#smartos_bouton_deux_ecrans:pressed"
            " { background-color: transparent; border: none; }"
        )

    def _smartos_rendre_le_bouton(self, actif):
        """
        Donner au bouton l'aspect de CE QU'IL FERA au prochain clic, et non de l'etat courant.

        Demande de l'utilisateur du 31/07/2026 : « je ne trouve pas l'icone pour lancer la 2eme
        fenetre tres adaptee, et il faudrait qu'elle change pour permettre un retour plus explicite
        sur une fenetre ». Deux moniteurs quand on est sur un ecran, un seul moniteur quand on est
        sur deux : c'est la convention du bouton maximiser/restaurer, que le greffon
        window_controls applique deja a ses propres boutons.

        Les icones viennent de qtawesome et non de create_icon() : le jeu interne de Spyder n'a
        rien qui parle d'ECRANS, et « dock » - ce qui etait pose ici - decrit un panneau ancre,
        c'est-a-dire tout autre chose.
        """
        _action = getattr(self, "_smartos_action_ecrans", None)
        if _action is None:
            return
        import qtawesome as _qta
        from spyder.utils.icon_manager import ima as _ima
        _action.setIcon(_qta.icon("mdi.monitor" if actif else "mdi.monitor-multiple",
                                  color=_ima.MAIN_FG_COLOR))
        _action.setText(_("Revenir à une fenêtre") if actif else _("Mode deux écrans"))
        _action.setToolTip(
            _("Rapatrier les panneaux du second écran dans la fenêtre principale") if actif
            else _("Déplacer les panneaux de droite dans une fenêtre pour le second écran"))

        # ⚠ REJOUE A CHAQUE BASCULE, PAS UNE SEULE FOIS A LA CREATION : cf.
        # `_smartos_rendre_transparent` pour le pourquoi (le bouton peut avoir ete reconstruit par
        # le greffon Toolbar entre-temps).
        _barre = getattr(self, "_smartos_barre_ecrans", None)
        if _barre is not None:
            self._smartos_rendre_transparent(_barre.widgetForAction(_action))

    def _smartos_installer_deux_ecrans(self):
        """
        Point d'entree du mode, appele une fois l'interface visible.

        Pose la barre, puis REND LE MODE s'il etait actif a la fermeture precedente - sans quoi
        l'utilisateur retrouverait ses panneaux rapatries a chaque demarrage, et le « souvenir »
        des deux dispositions ne servirait a rien.
        """
        try:
            self._smartos_poser_barre_deux_ecrans()
            if self.get_conf(self.SMARTOS_CONF_MODE, default=False):
                # setChecked declenche `toggled`, donc la bascule : une seule source de verite.
                self._smartos_action_ecrans.setChecked(True)
        except Exception:
            logger.exception("Mode deux ecrans non installe")

'''


def _debut_du_bloc(source):
    """Index ou commence le bloc SmartOS deja pose, indentation comprise, ou -1."""
    debut = source.find(DEBUT_BLOC)
    while debut > 0 and source[debut - 1] in " \t":
        debut -= 1
    return debut


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/layout/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as fichier:
            source = fichier.read()
    except OSError as erreur:
        print(f"layout/plugin.py illisible ({erreur}) - patch deux ecrans non applique.",
              file=sys.stderr)
        return 1

    # Garde la lecture initiale : c'est a ELLE que se compare la longueur finale, `source` etant
    # ampute du bloc precedent quelques lignes plus bas.
    original = source

    if source.count(ANCRE) != 1:
        print(f"Ancre introuvable ou non unique dans {path} : Spyder a peut-etre restructure son "
              f"greffon Layout. Patch deux ecrans non applique.", file=sys.stderr)
        return 1

    # Deja a jour ? Comparaison sur le TEXTE du bloc, et non sur un marqueur : un marqueur seul
    # dirait « present » d'une version anterieure, et sauterait la mise a jour en silence.
    # ⚠ Le "\n\n" fait partie du test, il n'est pas cosmetique : c'est lui qui distingue un bloc
    # correctement cousu d'un bloc colle a la ligne precedente par une version anterieure du
    # retrait. Sans lui, le patch se declarait « deja applique » sur une couture a reparer.
    if ("\n\n" + BLOC) in source and HIDE_NEW in source \
            and "_smartos_installer_deux_ecrans)" in source:
        print("Patch mode deux ecrans deja applique.")
        return 0

    # Rejeu sur un fichier que patch_spyder_deux_ecrans_maximize.py a deja repris : il a insere ses
    # methodes DANS le bloc et reecrit la boucle (HIDE_NEW n'y est plus), donc le test ci-dessus ne
    # peut pas repondre. On compare le bloc une fois ses methodes otees ; s'il differe, c'est une
    # version anterieure, que ce patch ne sait pas mettre a jour sous l'autre.
    import patch_spyder_deux_ecrans_maximize as maximize
    if maximize.MARKER in source:
        if ("\n\n" + BLOC) in source.replace(maximize.BLOC_METHODES, "") \
                and "_smartos_installer_deux_ecrans)" in source:
            print("Patch mode deux ecrans deja applique (et repris par le patch maximize).")
            return 0
        print(f"{path} porte une version anterieure du patch deux ecrans SOUS le patch maximize : "
              f"reinstaller le fichier d'origine puis rejouer la chaine.", file=sys.stderr)
        return 1

    if source.count(DEBUT_BLOC) > 1:
        print(f"{path} contient DEUX blocs SmartOS deux ecrans : une version anterieure du patch "
              f"s'y est ajoutee sans retirer la precedente. Reinstaller le fichier plutot que de "
              f"deviner lequel enlever.", file=sys.stderr)
        return 1

    # Retirer un bloc SmartOS deja pose, quelle que soit sa version.
    debut = _debut_du_bloc(source)
    if debut != -1:
        fin = source.find(ANCRE, debut)
        if fin == -1:
            print(f"Bloc SmartOS present dans {path} mais son ancre de fin est introuvable - je "
                  f"n'y touche pas plutot que de couper au hasard.", file=sys.stderr)
            return 1
        # ⚠ NORMALISER LA COUTURE, ET NE PAS SE CONTENTER DE RECOLLER. DEBUT_BLOC commence par un
        # saut de ligne : le retirer tel quel CONSOMME celui qui terminait la ligne precedente, et
        # le rejeu suivant en mange un de plus. Constate le 31/07/2026 sur l'installation en place,
        # ou le bloc avait fini colle a la fin de `return ... _maximize_dockwidget_action` - du
        # Python encore valide, donc invisible pour ast.parse comme pour le garde-fou de longueur.
        source = source[:debut].rstrip("\n") + "\n\n" + source[fin:]

    patched = source.replace(ANCRE, BLOC + ANCRE)

    # Retouche du code d'origine, REJOUABLE : on revient d'abord au texte de Spyder, puis on
    # reapplique. Sans ce retour, une retouche modifiee ne s'appliquerait jamais sur une
    # installation deja patchee - le piege des drapeaux versionnes, en pire, puisque rien ne le
    # signalerait.
    patched = patched.replace(HIDE_NEW, HIDE_OLD)
    if patched.count(HIDE_OLD) != 1:
        print(f"Boucle de maximize_dockwidget introuvable ou non unique dans {path} - patch deux "
              f"ecrans non applique.", file=sys.stderr)
        return 1
    patched = patched.replace(HIDE_OLD, HIDE_NEW)

    # Le point d'entree, sans lequel tout ce qui precede serait du code mort.
    if "_smartos_installer_deux_ecrans)" not in patched:
        if patched.count(ANCRE_APPEL) != 1:
            print(f"Ancre du point d'entree introuvable ou non unique dans {path} - patch deux "
                  f"ecrans non applique.", file=sys.stderr)
            return 1
        patched = patched.replace(ANCRE_APPEL, APPEL)

    try:
        ast.parse(patched)
    except SyntaxError as erreur:
        print(f"Le layout/plugin.py patche n'est pas du Python valide ({erreur}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    # ⚠ GARDE-FOU QUI MANQUAIT LE 31/07/2026 : un patch qui AJOUTE du code ne doit jamais rendre un
    # fichier plus court. Le bug de delimiteur ci-dessus avait emporte 190 lignes, et le fichier
    # restait du Python parfaitement valide - `ast.parse` ne voyait rien. C'est le cas legitime a ne
    # pas confondre : une coupe silencieuse ressemble en tout point a un patch reussi.
    if len(patched.splitlines()) < len(original.splitlines()):
        print(f"Le {path} patche est PLUS COURT que l'original "
              f"({len(original.splitlines())} -> {len(patched.splitlines())} lignes) : ce patch ne "
              f"fait qu'ajouter, il a donc coupe quelque chose. Aucune modification ecrite.",
              file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as fichier:
        fichier.write(patched)
    print(f"Patch mode deux ecrans applique : barre « Écrans » et bouton de bascule ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
