#!/usr/bin/env python3
"""Patch spyder/plugins/variableexplorer/widgets/main_widget.py : allege la barre d'outils du dock
"Explorateur de variables" en deplaçant des boutons dans son menu burger (options).

Contexte : chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt ("voir dock par
dock quels boutons on peut deplacer dans le menu burger du dock"), inventaire + approbation de
l'utilisateur le 25/07/2026.

CONSTAT. La barre portait quatre boutons - Importer des donnees, Enregistrer les donnees, Enregistrer
les donnees sous..., Supprimer toutes les variables - dont les trois premiers servent a echanger un
espace de noms avec un fichier .spydata : utile, mais rare, alors qu'ils occupaient trois icones en
permanence.

TROIS CHANGEMENTS (1re passe, 25/07/2026).
  1. Importer / Enregistrer / Enregistrer sous quittent la barre pour une nouvelle section EN TETE du
     menu burger (avant les exclusions d'affichage). Il ne reste dans la barre que "Supprimer toutes
     les variables". La barre de coin (Rechercher, Filtre, Rafraichir) n'est PAS touchee : ce sont
     des commandes du quotidien.
  2. _set_main_toolbar_state() grise/degrise explicitement les trois actions deplacees. C'est
     indispensable : cette methode grisait toute la barre quand la console courante est morte (elle
     itere sur main_toolbar.actions()) ; sorties de la barre, les trois actions seraient restees
     cliquables sur une console inexistante. update_actions() continue ensuite d'affiner l'etat de
     "Enregistrer les donnees" selon nsb.filename, comme avant.
  3. Correction d'un doublon de LIBELLE, sans rapport avec l'emplacement mais visible dans le meme
     menu : "Exclure les variables en majuscule" y apparaissait DEUX FOIS, la traduction francaise
     livree par Spyder rendant identiquement "Exclude all-uppercase variables" et "Exclude
     capitalized variables". Ce n'est PAS traite ici mais dans
     Commun/scripts/patch_spyder_add_translations.py (section OVERRIDES), qui corrige le catalogue
     gettext : le code source n'a pas a etre touche pour ca.

CHANGEMENT (2e passe, 26/07/2026). "Supprimer toutes les variables" rejoint a son tour le menu
burger : c'est une action DESTRUCTRICE et rare, mal placee en icone permanente. La barre principale
devient donc VIDE.

⚠ ON NE LA MASQUE PAS pour autant, contrairement aux panneaux Pyxel / Python Tutor / Edition
collaborative. Elle partage sa rangee avec la barre de COIN (Rechercher, Filtre, Rafraichir), qui
reste : la rangee existe de toute facon, il n'y a donc AUCUNE hauteur a gagner, et c'est
precisement l'etirement de la barre principale (stretch 10000 dans PluginMainWidget._setup) qui
pousse les boutons du coin a droite - la masquer les ferait retomber a gauche.

CHANGEMENT (3e passe, 26/07/2026, demande de l'utilisateur). Le bouton de FILTRE quitte a son tour
la barre de coin pour le menu burger, ou il se pose juste AU-DESSUS des cinq exclusions qu'il
commande (`_enable_filter_actions` les grise quand il est decoche) - elles etaient jusqu'ici
pilotees depuis un bouton qui n'etait pas dans le meme menu qu'elles. Exactement ce qui avait ete
fait pour le filtre du dock Fichiers le 22/07/2026.
⚠ Il faut lui DONNER UN LIBELLE : il est cree avec text="" (une icone suffit dans une barre), ce qui
en aurait fait une entree de menu VIDE. On prend _("Filter variables") - deja son infobulle, et deja
traduit par "Filtrer les variables" dans le catalogue de Spyder, rien a ajouter.
Le coin garde "Rechercher" et "Rafraichir", commandes du quotidien.

Les actions restent CREEES et enregistrees a l'identique (self.get_action(...) les retrouve
independamment de leur emplacement) : on ne change QUE ou elles s'affichent.

Usage : patch_spyder_varexp_toolbar.py <chemin vers variableexplorer/widgets/main_widget.py installe>

IDEMPOTENCE PAR BLOC. Chaque bloc porte SON marqueur et est saute si ce marqueur est deja dans le
fichier - c'est ce qui permet a la 2e passe de s'appliquer sur une installation ou la 1re est deja
en place, sans rien defaire (un marqueur global unique l'aurait rendue inoperante, piege deja paye
sur ce depot). Les blocs sont appliques DANS L'ORDRE, un bloc pouvant s'ancrer sur le resultat d'un
precedent ; chaque marqueur doit etre une chaine STABLE de son propre remplacement. Re-parse avant
ecriture, echec BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # ---- 1re passe (25/07/2026) ---------------------------------------------------------------
    # 1. Section du menu burger pour les actions de donnees, EN TETE (inseree avant la boucle des
    #    exclusions : les sections sont rendues dans leur ordre de premiere utilisation).
    (
        "quittent la barre d'outils pour cette section",
        '''        # Options menu
        options_menu = self.get_options_menu()
        for item in [self.exclude_private_action,''',
        '''        # Options menu
        options_menu = self.get_options_menu()

        # SmartOS (patch_spyder_varexp_toolbar.py) : Importer / Enregistrer / Enregistrer sous
        # quittent la barre d'outils pour cette section, placee en tete du menu (les sections sont
        # rendues dans leur ordre de premiere utilisation). Ce sont des actions rares - echanger un
        # espace de noms avec un fichier .spydata - qui occupaient trois icones en permanence.
        for item in [import_data_action, save_action, save_as_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=VariableExplorerWidgetOptionsMenuSections.Data,
            )

        for item in [self.exclude_private_action,''',
    ),
    # 2. Declaration de la nouvelle section.
    (
        "Data = 'data_section'",
        '''class VariableExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'
    Resize = 'resize_section\'''',
        '''class VariableExplorerWidgetOptionsMenuSections:
    # SmartOS (patch_spyder_varexp_toolbar.py) : section des actions de donnees (Importer /
    # Enregistrer / Enregistrer sous), deplacees de la barre d'outils vers le menu burger.
    Data = 'data_section'
    Display = 'excludes_section'
    Highlight = 'highlight_section'
    Resize = 'resize_section\'''',
    ),
    # 4. Grisage : les trois actions deplacees ne sont plus atteintes par la boucle sur la barre.
    (
        'elles resteraient cliquables sur une console inexistante',
        '''    def _set_main_toolbar_state(self, enabled):
        """Set main toolbar enabled state."""
        main_toolbar = self.get_main_toolbar()
        for action in main_toolbar.actions():
            action.setEnabled(enabled)''',
        '''    def _set_main_toolbar_state(self, enabled):
        """Set main toolbar enabled state."""
        main_toolbar = self.get_main_toolbar()
        for action in main_toolbar.actions():
            action.setEnabled(enabled)

        # SmartOS (patch_spyder_varexp_toolbar.py) : Importer / Enregistrer / Enregistrer sous ont
        # quitte la barre pour le menu burger. La boucle ci-dessus, qui grise toute la barre quand
        # la console courante est morte (message d'erreur), ne les atteint donc plus : on les grise
        # explicitement, sinon elles resteraient cliquables sur une console inexistante.
        # update_actions() affine ensuite l'etat de SaveData selon nsb.filename, comme avant.
        for action_id in [VariableExplorerWidgetActions.ImportData,
                          VariableExplorerWidgetActions.SaveData,
                          VariableExplorerWidgetActions.SaveDataAs]:
            self.get_action(action_id).setEnabled(enabled)''',
    ),
    # ---- 2e passe (26/07/2026) -----------------------------------------------------------------
    # 5. Barre principale VIDEE : "Supprimer toutes les variables" part aussi. On ne masque pas la
    #    barre pour autant, cf. l'avertissement en tete de fichier.
    (
        "la barre principale est desormais VIDE",
        # Deux ANCIENS possibles : le texte d'origine de Spyder (installation fraiche) ou celui
        # que la 1re passe avait pose (installation deja patchee) - ce bloc-ci les SUPPLANTE tous
        # les deux, il ne s'y ajoute pas, d'ou le tuple.
        (
            '''        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [import_data_action, save_action, save_as_action,
                     reset_namespace_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=VariableExplorerWidgetMainToolBarSections.Main,
            )
        save_action.setEnabled(False)''',
            '''        # Main toolbar
        # SmartOS (patch_spyder_varexp_toolbar.py) : la barre ne garde que "Supprimer toutes les
        # variables" ; Importer / Enregistrer / Enregistrer sous sont passees dans le menu burger
        # (cf. plus haut).
        main_toolbar = self.get_main_toolbar()
        for item in [reset_namespace_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=VariableExplorerWidgetMainToolBarSections.Main,
            )
        save_action.setEnabled(False)''',
        ),
        '''        # Main toolbar
        # SmartOS (2e passe, 26/07/2026) : la barre principale est desormais VIDE - "Supprimer
        # toutes les variables", destructrice et rare, a rejoint le menu burger avec les autres.
        # ⚠ On la LAISSE en place sans la masquer : elle partage sa rangee avec la barre de COIN
        # (Rechercher, Filtre, Rafraichir), qui reste. La rangee existe donc de toute facon - aucune
        # hauteur a gagner - et c'est l'etirement de cette barre (stretch 10000 dans
        # PluginMainWidget._setup) qui pousse les boutons du coin a droite : la masquer les ferait
        # retomber a gauche.
        main_toolbar = self.get_main_toolbar()
        save_action.setEnabled(False)''',
    ),
    # 6. Menu burger : "Supprimer toutes les variables" rejoint la section des actions de donnees.
    (
        '"Supprimer toutes les variables" les rejoint',
        '''        for item in [import_data_action, save_action, save_as_action]:''',
        '''        # SmartOS (2e passe, 26/07/2026) : "Supprimer toutes les variables" les rejoint.
        for item in [import_data_action, save_action, save_as_action,
                     reset_namespace_action]:''',
    ),
    # 7. Grisage : la barre etant vide, la 4e action deplacee doit elle aussi etre grisee a la main.
    (
        "VariableExplorerWidgetActions.ResetNamespace]",
        '''        for action_id in [VariableExplorerWidgetActions.ImportData,
                          VariableExplorerWidgetActions.SaveData,
                          VariableExplorerWidgetActions.SaveDataAs]:''',
        '''        for action_id in [VariableExplorerWidgetActions.ImportData,
                          VariableExplorerWidgetActions.SaveData,
                          VariableExplorerWidgetActions.SaveDataAs,
                          VariableExplorerWidgetActions.ResetNamespace]:''',
    ),
    # ---- 3e passe (26/07/2026) -----------------------------------------------------------------
    # 8. Le bouton de filtre recoit un LIBELLE : sans lui, son entree de menu serait vide.
    (
        'Libelle du bouton de filtre dans le MENU',
        '''        self.filter_button = self.create_action(
            VariableExplorerWidgetActions.ToggleFilter,
            text="",''',
        '''        self.filter_button = self.create_action(
            VariableExplorerWidgetActions.ToggleFilter,
            # SmartOS (3e passe, 26/07/2026) : Libelle du bouton de filtre dans le MENU burger, ou
            # il est desormais - une icone suffisait tant qu'il etait dans la barre de coin, mais
            # une entree de menu sans texte serait vide. _("Filter variables") est deja son
            # infobulle, et deja traduit ("Filtrer les variables") : rien a ajouter au catalogue.
            text=_("Filter variables"),''',
    ),
    # 9. Coin : le filtre part dans le menu burger, "Rechercher" et "Rafraichir" restent.
    (
        "le filtre part dans le menu burger",
        '''        for action in [
            self.search_action,
            self.filter_button,
            self.refresh_action,
        ]:
            self.add_corner_widget(action, before=self._options_button)''',
        '''        # SmartOS (3e passe, 26/07/2026) : le filtre part dans le menu burger, juste au-dessus
        # des exclusions qu'il commande. Le coin garde "Rechercher" et "Rafraichir".
        for action in [
            self.search_action,
            self.refresh_action,
        ]:
            self.add_corner_widget(action, before=self._options_button)''',
    ),
    # 10. Menu burger : le filtre en tete de la section des exclusions, qu'il commande.
    (
        "le filtre, juste au-dessus des cinq exclusions",
        '''        for item in [self.exclude_private_action,''',
        '''        # SmartOS (3e passe, 26/07/2026) : le filtre, juste au-dessus des cinq exclusions
        # qu'il grise ou degrise (cf. _enable_filter_actions).
        for item in [self.filter_button,
                     self.exclude_private_action,''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0).

    Le texte ANCIEN d'un bloc peut etre une chaine ou un TUPLE de chaines : c'est ce qui permet a un
    bloc de 2e passe de remplacer indifferemment le texte d'origine de Spyder (installation fraiche)
    ou celui qu'une passe precedente avait deja pose (installation existante), quand le second
    SUPPLANTE le premier au lieu de s'y ajouter. Exactement un des candidats doit matcher, une seule
    fois - sinon on echoue bruyamment sans rien ecrire.
    """
    applied = 0
    for marqueur, olds, new in pairs:
        if marqueur in source:
            continue  # bloc deja en place
        if isinstance(olds, str):
            olds = (olds,)
        # PREMIER candidat qui matche exactement une fois, les candidats etant donnes DU PLUS
        # SPECIFIQUE AU PLUS GENERAL. Ce n'est pas un detail : le texte pose par une passe
        # precedente CONTIENT en general le texte d'origine de Spyder (elle n'avait fait qu'y
        # ajouter des lignes), donc les deux matchent, et exiger un candidat unique echouerait.
        trouve = next((o for o in olds if source.count(o) == 1), None)
        if trouve is None:
            print(f"Aucun des {len(olds)} textes attendus n'est present exactement une fois dans "
                  f"{path} - le code amont a peut-etre ete restructure, patch {nom} non applique. "
                  f"Bloc:\n{olds[0][:80]}...", file=sys.stderr)
            return None, 0
        source = source.replace(trouve, new)
        applied += 1
    return source, applied


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers variableexplorer/widgets/main_widget.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Explorateur de variables non "
              "applique.", file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Explorateur de variables", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Explorateur de variables : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Explorateur de variables applique ({applied} bloc(s)) : les quatre actions "
          f"de la barre deplacees dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
