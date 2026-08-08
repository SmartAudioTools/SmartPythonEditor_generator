#!/usr/bin/env python3
"""Patch spyder/plugins/toolbar/container.py : ORDRE EXPLICITE des barres d'outils d'application.

Contexte : demande de l'utilisateur du 26/07/2026 ("je veux reorganiser les icones de Spyder"),
perimetre precise a l'ordre de la rangee du haut, puis ordre DICTE par lui barre par barre. Resultat
vise :

    [burger] | Ouvrir Nouveau Enregistrer Enregistrer-tout | Docteur Executer Deboguer Profiler
             Python-Tutor Arreter | interpreteur | [nom du fichier + boutons de fenetre]

Le burger et la barre Fichiers restent EPINGLES a gauche (c'est patch_spyder_burger_menu.py qui les
y place et qui centre le groupe du milieu) ; la barre des controles de fenetre reste a droite (son
propre greffon s'en charge). La barre "Agrandir le volet courant" (Main) ne fait plus partie de la
rangee : l'utilisateur ne l'a pas retenue, elle est MASQUEE par configuration
(toolbar/last_visible_toolbars, retire par installation_SmartPythonEditor.sh via tools/spyder_config_set.py) -
pas supprimee, donc recochable dans Affichage > Barres d'outils, et sa place dans la liste ci-dessous
la ramenerait alors apres "Arreter" plutot qu'en bout de rangee. La commande elle-meme reste
accessible au clavier et par le menu Affichage.

D'OU VIENT L'ORDRE, ET POURQUOI IL ETAIT BANCAL
ToolbarContainer.load_last_toolbars() construit l'ordre comme
"internal_toolbars_order + external_toolbars", ou internal_toolbars_order est une liste EN DUR
[File, Run, Debug, Profile, Main] et external_toolbars les barres des greffons dans leur ordre de
CREATION (donc d'initialisation des greffons, pas un choix). Consequences :
  - "Agrandir le volet courant" (barre Main), une action de VUE, se retrouvait plantee au milieu des
    lanceurs, entre Profiler et Python Tutor ;
  - la place de nos barres dependait de l'ordre de chargement des greffons, c'est-a-dire de rien.
Ce patch remplace ce calcul par une liste explicite (_smartos_order), a laquelle sont ajoutees en fin
les barres qu'elle ne connait pas : un greffon installe plus tard apparait donc toujours, sans pouvoir
se glisser au milieu des groupes. La barre du repertoire de travail reste en DERNIER, comme le veut
Spyder (son commentaire d'origine est conserve : on ne voit pas ou elle finit, une barre placee a sa
suite serait introuvable).

REORGANISATION "UNE SEULE FOIS", ET POURQUOI IL FALLAIT S'EN OCCUPER
Spyder ne reorganise QUE si l'ensemble des barres a change depuis la derniere fermeture
(set(last_toolbars) != set(app_toolbars)) ; sinon il laisse Qt restaurer les positions memorisees.
Poser un nouvel ordre sans y toucher n'aurait donc rien fait des le deuxieme demarrage - et une fois
l'utilisateur ayant demarre Spyder apres l'ajout des barres "Stop" et "Analyse de code", les deux
ensembles coincident a nouveau. On ajoute donc au test un drapeau de configuration, pose juste apres
la reorganisation : l'ordre est impose UNE fois, puis on respecte le choix de l'utilisateur.
⚠ LE DRAPEAU EST VERSIONNE DANS SON NOM (smartos_order_v2). Changer _smartos_order sans changer ce
nom serait SANS EFFET sur une installation ou le drapeau est deja pose - le nouvel ordre ne se
verrait jamais. C'est exactement le piege des drapeaux de patch_spyder_hide_docks.py, et il s'est
present ici des la premiere retouche : la version v1 de ce patch avait un autre ordre, dicte ensuite
autrement par l'utilisateur.

Usage : patch_spyder_toolbar_order.py <chemin vers plugins/toolbar/container.py installe>

IDEMPOTENCE PAR MARQUEUR VERSIONNE : le bloc n'est saute que si le marqueur de CETTE version est
present, et il declare DEUX textes anciens possibles - celui de la version precedente du patch et
celui d'origine de Spyder - du plus specifique au plus general (le second est un sous-ensemble du
premier). Re-parse avant ecriture ; echec BRUYANT (code 1) si aucun des deux n'est present exactement
une fois - jamais deviner.
"""
import ast
import sys

# Marqueur d'idempotence du TEXTE du patch, distinct du drapeau de configuration ci-dessous : le
# texte a change une fois de plus que l'ordre (retrait de la barre du repertoire courant de la zone
# d'outils), et confondre les deux aurait fait dire "deja applique" a un patch pourtant modifie.
MARKER = "N'EST PLUS REMISE DANS LA FENETRE"

# Texte d'origine de Spyder (installation fraiche).
OLD_SPYDER = '''        last_toolbars = self.get_conf("last_toolbars")
        if (
            not last_toolbars
            or set(last_toolbars) != set(app_toolbars.keys())
        ):
            logger.debug("Reorganize application toolbars")

            # We need to remove all toolbars first to organize them in the way
            # we want
            for toolbar in self._toolbarslist:
                self._plugin.main.removeToolBar(toolbar)

            # Add toolbars with the working directory to the right because it's
            # not clear where it ends, so users can have a hard time finding a
            # new toolbar in the interface if it's placed next to it.
            toolbars_order = internal_toolbars_order + external_toolbars
            for toolbar_id in (
                toolbars_order
                + [ApplicationToolbars.WorkingDirectory]
            ):
                toolbar = app_toolbars.get(toolbar_id)
                if toolbar:
                    self._plugin.main.addToolBar(toolbar)
                    toolbar.render()'''

# Texte pose par la version v1 de ce patch (ordre anterieur, drapeau smartos_order_applied).
OLD_V1 = '''        # SMARTOS : ordre explicite des barres d'outils (cf.
        # Commun/scripts/patch_spyder_toolbar_order.py). Les identifiants des barres de greffons
        # sont ecrits en clair a dessein : ce fichier ne doit dependre d'aucun greffon, et une barre
        # absente est simplement ignoree (app_toolbars.get renvoie None).
        _smartos_order = [
            ApplicationToolbars.File,          # Ouvrir, Nouveau, Enregistrer, Enregistrer tout
            ApplicationToolbars.Run,           # Executer le fichier
            ApplicationToolbars.Debug,         # Deboguer le fichier
            ApplicationToolbars.Profile,       # Profiler le fichier
            "python_tutor_toolbar",            # Lancer Python Tutor (greffon SmartOS)
            "smartos_stop_toolbar",            # Tout arreter - contrepartie des quatre lanceurs
            "smartos_code_analysis_toolbar",   # Docteur (pylint sur le fichier courant)
            ApplicationToolbars.Main,          # Agrandir le volet courant : une action de VUE, elle
                                               # n'a rien a faire au milieu des lanceurs
            "interpreter_toolbar",             # combobox d'interpreteur (greffon SmartOS)
            "window_controls_toolbar",         # nom du fichier + boutons de fenetre, a droite
        ]

        last_toolbars = self.get_conf("last_toolbars")
        if (
            not last_toolbars
            or set(last_toolbars) != set(app_toolbars.keys())
            # SMARTOS : imposer l'ordre ci-dessus UNE fois. Sans ce drapeau, le nouvel ordre ne
            # s'appliquerait qu'au demarrage suivant l'ajout ou le retrait d'une barre - les deux
            # tests ci-dessus etant faux le reste du temps, Qt restaurant alors les positions
            # memorisees. Une fois pose, on respecte le choix de l'utilisateur.
            or not self.get_conf("smartos_order_applied", False)
        ):
            logger.debug("Reorganize application toolbars")

            # We need to remove all toolbars first to organize them in the way
            # we want
            for toolbar in self._toolbarslist:
                self._plugin.main.removeToolBar(toolbar)

            # Add toolbars with the working directory to the right because it's
            # not clear where it ends, so users can have a hard time finding a
            # new toolbar in the interface if it's placed next to it.
            # SMARTOS : _smartos_order d'abord, puis les barres qu'il ne connait pas (greffon
            # installe plus tard, barre ajoutee par une montee de version de Spyder) - elles
            # apparaissent ainsi toujours, mais jamais au milieu de nos groupes.
            toolbars_order = _smartos_order + [
                _tid for _tid in (internal_toolbars_order + external_toolbars)
                if _tid not in _smartos_order
            ]
            for toolbar_id in (
                toolbars_order
                + [ApplicationToolbars.WorkingDirectory]
            ):
                toolbar = app_toolbars.get(toolbar_id)
                if toolbar:
                    self._plugin.main.addToolBar(toolbar)
                    toolbar.render()

            self.set_conf("smartos_order_applied", True)'''

NEW = '''        # SMARTOS : ordre explicite des barres d'outils, dicte par l'utilisateur le 26/07/2026
        # (cf. Commun/scripts/patch_spyder_toolbar_order.py). Les identifiants des barres de
        # greffons sont ecrits en clair a dessein : ce fichier ne doit dependre d'aucun greffon, et
        # une barre absente est simplement ignoree (app_toolbars.get renvoie None).
        _smartos_order = [
            ApplicationToolbars.File,          # Ouvrir, Nouveau, Enregistrer, Enregistrer tout
                                               # (epinglee a gauche par le patch du burger)
            "smartos_code_analysis_toolbar",   # Docteur (pylint sur le fichier courant)
            ApplicationToolbars.Run,           # Executer le fichier
            ApplicationToolbars.Debug,         # Deboguer le fichier
            ApplicationToolbars.Profile,       # Profiler le fichier
            "python_tutor_toolbar",            # Lancer Python Tutor (greffon SmartOS)
            "smartos_stop_toolbar",            # Tout arreter (greffon SmartOS)
            ApplicationToolbars.Main,          # Agrandir le volet courant : action de VUE, donc
                                               # apres les lanceurs et l'arret, pas au milieu d'eux.
                                               # Son bouton porte nos deux icones, cf.
                                               # patch_spyder_maximize_icons.py.
            "interpreter_toolbar",             # combobox d'interpreteur (greffon SmartOS)
            "window_controls_toolbar",         # nom du fichier + boutons de fenetre, a droite
        ]

        last_toolbars = self.get_conf("last_toolbars")
        if (
            not last_toolbars
            or set(last_toolbars) != set(app_toolbars.keys())
            # SMARTOS : imposer l'ordre ci-dessus UNE fois. Sans ce drapeau, le nouvel ordre ne
            # s'appliquerait qu'au demarrage suivant l'ajout ou le retrait d'une barre - les deux
            # tests ci-dessus etant faux le reste du temps, Qt restaurant alors les positions
            # memorisees. Une fois pose, on respecte le choix de l'utilisateur.
            # Le nom du drapeau est VERSIONNE : changer _smartos_order sans le renommer serait sans
            # effet la ou il est deja pose.
            or not self.get_conf("smartos_order_v2", False)
        ):
            logger.debug("Reorganize application toolbars")

            # We need to remove all toolbars first to organize them in the way
            # we want
            for toolbar in self._toolbarslist:
                self._plugin.main.removeToolBar(toolbar)

            # SMARTOS : _smartos_order d'abord, puis les barres qu'il ne connait pas (greffon
            # installe plus tard, barre ajoutee par une montee de version de Spyder) - elles
            # apparaissent ainsi toujours, mais jamais au milieu de nos groupes.
            # ⚠ LA BARRE DU REPERTOIRE COURANT N'EST PLUS REMISE DANS LA FENETRE. Spyder l'ajoutait
            # ici en dur, tout a droite (son commentaire d'origine, conserve juste en dessous,
            # explique pourquoi). Or patch_spyder_workingdir_in_files.py la sort de la zone d'outils
            # pour la poser SOUS la barre du dock Fichiers, ou est sa place : le repertoire courant
            # est fonctionnellement lie a l'explorateur de fichiers. La rajouter ici la reprenait au
            # dock a chaque REORGANISATION - donc chaque fois que l'ensemble des barres change (un
            # greffon installe, une barre ajoutee), ce qui explique qu'elle "revenait toujours" dans
            # la rangee du haut sans qu'on comprenne pourquoi. Elle reste CREEE et visible, dans le
            # dock ; seule sa remise en zone d'outils disparait.
            #   Commentaire d'origine de Spyder, pour memoire : "Add toolbars with the working
            #   directory to the right because it's not clear where it ends, so users can have a
            #   hard time finding a new toolbar in the interface if it's placed next to it."
            toolbars_order = _smartos_order + [
                _tid for _tid in (internal_toolbars_order + external_toolbars)
                if _tid not in _smartos_order
                and _tid != ApplicationToolbars.WorkingDirectory
            ]
            for toolbar_id in toolbars_order:
                toolbar = app_toolbars.get(toolbar_id)
                if toolbar:
                    self._plugin.main.addToolBar(toolbar)
                    toolbar.render()

            self.set_conf("smartos_order_v2", True)'''

# Fin du bloc, version par version. OLD_V2 est DERIVE de NEW par substitution de sa fin, plutot que
# recopie a la main : les deux versions ne different que par la, et une recopie se serait desynchronisee
# au premier ajustement de commentaire (le bloc ne matcherait plus, et le patch echouerait bruyamment
# sur une installation deja patchee).
FIN_V3 = NEW[NEW.index("            # SMARTOS : _smartos_order d'abord"):]

FIN_V2 = '''            # Add toolbars with the working directory to the right because it's
            # not clear where it ends, so users can have a hard time finding a
            # new toolbar in the interface if it's placed next to it.
            # SMARTOS : _smartos_order d'abord, puis les barres qu'il ne connait pas (greffon
            # installe plus tard, barre ajoutee par une montee de version de Spyder) - elles
            # apparaissent ainsi toujours, mais jamais au milieu de nos groupes.
            toolbars_order = _smartos_order + [
                _tid for _tid in (internal_toolbars_order + external_toolbars)
                if _tid not in _smartos_order
            ]
            for toolbar_id in (
                toolbars_order
                + [ApplicationToolbars.WorkingDirectory]
            ):
                toolbar = app_toolbars.get(toolbar_id)
                if toolbar:
                    self._plugin.main.addToolBar(toolbar)
                    toolbar.render()

            self.set_conf("smartos_order_v2", True)'''

OLD_V2 = NEW.replace(FIN_V3, FIN_V2)

# Du plus specifique au plus general : chaque version CONTIENT la precedente en grande partie, c'est
# donc l'ordre qui designe le bon candidat.
CANDIDATS = (OLD_V2, OLD_V1, OLD_SPYDER)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/toolbar/container.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"container.py illisible ({error}) - patch ordre des barres non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch ordre des barres d'outils deja applique.")
        return 0

    # PREMIER candidat present exactement une fois, du plus specifique au plus general : le texte
    # d'une version anterieure du patch CONTIENT celui d'origine de Spyder, donc plusieurs candidats
    # matchent sur une installation deja patchee, et c'est l'ordre qui designe le bon.
    trouve = next((o for o in CANDIDATS if source.count(o) == 1), None)
    if trouve is None:
        print(f"Aucun des {len(CANDIDATS)} blocs load_last_toolbars attendus (celui d'origine de "
              f"Spyder ou ceux des versions precedentes du patch) n'est present exactement une fois "
              f"dans {path} - Spyder a peut-etre restructure son code, patch ordre des barres non "
              f"applique.", file=sys.stderr)
        return 1

    patched = source.replace(trouve, NEW)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le container.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch ordre des barres d'outils applique : Docteur en tete du groupe, puis Executer, "
          f"Deboguer, Profiler, Python Tutor, Arreter ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
